# delivery-os

delivery-os keeps a proposed change, its approval, its acceptance evidence, and its
measured business result in one Markdown file called a **card**.

There is no server or database. Cards live with the code, can be reviewed in a pull
request, and keep working without GitHub.

> Project status: `0.2.0` is alpha. The card schema is versioned and legacy cards
> are migratable, but the public package has not been released yet.

## Why it exists

A code change does not explain who authorized it, what business number it should
move, or whether it worked. A card does:

```text
problem -> proposal -> approval -> build -> acceptance check -> measured outcome
```

delivery-os reports decision delays, whether acceptance checks have demonstrated
that they can fail, unfinished behavior changes, and business outcomes. It never
reports velocity, individual throughput, commits, or lines of code.

## Run from this source checkout

Python 3.11 or newer is required:

```bash
python3 -m pip install -r requirements.txt
python3 -m delivery_os doctor
python3 -m delivery_os lint
```

Source development does not require an editable install. The package uses the
Hatchling build backend, so normal development and release builds do not create
`delivery_os.egg-info` in the checkout; `dos doctor` also flags that directory if
another tool creates it. Installed releases expose the shorter `dos` command:

```bash
pipx install delivery-os
dos version
```

The installed command becomes available when the first public release is
published.

## Five-minute workflow

Initialize delivery-os inside another repository:

```bash
dos init --github
dos doctor
```

Create a top-level business-outcome card:

```bash
dos new acme "recover checkout after a transient payment failure"
```

The command prints the created file. Fill in its decision-maker, acceptance
command, target business result, stop condition, and observation date. Then run:

```bash
dos lint
dos explain C-0001
dos move C-0001 contest --by delivery-lead
dos approve C-0001 \
  --approved-by "Priya Raman <priya@example.com>" \
  --recorded-by delivery-lead \
  --evidence "meeting-notes:2026-09-01"
dos move C-0001 build --by delivery-lead
dos move C-0001 verify --by delivery-lead
dos verify C-0001
```

On the agreed measurement date:

```bash
dos move C-0001 observe --by delivery-lead
dos observe C-0001 --by priya --moved --delta-held
dos move C-0001 closed --by delivery-lead
dos report
```

The [complete end-to-end example](docs/end-to-end-example.md) explains every term,
field, command, expected failure, and report.

## Review levels in plain language

Cards have two internal levels:

- **T1 — fast:** small, reversible work linked to a larger card.
- **T2 — reviewed:** work that needs an explicit named decision.

You do not have to memorize the labels. `dos explain` prints the reasons in plain
language. Reviewed approval is required for top-level outcomes, authentication or
production-data changes, external commitments, customer-visible behavior changes,
and changes that cannot be disabled with a feature flag.

The reviewed lifecycle is:

```text
draft -> contest -> commit -> build -> verify -> observe -> closed
```

Here, `contest` means “open for examination,” and `commit` means “the named person
accepted the proposal”; neither term is a Git operation.

## Acceptance commands can use any language

An acceptance eval is an argument list, not Python-specific test syntax:

```yaml
eval:
  command: [npm, test, --, checkout-recovery]
  timeout_seconds: 180
  working_directory: web
  failure_exit_codes: [1]
```

Python and Go projects can use their native tools just as easily. delivery-os
distinguishes a real test failure from a missing executable, invalid configuration,
unexpected exit code, or timeout. Only genuine passes and failures are recorded.

Inspect a command safely before execution:

```bash
dos verify C-0001 --dry-run
```

## Main commands

```text
dos init                 initialize a project
dos doctor               diagnose setup and dependencies
dos new                  draft a card
dos show                 show the complete card
dos explain              explain policy and next steps
dos status               list active cards
dos lint                 validate all cards
dos move                 make a legal state transition
dos approve              record named approval and evidence
dos verify               run acceptance evidence
dos observe              record the measured outcome
dos report               calculate decision and outcome measures
dos migrate              upgrade legacy cards
dos archive              recoverably archive a finished card
dos restore              restore an archived card
dos version              show product and protocol versions
```

Use global `--json` for automation and `--dry-run` before mutations. See the
[reference](docs/reference.md) for fields, commands, exit codes, configuration,
evals, metrics, and migrations.

Commands discover the project from the current directory. To operate on another
checkout explicitly, use `dos --project /path/to/repository COMMAND`.

## GitHub integration

`dos init --github` installs two workflows:

- Card linting with read-only repository permission.
- Pull-request synchronization that records contest time and requires the mapped
  decision-maker's approval before reviewed work commits.

GitHub usernames map to exact card identities in `contract/deciders.yml`. Sync jobs
are serialized to avoid concurrent card writes, stale approvals do not count, fork
write-back is skipped, and the pull-request number is recorded as evidence.

GitHub is optional. `dos approve` records an external meeting, ticket, email, or
other evidence reference for decision-makers who do not use GitHub.

## Documentation

- [End-to-end example](docs/end-to-end-example.md)
- [Reference](docs/reference.md)
- [Release process](docs/releases.md)
- [GitHub integration](docs/github-integration.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

The original design argument remains in
[the design document](docs/2026-08-19-spec-as-product-delivery-os-design.md).

## Repository layout

```text
delivery_os/   schema, policy, command execution, metrics, integrations, and CLI
cards/         active card collection
contract/      named decision-maker clause, service agreement, and identity mapping
docs/          guides and protocol references
.github/       source-project automation and release workflows
```

Closing preserves evidence. Archiving moves a closed, unreferenced card out of the
active collection without deleting it. delivery-os intentionally provides no
command that erases historical cards.

## Support

Use [GitHub Issues](https://github.com/ankit-realfast/delivery-os/issues) for bugs,
installation problems, and feature requests. Include `dos version`, the operating
system and Python version, the failing command, and its complete error. Redact
client identities, contract details, credentials, and other sensitive card data.
Report vulnerabilities through GitHub private security advisories.

## License

delivery-os is licensed under the [Apache License 2.0](LICENSE).
