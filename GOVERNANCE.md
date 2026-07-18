<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- SPDX-FileCopyrightText: Copyright (c) 2026 Revyr Labs -->

# Governance

## Project Ownership

Ferqon Firmware is owned and maintained by **Revyr Labs**. The project
is released under the Apache License 2.0 and welcomes community
contributions.

## Decision-Making Process

- **Day-to-day decisions** (bug fixes, documentation, minor features):
  any maintainer can review and merge.
- **Significant changes** (new commands, protocol changes, new platform
  support): require review and approval from at least one Revyr Labs
  maintainer. Open an issue for discussion before starting work.
- **Breaking changes** (protocol version bumps, API removals): require
  a written proposal in a GitHub issue, a CHANGELOG entry under
  `[Unreleased]`, and a migration guide.

## Maintainer Responsibilities

See [MAINTAINERS.md](MAINTAINERS.md) for the current maintainer list.

Maintainers are responsible for:
- Reviewing and merging pull requests
- Triaging issues and prioritizing the roadmap
- Keeping the build green across all supported PlatformIO environments
- Updating generated headers and documentation when `board.yml` changes
- Ensuring DCO sign-off on all merged commits

## Becoming a Maintainer

Contributors who make sustained, high-quality contributions may be
invited to take on maintainer responsibilities. See
[CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute.

## Code of Conduct

All participants are expected to follow the Code of Conduct described
in [CONTRIBUTING.md](CONTRIBUTING.md). Report violations to
[conduct@revyrlabs.com](mailto:conduct@revyrlabs.com).
