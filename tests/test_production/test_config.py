#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
test_config.py
--------------
Tests for production configuration: precedence, validation, and manifest coverage.
"""

import json
import sys
from pathlib import Path

import pytest

# Add tools to path
tools_dir = Path(__file__).resolve().parent.parent.parent / "tools"
sys.path.insert(0, str(tools_dir))


class TestProductionConfig:
    """Test production_config.json loading and override validation."""

    @pytest.fixture
    def config(self):
        config_path = tools_dir / "production_config.json"
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)

    def test_config_has_required_fields(self, config):
        """Config must have all required fields."""
        assert "serial_baud" in config
        assert "log_level_default" in config
        assert "heartbeat_interval_ms" in config
        assert "constraints" in config
        assert "log_levels" in config

    def test_defaults_match_firmware(self, config):
        """Defaults must match the firmware's current values."""
        assert config["serial_baud"] == 115200
        assert config["log_level_default"] == "INFO"
        assert config["heartbeat_interval_ms"] == 5000

    def test_constraints_are_sane(self, config):
        """Constraints must have reasonable bounds."""
        c = config["constraints"]
        assert (
            c["serial_baud"]["min"] <= config["serial_baud"] <= c["serial_baud"]["max"]
        )
        assert c["heartbeat_interval_ms"]["min"] <= config["heartbeat_interval_ms"]
        assert c["heartbeat_interval_ms"]["max"] > config["heartbeat_interval_ms"]


class TestProductionManifest:
    """Test production_manifest.json coverage."""

    @pytest.fixture
    def manifest(self):
        manifest_path = tools_dir / "production_manifest.json"
        with open(manifest_path, encoding="utf-8") as f:
            return json.load(f)

    @pytest.fixture
    def firmware_dir(self):
        return tools_dir.parent

    def test_all_production_boards_have_files(self, manifest, firmware_dir):
        """Every production board must have its files listed and present."""
        for board in manifest["production_boards"]:
            board_files = manifest["board_files"].get(board, [])
            assert len(board_files) > 0, f"Board {board} has no files in manifest"
            for rel_path in board_files:
                assert (
                    firmware_dir / rel_path
                ).exists(), f"Missing board artifact: {rel_path}"

    def test_all_source_files_exist(self, manifest, firmware_dir):
        """Every source file in the manifest must exist."""
        for rel_path in manifest["source_files"]:
            assert (
                firmware_dir / rel_path
            ).exists(), f"Missing source file: {rel_path}"

    def test_forbidden_paths_are_marked(self, manifest):
        """Forbidden paths must include tests, examples, in_development, dev CLI."""
        forbidden = manifest["forbidden_paths"]
        assert "tests/" in forbidden
        assert "platforms/in_development/" in forbidden
        assert "tools/ferqon_emulator.py" in forbidden
        assert "tools/ferqonfw/dev_main.py" in forbidden
        assert "tools/gen_protocol.py" in forbidden
        assert "tools/gen_platform_caps.py" in forbidden

    def test_five_production_environments(self, manifest):
        """Manifest must list exactly five production environments."""
        envs = manifest["production_environments"]
        assert len(envs) == 5
        assert "pico_arduino" in envs
        assert "esp32" in envs
        assert "esp32s3" in envs
        assert "teensy40" in envs
        assert "teensy41" in envs


class TestPlatformIOSrcFilter:
    """Test that platformio.ini source filter matches the manifest."""

    def test_src_filter_matches_manifest(self):
        """The platformio.ini _src_filter must match the manifest source_files."""
        firmware_dir = tools_dir.parent
        pio_ini = firmware_dir / "platformio.ini"
        manifest_path = tools_dir / "production_manifest.json"

        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        # Extract .cpp files from manifest source_files
        manifest_cpp = {
            Path(f).name for f in manifest["source_files"] if f.endswith(".cpp")
        }

        # Parse _src_filter from platformio.ini
        pio_text = pio_ini.read_text(encoding="utf-8")
        filter_files = set()
        in_filter = False
        for line in pio_text.splitlines():
            line = line.strip()
            if line.startswith("_src_filter"):
                in_filter = True
                continue
            if in_filter:
                if line.startswith("+<") and line.endswith(">"):
                    fname = line[2:-1]
                    filter_files.add(fname)
                elif not line.startswith("+"):
                    in_filter = False
                    break

        assert filter_files == manifest_cpp, (
            f"platformio.ini src_filter does not match manifest:\n"
            f"  in pio but not manifest: {filter_files - manifest_cpp}\n"
            f"  in manifest but not pio: {manifest_cpp - filter_files}"
        )
