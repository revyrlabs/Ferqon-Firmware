#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs
"""
create_production_bundle.py
---------------------------
Creates a sealed production source bundle from the firmware repository.

Copies only the files listed in tools/production_manifest.json into a
staging directory, then validates that no forbidden development paths
are present in the bundle.

Usage:
    python3 tools/create_production_bundle.py [--output-dir <dir>] [--verify]

    --output-dir <dir>  Destination directory (default: dist/production-bundle)
    --verify            After creating the bundle, verify it builds all envs

This is a standard-library-only script — no third-party dependencies.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

COPYRIGHT = "SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs"


def load_manifest(firmware_dir: Path) -> dict:
    """Load the production manifest."""
    manifest_path = firmware_dir / "tools" / "production_manifest.json"
    if not manifest_path.exists():
        print(f"Error: production manifest not found: {manifest_path}")
        sys.exit(1)
    with open(manifest_path, encoding="utf-8") as f:
        return json.load(f)


def collect_all_files(manifest: dict) -> list[str]:
    """Collect all file paths from the manifest."""
    files: list[str] = []
    files.extend(manifest.get("source_files", []))
    files.extend(manifest.get("config_files", []))
    files.extend(manifest.get("build_hook_files", []))
    files.extend(manifest.get("cli_files", []))
    files.extend(manifest.get("protocol_files", []))
    files.extend(manifest.get("doc_files", []))

    for board_files in manifest.get("board_files", {}).values():
        files.extend(board_files)

    return files


def create_bundle(firmware_dir: Path, output_dir: Path, manifest: dict) -> list[str]:
    """Copy allowlisted files into the output directory. Returns copied paths."""
    files = collect_all_files(manifest)
    copied: list[str] = []

    for rel_path in files:
        src = firmware_dir / rel_path
        if not src.exists():
            print(f"  WARNING: source file missing: {rel_path}")
            continue
        dst = output_dir / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel_path)

    return copied


def verify_no_forbidden(output_dir: Path, manifest: dict) -> list[str]:
    """Verify that no forbidden paths exist in the bundle. Returns violations."""
    violations: list[str] = []
    for forbidden in manifest.get("forbidden_paths", []):
        # Check both as a directory and as a file
        candidate = output_dir / forbidden
        if candidate.exists():
            violations.append(forbidden)

    # Also scan for any stray files in directories that should not exist
    for forbidden in manifest.get("forbidden_paths", []):
        if forbidden.endswith("/"):
            # Directory check — look for any files under it
            dir_path = output_dir / forbidden.rstrip("/")
            if dir_path.exists() and dir_path.is_dir():
                for _ in dir_path.rglob("*"):
                    violations.append(forbidden)
                    break

    return violations


def verify_manifest_coverage(manifest: dict, firmware_dir: Path) -> list[str]:
    """Verify that all production boards have generated artifacts."""
    errors: list[str] = []
    for board in manifest.get("production_boards", []):
        board_files = manifest.get("board_files", {}).get(board, [])
        for rel_path in board_files:
            if not (firmware_dir / rel_path).exists():
                errors.append(f"Missing board artifact for {board}: {rel_path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a sealed production source bundle"
    )
    parser.add_argument(
        "--output-dir",
        default="dist/production-bundle",
        help="Destination directory (default: dist/production-bundle)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="After creating the bundle, verify it builds all production envs",
    )
    args = parser.parse_args()

    firmware_dir = Path(__file__).resolve().parent.parent
    output_dir = Path(args.output_dir)

    if not output_dir.is_absolute():
        output_dir = firmware_dir / output_dir

    print("=" * 60)
    print("Ferqon Production Bundle Creator")
    print("=" * 60)
    print(f"Source: {firmware_dir}")
    print(f"Output: {output_dir}")
    print()

    # Load manifest
    manifest = load_manifest(firmware_dir)

    # Verify manifest coverage first
    coverage_errors = verify_manifest_coverage(manifest, firmware_dir)
    if coverage_errors:
        print("ERROR: Manifest coverage check failed:")
        for err in coverage_errors:
            print(f"  {err}")
        return 1
    print("Manifest coverage: OK")

    # Clean output directory
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    # Create bundle
    print(f"\nCopying {len(collect_all_files(manifest))} files...")
    copied = create_bundle(firmware_dir, output_dir, manifest)
    print(f"Copied {len(copied)} files")

    # Verify no forbidden paths
    print("\nVerifying no forbidden development paths...")
    violations = verify_no_forbidden(output_dir, manifest)
    if violations:
        print("ERROR: Forbidden paths found in bundle:")
        for v in sorted(set(violations)):
            print(f"  {v}")
        return 1
    print("Forbidden path check: OK (no development files present)")

    # Verify source filter matches manifest
    print("\nVerifying source filter matches manifest...")
    src_in_manifest = set(manifest.get("source_files", []))
    src_in_bundle = {f for f in copied if f.startswith("src/")}

    # Check that all source files in manifest are in the bundle
    missing = src_in_manifest - src_in_bundle
    if missing:
        print(f"WARNING: source files in manifest but not copied: {missing}")

    print(f"\nBundle created successfully at: {output_dir}")
    print(f"  {len(copied)} files")
    print(
        f"  {len(manifest.get('production_environments', []))} production environments"
    )

    if args.verify:
        print("\n" + "=" * 60)
        print("Verifying bundle builds all production environments...")
        print("=" * 60)
        import subprocess

        all_ok = True
        for env in manifest.get("production_environments", []):
            print(f"\nBuilding {env}...")
            result = subprocess.run(
                ["pio", "run", "-e", env],
                cwd=str(output_dir),
                capture_output=False,
            )
            if result.returncode != 0:
                print(f"FAILED: {env}")
                all_ok = False
            else:
                print(f"OK: {env}")

        if not all_ok:
            print("\nBundle verification FAILED")
            return 1
        print("\nBundle verification PASSED — all environments build")

    print("\n" + "=" * 60)
    print("Production bundle ready")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
