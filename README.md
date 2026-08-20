# delivery-os

A delivery operating system where the unit of work is a **spec card**: a markdown
file that carries its own intent, its acceptance test, the client number it moves,
and the name of the person who authorised it.

Text files and one CLI. No server, no database, no dashboard to operate.

## Why it exists

When building is cheap, the things that stay expensive are deciding what to build,
knowing whether it's right, and getting anyone to use it. This tool instruments
those three and treats build capacity as free.

The practical consequence: **your delivery metrics are a property of the work
artifact, not a system you buy.** A commit doesn't know what it was for or whether
it worked, so tools that scrape git have to guess. A card knows.

## Install

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

Python 3.11+. Depends on PyYAML and pytest, nothing else.

## The whole interface

```bash
dos new acme "retry failed webhooks" --parent C-0001   # draft a card
dos lint                                               # is every card valid?
dos move C-0007 commit --by priya                      # advance state
dos verify C-0007                                      # run the card's eval
dos observe C-0007 --by akp --moved --delta-held       # record the outcome
dos report                                             # the four numbers
```

`--root` points at the card corpus (default `cards/`).

## What a card looks like

```yaml
---
id: C-0001
title: named decider clause is contractual
tier: T2
state: commit
parent: null
decider: Ankit P <ankit.p@realfast.ai>
eval: evals/C-0001_named_decider_test.py
behaviour_delta: none
value_line: 'engagements where a late delivery is an unwinnable argument: 1 -> 0'
kill_criterion: the first client refuses the Named Decider clause
observation_date: 2026-12-01
history:
- {state: draft,   at: '2026-08-18T09:00:00+00:00', by: akp}
- {state: contest, at: '2026-08-18T10:30:00+00:00', by: akp}
- {state: commit,  at: '2026-08-19T02:30:00+00:00', by: akp}
---
The Named Decider clause appears in the signed SOW.
```

Two rules make the format work:

**If you can't write the eval, you don't have a spec — you have a wish.** A card
that can't be tested is too vague or too big, and splits without anyone arguing
about points.

**A card with no parent is T2 by definition.** Every piece of work traces up to a
stated value line and a named decider. Nothing hides in the fast lane.

## Two tiers

Tier is **derived**, never authored. You can voluntarily mark a card T2; you cannot
mark it T1 to skip the gate.

**T1 — reversible.** Three fields, no contest, agents build, the eval decides. If
it's wrong, delete it. Finding out is cheaper than meeting about it.

**T2 — irreversible.** Full field set, named decider signs, kill criterion agreed
before the build. Triggered automatically by any of: no parent, changes production
data shape, touches auth, creates an external commitment, non-zero behaviour delta,
or can't be switched off with a flag.

That last trigger is deliberate: teams who want the fast lane build behind flags.

## The loop

```
DRAFT ──▶ CONTEST ──▶ COMMIT ──▶ BUILD ──▶ VERIFY ──▶ OBSERVE
             ▲                                │
             └──── eval red, build was right ─┘
                   (the spec was wrong)
```

Only `CONTEST → COMMIT` costs anything — that's the client deciding. Everything
else is free or automatic, which means the system has exactly one bottleneck and
it's measurable.

A red eval tells you *which layer* broke. Build wrong → rebuild, nobody is told.
Build right and the eval still fails → the **spec** was wrong, and that goes back
to the decider, not the backlog.

Cards close at Observe, not Verify. The observation date is set at commit time,
when the client is most willing to agree to be measured.

## The four numbers

```
$ dos report
M1 decision latency   median 31.0h   open 3
M2 eval fallibility   0.94   proven 47/50   never-run 2   never-red 1   no-eval 0
M3 behaviour-delta debt  live 1   unowned 0   delta claim disproved 0

SCOREBOARD  value lines moved 0.75   unrecorded 1
  waiting 62.0h on Priya Raman for C-0014
  observation overdue: C-0009
```

M1/M2/M3 watch the constraints. The **scoreboard** is the output — did the promised
number move — and it's kept in its own box on purpose. "Is it running" and "did it
pay" are different questions with different answers.

`waiting 62.0h on Priya Raman for C-0014` is the line that makes a speed promise
enforceable. Half the delivery clock sits inside the client's organisation; without
this, a late engagement is an unwinnable argument.

**M2 measures fallibility, not coverage.** An eval that has never gone red is
presumed broken. A card whose eval can't even run records nothing and reports an
error — a config failure must never masquerade as a test result.

**Never measured:** per-person throughput, velocity, commits, lines, cards per week.
When agents do the building, those count how many agents someone ran.

## GitHub integration

Two workflows, both optional.

`cards.yml` lints every card on push and PR. Conformance is a test, not a portal.

`card-sync.yml` makes the contest state literal: opening a PR moves its cards to
`contest`, merging moves them to `commit` — **but a T2 card only commits if the
named decider is among the approvers.** Map GitHub handles in
`contract/deciders.yml`; a handle that isn't in that file can never satisfy the
clause.

## What this deliberately doesn't have

- No phase model. Cards have states; projects don't have stages.
- No estimates, points, velocity, or burndown. Schedule ≈ number of decisions ×
  decision latency. Estimate the decisions.
- No separate governance layer. The T2 contest **is** the stage gate.
- No purchased tooling. Nothing here needs a vendor.

## Known limitations

Read these before relying on it.

- **`contract/deciders.yml` ships empty.** Until you populate it, the decider gate
  is a no-op — `sync-pr` will never advance a T2 card, which fails closed rather
  than open, but it does mean the automation does nothing until configured.
- **Fork PRs can't be synced.** `card-sync` pushes card state back to the branch;
  it has no write access to a fork.
- **Concurrent writes to the same card conflict.** `card-sync` pushes state while a
  human may be editing the same card on a branch. `history` is an appended list, so
  both sides touch the same lines. Not solved.
- **`dos observe` warns but doesn't refuse before the observation date.** You can
  record an outcome early.
- **Eval strings are only checked for resolvability**, not relevance. `eval:` can
  point at a real test that tests the wrong thing.
- **Non-technical deciders can't easily use this.** The decision gate runs on GitHub
  PR approvals, so a business-side decider has to review a git diff to register a
  decision. If your decider isn't an engineer, this is the first thing that will
  break — and GitHub Issues with a required issue form may simply be the better
  substrate for you.

## Layout

```
delivery_os/
  card.py      the file format, and nothing else knows it
  lint.py      validation policy, including the tier triggers
  machine.py   state transitions and history
  meters.py    M1/M2/M3 and the scoreboard, pure arithmetic
  gh.py        PR-event interpretation
  cli.py       thin argparse shell over the above
cards/         the corpus
contract/      named-decider clause, reciprocal SLA, handle mapping
  templates/ card-t1, card-t2, handover (shipped in the wheel)
docs/          the design spec and the implementation plan
```

The design document in `docs/` is the authority. Where this README and the spec
disagree, the spec wins.

## Tests

```bash
.venv/bin/pytest -q      # 200 tests
```

A note on how they're written, because it caused most of the defects found during
the build: a test that passes when its guard is deleted is not a test. Several here
were rebuilt specifically so they fail when the line they protect is removed. If you
add one, delete the code it covers and watch it go red before you trust it.
