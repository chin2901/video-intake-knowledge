"""
Models command for video-intake-knowledge.

Manages model listing, installation, and verification.
"""

from __future__ import annotations

import argparse
import logging

logger = logging.getLogger(__name__)


def models_list_command(args: argparse.Namespace) -> int:
    """List available models."""
    print("Available models (built-in):")
    print("  Transcription:")
    print("    - whisper (tiny, base, small, medium, large)")
    print("  Visual:")
    print("    - clip (ViT-B/32, ViT-L/14)")
    print("  OCR:")
    print("    - tesseract")
    return 0


def models_install_command(args: argparse.Namespace) -> int:
    """Install a model."""
    model_name = args.model
    print(f"Installing model: {model_name}")
    print("Model installation feature not yet implemented.")
    return 0


def models_verify_command(args: argparse.Namespace) -> int:
    """Verify installed models."""
    print("Verifying installed models...")
    print("Model verification feature not yet implemented.")
    return 0


def models_remove_command(args: argparse.Namespace) -> int:
    """Remove a model."""
    model_name = args.model
    if not args.yes:
        print(f"Remove model '{model_name}'? Use --yes to confirm.")
        return 1
    print(f"Removing model: {model_name}")
    print("Model removal feature not yet implemented.")
    return 0


def models_command(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the models subcommand to the parser."""
    parser = subparsers.add_parser("models", help="Manage models")
    models_sub = parser.add_subparsers(dest="model_action", required=True)

    list_p = models_sub.add_parser("list", help="List available models")
    list_p.set_defaults(func=models_list_command)

    install_p = models_sub.add_parser("install", help="Install a model")
    install_p.add_argument("model", help="Model name to install")
    install_p.set_defaults(func=models_install_command)

    verify_p = models_sub.add_parser("verify", help="Verify installed models")
    verify_p.set_defaults(func=models_verify_command)

    remove_p = models_sub.add_parser("remove", help="Remove a model")
    remove_p.add_argument("model", help="Model name to remove")
    remove_p.add_argument(
        "--yes",
        action="store_true",
        help="Confirm without prompting",
    )
    remove_p.set_defaults(func=models_remove_command)

    return parser
