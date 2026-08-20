# Changelog

Notable changes to the `main` branch are documented here.

## Main

### Added

- Versioned card and configuration schemas.
- Language-neutral acceptance commands with timeouts and explicit outcomes.
- Atomic writes, concurrent-edit detection, migrations, and recoverable archives.
- Approval evidence, JSON output, deterministic reports, diagnostics, dry runs,
  and expanded CLI commands.
- Installable Python package sourced directly from the repository.
- Apache License 2.0 project and package metadata.
- Card, eval, metric, configuration, migration, integration, security, support,
  architecture, and contribution documentation.

### Changed

- Reviewed cards must use `dos approve` to reach `commit` locally.
- Reports use plain-language headings while retaining versioned metric semantics.
- GitHub synchronization is serialized and records pull-request evidence.

### Compatibility

- Unversioned cards remain readable and can be upgraded with `dos migrate`.
