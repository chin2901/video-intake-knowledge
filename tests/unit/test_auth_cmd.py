"""
Unit tests for the assisted authentication CLI command (video-intake auth).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from video_intake_core.cli import build_parser
from video_intake_core.cli.auth import (
    auth_command,
    configure_auth,
    detect_browser_cookies,
    run_auth,
    validate_cookies_file,
)
from video_intake_core.cli.auth import (
    test_auth_access as auth_test_access,
)
from video_intake_core.cli.menu import format_auth_menu


class TestAuthCLIUnit:
    """Unit tests for assisted authentication command and detection."""

    def test_detect_browser_cookies_structure(self):
        """detect_browser_cookies returns structured info for all supported browsers."""
        detected = detect_browser_cookies()
        assert "chrome" in detected
        assert "chromium" in detected
        assert "firefox" in detected
        assert "brave" in detected
        assert "edge" in detected

        for _b_name, b_info in detected.items():
            assert "installed" in b_info
            assert "display_name" in b_info
            assert "profiles" in b_info
            assert "has_cookies" in b_info
            assert "cookie_files_count" in b_info

    def test_validate_cookies_file_valid_netscape(self, tmp_path: Path):
        """validate_cookies_file correctly parses Netscape format and detects domains."""
        cookies_txt = tmp_path / "valid_cookies.txt"
        cookies_txt.write_text(
            "# Netscape HTTP Cookie File\n"
            "# https://curl.se/docs/http-cookies.html\n"
            ".youtube.com\tTRUE\t/\tTRUE\t2147483647\tSID\tsample_session_id_123\n"
            ".instagram.com\tTRUE\t/\tTRUE\t2147483647\tsessionid\tsample_ig_token_456\n"
            ".facebook.com\tTRUE\t/\tTRUE\t2147483647\tc_user\t10001234567\n",
            encoding="utf-8",
        )

        res = validate_cookies_file(cookies_txt)
        assert res["valid"] is True
        assert res["is_netscape"] is True
        assert res["cookie_count"] == 3
        assert "youtube.com" in res["domains"]
        assert "instagram.com" in res["domains"]
        assert "facebook.com" in res["domains"]

    def test_validate_cookies_file_httponly_and_whitespace(self, tmp_path: Path):
        """validate_cookies_file handles #HttpOnly_ cookies and whitespace-aligned columns."""
        cookies_txt = tmp_path / "httponly_cookies.txt"
        cookies_txt.write_text(
            "# Netscape HTTP Cookie File\n"
            "#HttpOnly_.youtube.com\tTRUE\t/\tTRUE\t2147483647\tSID\tsecure_session_123\n"
            "#HttpOnly_.google.com   TRUE   /   TRUE   2147483647   HSID   sample_token_456\n",
            encoding="utf-8",
        )
        res = validate_cookies_file(cookies_txt)
        assert res["valid"] is True
        assert res["cookie_count"] == 2
        assert "youtube.com" in res["domains"]
        assert "google.com" in res["domains"]

    def test_validate_cookies_file_missing_and_empty(self, tmp_path: Path):
        """validate_cookies_file reports failure for missing or empty files."""
        # Missing file
        missing_res = validate_cookies_file(tmp_path / "missing.txt")
        assert missing_res["valid"] is False
        assert "no existe" in missing_res["error"]

        # Empty file
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")
        empty_res = validate_cookies_file(empty_file)
        assert empty_res["valid"] is False
        assert "vacío" in empty_res["error"]

    def test_test_auth_access_with_cookies_file(self, tmp_path: Path):
        """test_auth_access validates a provided cookies file when no URL is given."""
        cookies_txt = tmp_path / "cookies.txt"
        cookies_txt.write_text(
            "# Netscape HTTP Cookie File\n"
            ".youtube.com\tTRUE\t/\tTRUE\t2147483647\tLOGIN_INFO\taf938210\n",
            encoding="utf-8",
        )
        res = auth_test_access(cookies_path=str(cookies_txt))
        assert res["status"] == "pass"
        assert res["authenticated"] is True
        assert res["details"]["cookie_count"] == 1

    def test_test_auth_access_url_success(self):
        """test_auth_access with URL reports success when yt-dlp metadata succeeds."""
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = json.dumps({"title": "Private Reel", "extractor": "instagram"})
        mock_res.stderr = ""

        with patch("subprocess.run", return_value=mock_res):
            res = auth_test_access(url="https://instagram.com/reel/123", browser="chrome")
            assert res["status"] == "pass"
            assert res["authenticated"] is True
            assert res["title"] == "Private Reel"
            assert "Acceso verificado exitosamente" in res["message"]

    def test_test_auth_access_url_login_required(self):
        """test_auth_access detects login required / age restricted errors."""
        mock_res = MagicMock()
        mock_res.returncode = 1
        mock_res.stdout = ""
        mock_res.stderr = (
            "ERROR: Sign in to confirm your age. This video may be inappropriate for some users."
        )

        with patch("subprocess.run", return_value=mock_res):
            res = auth_test_access(url="https://youtube.com/watch?v=restricted", browser="chrome")
            assert res["status"] == "fail"
            assert res["authenticated"] is False
            assert res.get("login_required") is True

    def test_configure_auth_set_and_clear(self, tmp_path: Path):
        """configure_auth updates YAML config and allows clearing."""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(
            "acquisition:\n  auth:\n    cookies_from_browser: ''\n    cookies_path: ''\n",
            encoding="utf-8",
        )

        # Set browser
        res1 = configure_auth(browser="firefox", config_path=str(cfg_file))
        assert res1["success"] is True
        assert res1["auth"]["cookies_from_browser"] == "firefox"

        # Set cookies path
        res2 = configure_auth(cookies_path="/tmp/my_cookies.txt", config_path=str(cfg_file))
        assert res2["success"] is True
        assert res2["auth"]["cookies_path"] == "/tmp/my_cookies.txt"

        # Clear
        res3 = configure_auth(clear=True, config_path=str(cfg_file))
        assert res3["success"] is True
        assert res3["auth"]["cookies_from_browser"] == ""
        assert res3["auth"]["cookies_path"] == ""

    def test_run_auth_cli_status(self, capsys: pytest.CaptureFixture):
        """run_auth 'status' prints active configuration and available browsers."""
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        auth_command(sub)

        args = parser.parse_args(["auth", "status"])
        ret = run_auth(args)
        assert ret == 0

        captured = capsys.readouterr()
        assert "video-intake auth" in captured.out
        assert "Configuración activa:" in captured.out

    def test_run_auth_cli_detect_json(self, capsys: pytest.CaptureFixture):
        """run_auth 'detect --json' outputs valid JSON structure."""
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        auth_command(sub)

        args = parser.parse_args(["auth", "detect"])
        args.json = True
        ret = run_auth(args)
        assert ret == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "chrome" in data
        assert "firefox" in data

    def test_run_auth_cli_set_browser_and_clear(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ):
        """run_auth set-browser and clear execute cleanly via CLI."""
        cfg_file = tmp_path / "cfg.yaml"
        cfg_file.write_text(
            "acquisition:\n  auth:\n    cookies_from_browser: ''\n", encoding="utf-8"
        )

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        auth_command(sub)

        # Set browser
        args_set = parser.parse_args(["auth", "set-browser", "chrome"])
        args_set.config = str(cfg_file)
        ret_set = run_auth(args_set)
        assert ret_set == 0

        # Clear
        args_clear = parser.parse_args(["auth", "clear"])
        args_clear.config = str(cfg_file)
        ret_clear = run_auth(args_clear)
        assert ret_clear == 0

    def test_format_auth_menu(self):
        """format_auth_menu displays options for interactive CLI menu."""
        menu = format_auth_menu()
        assert "Menú de Autenticación Asistida" in menu
        assert "Detectar navegadores instalados" in menu
        assert "Configurar cookies desde navegador" in menu

    def test_cli_build_parser_includes_auth(self):
        """build_parser registers the 'auth' command and parses arguments."""
        parser = build_parser()
        args = parser.parse_args(["auth", "status"])
        assert args.command == "auth"
        assert args.action == "status"

        args_test = parser.parse_args(
            ["auth", "test", "--url", "https://youtube.com/watch?v=123", "-b", "chrome"]
        )
        assert args_test.command == "auth"
        assert args_test.action == "test"
        assert args_test.url == "https://youtube.com/watch?v=123"
        assert args_test.browser == "chrome"

    def test_run_auth_menu_action(self):
        """run_auth 'menu' renders options and executes chosen sub-action or cancellation."""
        parser = build_parser()
        args = parser.parse_args(["auth", "menu"])

        # Test cancel option "0"
        with patch("builtins.input", return_value="0"):
            ret = run_auth(args)
            assert ret == 0

        # Test selecting option "1" (status)
        with patch("builtins.input", return_value="1"):
            ret = run_auth(args)
            assert ret == 0

    def test_cli_build_parser_interactive_flag(self):
        """build_parser recognizes --interactive and -i flags for auth."""
        parser = build_parser()
        args1 = parser.parse_args(["auth", "--interactive"])
        assert args1.interactive is True

        args2 = parser.parse_args(["auth", "-i"])
        assert args2.interactive is True
