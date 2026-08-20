# delivery-os reference

Installing from the repository's `main` branch exposes `dos`. From a source
checkout, replace `dos` with `python3 -m delivery_os`.

## Card format

Cards are Markdown files with YAML metadata between `---` lines and a
plain-language intent below the metadata. Schema version `1` is current.

```yaml
---
schema_version: 1
id: C-0042
title: recover checkout after a transient failure
tier: T2
state: draft
parent: null
decider: Priya Raman <priya@example.com>
eval:
  preflight: [python3, -c, "import example_checkout, evals.c0042_checkout_recovery"]
  command: [python3, -m, evals.c0042_checkout_recovery]
  timeout_seconds: 300
  working_directory: .
  failure_exit_codes: [1]
behaviour_delta: checkout retries once after a timeout
delta_owner: Payments team
value_line: 'abandoned checkouts: 4% -> below 1%'
kill_criterion: any duplicate charge
observation_date: 2026-09-30
blocked_on: null
touches_production_data: false
touches_auth: false
external_commitment: false
flag_off: true
value_moved: null
delta_held: null
history: []
---
The checkout retries one transient provider timeout without charging twice.
```

| Field | Type | Meaning |
| --- | --- | --- |
| `schema_version` | integer | Card-format version. Version 1 is current. |
| `id` | text | Stable `C-NNNN` identifier. The filename starts with it. |
| `title` | text | Short human-readable outcome. |
| `tier` | `T1` or `T2` | Authored review level. Policy may only increase it. |
| `state` | state name | Current lifecycle position. Commands maintain it. |
| `parent` | card ID or `null` | Larger outcome this work supports. No parent requires review. |
| `decider` | text or `null` | Person authorized to approve reviewed work. |
| `eval` | mapping or `null` | Optional preflight and executable acceptance evidence. |
| `behaviour_delta` | text | Externally visible change, or exactly `none`. |
| `delta_owner` | text or `null` | Owner of a non-`none` behavior change. |
| `value_line` | text or `null` | Starting business measure and target. |
| `kill_criterion` | text or `null` | Evidence that requires stopping or reversal. |
| `observation_date` | date or `null` | Date the business claim is checked. |
| `blocked_on` | text or `null` | Named unresolved dependency. |
| `touches_production_data` | boolean | Alters stored production-data shape. |
| `touches_auth` | boolean | Alters authentication, permissions, or security. |
| `external_commitment` | boolean | Creates a promise to an outside party. |
| `flag_off` | boolean | A feature flag can disable the change. |
| `value_moved` | boolean or `null` | Whether the observed business measure improved. |
| `delta_held` | boolean or `null` | Whether observed behavior matched the claim. |
| `history` | list | Append-only transition, verification, and observation evidence. |

Unknown fields and invalid types fail loading before any report or mutation runs.

### Review levels and states

T1 is the fast lane. T2 is the reviewed lane. T2 is required when a card has no
parent, changes visible behavior, cannot be disabled by a feature flag, affects
production data or authentication, or creates an external commitment. Writing
`tier: T1` cannot bypass these rules; `dos explain ID` prints the exact reasons.

```text
draft -> contest -> commit -> build -> verify -> observe -> closed
```

T1 may move directly from `draft` to `commit`. Rework may move `contest` back to
`draft`, or `verify` back to `build` or `contest`. Reviewed work reaches `commit`
through `dos approve`, which records the approver and evidence. A card cannot close
until both observation answers exist. Archive closed cards instead of deleting
them; `dos restore ID --yes` returns an archived card.

Every history entry has `state`, timezone-aware `at`, and `by`. Approval entries
also record `approved_by` and `approval_evidence`; verification entries record the
outcome, command, exit code, and duration; observation entries record both answers.

## Acceptance commands

An eval is a command list rather than a shell string, so arguments are passed
without shell expansion.

```yaml
eval:
  preflight: [npm, --version]
  command: [npm, test, --, checkout-recovery]
  timeout_seconds: 180
  working_directory: web
  environment: {}
  failure_exit_codes: [1]
```

| Outcome | Meaning | Recorded? |
| --- | --- | --- |
| pass | Exit code 0. | Yes |
| fail | Exit code listed in `failure_exit_codes`. | Yes |
| error | Missing executable, invalid setup, or another exit code. | No |
| timeout | Command exceeded its time limit. | No |

Only a genuine pass or failure is evidence. Use `preflight` when a tool needs a
separate setup check; any non-zero preflight result is an unrecorded error.

`{python}` becomes the interpreter running delivery-os and exists for legacy
compatibility. New cards should name the project's own interpreter because the
tool's installer does not include project dependencies. `{repo}` becomes the
absolute project path.

The working directory must stay inside the project. Explicit environment-variable
names must appear in `allowed_eval_environment`. The current environment is
inherited, so acceptance commands must not print secrets.

```yaml
# Dependency-free Python check
command: [python3, -m, evals.c0042_checkout_recovery]

# TypeScript
command: [npm, test, --, checkout-recovery]

# Go
command: [go, test, ./checkout]
```

Use `dos verify ID --dry-run` to inspect a command without running it and
`dos verify ID --no-record` to execute it without changing card history.

## Configuration

`dos init` creates `.delivery-os.yml`:

```yaml
schema_version: 1
cards_root: cards
archive_root: archive/cards
deciders_file: contract/deciders.yml
default_eval_timeout_seconds: 300
support_url: https://github.com/ankit-realfast/delivery-os/issues
allowed_eval_environment: []
```

| Setting | Purpose |
| --- | --- |
| `schema_version` | Configuration-format version. Version 1 is current. |
| `cards_root` | Directory containing active cards. |
| `archive_root` | Version-controlled archive outside `cards_root`. |
| `deciders_file` | GitHub username-to-decider mapping. |
| `default_eval_timeout_seconds` | Default eval time limit. |
| `support_url` | Where users report problems. |
| `allowed_eval_environment` | Environment-variable names an eval may set. |

Paths are relative to the project root. Unknown settings fail closed.
`--project PATH` selects another initialized project; `--root PATH` temporarily
overrides only its card directory.

The decider file maps a GitHub username to the exact card identity:

```yaml
priya-r: "Priya Raman <priya@example.com>"
```

## Commands and exit codes

| Command | Purpose |
| --- | --- |
| `dos init [path] [--github]` | Initialize configuration and optional workflows. |
| `dos doctor` | Diagnose configuration, cards, dependencies, and eval commands. |
| `dos new ENGAGEMENT TITLE` | Create a draft card. |
| `dos show ID` | Print one card. |
| `dos explain ID` | Explain review policy, missing data, and next states. |
| `dos status` | List active cards. |
| `dos lint` | Validate the card collection. |
| `dos move ID STATE --by NAME` | Make a legal non-approval transition. |
| `dos approve ID ...` | Record reviewed approval and evidence. |
| `dos verify ID` | Execute and record acceptance evidence. |
| `dos observe ID ...` | Record business and behavior outcomes. |
| `dos report [--explain]` | Calculate or explain decision and outcome measures. |
| `dos migrate [ID]` | Upgrade legacy cards. |
| `dos archive ID --yes` | Recoverably archive a closed, unreferenced card. |
| `dos restore ID --yes` | Restore an archived card. |
| `dos version` | Print product and protocol versions. |

Global `--json` emits structured output. Mutating commands support `--dry-run`
where meaningful.

| Exit code | Meaning |
| --- | --- |
| 0 | Success. |
| 1 | A valid check found a negative result. |
| 2 | Usage, state, configuration, or input error. |
| 3 | An eval could not express a pass or failure. |
| 4 | Concurrent write detected; reload and retry. |

Run `dos COMMAND --help` for complete arguments.

## Metrics

Metric schema version `1` defines four independent measures. `dos report --json`
includes contributing cards so every result can be audited.

- **Decision latency:** median hours from reviewed `contest` to later `commit`;
  cards still waiting are listed separately with the named decision-maker.
- **Acceptance evidence:** accepted cards with at least one recorded eval failure
  divided by all accepted cards in scope. Never-run and never-failed cards remain
  visible separately.
- **Behavior-change debt:** unfinished cards with a non-`none` behavior change,
  including missing owners and disproved behavior claims.
- **Business results:** due reviewed cards with `value_moved=true` divided by due
  cards with a recorded answer. Missing answers are listed but excluded from the
  fraction.

For reproducible reporting, supply both clocks:

```bash
dos report --at 2026-08-21T12:00:00+00:00 --today 2026-08-21 --json
```

Metric semantics change only with a new metric-schema version.

## Compatibility and migrations

Version 1 is the first public card schema. Legacy unversioned cards remain readable,
but lint asks for an explicit migration:

```bash
dos migrate --dry-run
dos migrate
dos lint
```

Migration adds `schema_version: 1` and converts a legacy pytest path into an
argument-list command with a dependency preflight. It does not invent missing
approval evidence or outcomes.

- `main` reads the current card schema and at least the immediately previous one.
- Unknown future versions are rejected before mutation.
- Migrations are deterministic and support `--dry-run`.
- Breaking card or metric semantics require a schema change and migration guide.
- Closed historical evidence is never silently rewritten.
