# Delivery OS findings

You’re right—the repository’s own Markdown expresses the creator’s theory, not
independent proof. Looking from first principles and current market evidence, my
conclusion is:

> A Thoughtworks-style delivery consultant might adopt a focused, repo-native
> version of delivery-os. A McKinsey-style transformation consultant would not use
> the current product because its unit of work is too close to code and too far from
> the overall engagement.

## First-principles job of a consultant

A technology consultant is ultimately paid to reduce uncertainty across seven
questions:

1. What client problem are we solving?
2. What is inside and outside the commercial commitment?
3. Who can make each decision?
4. What is blocking delivery?
5. What evidence proves the promised change works?
6. Did users adopt it and did the expected value materialize?
7. Can the client understand, operate and audit everything after the consultant
   leaves?

Code is only one component.

McKinsey’s public research evaluates technology projects across strategy,
technology, governance and adoption—not merely implementation. It reports that
projects must be judged on time, cost and intended benefits. See
[McKinsey’s IT-project research](https://www.mckinsey.com/industries/public-sector/our-insights/unlocking-the-potential-of-public-sector-it-projects).

Thoughtworks is a much closer philosophical fit. It explicitly describes lightweight
governance stored in source control as machine-readable delivery artifacts, while
emphasizing business hypotheses, feedback and customer outcomes. See
[Thoughtworks on lightweight technology governance](https://www.thoughtworks.com/en-gb/insights/articles/lightweight-technology-governance).

That means delivery-os is directionally sound—but currently covers only part of the
consultant’s job.

## McKinsey versus Thoughtworks fit

| Consultant archetype | What they need | Current fit |
| --- | --- | --- |
| McKinsey transformation consultant | Portfolio of initiatives, quantified value cases, executive decisions, dependencies, financial impact, adoption, organizational changes and client-facing reporting | Low. A Markdown card inside one code repository is too narrow and too technical. |
| Thoughtworks delivery consultant | Executable acceptance, lightweight governance, fast feedback, product outcomes, source-controlled evidence and integration with engineering workflows | Medium. The repository-native model is attractive, but the workflow currently creates too much manual and isolated state. |
| Engagement manager | Scope, decision delays, client dependencies, delivery risks, change requests, forecast and margin exposure | Low. Cards do not represent the complete engagement or its economics. |
| Client sponsor | A simple view of promises, pending decisions, evidence, risks and realized value | Low. The client must understand Git, YAML, CLI commands and internal vocabulary. |
| Engineer | Clear intent and acceptance criteria without another tracker to maintain | Medium. Executable evals are useful, but cards can become duplicate administration. |

Thoughtworks also measures delivery through several dimensions—business outcomes,
quality, speed, feedback, team engagement and practice maturity. Two manually
entered booleans cannot represent that evidence adequately. See
[Thoughtworks’ delivery-governance framework](https://www.thoughtworks.com/en-us/insights/articles/engineering-productivity-governance-and-improvement-in-software-).

## Other solutions already exist

This is not an empty market.

| Category | Existing solutions | What they already cover |
| --- | --- | --- |
| Direct “delivery OS” competitors | [Preflight](https://www.preflightops.com/), [NolteOS](https://nolte.io/about/nolteos), [Stride](https://www.stride.page/), [Pathfinder](https://pathfinderai.app/) | Structured gates, decisions, approvals, client visibility, linked specifications, tests, delivery status and AI workflows |
| Spec-driven development | [GitHub Spec Kit](https://github.github.com/spec-kit/), [OpenSpec](https://github.com/Fission-AI/OpenSpec) | Version-controlled intent, plans, tasks and structured context for coding agents |
| Product and portfolio management | [Jira Product Discovery](https://www.atlassian.com/software/jira/product-discovery/guides/delivery/overview), [Jira Align](https://www.atlassian.com/software/jira-align), Planview | Ideas, business goals, prioritization, dependencies, capacity, investments and multi-team delivery |
| Engineering intelligence | [Jellyfish](https://jellyfish.co/platform/engineering-management-platform/), [LinearB](https://linearb.io/), Swarmia, DORA tooling | Automated delivery telemetry, bottlenecks, forecasts, resource allocation and engineering/business alignment |
| Consulting operations | [Productive](https://productive.io/), SAP PSA, Kantata, Scoro | Staffing, utilization, budgets, invoicing, revenue and engagement profitability |

The closest competitor is probably NolteOS. It tracks objectives, decisions,
asynchronous approvals, client dependencies, delivery flow, validation and engagement
reporting. Its delivery process even uses Git as the permanent source of truth. See
the [NolteOS delivery process](https://nolte.io/about/nolteos/how-we-build).

Preflight overlaps from the other direction: it converts SOWs and proposals into
validated scope, risks, capabilities, journeys and quality commitments before
implementation begins.

The phrase “delivery OS” is therefore already crowded. It no longer differentiates
the project.

## The remaining market gap

I did not find a mature open tool that combines this exact chain:

```text
client promise
    → named decision
    → implementation
    → executable acceptance evidence
    → deployment/adoption evidence
    → measured business outcome
    → portable client handover
```

Spec-driven tools generally stop around implementation. Engineering-intelligence
tools begin with activity already occurring. Portfolio tools connect strategy to
work but rarely make acceptance executable. PSA tools track engagement economics,
not whether the software fulfilled a precise behavioral promise.

That gap is real. It is narrower than “delivery OS,” but more defensible.

## What I would require before using this repository

### 1. Evidence that the method works

I would need real engagement evidence, not another illustrative checkout example:

- Time required to create and maintain cards
- Decision delays exposed
- Rework or scope disputes prevented
- Percentage of cards actually observed after delivery
- Whether clients accepted named decision responsibility
- Cases where the card changed or stopped a bad investment
- Cases where the process failed or was bypassed

Without that, this is an internally consistent methodology rather than a validated
tool.

### 2. No second system of record

I would not manually keep Jira, GitHub, Slack and a card synchronized.

The card would have to reference or derive existing facts—work items, PRs,
approvals, test runs, deployments and analytics—while adding only the information
missing elsewhere.

Jellyfish explicitly markets adoption without disrupting existing workflows, and
Jira Product Discovery connects one idea to delivery across several projects. That
is the usability bar established by current products. See
[Jellyfish integrations](https://jellyfish.co/solutions/business-alignment/).

### 3. A real engagement model

One business outcome can involve:

- Several repositories
- Multiple delivery teams
- Non-code work
- Client dependencies
- Training and process changes
- Data migration
- Vendor delivery
- Multiple releases

The current one-card/one-repository orientation does not represent that reality. I
would need traceability from engagement objective to multiple deliverables,
decisions, repositories and evidence sources.

### 4. Client participation without Git

A client sponsor will not install Python, edit YAML or run `dos approve`.

I would require an approval and observation mechanism that gives clients:

- The exact proposition they are approving
- Material risks and alternatives
- Identity and timestamp evidence
- A simple approve, reject or request-change interaction
- A permanent record transferable to the repository

This is where NolteOS is currently far ahead: the client gets a dashboard, pending
approvals and searchable decision history.

### 5. Credible outcome evidence

`value_moved: true` is not sufficient consulting evidence.

A credible outcome record needs to distinguish:

- Baseline
- Target
- Measurement window
- Data source
- Measurement owner
- Actual observed value
- Adoption
- Software behavior
- Operational reliability
- External factors
- Confidence or attribution

DORA’s research focuses on system-level measures because local activity metrics
create local optimization and conflict. See
[Google Cloud’s DORA research](https://cloud.google.com/resources/state-of-devops).

### 6. Configurable governance

T1/T2 and one fixed lifecycle cannot be assumed to fit:

- A bank
- A government department
- A startup
- A fixed-price engagement
- A staff-augmentation engagement
- An internal platform team

I would need the repository to demonstrate that its underlying protocol is stable
while the client’s decision rules, evidence requirements and lifecycle can vary.

### 7. Professional trust

The current repository is below the trust bar for use on a client:

- It currently has no `.github` directory, so the project itself has no automated
  CI.
- There is no repeatable behavioral verification of lifecycle transitions,
  migrations, concurrency or generated workflows.
- Downstream workflows install mutable `main`.
- `SECURITY.md` still promises released minor versions and provenance artifacts
  that no longer exist.
- Cards can execute commands while inheriting the surrounding environment.
- There is no defined client-data retention or deletion model.

This does not require adopting PyPI or formal package releases. But a client
engagement must be able to identify and reproduce the exact code and protocol it
approved. GitHub itself warns that mutable branches can introduce breaking changes
and recommends immutable commit SHAs for dependable automation. See
[GitHub Actions security guidance](https://docs.github.com/en/actions/reference/security/secure-use).

Even if traditional tests are considered low value, I would still require
repeatable behavioral evidence. Static linting cannot prove that an approval,
migration or state transition preserves client records correctly.

### 8. Client-grade handover

The strongest part of delivery-os is that its artifacts remain with the client. I
would require the final corpus to answer, without the consultancy present:

- What was promised?
- Who approved it?
- What changed?
- What evidence demonstrated completion?
- What value was observed?
- What remains uncertain?
- What should be stopped or revisited?

That portable evidence chain is much more compelling than positioning the tool as
another project manager.

## My honest adoption decision

As a Thoughtworks-style consultant, I would pilot delivery-os after four gates were
met:

1. It adds no duplicate delivery state.
2. Clients can participate without Git.
3. Evidence is sourced automatically and is richer than booleans.
4. The tool itself is reproducible and demonstrably reliable.

As a McKinsey-style consultant, I would still treat it as a technical evidence
component beneath a broader transformation and value-management system—not as the
engagement operating system.

The sharpest product identity is therefore:

> An open, repository-native delivery assurance protocol connecting an authorized
> client promise to executable proof and observed value.

That is narrower than “delivery OS,” but it is the part of the market where this
repository can be genuinely different rather than becoming a smaller Jira,
Planview, Productive or Stride.
