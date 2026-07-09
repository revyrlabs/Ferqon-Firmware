# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2024-2026 Revyr Labs
"""
cmd_list.py
-----------
List command for ferqonfw CLI - list available platforms.
"""


from ferqonfw.board_loader import load_all_boards


def cmd_list(args) -> int:
    """List all available platforms."""
    boards = load_all_boards()

    if not boards:
        print("No boards found")
        return 1

    print("Available platforms:")
    for board_name in sorted(boards.keys()):
        print(f"  {board_name}")

    return 0
