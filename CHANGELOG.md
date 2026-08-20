# Changelog

All notable changes are documented here. The project uses semantic versioning.

## 0.2.0 - Unreleased

### Added

- Versioned card and configuration schemas.
- Language-neutral acceptance commands with timeouts and explicit outcomes.
- Atomic writes, concurrent-edit detection, migrations, and recoverable archives.
- Approval evidence, JSON output, deterministic reports, diagnostics, dry runs,
  and expanded CLI commands.
- Installable Python package and automated PyPI release workflow.
- Apache License 2.0 project and package metadata.
- Card, eval, metric, configuration, migration, integration, security, support,
  architecture, and contribution documentation.

### Changed

- Reviewed cards must use `dos approve` to reach `commit` locally.
- Reports use plain-language headings while retaining versioned metric semantics.
- GitHub synchronization is serialized and records pull-request evidence.

### Compatibility

- Unversioned cards remain readable and can be upgraded with `dos migrate`.
