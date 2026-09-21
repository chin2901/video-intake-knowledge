"""
CLI Menu parsing utilities.

Provides functions for parsing user menu selections from command line input.
"""

from __future__ import annotations


def parse_menu_selection(selection: str) -> list[int] | bool:
    """
    Parse a menu selection string into a list of option indices (1-based).

    Supports formats:
    - Single number: "1" -> [1]
    - Multiple numbers: "1,3,5" or "1 3 5" -> [1, 3, 5]
    - "todo" or "todos" -> [1, 2, 3, 4, 5, 6] (all 6 options)
    - "6" -> [1, 2, 3, 4, 5, 6] (alias for all)
    - "0" or "cancelar" -> [0] (cancel signal)
    - Empty or invalid -> False

    Args:
        selection: Raw selection string from user input.

    Returns:
        List of selected option indices (1-based), or False if cancelled/invalid.
    """
    if not selection or selection.strip() == "":
        return False

    selection = selection.strip().lower()

    # Cancel cases
    if selection in ("0", "cancelar", "cancel", "c", "exit", "quit", "q"):
        return [0]

    # Select all cases (6 options)
    if selection in ("todo", "todos", "all", "*", "a", "6"):
        return [1, 2, 3, 4, 5, 6]

    # Split by comma or whitespace
    parts = []
    for part in selection.replace(",", " ").split():
        parts.append(part)

    result: list[int] = []

    for part in parts:
        try:
            num = int(part)
            if 1 <= num <= 6 and num not in result:
                result.append(num)
        except ValueError:
            continue

    return result if result else False


def format_menu_options(options: list[str], selected: list[int] | None = None) -> str:
    """
    Format menu options for display.

    Args:
        options: List of option descriptions.
        selected: List of currently selected indices (1-based).

    Returns:
        Formatted menu string.
    """
    selected_set = set(selected) if selected else set()
    lines = []
    for i, opt in enumerate(options, 1):
        prefix = "  "
        marker = "[x]" if i in selected_set else "[ ]"
        lines.append(f"{prefix}{i}. {marker} {opt}")
    return "\n".join(lines)
