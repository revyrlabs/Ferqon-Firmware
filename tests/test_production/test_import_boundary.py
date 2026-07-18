#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
test_import_boundary.py
-----------------------
Tests that production CLI modules can be imported without any development-only
modules (ferqon_emulator, ferqon_selftest, device_config, device_discovery)
available on the path.

This proves the production CLI is self-contained and does not accidentally
depend on test, backend, or hardware-SDK code.
"""

import sys
import importlib
from pathlib import Path

import pytest

# Development-only modules that must NOT be importable by production CLI
DEV_ONLY_MODULES = [
    "ferqon_emulator",
    "ferqon_selftest",
    "device_config",
    "device_discovery",
]


@pytest.fixture
def clean_production_import():
    """Set up a clean import environment where dev-only modules are blocked."""
    tools_dir = Path(__file__).resolve().parent.parent.parent / "tools"

    # Save and clear sys.modules for ferqonfw
    saved_modules = dict(sys.modules)
    for key in list(sys.modules.keys()):
        if key.startswith("ferqonfw") or key in DEV_ONLY_MODULES:
            del sys.modules[key]

    # Insert a meta-path blocker for dev-only modules
    class Blocker:
        def find_spec(self, name, path=None, target=None):
            if name in DEV_ONLY_MODULES:
                raise ImportError(f"BLOCKED (dev-only): {name}")
            return None

    blocker = Blocker()
    sys.meta_path.insert(0, blocker)

    # Add tools to path
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))

    yield

    # Restore
    sys.meta_path.remove(blocker)
    sys.modules.clear()
    sys.modules.update(saved_modules)


class TestProductionImportBoundary:
    """Verify that production CLI modules import without dev-only dependencies."""

    PRODUCTION_MODULES = [
        "ferqonfw",
        "ferqonfw.main",
        "ferqonfw.protocol",
        "ferqonfw.board_loader",
        "ferqonfw.cmd_build",
        "ferqonfw.cmd_clean",
        "ferqonfw.cmd_doctor",
        "ferqonfw.cmd_flash",
        "ferqonfw.cmd_identify",
        "ferqonfw.cmd_info",
        "ferqonfw.cmd_list",
        "ferqonfw.cmd_packet",
        "ferqonfw.cmd_selftest",
    ]

    def test_all_production_modules_import(self, clean_production_import):
        """Every production CLI module should import without dev-only deps."""
        for mod_name in self.PRODUCTION_MODULES:
            try:
                importlib.import_module(mod_name)
            except ImportError as e:
                pytest.fail(
                    f"Production module {mod_name} failed to import "
                    f"without dev-only deps: {e}"
                )

    def test_dev_modules_are_blocked(self, clean_production_import):
        """Dev-only modules should be blocked in the clean environment."""
        for mod_name in DEV_ONLY_MODULES:
            # Ensure not cached
            if mod_name in sys.modules:
                del sys.modules[mod_name]
            with pytest.raises(ImportError, match="BLOCKED"):
                importlib.import_module(mod_name)
