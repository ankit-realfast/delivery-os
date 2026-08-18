# Client Delivery — Model, Coverage Assessment, and Practice Tooling

**Date:** 2026-08-10
**Scope:** realfast (`ontic-in` GitHub organisation). Two linked questions: *what does client delivery actually consist of, and where are we covered?* (§2–§3), and *which open-source tools embed delivery practice, in the manner of Thoughtworks, McKinsey, or BCG?* (§4–§7).
**Status:** Assessment. No decision taken, no tool installed.

**How the two halves relate.** §2 is the **object** — the phases and spines of an engagement. §4 is the **meta-loop** — how any given practice stays alive once adopted. Every practice is a practice *about* some phase; every tool in §5 serves one stage of the meta-loop. Read §2–§3 to see what is missing; read §4–§7 to see what can be bought rather than built.

---

## Bottom line

**On coverage: realfast's delivery system is excellent in the band Thoughtworks occupies and near-empty in the band McKinsey and BCG occupy — and the client's renewal decision is made in the second band.** Of 12 delivery phases and 4 continuous spines, 6 are strongly covered (all of them between planning and release), 5 are partial, and **5 are absent: adoption, value realisation, capability transfer, engagement closure, and stage-gated governance.** Detail in §3.

**On tooling: there is no single tool. Embedding practice is four distinct jobs, and each has one clear open-source answer as of August 2026.**

| # | Job | Tool | Licence | Verified alive |
|---|-----|------|---------|----------------|
| 1 | **Decide** which practices are standard | [Thoughtworks Build Your Own Radar](https://github.com/thoughtworks/build-your-own-radar) | AGPL-3.0 ⚠️ | v1.2.0, 2026-04-15 |
| 2 | **Propagate** a standard into every project | [Copier](https://github.com/copier-org/copier) | MIT | v9.17.1, 2026-08-04 |
| 3 | **Verify** projects still conform | [Backstage](https://github.com/backstage/backstage) + [Tech Insights](https://github.com/backstage/community-plugins/tree/main/workspaces/tech-insights) *(or)* [OpenSSF Scorecard](https://github.com/ossf/scorecard) | Apache-2.0 | commits 2026-08-10 |
| 4 | **Measure** whether practice produced outcomes | **[Apache DevLake](https://github.com/apache/devlake)** | Apache-2.0 | commits 2026-08-08 |

**If only one thing is adopted, adopt [Apache DevLake](https://devlake.apache.org/) (slot 4).** It is the only slot where realfast currently has no instrument at all, it is the slot that produces client-facing evidence, and it is deployable without writing code.

**Thoughtworks' own [HeartBeat](https://github.com/au-heartbeat/HeartBeat) — the tool that prompted this evaluation — is not recommended.** Its reasons are documented in §6.

**A warning that governs everything below: the five absent phases are not tool-shaped.** No software in §5 closes adoption, value realisation, or capability transfer. Those need artefacts and rituals. Buying tools for the covered band while the empty band stays empty is the most likely way this assessment fails.

*Every link in this document was checked and returned HTTP 200 on 2026-08-10, except where explicitly marked dead. A consolidated link index is in [Appendix B](#appendix-b--link-index).*

---

## 1. What this document answers

> **Q1.** What does "client delivery" actually consist of, end to end, and where is realfast covered or exposed?
> **Q2.** Which open-source tools do technology consultancies use to embed best practice across client delivery projects, and which should realfast adopt?

**In scope:** the full engagement lifecycle as a coverage map; open-source, self-hostable tools that survive being deployed once per client engagement.

**Out of scope:** commercial tooling (LinearB, Swarmia, Cortex, Port, Sleuth); anything requiring a vendor contract; the design of the missing rituals themselves — this document names the gaps, it does not fill them.

---

## 2. What client delivery consists of

A common way to describe delivery — *discovery → execution → monitoring* — is not wrong, it is **incomplete and structurally mixed**. It omits everything before and after the build, and it blends two different kinds of thing:

- **Phases** happen in sequence and end.
- **Spines** run continuously across every phase and never end.

Any list that mixes them stops being mutually exclusive, which is why delivery models feel arbitrary. Separate them and the model closes.

### The four spines — continuous, all engagement long

| | Spine | What it owns | What breaks without it |
|---|---|---|---|
| **S1** | **Governance & decision rights** | steering cadence, stage gates, escalation paths | decisions get made twice, or never |
| **S2** | **Risks, assumptions, issues, dependencies** | the live register and its owners | the same blocker surprises everyone monthly |
| **S3** | **Stakeholder management & communication** | who hears what, when, in what form | the work is fine and the client is unhappy |
| **S4** | **Commercial & scope control** | change control, burn, margin | scope creep consumes margin invisibly |

### The twelve phases — sequential

| | Phase | What it produces |
|---|---|---|
| **P0** | **Origination & qualification** | scope, proposal, commercial model. *Delivery risk is created here, before the work is won* |
| **P1** | **Mobilisation / inception** | team, access, governance, baseline, success criteria, ways of working |
| **P2** | **Discovery & framing** | problem definition, current state, stakeholder map, **quantified value hypothesis** |
| **P3** | **Solution design** | target state, options and trade-offs, architecture decision records |
| **P4** | **Planning & sequencing** | value-ordered roadmap and milestones |
| **P5** | **Execution / build** | working software |
| **P6** | **Quality, security & assurance** | tests, security review, compliance, model evaluations for AI systems |
| **P7** | **Change management & adoption** | training, process redesign, incentives, actual usage |
| **P8** | **Deployment & cutover** | release, data migration, hypercare |
| **P9** | **Run & support** | service levels, on-call, monitoring |
| **P10** | **Value realisation** | evidence the promised number appeared |
| **P11** | **Capability transfer & exit** | a client able to operate it without you |
| **P12** | **Closure & extension** | retrospective, case study, next phase |

### Two distinctions that are usually collapsed — and shouldn't be

1. **P9 is not P10.** "Monitoring" answers *is it running*. **Value realisation answers *did it pay*.** Different data, different owner, different cadence — and **clients renew on the second one.**
2. **P7 is not P8.** Deploying software and getting an organisation to change how it works are separate programmes of work. Consultancy research is consistent on this point: transformations fail at adoption far more often than at build.

### Where each consultancy tradition actually operates

| Band | Phases | Whose practice is best here |
|---|---|---|
| Framing & value | P0–P4, P10–P12 | **McKinsey, BCG** — value assurance, stage gates, adoption, capability transfer |
| Build & release | P5–P9 | **Thoughtworks** — TDD, continuous delivery, evolutionary architecture, delivery metrics |

These are complementary layers, not competing schools. A team strong in only one band has a predictable failure mode: strong-in-build ships excellent software nobody adopts; strong-in-framing sells transformations that never work.

#### What the strategy firms' tech arms actually produce

Both firms now run real engineering units — McKinsey through QuantumBlack (acquired 2015) and McKinsey Digital; BCG through **BCG X** (formed 2022 by merging BCG GAMMA, BCG Digital Ventures, and BCG Platinion). Their open-source output, verified 2026-08-10:

| Project | Owner | Stars | Newest commit | Latest release |
|---|---|---|---|---|
| **[Kedro](https://github.com/kedro-org/kedro)** — reproducible data/ML pipelines | McKinsey/QuantumBlack → Linux Foundation | **10,949** | **2026-08-10** | 1.5.0 (2026-06-29) |
| [Vizro](https://github.com/mckinsey/vizro) — dashboard framework | McKinsey | 3,773 | 2026-08-06 | 0.1.60 (2026-07-30) |
| [CausalNex](https://github.com/mckinsey/causalnex) | McKinsey/QuantumBlack | 2,472 | 2026-06-24 | **0.12.1 — 2023-06-22** |
| [AgentKit](https://github.com/BCG-X-Official/agentkit) | BCG X | 1,948 | 2026-03-18 | **ARCHIVED** |
| [FACET](https://github.com/BCG-X-Official/facet) | BCG X | 534 | 2025-09-12 | 2.2.2 (2025-09-12) |
| [ARTKIT](https://github.com/BCG-X-Official/artkit) — gen-AI testing | BCG X | **170** | **2025-02-18** | 1.0.8 (2024-09-24) |

**Conclusion: do not look to either firm for engineering practice.** McKinsey has exactly one world-class artefact (Kedro, now Linux-Foundation-governed and committed to daily). BCG's most popular repository is archived, and its flagship generative-AI testing kit has been untouched for roughly 18 months. Public repo counts: `mckinsey` 7, `kedro-org` 21, `BCG-X-Official` 11, `BCG-Gamma` 1.

#### What they *are* worth copying — six engagement-level practices

1. **Value assurance** — every initiative carries a quantified value hypothesis tied to a line the client's finance function recognises, tracked from business case to realised benefit. **This is the single practice most absent from engineering-led delivery shops.**
2. **Stage gates with pre-agreed evidence** — go/no-go where the evidence threshold was set before the work, with explicit kill criteria (inherited from BCG Digital Ventures' venture funnel).
3. **Value-ordered portfolio** — sequence by value × feasibility, never by technical readiness.
4. **Adoption and scaling as a first-class workstream** — McKinsey's *Rewired* (2023) treats technology as one of six capabilities alongside strategy, talent, operating model, data, and adoption/scaling.
5. **Capability transfer as a contractual deliverable**, with acceptance criteria — not goodwill at the end.
6. **Hypothesis-driven MECE framing and the Pyramid Principle** — already standard practice at realfast.

⚠️ **One practice to explicitly reject.** McKinsey's August 2023 position that software developer productivity can be measured at the individual level was publicly and substantively rebutted by practitioners including Kent Beck and Gergely Orosz. Take the **value** framing from these firms; refuse the **developer-productivity** framing. Importing it would corrupt the measurement work in §5 slot 4.

---

## 3. Coverage assessment — realfast today

Assessed against the harness, playbooks, and repositories inventoried on 2026-08-10.

**Legend:** ✅ strong · 🟡 partial · 🔴 absent

### Phases

| | Phase | Covered by | Verdict |
|---|---|---|---|
| P0 | Origination & qualification | `estimation` skill (T-shirt scales); `sales` repo (scoping, org analysis) | 🟡 sizing exists; no qualification gate |
| P1 | Mobilisation / inception | `realfast-client-delivery-template`, `realfast-rails-app-baseline-template` | 🟡 repo scaffolding only; no engagement mobilisation checklist |
| P2 | Discovery & framing | `fde-discovery`, `business-analysis`, `open-questions-distribution` | ✅ **strong** — but no *quantified value hypothesis* in the canvas |
| P3 | Solution design | `specs/`, `docs/decisions.md`, `client-flow-diagrams`, `excalidraw-diagramming`, `arch-decision-record` repo | ✅ strong; the decision-record repo is idle since 2026-03 |
| P4 | Planning & sequencing | `/plan`, `steelmanning-a-plan`, `estimation`, sequencing principles in `CLAUDE.md` | ✅ **strong** |
| P5 | Execution / build | `.claude/rules/` (TDD, integration-first, test performance), `/implement`, `persona-developer` | ✅ **strongest** |
| P6 | Quality, security & assurance | `/code-review`, `/code-quality`, `/security-review`, 7 CI workflows, brakeman + bundler-audit + npm audit | ✅ strong for code; 🟡 **no model-evaluation harness for AI features** |
| P7 | **Change management & adoption** | — | 🔴 **absent** |
| P8 | Deployment & cutover | `/cut-release`, tag-gated production deploy, `/apply-terraform-change`, `/smoke-test` | ✅ strong on release; no cutover or hypercare ritual |
| P9 | Run & support | `docs/playbooks/devops/` (troubleshoot, analyse-logs, debug jobs), `docs/rca/` | ✅ good; incident write-ups idle since 2026-06 |
| P10 | **Value realisation** | — | 🔴 **absent** — no instrument ties delivery to a client number |
| P11 | **Capability transfer & exit** | — | 🔴 **absent** |
| P12 | **Closure & extension** | `ticket-complete-reconcile` (ticket-level only) | 🔴 absent at engagement level |

### Spines

| | Spine | Covered by | Verdict |
|---|---|---|---|
| S1 | Governance & decision rights | Monday board statuses and cadence | 🔴 **no stage gates** — no defined evidence threshold for go/no-go |
| S2 | Risks, assumptions, issues, dependencies | `open-questions-distribution` (open-question register, typed by owner) | 🟡 genuinely good for *questions*; no risk or dependency register |
| S3 | Stakeholder management & communication | `client-communications-runbook.md`, `client-stakeholder-comms-model.md`, `calibrating-client-docs`, `weekly-stream-dashboard`, Monday comment discipline | ✅ **strong** |
| S4 | Commercial & scope control | `estimation`; `manazer` repo (time/cost attribution, unit economics) | 🟡 instruments exist; not wired to delivery decisions |

### The shape of the gap

**Tally: 6 strong · 5 partial · 5 absent.** Every strong area falls between P2 and P9. Every absent area falls at the two ends — **before the build (P0–P1, S1) and after it (P7, P10, P11, P12).**

That is the exact signature of an engineering-led delivery organisation. It is also the signature of one whose client conversations get harder over time, because the ends of the lifecycle are where a client forms its judgement about value.

**Three consequences worth stating plainly:**

1. **The tooling in §5 does not fix this.** Apache DevLake instruments P5–P9 — the band already strong. It says nothing about P7, P10, or P11.
2. **P10 is the highest-value single gap.** It converts "we shipped 25 releases in 49 days" — true, measurable, and unpersuasive to a buyer — into a claim about the client's own numbers.
3. **P7 is the highest-risk gap.** Software that ships and is not adopted is indistinguishable, at renewal time, from software that was never built.

---

## 4. The frame: the lifecycle of a practice

A "best practice" has a life. It gets decided on, it reaches projects, it decays, and it either does or doesn't produce results. Tooling that "embeds practice" is always doing exactly one of those four jobs.

```
   ┌──────────────────────────────────────────────────┐
   │                                                  │
   ▼                                                  │
[1 DECIDE] ──▶ [2 PROPAGATE] ──▶ [3 VERIFY] ──▶ [4 MEASURE]
 which           into new          still            did it
 practices?      projects          conforming?      work?
```

### Why this frame is mutually exclusive and collectively exhaustive

**Mutually exclusive** — each slot acts on a different object at a different time:

| Slot | Acts on | At what moment | Fails how |
|------|---------|----------------|-----------|
| 1 Decide | the *practice set* | before any project | you accumulate practices and retire none |
| 2 Propagate | a *new project* | at project creation | every project reinvents the baseline |
| 3 Verify | an *existing project* | continuously after creation | projects drift silently from the standard |
| 4 Measure | *delivery outcomes* | after work ships | you cannot tell good practice from ritual |

No tool in one slot can do another slot's job. A radar cannot scaffold a repository. A scaffolding tool cannot detect drift six months later. A drift checker cannot tell you whether conformance improved delivery. A metrics platform has no opinion on what should be standard.

**Collectively exhaustive** — the loop closes. Slot 4's output is slot 1's input: measurement is what tells you a practice deserves promotion or retirement. Any fifth candidate job collapses into one of these four:

- *"Teach the practice to people"* → the artefact that teaches is the template and its documentation → **slot 2**.
- *"Enforce the practice in code review"* → an automated conformance check → **slot 3**.
- *"Retire a stale practice"* → a decision about the practice set → **slot 1**.

---

## 5. The four slots

### Slot 1 — Decide

**What the job is.** Maintain an explicit, versioned, forced-choice list of which technologies and practices are standard, which are being trialled, which are under assessment, and which are **on hold** — meaning: stop starting new work with this.

**Why the job exists.** A consultancy accumulates practices monotonically. Every engagement adds a technique; nothing removes one. Without a mechanism whose output can be *negative*, the practice set only grows, and growth past a certain point makes the standard unusable — nobody can hold it in their head, so everybody ignores it. The Hold ring is the load-bearing part; the other three rings are just staging.

**The tool.** **[Thoughtworks Build Your Own Radar](https://github.com/thoughtworks/build-your-own-radar)** — the open-source engine behind the [Technology Radar](https://www.thoughtworks.com/radar). Reads a spreadsheet or CSV, renders the four-ring visualisation. [Hosted instance to try it](https://radar.thoughtworks.com/).

| Signal | Value |
|---|---|
| Repository | [`thoughtworks/build-your-own-radar`](https://github.com/thoughtworks/build-your-own-radar) |
| Stars | 2,562 |
| Latest release | v1.2.0 — 2026-04-15 |
| Latest commit | 2026-04-22 |
| Licence | **AGPL-3.0** |

**⚠️ Licence caveat.** AGPL-3.0 extends copyleft to network use. Hosting a radar as a service that clients access may oblige source disclosure. Fine for internal use; get a legal read before it becomes a client-facing deliverable.

**Fit to realfast.** This is the emptiest slot. The organisation has 31 skills, 29 slash commands, and 4 always-loaded rules in the NUS harness alone, with no mechanism that has ever retired one. The tool is trivial; the discipline of holding a quarterly forced-choice session is the actual work.

---

### Slot 2 — Propagate

**What the job is.** Ensure a new project begins already conforming to the standard — directory layout, CI pipeline, linting, test harness, documentation skeleton, agent configuration — without anyone copying from a previous project by hand.

**Why the job exists.** Practice adopted at project creation costs nothing. The same practice retrofitted at month six costs a negotiation. More importantly: **when a standard improves, every project generated from the old version is now stale**, and hand-rolled templates have no mechanism to push the improvement downstream. That is the difference between a template and true inheritance.

**The tool.** **[Copier](https://github.com/copier-org/copier)** — [documentation](https://copier.readthedocs.io/en/stable/).

| Signal | Value |
|---|---|
| Repository | [`copier-org/copier`](https://github.com/copier-org/copier) |
| Stars | 3,518 |
| Latest release | v9.17.1 — 2026-08-04 |
| Licence | MIT |

**Why Copier over Cookiecutter.** [Cookiecutter](https://github.com/cookiecutter/cookiecutter) (25,052 stars, v2.7.1 2026-03-04, [docs](https://cookiecutter.readthedocs.io/en/stable/)) is more popular and generates a project once — a **one-time stamp**. Copier supports [`copier update`](https://copier.readthedocs.io/en/stable/updating/): a project generated from a template can pull later template changes, with conflict resolution. That is the *inheritance* semantic — fix the standard once, propagate to every existing engagement.

**Fit to realfast.** The pattern is already in use without the update mechanism. The organisation has `realfast-client-delivery-template`, `realfast-rails-app-baseline-template`, and `template-personal-agent-logs-sync`. Each is a stamp. Converting them to Copier templates is the smallest high-value change in this document — it turns three dead-end templates into a live distribution channel.

---

### Slot 3 — Verify

**What the job is.** Continuously answer, per repository: *does this project still meet the standard?* Not at creation — now.

**Why the job exists.** Conformance decays without anyone deciding it should. A workflow gets disabled to unblock a release. A branch protection rule is dropped during an incident. A dependency scanner is removed because it was noisy. Each is locally rational and none is recorded. Slot 2 guarantees the starting state; only slot 3 detects the drift away from it. Across 435 repositories this cannot be a human activity.

**Two options, deliberately different weights:**

**Heavy — [Backstage](https://backstage.io/) with the [Tech Insights](https://github.com/backstage/community-plugins/tree/main/workspaces/tech-insights) plugin.** A full developer portal: software catalogue, ownership, documentation, scaffolder, and scorecards that grade each component against defined checks.

| Signal | Value |
|---|---|
| Repository | [`backstage/backstage`](https://github.com/backstage/backstage) (+ [`backstage/community-plugins`](https://github.com/backstage/community-plugins)) |
| Stars | 34,059 |
| Latest commit | 2026-08-10 |
| Licence | Apache-2.0 |

*Why you might not want it:* Backstage is a platform you operate, not a tool you run. It expects a catalogue, owners, and someone maintaining the deployment. It repays that cost at large organisations with a platform team.

**Light — [OpenSSF Scorecard](https://scorecard.dev/), optionally with [Allstar](https://github.com/ossf/allstar) for enforcement.** Scorecard grades a repository against defined checks (branch protection, code review, pinned dependencies, dangerous workflow patterns) and emits a score. Allstar enforces policy continuously and files issues on violation.

| Signal | Scorecard | Allstar |
|---|---|---|
| Repository | [`ossf/scorecard`](https://github.com/ossf/scorecard) | [`ossf/allstar`](https://github.com/ossf/allstar) |
| Stars | 5,624 | 1,441 |
| Latest commit | 2026-08-07 | 2026-08-02 |
| Licence | Apache-2.0 | Apache-2.0 |

*Why you might prefer it:* runs as a GitHub Action across an entire organisation with no platform to operate. It grades security and supply-chain hygiene specifically, not arbitrary delivery standards — narrower, but free to run.

**Fit to realfast.** With 435 repositories and 61 members, the light option is the honest starting point. Backstage becomes justifiable only if there is a named person operating it.

---

### Slot 4 — Measure

**What the job is.** Produce defensible numbers on delivery performance — how often you ship, how long change takes, how often it fails, how fast you recover — from the systems the team already uses, without anyone hand-assembling a spreadsheet.

**Why the job exists.** Three reasons, in ascending order of importance:

1. **Practice without measurement is faith.** You cannot tell a practice that works from one that is merely familiar.
2. **Comparability.** A fixed operational definition means "cycle time is 4.2 days" means the same thing across two clients and two quarters. Ad-hoc reports cannot be compared to each other, which makes trend claims unfalsifiable.
3. **It is the only slot that produces a client-facing artefact.** Slots 1–3 improve how you work. Slot 4 is what you show the client — and what lets you claim delivery performance rather than assert it.

**The tool. [Apache DevLake](https://devlake.apache.org/).**

| Signal | Value |
|---|---|
| Repository | [`apache/devlake`](https://github.com/apache/devlake) (graduated from `apache/incubator-devlake`) |
| Documentation | https://devlake.apache.org/ |
| Governance | Apache Software Foundation |
| Stars | 3,097 |
| Contributors | 100+ |
| Latest release | v1.0.3-beta15 — 2026-07-19 (~monthly cadence) |
| Latest commit | 2026-08-08 |
| Licence | Apache-2.0 |
| Deployment | docker-compose, ships with Grafana |

**Why DevLake specifically — the [connector list](https://github.com/apache/devlake/tree/main/backend/plugins) is the argument.** 44 plugins, including:

- **Source control / CI:** `github`, `github_graphql`, `gitlab`, `bitbucket`, `bitbucket_server`, `azuredevops_go`, `jenkins`, `circleci`, `bamboo`, `argocd`, `gitextractor`, `refdiff`
- **Work tracking:** `jira`, `linear`, `clickup`, `trello`, `asana`, `taiga`, `tapd`, `teambition`, `zentao`
- **Incidents:** `pagerduty`, `opsgenie`, `incidentio`, `rootly`
- **Quality:** `sonarqube`, `testmo`, `dbt`
- **Metrics engine:** `dora`
- **Extension points:** `webhook`, `customize`
- **Agent-assisted development:** **`claude_code`**, `gh-copilot`, `q_dev`

**The `claude_code` plugin is strategically significant for realfast.** DevLake ingests agent-assisted development activity as of 2026. For a consultancy whose thesis is agent-native delivery, this is the difference between asserting that agent-assisted delivery is faster and demonstrating it with the same instrument the client uses to judge their own teams. No competitor telling that story from a spreadsheet can match it.

**Known gap: there is no Monday plugin.** Board-side metrics (velocity, cycle time, rework) require feeding Monday data through the `webhook` and `customize` plugins. This is a supported extension point rather than a fork, and realfast already operates a Monday GraphQL client that can supply the data. Treat it as phase two, not a blocker — the source-control and pipeline metrics work natively on day one.

---

## 6. Why not HeartBeat

**What it is.** Thoughtworks' own delivery-metrics tool. Select a date range, connect a board, a repository, and a pipeline, and it generates a report covering eight metrics: Velocity, Cycle Time, Classification, Rework, Deployment Frequency, Lead Time for Changes, Change Failure Rate, and Mean Time To Recovery. Java backend, TypeScript frontend, docker-compose or Kubernetes, MIT licence.

**Why it exists and what is genuinely good about it.** It solves the *definition and extraction* problem, not the analysis problem. The formulas are trivial; reconciling board transitions, commits, and deploys onto one time window is not. Its config exports as JSON, so an identical baseline can be re-run at the next engagement — that reproducibility is the consultancy value. And two of its eight metrics are not in the standard DevOps Research and Assessment (DORA) set:

- **Classification** — distribution of work by type.
- **Rework** — how many times a work item moves *backward* through statuses. This is a genuine quality counter-measure to Velocity, and it is the single most valuable idea to take from the tool regardless of whether the tool is adopted. "We completed 10 items" is meaningless if 6 came back.

**Why it is not recommended here — four reasons:**

1. **The linked repository is stale.** [`thoughtworks/HeartBeat`](https://github.com/thoughtworks/HeartBeat) (106 stars) has its newest commit on **2024-04-12**, and that commit is a merge from `au-heartbeat/main`. It is not a GitHub fork (`fork: false`, no parent), so no banner points upstream. Its `pushed_at` reads 2025-10-20, which makes it look active; that field moves on any branch or tag push. Live development is at **[`au-heartbeat/HeartBeat`](https://github.com/au-heartbeat/HeartBeat)** (12 stars) — v1.4.0, 2026-07-14.

2. **Upstream tempo is slow.** Releases went v1.3.2 (2024-10-11) → v1.4.0 (2026-07-14), a ~21-month gap. Recent commits are mostly dependency bumps plus two features.

3. **It cannot read realfast's stack — this is decisive.** Its support matrix is Board: Jira only (Trello explicitly unsupported); Pipeline: Buildkite only (TeamCity, GoCD unsupported); Repository: GitHub only. realfast runs **GitHub Actions** and **Monday/GitHub Issues** — zero Buildkite, zero Jira observed. Four of the eight metrics need Board. Three need Pipeline. The eighth needs Repository *and* Pipeline. **Zero of eight metrics work without new adapters.**

4. **DevLake dominates it on every axis** — governance, connector count (44 vs 3), contributor base, release cadence — while being the same category of tool.

**Verdict:** take HeartBeat's metric definitions, particularly Rework. Do not take its code.

---

## 7. Verified dead ends

These still appear in blog posts and recommendation lists. All three were checked on 2026-08-10 and should not be pursued.

| Tool | What it was | Status |
|---|---|---|
| **Four Keys** — [`dora-team/fourkeys`](https://github.com/dora-team/fourkeys) | Google Cloud's DORA metrics pipeline, 2,236 stars | **Archived.** Last commit 2024-01-23; last release v1.0.2, 2023-05-04 |
| **Repolinter** — [`todogroup/repolinter`](https://github.com/todogroup/repolinter) | TODO Group's repository standards linter, 465 stars | **Archived** 2026-02-06 |
| **Faros Community Edition** — `faros-ai/faros-community-edition` | Open-source engineering-metrics platform | **Gone** — `https://github.com/faros-ai/faros-community-edition` returns **404** (re-confirmed 2026-08-10) |

---

## 8. Fit assessment — the [`ontic-in`](https://github.com/orgs/ontic-in/repositories) organisation

Facts measured on 2026-08-10, not assumed.

**Shape of the estate**

| Fact | Value | Implication |
|---|---|---|
| Repositories | 435 (20 public, 415 private) | too many to govern by hand |
| Members | 61 | ~7 repositories per person |
| GitHub Actions adoption | 21 of the 30 most recently pushed repositories | **GitHub Actions is the uniform substrate** |
| Buildkite | none observed | HeartBeat has nothing to read |
| Jira | none observed | HeartBeat has nothing to read |
| Trackers in use | GitHub Issues (`apply-to` 74 open, `content-branding` 91, `heimdall` 57) + Monday for NUS delivery | heterogeneous; DevLake covers GitHub Issues natively |

**The measurable unit is not "a repository."** At ~7 repositories per person, most are single-contributor. Deployment frequency on a repository touched twice a month is noise. The estate contains wikis, marketing sites, bootcamp exercises, and third-party sample applications (`redwoods-insurance`, `coral-cloud` — not realfast code). Any measurement programme must scope explicitly.

**Candidate set of genuinely continuously-delivered products** (by workflow count and push recency — *requires confirmation before use*): `nus-agentic-ops` (7 workflows), `apply-to` (5), `atlas` (15), `manazer` (5), `heimdall` (5), `exo-help` (7), `recruitments-wiki` (7), `sales` (3).

**Existing instruments already in the estate**

| Repository | What it is | Newest commit |
|---|---|---|
| `saurabhs-metrics` | Platform-health collector — Konfirmity, AWS Cost Explorer, CloudWatch → SQLite, with advisor agents, `philosophy.md`, and a documented cadence per metric | 2026-04-10 |
| `arch-decision-record` | 10 architecture decision records across the platform team | 2026-03-03 |

`saurabhs-metrics` is worth studying before building anything: it assigns every metric an explicit **cadence** and **"the question it answers"**, which is better metric design than HeartBeat offers. It measures platform health (compliance, reliability, cost per user) — a **different domain** from delivery performance, so DevLake complements rather than replaces it.

---

## 9. Recommended sequence

Ordered by evidence produced per unit of effort.

| Step | Action | Why first / why here |
|---|---|---|
| **1** | Deploy **[DevLake](https://devlake.apache.org/)** via docker-compose, point it at the `ontic-in` GitHub organisation, scope to the ~8 continuously-delivered repositories | Produces a real delivery baseline in an afternoon with **zero code written**. Everything else is easier to argue once numbers exist. |
| **2** | Convert `realfast-client-delivery-template` and `realfast-rails-app-baseline-template` to **[Copier](https://copier.readthedocs.io/en/stable/)** templates | Smallest change with compounding return — converts three one-time stamps into a live distribution channel for every future engagement. |
| **3** | Run **[OpenSSF Scorecard](https://scorecard.dev/)** as an organisation-wide GitHub Action | Reveals actual conformance across 435 repositories with no platform to operate. |
| **4** | Stand up **[Build Your Own Radar](https://github.com/thoughtworks/build-your-own-radar)** internally; run the first forced-choice pass over the existing practice set | Needs steps 1–3 to supply evidence for what belongs on Hold. Resolve the AGPL question before any client sees it. |
| **5** | Feed Monday into DevLake via the [`webhook`/`customize`](https://github.com/apache/devlake/tree/main/backend/plugins) plugins; add **[packwerk](https://github.com/Shopify/packwerk)** to `nus-agentic-ops` | Deferred integration work, justified only once steps 1–4 prove the programme is being used. |

**Deliberately deferred:** [Backstage](https://backstage.io/). It is the right answer at a larger scale with a platform owner; adopting it before a named operator exists would create a fifth surface to maintain.

### What this sequence deliberately does not address

Every step above serves **P5–P9** — the band already strong (§3). **None of the five absent phases is closed by any tool in this document**, because none of them is tool-shaped. They are closed by artefacts and rituals:

| Gap | What would close it | Shape |
|---|---|---|
| **P10 Value realisation** | A value hypothesis stated per milestone in the client's own units, baselined at P2 and re-measured after go-live | one page per milestone, not software |
| **P7 Adoption** | A named adoption owner, a usage measure alongside the delivery measure, and a training/process-change deliverable in the plan | a workstream, not a tool |
| **P11 Capability transfer** | Handover defined as a deliverable with acceptance criteria, written from the start rather than at exit | contract language + a runbook |
| **P12 Closure & extension** | An engagement-level retrospective and case study, distinct from ticket reconciliation | a ritual with a date |
| **S1 Stage gates** | Go/no-go points with the evidence threshold agreed *before* the work starts | a governance calendar |

**These are cheaper than any tool in this document and worth more.** Sequencing note: P10 depends on P2 capturing a value hypothesis in the first place — so the earliest real step is adding one line to the discovery canvas, not deploying anything.

---

## 10. Risks and open questions

| # | Risk / question | Notes |
|---|---|---|
| R1 | **No Monday connector in DevLake** | Board-side metrics (velocity, cycle time, rework) are unavailable until webhook adapters are written. Source-control and pipeline metrics are unaffected. |
| R2 | **Build Your Own Radar is AGPL-3.0** | Network-use copyleft. Requires a legal read before client-facing hosting. |
| R3 | **DevLake is on a beta release line** | v1.0.3-beta15. Cadence is healthy and governance is Apache, but the version string warrants a pilot before client-facing use. |
| R4 | **Continuously-delivered repository set is unconfirmed** | The list in §6 was derived from workflow counts and push recency. It needs human confirmation before any metric is published. |
| R5 | **Metric signal at this team size** | With ~7 repositories per person, several DORA metrics may lack statistical signal at repository granularity. Consider aggregating to the engagement level. |
| Q1 | Is the goal internal improvement, or a client-facing capability? | Changes the priority order materially. A client-facing metrics capability raises the bar on R2 and R3. |
| Q2 | Who operates whichever tool is adopted? | Two existing instruments in this estate went idle within four months. Named ownership is a precondition, not a detail. |

---

## Appendix A — verification method

Every statistic in this document was retrieved from the GitHub REST API on **2026-08-10**, not recalled. Specifically:

- Repository metadata — `GET /repos/{owner}/{repo}` (stars, licence, `archived`, `pushed_at`, fork relationship)
- Activity — `GET /repos/{owner}/{repo}/commits?per_page=1` for the newest commit date, because `pushed_at` moves on branch and tag pushes and overstates liveness
- Releases — `GET /repos/{owner}/{repo}/releases`
- DevLake connectors — directory listing of `backend/plugins` on `apache/devlake`
- Organisation shape — `GET /orgs/ontic-in`, `GET /orgs/ontic-in/repos?sort=pushed`, `GET /orgs/ontic-in/members`
- Continuous-delivery detection — presence of `.github/workflows` across the 30 most recently pushed repositories

**Known limits of this evaluation:**
- Continuous-integration presence was sampled across the 30 most recently pushed repositories, **not all 435**.
- `saurabhs-metrics` was assessed from its README, **not its source**.
- Tool capabilities are taken from official documentation and connector listings; **none of the four recommended tools was installed or run**.

---

## Appendix B — link index

Every URL below returned **HTTP 200 on 2026-08-10** unless marked otherwise.

### Recommended — the four slots

| Slot | Tool | Source | Documentation / demo |
|---|---|---|---|
| 4 Measure | **Apache DevLake** | https://github.com/apache/devlake | https://devlake.apache.org/ |
| 4 Measure | DevLake connector list (44 plugins) | https://github.com/apache/devlake/tree/main/backend/plugins | — |
| 2 Propagate | **Copier** | https://github.com/copier-org/copier | https://copier.readthedocs.io/en/stable/ |
| 2 Propagate | Copier `update` — the inheritance mechanism | — | https://copier.readthedocs.io/en/stable/updating/ |
| 3 Verify | **OpenSSF Scorecard** | https://github.com/ossf/scorecard | https://scorecard.dev/ |
| 3 Verify | OpenSSF Allstar (enforcement) | https://github.com/ossf/allstar | — |
| 3 Verify | **Backstage** | https://github.com/backstage/backstage | https://backstage.io/ |
| 3 Verify | Backstage Tech Insights (scorecards) | https://github.com/backstage/community-plugins/tree/main/workspaces/tech-insights | — |
| 1 Decide | **Build Your Own Radar** ⚠️ AGPL-3.0 | https://github.com/thoughtworks/build-your-own-radar | https://radar.thoughtworks.com/ · https://www.thoughtworks.com/radar |

### Considered, not recommended

| Tool | Source | Note |
|---|---|---|
| HeartBeat — **live upstream** | https://github.com/au-heartbeat/HeartBeat | v1.4.0, 2026-07-14. Jira + Buildkite only |
| HeartBeat — **stale mirror** | https://github.com/thoughtworks/HeartBeat | Newest commit 2024-04-12. Do not use |
| Cookiecutter | https://github.com/cookiecutter/cookiecutter | Alive, but no update-in-place — see §5 slot 2 |
| Shopify packwerk (Rails fitness functions) | https://github.com/Shopify/packwerk | Sequence step 5 candidate (§9) |

### Verified dead — do not pursue

| Tool | Source | Status |
|---|---|---|
| Four Keys | https://github.com/dora-team/fourkeys | **Archived**, last commit 2024-01-23 |
| Repolinter | https://github.com/todogroup/repolinter | **Archived** 2026-02-06 |
| Faros Community Edition | `https://github.com/faros-ai/faros-community-edition` | **HTTP 404** |

### Strategy-firm tech arms (context for §2, not recommendations)

| Project | Owner | Link | Status |
|---|---|---|---|
| Kedro | McKinsey → Linux Foundation | https://github.com/kedro-org/kedro | Alive — commit 2026-08-10 |
| Vizro | McKinsey | https://github.com/mckinsey/vizro | Alive — commit 2026-08-06 |
| CausalNex | McKinsey | https://github.com/mckinsey/causalnex | Maintenance only — no release since 2023-06 |
| AgentKit | BCG X | https://github.com/BCG-X-Official/agentkit | **Archived** |
| FACET | BCG X | https://github.com/BCG-X-Official/facet | Slowing — 2025-09 |
| ARTKIT | BCG X | https://github.com/BCG-X-Official/artkit | Stale — commit 2025-02-18 |

### Internal context

| Subject | Link |
|---|---|
| The organisation under evaluation | https://github.com/orgs/ontic-in/repositories |
