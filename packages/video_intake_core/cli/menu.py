"""
CLI Menu parsing utilities.

Provides functions for parsing user menu selections from command line input.
"""

from __future__ import annotations


def parse_menu_selection(selection: str | None) -> list[int] | bool:
    """
    Parse a menu selection string into a list of option indices (1-based).

    Supports formats:
    - Single number: "1" -> [1]
    - Multiple numbers: "1,3,5" or "1 3 5" or "1;3;5" -> [1, 3, 5]
    - "todo", "todos", "all", "*", "a", "6" -> [1, 2, 3, 4, 5, 6] (all 6 options)
    - "0" or "cancelar" -> [0] (cancel signal)
    - Empty or invalid -> False

    Args:
        selection: Raw selection string from user input.

    Returns:
        List of selected option indices (1-based), or False if cancelled/invalid.
    """
    if not selection or str(selection).strip() == "":
        return [1, 2, 3, 4, 5, 6]

    raw = str(selection).strip().lower()

    # Cancel cases
    if raw in ("0", "cancelar", "cancel", "c", "exit", "quit", "q", "salir"):
        return [0]

    # Select all cases (6 options)
    if raw in ("todo", "todos", "all", "*", "a", "6", "todas", "todos lo anterior"):
        return [1, 2, 3, 4, 5, 6]

    result: list[int] = []

    seen: set[int] = set()
    for part in raw.replace(",", " ").split():
        part = part.strip()
        if part.isdigit():
            val = int(part)
            if val == 6:
                return [1, 2, 3, 4, 5, 6]
            if 1 <= val <= 5 and val not in seen:
                result.append(val)
                seen.add(val)
            elif val == 0:
                return [0]
    return sorted(result) if result else []


def parse_selection_to_set(selection: str | list[int] | set[int] | None) -> set[int]:
    """
    Authoritative parser converting user menu selections into active extraction operation sets.

    Converts option 6 or 'all'/'todo' into the active extraction layers {1, 2, 3, 4, 5}.
    Defaults to all active layers {1, 2, 3, 4, 5} on empty selection.
    """
    if selection is None or selection == "":
        return {1, 2, 3, 4, 5}

    if isinstance(selection, (set, list)):
        nums = {int(x) for x in selection if str(x).isdigit() or isinstance(x, (int, float))}
        if 6 in nums or nums == {1, 2, 3, 4, 5, 6}:
            return {1, 2, 3, 4, 5}
        valid = {n for n in nums if 1 <= n <= 5}
        return valid or {1, 2, 3, 4, 5}

    parsed = parse_menu_selection(str(selection))
    if not parsed or parsed == [0]:
        return set()

    nums = set(parsed)
    if 6 in nums or len(nums) >= 5:
        return {1, 2, 3, 4, 5}

    valid = {n for n in nums if 1 <= n <= 5}
    return valid or {1, 2, 3, 4, 5}


def parse_selections_as_strings(raw: str | None) -> set[str]:
    """Parse string selections returning set of string digits (e.g. {'1', '3', '5'})."""
    parsed = parse_menu_selection(raw)
    if not parsed or parsed == [0]:
        return set()
    return {str(x) for x in parsed}


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
