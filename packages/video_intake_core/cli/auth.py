"""
CLI de Autenticación Asistida (video-intake auth).

Permite detectar navegadores con perfiles de cookies (Chrome, Chromium, Firefox, Brave, Edge),
verificar acceso o testear URLs restringidas, y configurar de forma amigable
cookies_from_browser o cookies_path.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Navegadores soportados y ubicaciones de perfiles/cookies por plataforma
SUPPORTED_BROWSERS: dict[str, dict[str, Any]] = {
    "chrome": {
        "display_name": "Google Chrome",
        "binaries": ["google-chrome", "google-chrome-stable", "chrome"],
        "paths": {
            "linux": [
                Path("~/.config/google-chrome"),
                Path("~/snap/google-chrome/common/google-chrome"),
                Path("~/.var/app/com.google.Chrome/config/google-chrome"),
            ],
            "darwin": [
                Path("~/Library/Application Support/Google/Chrome"),
            ],
            "win32": [
                Path("~/AppData/Local/Google/Chrome/User Data"),
            ],
        },
        "cookie_rel_paths": [
            "Default/Cookies",
            "Default/Network/Cookies",
            "Profile */Cookies",
            "Profile */Network/Cookies",
        ],
    },
    "chromium": {
        "display_name": "Chromium",
        "binaries": ["chromium", "chromium-browser"],
        "paths": {
            "linux": [
                Path("~/.config/chromium"),
                Path("~/snap/chromium/common/chromium"),
                Path("~/.var/app/org.chromium.Chromium/config/chromium"),
            ],
            "darwin": [
                Path("~/Library/Application Support/Chromium"),
            ],
            "win32": [
                Path("~/AppData/Local/Chromium/User Data"),
            ],
        },
        "cookie_rel_paths": [
            "Default/Cookies",
            "Default/Network/Cookies",
            "Profile */Cookies",
            "Profile */Network/Cookies",
        ],
    },
    "firefox": {
        "display_name": "Mozilla Firefox",
        "binaries": ["firefox", "firefox-esr"],
        "paths": {
            "linux": [
                Path("~/.mozilla/firefox"),
                Path("~/snap/firefox/common/.mozilla/firefox"),
                Path("~/.var/app/org.mozilla.firefox/.mozilla/firefox"),
            ],
            "darwin": [
                Path("~/Library/Application Support/Firefox/Profiles"),
            ],
            "win32": [
                Path("~/AppData/Roaming/Mozilla/Firefox/Profiles"),
            ],
        },
        "cookie_rel_paths": [
            "*.default*/cookies.sqlite",
            "*.default-release*/cookies.sqlite",
            "cookies.sqlite",
        ],
    },
    "brave": {
        "display_name": "Brave Browser",
        "binaries": ["brave-browser", "brave"],
        "paths": {
            "linux": [
                Path("~/.config/BraveSoftware/Brave-Browser"),
                Path("~/.var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser"),
            ],
            "darwin": [
                Path("~/Library/Application Support/BraveSoftware/Brave-Browser"),
            ],
            "win32": [
                Path("~/AppData/Local/BraveSoftware/Brave-Browser/User Data"),
            ],
        },
        "cookie_rel_paths": [
            "Default/Cookies",
            "Default/Network/Cookies",
            "Profile */Cookies",
            "Profile */Network/Cookies",
        ],
    },
    "edge": {
        "display_name": "Microsoft Edge",
        "binaries": ["microsoft-edge", "microsoft-edge-stable", "edge"],
        "paths": {
            "linux": [
                Path("~/.config/microsoft-edge"),
                Path("~/.var/app/com.microsoft.Edge/config/microsoft-edge"),
            ],
            "darwin": [
                Path("~/Library/Application Support/Microsoft Edge"),
            ],
            "win32": [
                Path("~/AppData/Local/Microsoft/Edge/User Data"),
            ],
        },
        "cookie_rel_paths": [
            "Default/Cookies",
            "Default/Network/Cookies",
            "Profile */Cookies",
            "Profile */Network/Cookies",
        ],
    },
}


def detect_browser_cookies() -> dict[str, Any]:
    """Detecta navegadores instalados y busca perfiles de cookies existentes."""
    plat = sys.platform
    plat_key = "darwin" if plat == "darwin" else ("win32" if plat == "win32" else "linux")

    detected: dict[str, Any] = {}

    for b_id, b_meta in SUPPORTED_BROWSERS.items():
        # 1. Comprobar ejecutable en PATH
        executable = None
        for b_bin in b_meta["binaries"]:
            found_bin = shutil.which(b_bin)
            if found_bin:
                executable = found_bin
                break

        # 2. Comprobar directorios de configuración
        config_dir = None
        candidate_paths = b_meta["paths"].get(plat_key, [])
        for p in candidate_paths:
            expanded = p.expanduser().resolve()
            if expanded.exists():
                config_dir = expanded
                break

        # 3. Detectar perfiles y archivos de cookies
        profiles: list[str] = []
        cookie_files: list[str] = []

        if config_dir and config_dir.exists():
            if b_id == "firefox":
                # Perfiles Firefox
                profiles_ini = config_dir / "profiles.ini"
                if profiles_ini.exists():
                    try:
                        content = profiles_ini.read_text(encoding="utf-8", errors="ignore")
                        for line in content.splitlines():
                            if line.strip().startswith("Name="):
                                p_name = line.split("=", 1)[1].strip()
                                if p_name not in profiles:
                                    profiles.append(p_name)
                    except Exception:
                        pass

                # Buscar cookies.sqlite en subdirectorios
                for c_file in config_dir.glob("**/cookies.sqlite"):
                    if c_file.is_file() and c_file.stat().st_size > 0:
                        cookie_files.append(str(c_file))
                        parent_name = c_file.parent.name
                        if parent_name not in profiles:
                            profiles.append(parent_name)
            else:
                # Perfiles Chromium (Chrome, Chromium, Brave, Edge)
                # Default profile
                def_profile = config_dir / "Default"
                if def_profile.exists():
                    profiles.append("Default")

                # Otros perfiles numerados
                for prof_dir in config_dir.glob("Profile *"):
                    if prof_dir.is_dir():
                        profiles.append(prof_dir.name)

                # Comprobar base de datos de cookies
                for pattern in [
                    "Default/Cookies",
                    "Default/Network/Cookies",
                    "Profile */Cookies",
                    "Profile */Network/Cookies",
                ]:
                    for c_file in config_dir.glob(pattern):
                        if c_file.is_file() and c_file.stat().st_size > 0:
                            cookie_files.append(str(c_file))

        installed = bool(executable or config_dir)
        has_cookies = bool(cookie_files)

        detected[b_id] = {
            "name": b_id,
            "display_name": b_meta["display_name"],
            "installed": installed,
            "executable": executable,
            "config_dir": str(config_dir) if config_dir else None,
            "profiles": sorted(set(profiles)),
            "has_cookies": has_cookies,
            "cookie_files_count": len(cookie_files),
            "cookie_files": cookie_files[:5],  # Muestra primeros 5
        }

    return detected


def validate_cookies_file(cookies_path: str | Path) -> dict[str, Any]:
    """Valida un archivo de cookies en formato Netscape."""
    path = Path(cookies_path).expanduser().resolve()
    if not path.exists():
        return {
            "valid": False,
            "path": str(path),
            "error": "El archivo de cookies no existe",
            "domains": [],
            "cookie_count": 0,
        }

    if path.stat().st_size == 0:
        return {
            "valid": False,
            "path": str(path),
            "error": "El archivo de cookies está vacío",
            "domains": [],
            "cookie_count": 0,
        }

    domains: set[str] = set()
    count = 0
    is_netscape = False

    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line_s = line.strip()
                if not line_s:
                    continue
                if line_s.startswith("# Netscape") or line_s.startswith("# HTTP Cookie File"):
                    is_netscape = True
                    continue
                if line_s.startswith("#HttpOnly_"):
                    pass
                elif line_s.startswith("#"):
                    continue

                parts = line_s.split("\t")
                if len(parts) < 7:
                    import re

                    parts = re.split(r"\s+", line_s)
                if len(parts) >= 7:
                    count += 1
                    raw_domain = parts[0]
                    if raw_domain.startswith("#HttpOnly_"):
                        raw_domain = raw_domain[len("#HttpOnly_") :]
                    domain = raw_domain.lstrip(".")
                    if domain:
                        domains.add(domain)
    except Exception as e:
        return {
            "valid": False,
            "path": str(path),
            "error": f"Error leyendo archivo de cookies: {e}",
            "domains": [],
            "cookie_count": 0,
        }

    # Si tiene entradas tabulares válidas se considera válido aunque no tenga cabecera
    valid = count > 0 or is_netscape
    return {
        "valid": valid,
        "path": str(path),
        "is_netscape": is_netscape,
        "cookie_count": count,
        "domains": sorted(domains)[:15],
        "size_bytes": path.stat().st_size,
    }


def test_auth_access(
    url: str | None = None,
    browser: str | None = None,
    cookies_path: str | None = None,
) -> dict[str, Any]:
    """Testea acceso autenticado a una URL o valida el origen de cookies configurado."""
    # 1. Si no hay URL, validar las cookies disponibles
    if not url:
        browsers_detected = detect_browser_cookies()
        if browser:
            b_info = browsers_detected.get(browser.lower())
            if not b_info or not b_info["installed"]:
                return {
                    "status": "fail",
                    "authenticated": False,
                    "target": f"browser:{browser}",
                    "message": f"El navegador '{browser}' no está instalado o no se detectó.",
                }
            if not b_info["has_cookies"]:
                return {
                    "status": "warn",
                    "authenticated": False,
                    "target": f"browser:{browser}",
                    "message": f"Navegador '{browser}' detectado, pero no se encontraron bases de cookies activas.",
                }
            return {
                "status": "pass",
                "authenticated": True,
                "target": f"browser:{browser}",
                "message": f"Navegador '{b_info['display_name']}' disponible con {b_info['cookie_files_count']} almacén(es) de cookies.",
                "details": b_info,
            }

        if cookies_path:
            c_val = validate_cookies_file(cookies_path)
            if not c_val["valid"]:
                return {
                    "status": "fail",
                    "authenticated": False,
                    "target": f"file:{cookies_path}",
                    "message": c_val.get("error", "Archivo de cookies inválido"),
                }
            return {
                "status": "pass",
                "authenticated": True,
                "target": f"file:{cookies_path}",
                "message": f"Archivo de cookies válido ({c_val['cookie_count']} cookies encontradas).",
                "details": c_val,
            }

        # Comprobar el entorno global o la configuración actual
        auth_cfg = _get_current_auth_config()
        configured_browser = auth_cfg.get("cookies_from_browser")
        configured_path = auth_cfg.get("cookies_path")

        if configured_browser:
            return test_auth_access(browser=configured_browser)
        if configured_path:
            return test_auth_access(cookies_path=configured_path)

        # Sugerir navegador disponible
        for b_name, b_info in browsers_detected.items():
            if b_info["has_cookies"]:
                return {
                    "status": "info",
                    "authenticated": False,
                    "message": f"No hay autenticación configurada. Se detectaron cookies en {b_info['display_name']} ('{b_name}').",
                    "suggested_browser": b_name,
                }

        return {
            "status": "warn",
            "authenticated": False,
            "message": "No hay cookies configuradas ni perfiles de navegador detectados con sesión activa.",
        }

    # 2. Si se proporciona URL, testear acceso real con yt-dlp
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--dump-single-json",
        "--no-playlist",
    ]

    auth_source = "ninguna"
    if browser:
        cmd += ["--cookies-from-browser", browser]
        auth_source = f"browser:{browser}"
    elif cookies_path and Path(cookies_path).expanduser().exists():
        cmd += ["--cookies", str(Path(cookies_path).expanduser())]
        auth_source = f"file:{cookies_path}"
    else:
        # Usar la configuración actual
        auth_cfg = _get_current_auth_config()
        if auth_cfg.get("cookies_from_browser"):
            cmd += ["--cookies-from-browser", auth_cfg["cookies_from_browser"]]
            auth_source = f"browser:{auth_cfg['cookies_from_browser']}"
        elif auth_cfg.get("cookies_path") and Path(auth_cfg["cookies_path"]).expanduser().exists():
            cmd += ["--cookies", str(Path(auth_cfg["cookies_path"]).expanduser())]
            auth_source = f"file:{auth_cfg['cookies_path']}"

    cmd.append(url)

    try:
        proc_env = os.environ.copy()
        xdg_override = os.environ.get("VITK_XDG_CONFIG_HOME")
        if xdg_override:
            proc_env["XDG_CONFIG_HOME"] = xdg_override

        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=20,
            env=proc_env,
        )
        if res.returncode == 0:
            info = {}
            with __import__("contextlib").suppress(Exception):
                info = json.loads(res.stdout)
            title = info.get("title", "Desconocido")
            extractor = info.get("extractor", "N/A")
            return {
                "status": "pass",
                "authenticated": True,
                "url": url,
                "auth_source": auth_source,
                "title": title,
                "extractor": extractor,
                "message": f"Acceso verificado exitosamente a '{title}' ({extractor}).",
            }
        else:
            err = res.stderr or res.stdout
            is_login_req = any(
                k in err.lower()
                for k in [
                    "login",
                    "sign in",
                    "private",
                    "inicia sesión",
                    "restricted",
                    "age-restricted",
                    "403",
                ]
            )
            return {
                "status": "fail",
                "authenticated": False,
                "url": url,
                "auth_source": auth_source,
                "login_required": is_login_req,
                "message": "Fallo de autenticación o acceso denegado."
                if is_login_req
                else f"Error al acceder a la URL: {err.strip()[:200]}",
            }
    except subprocess.TimeoutExpired:
        return {
            "status": "warn",
            "authenticated": False,
            "url": url,
            "auth_source": auth_source,
            "message": "Tiempo de espera agotado al consultar la URL con yt-dlp.",
        }
    except Exception as e:
        return {
            "status": "fail",
            "authenticated": False,
            "url": url,
            "auth_source": auth_source,
            "message": f"Error ejecutando prueba de acceso: {e}",
        }


def _get_current_auth_config(config_path: str | None = None) -> dict[str, Any]:
    """Lee la configuración actual de auth."""
    from video_intake_core.policies import PolicyResolver

    cand_paths = (
        [Path(config_path)]
        if config_path
        else [
            Path("config/default.yaml"),
            Path(__file__).resolve().parents[3] / "config" / "default.yaml",
        ]
    )
    for cand in cand_paths:
        if cand.exists():
            try:
                resolver = PolicyResolver(config_path=str(cand))
                return resolver.get_acquisition_auth()
            except Exception:
                pass
    return {"cookies_from_browser": "", "cookies_path": ""}


def configure_auth(
    browser: str | None = None,
    cookies_path: str | None = None,
    clear: bool = False,
    config_path: str | None = None,
) -> dict[str, Any]:
    """Actualiza la configuración de autenticación en config/default.yaml."""
    target_path = Path(config_path or "config/default.yaml").resolve()
    if not target_path.exists():
        # Fallback a ubicación relativa al paquete
        cand = Path(__file__).resolve().parents[3] / "config" / "default.yaml"
        if cand.exists():
            target_path = cand

    if not target_path.exists():
        return {"success": False, "error": f"Archivo de configuración no encontrado: {target_path}"}

    import yaml

    try:
        with open(target_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

        if "acquisition" not in cfg:
            cfg["acquisition"] = {}
        if "auth" not in cfg["acquisition"]:
            cfg["acquisition"]["auth"] = {}

        if clear:
            cfg["acquisition"]["auth"]["cookies_from_browser"] = ""
            cfg["acquisition"]["auth"]["cookies_path"] = ""
            action_desc = "Configuración de autenticación limpiada."
        else:
            if browser is not None:
                cfg["acquisition"]["auth"]["cookies_from_browser"] = browser.strip().lower()
            if cookies_path is not None:
                cfg["acquisition"]["auth"]["cookies_path"] = str(cookies_path).strip()
            action_desc = f"Configuración guardada (browser='{cfg['acquisition']['auth'].get('cookies_from_browser')}', path='{cfg['acquisition']['auth'].get('cookies_path')}')."

        with open(target_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        return {
            "success": True,
            "message": action_desc,
            "config_file": str(target_path),
            "auth": cfg["acquisition"]["auth"],
        }
    except Exception as e:
        return {"success": False, "error": f"Error modificando configuración: {e}"}


# ============================================================================
# CLI Command Execution
# ============================================================================


def run_auth(args: argparse.Namespace) -> int:
    """Punto de entrada para el comando video-intake auth."""
    action = getattr(args, "action", None) or "status"
    is_json = getattr(args, "json", False)

    # Subcomando: set-browser
    if action == "set-browser":
        b_val = getattr(args, "value", None) or getattr(args, "browser", None)
        if not b_val:
            print("Error: Se requiere especificar el nombre del navegador.", file=sys.stderr)
            return 1
        res = configure_auth(browser=b_val, config_path=getattr(args, "config", None))
        if is_json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            if res["success"]:
                print(f"✓ {res['message']}")
            else:
                print(f"✗ {res['error']}", file=sys.stderr)
        return 0 if res["success"] else 1

    # Subcomando: set-cookies
    if action == "set-cookies":
        c_val = getattr(args, "value", None) or getattr(args, "cookies", None)
        if not c_val:
            print("Error: Se requiere especificar la ruta al archivo de cookies.", file=sys.stderr)
            return 1
        res = configure_auth(cookies_path=c_val, config_path=getattr(args, "config", None))
        if is_json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            if res["success"]:
                print(f"✓ {res['message']}")
            else:
                print(f"✗ {res['error']}", file=sys.stderr)
        return 0 if res["success"] else 1

    # Subcomando: clear
    if action == "clear":
        res = configure_auth(clear=True, config_path=getattr(args, "config", None))
        if is_json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"✓ {res['message']}")
        return 0 if res["success"] else 1

    # Subcomando: detect
    if action == "detect":
        detected = detect_browser_cookies()
        if is_json:
            print(json.dumps(detected, indent=2, ensure_ascii=False))
            return 0

        print("=== Navegadores y Perfiles de Cookies Detectados ===\n")
        for b_id, b_info in detected.items():
            status_icon = "✓" if b_info["installed"] else "·"
            cookies_icon = "🍪 Con cookies" if b_info["has_cookies"] else "sin cookies detectadas"
            exec_str = f" ({b_info['executable']})" if b_info["executable"] else ""
            print(f"  {status_icon} {b_info['display_name']} [{b_id}]{exec_str}")
            if b_info["installed"]:
                print(f"     Directorio: {b_info['config_dir']}")
                print(f"     Estado: {cookies_icon} ({b_info['cookie_files_count']} almacenes)")
                if b_info["profiles"]:
                    print(f"     Perfiles: {', '.join(b_info['profiles'])}")
            print()
        return 0

    # Subcomando: test
    if action == "test":
        url = getattr(args, "url", None)
        browser = getattr(args, "browser", None)
        cookies = getattr(args, "cookies", None)
        res = test_auth_access(url=url, browser=browser, cookies_path=cookies)
        if is_json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            icon = {"pass": "✓", "fail": "✗", "warn": "⚠", "info": "ℹ"}.get(res["status"], "·")
            print("=== Prueba de Autenticación ===")
            print(f"  {icon} {res['message']}")
            if res.get("title"):
                print(f"  Vídeo detectado: {res['title']}")
            if res.get("details"):
                print(f"  Detalles: {res['details']}")
        return 0 if res["status"] in ("pass", "info") else 1

    # Subcomando: interactive / menu
    if action in ("interactive", "menu") or getattr(args, "interactive", False):
        from video_intake_core.cli.menu import format_auth_menu

        detected = detect_browser_cookies()
        print(format_auth_menu(detected))
        print("\nSelecciona una opción (0 para salir):")
        try:
            choice = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nOperación cancelada.")
            return 0

        if not choice or choice in ("0", "q", "exit", "cancelar"):
            print("Operación cancelada.")
            return 0

        if choice == "1":
            args.action = "status"
            return run_auth(args)
        elif choice == "2":
            args.action = "detect"
            return run_auth(args)
        elif choice == "3":
            print("\nNavegadores disponibles:")
            for b_name, b_data in detected.items():
                cookie_tag = " (con cookies)" if b_data["has_cookies"] else ""
                inst_tag = " [instalado]" if b_data["installed"] else ""
                print(f"  - {b_name}{inst_tag}{cookie_tag}")
            try:
                selected_browser = input("Escribe el nombre del navegador: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                return 0
            if selected_browser:
                args.action = "set-browser"
                args.value = selected_browser
                return run_auth(args)
            return 0
        elif choice == "4":
            try:
                c_path = input("Ruta al archivo de cookies (Netscape format): ").strip()
            except (EOFError, KeyboardInterrupt):
                return 0
            if c_path:
                args.action = "set-cookies"
                args.value = c_path
                return run_auth(args)
            return 0
        elif choice == "5":
            try:
                t_url = input("URL restringida a testear: ").strip()
            except (EOFError, KeyboardInterrupt):
                return 0
            if t_url:
                args.action = "test"
                args.url = t_url
                return run_auth(args)
            return 0
        elif choice == "6":
            args.action = "clear"
            return run_auth(args)
        else:
            print(f"Opción desconocida: '{choice}'")
            return 1

    # Subcomando: status (predeterminado)
    auth_cfg = _get_current_auth_config(getattr(args, "config", None))
    detected = detect_browser_cookies()

    active_browser = auth_cfg.get("cookies_from_browser")
    active_path = auth_cfg.get("cookies_path")
    env_browser = os.environ.get("VITK_COOKIES_FROM_BROWSER", "")
    env_cookies = os.environ.get("VITK_COOKIES", "")

    status_data = {
        "configured_browser": active_browser,
        "configured_cookies_path": active_path,
        "env_override_browser": env_browser,
        "env_override_cookies": env_cookies,
        "detected_browsers": detected,
    }

    if is_json:
        print(json.dumps(status_data, indent=2, ensure_ascii=False))
        return 0

    print("=== video-intake auth — Autenticación Asistida ===\n")
    print("Configuración activa:")
    print(f"  - cookies_from_browser: '{active_browser or '(desactivado)'}'")
    print(f"  - cookies_path:         '{active_path or '(desactivado)'}'")
    if env_browser or env_cookies:
        print(
            f"  - Variables de entorno: VITK_COOKIES_FROM_BROWSER='{env_browser}', VITK_COOKIES='{env_cookies}'"
        )

    print("\nNavegadores instalados con cookies disponibles:")
    found_any = False
    for b_id, b_info in detected.items():
        if b_info["installed"]:
            cookie_tag = "🍪 DISPONIBLE" if b_info["has_cookies"] else "sin sesión"
            is_active = " [ACTIVO]" if b_id == (env_browser or active_browser) else ""
            print(f"  · {b_info['display_name']} ({b_id}): {cookie_tag}{is_active}")
            found_any = True

    if not found_any:
        print("  · No se detectaron navegadores en rutas estándar.")

    print("\nComandos útiles:")
    print("  video-intake auth menu                # Menú interactivo asistido")
    print("  video-intake auth detect              # Diagnostica perfiles y rutas")
    print("  video-intake auth set-browser chrome  # Configura Chrome para cookies")
    print("  video-intake auth set-cookies path    # Configura archivo Netscape")
    print("  video-intake auth test --url <URL>    # Comprueba acceso a un vídeo")
    print("  video-intake auth clear               # Desactiva cookies")
    return 0


def auth_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Registra el subcomando auth en el CLI."""
    auth_p = subparsers.add_parser(
        "auth",
        help="Gestión y diagnóstico de autenticación asistida (cookies de navegador y archivos).",
    )
    auth_p.add_argument(
        "action",
        nargs="?",
        default="status",
        choices=[
            "status",
            "detect",
            "test",
            "set-browser",
            "set-cookies",
            "clear",
            "interactive",
            "menu",
        ],
        help="Acción a realizar: status (default), detect, test, set-browser, set-cookies, clear, menu.",
    )
    auth_p.add_argument(
        "value",
        nargs="?",
        default=None,
        help="Valor para set-browser (ej. 'chrome') o set-cookies (ej. 'cookies.txt').",
    )
    auth_p.add_argument(
        "--browser",
        "-b",
        type=str,
        default=None,
        help="Navegador a utilizar (chrome, chromium, firefox, brave, edge).",
    )
    auth_p.add_argument(
        "--cookies",
        "-c",
        type=str,
        default=None,
        help="Ruta a archivo de cookies en formato Netscape.",
    )
    auth_p.add_argument(
        "--url",
        "-u",
        type=str,
        default=None,
        help="URL a testear para comprobar acceso autenticado.",
    )
    auth_p.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        default=False,
        help="Iniciar menú interactivo de configuración y prueba de autenticación.",
    )
    auth_p.set_defaults(func=run_auth)
    return auth_p
