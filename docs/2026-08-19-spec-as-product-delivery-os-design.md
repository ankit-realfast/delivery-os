# The Spec-as-Product Delivery OS

**Date:** 2026-08-19
**Status:** Design approved. No implementation started.
**Supersedes as the answer to "what should our delivery framework be":** `2026-08-10-delivery-practice-tooling-evaluation.md`
**Scope:** realfast.ai's operating model for client delivery. What the unit of work is, how it moves, how it is measured, how it is sold, and how an engagement ends.

---

## Bottom line

**When building is free, the scarce good is precision about what should exist and proof that it arrived.** This OS denominates everything — work, verification, adoption, handover, measurement, and invoicing — in a single artifact that carries that precision: the **spec card**.

Three consequences follow, and they are the whole design:

1. **The only queue that matters is the client's decision queue**, because every other state in the system is free or automatic. The OS exists to make that queue visible, named, dated, and contractual.
2. **Measurement is a property of the artifact, not a system you buy.** Cards carry intent, proof, value, and ownership, so the numbers fall out. No metrics platform is required.
3. **Adoption is a design-time constraint, not a workstream.** Every card declares what humans must do differently, defaulting to *nothing*, and must argue against that default.

**Nothing is purchased in v1.**

---

## 1. Why this replaces the tooling evaluation

The prior document assessed realfast against Thoughtworks (build practice) and McKinsey/BCG (framing practice), found the firm strong across the build band and empty at both ends, and recommended four open-source tools to close the gap.

Two errors, one structural and one internal:

**Structural.** Benchmarking against incumbents can only produce a catch-up agenda, and catch-up agendas are purchasable — which is why the recommendation was a shopping list. Both benchmark models were designed when delivery capacity was human, scarce, and billed hourly.

**Internal.** The document diagnosed value realisation as the highest-value gap, stated plainly that no tool in it addressed that gap, observed that build-band metrics are "unpersuasive to a buyer" — and then recommended deploying a build-band metrics tool as step one, justified by *ease* rather than value.

The deeper point: the document read realfast's strength across the build band and weakness at the ends as a **gap to close**. It is not a gap. It is a **mirror image of where the constraint used to be**. Every tool it recommended instruments the one band that stopped being scarce.

---

## 2. First-principles derivation

If agents collapse the cost of building, the binding constraint moves to whatever did not collapse. Three things did not:

| | Constraint | Why it did not collapse |
|---|---|---|
| **C1** | **Deciding what to build** | Requires client context, authority, and judgment |
| **C2** | **Knowing whether it is right** | Verification of probabilistic systems is not free |
| **C3** | **Getting the organisation to use it** | Behaviour change runs on organisational clock |

An AI-native delivery OS is therefore **a machine for maximising throughput of decisions, verification, and adoption**, with build treated as near-free capacity that floods whatever those three release.

realfast owns all three. C3 is resolved not by running change programmes — which would import MBB's cost structure and cancel the speed promise — but by **engineering the behaviour delta toward zero at design time**: building systems that absorb a process rather than tools humans must learn.

---

## 3. The unit of work — the spec card

**A spec card is not a ticket and not a user story.** A story describes work to be done. A card describes **a verifiable end state and the proof that it arrived.** Agents can act on the second and cannot act on the first.

### Fields

| Field | What it is | Why it exists |
|---|---|---|
| **Intent** | One sentence: what will be true that is not true now, in the client's language | The thing being bought |
| **Decider** | The named client-side human whose judgment this encodes | Decision latency is unattributable without a name |
| **Acceptance eval** | The executable test that decides done. For AI behaviour: a dataset and a threshold. For deterministic work: assertions | Removes "done" from the realm of opinion and demos |
| **Behaviour delta** | What a human must do differently once this lands. **Default target: none** | Makes adoption a design-time constraint |
| **Value line** | Which number in the client's world moves, and roughly how much | The renewal argument, captured at commitment rather than reconstructed at the end |
| **Tier** | T1 reversible / T2 irreversible. *Derived by the trigger test in §4, never authored* | Sets how much argument precedes build |
| **Blocked-on** | The specific decision or input missing right now | Makes the client's clock visible instead of absorbing it |

### Rule 1 — if you cannot write the eval, you do not have a spec, you have a wish

Load-bearing. It makes card size self-regulating: any card too vague or too large to test is too large, and splits without anyone arguing about points. It also prevents the classic AI-work failure — "make it smarter" — from entering the system at all.

### Rule 2 — T1 cards inherit; only T2 cards state fresh

A T1 card inherits value line and behaviour delta from its parent T2 card and carries **three authored fields**: Intent, eval, blocked-on. One line each. Tier is not authored — it is the output of the trigger test in §4, and defaults to T1.

**A card with no parent is T2 by definition.** That single rule guarantees every piece of work in the system traces upward to a stated value line and a named Decider, with no orphan work able to hide in the fast lane.

This is the direct guard against the design's main risk. If every card required seven fields, the OS would have rebuilt the bureaucracy it exists to escape. Most cards are T1 and cost about a minute. The seven-field form is reserved for decisions that are genuinely expensive to unwind.

### Why the fields close two previously-open gaps

- **Behaviour delta** means a card proposing that forty people change their workflow cannot quietly become someone's problem in month six. It is argued at authorship, against a default of *no*. Adoption stops being a discipline anyone must remember and becomes a field that defaults to the right answer.
- **Value line** is captured when the client is most motivated to state it — before the work — rather than negotiated afterwards, which never works.

---

## 4. The loop and the rigour policy

```
  DRAFT ──▶ CONTEST ──▶ COMMIT ──▶ BUILD ──▶ VERIFY ──▶ OBSERVE
    │          │           │          │          │          │
  agent      T1: skip   decider    agents      eval     value line
  drafts     T2: argue   signs      build     decides   + delta
   it                              (free)      done     checked
               ▲                                 │
               └──── eval red + build was right ─┘
                     (spec was wrong → decision)
```

**Only one state costs anything.** Build is free, Verify is automatic, Draft is cheap because agents do it. That leaves **Contest→Commit** as the sole queue worth managing — and it is the client's decision latency. The OS has exactly one bottleneck by construction.

### Tier test

**If this turns out wrong, what does it cost to reverse?** About what it cost to build → **T1**. Materially more → **T2**.

Because building is free, this test sorts far more work into T1 than any pre-agent process would. That is where speed comes from: not working harder, but arguing less about things that do not need arguing.

**T1 — reversible.** No contest. Author drafts, agents build, eval decides. If wrong, delete it. Finding out is cheaper than meeting about it.

**T2 — irreversible.** All seven fields, named Decider signs, and a **kill criterion agreed before the build** — the evidence that would make you stop.

### Automatic T2 triggers

1. Changes the shape of production data
2. Touches auth, permissions, or security posture
3. Creates an external commitment — integration contract, SLA, public statement
4. Behaviour delta is not none
5. **Cannot be switched off with a flag**

Trigger 5 is deliberately mechanical, and induces a useful side effect: teams wanting the fast lane will build behind flags. The rigour policy produces good engineering hygiene as a by-product of wanting speed, rather than by asking anyone to be disciplined.

**Anti-gaming.** The temptation is to tier everything T1. The eval is the check — a mis-tiered card usually announces itself within hours. When it does not and something breaks, the retro subject is *the tier decision*, never the person who made it. Tiering must stay cheap to stay honest.

### The red-eval fork

- **Build was wrong** → rebuild. Free, minutes, nobody is informed. Not an event.
- **Build was right and the eval still fails** → **the spec was wrong.** That is a decision problem, not an engineering problem. It returns to the named Decider, not to a backlog.

A red eval therefore diagnoses which layer is broken. Elsewhere, a wrong specification surfaces at UAT months later, when it is expensive.

### Cards close at Observe, not at Verify

**The rule the system will most try to skip, and the one that decides whether value can be proved at renewal.**

Every T2 card gets an **observation date set at commit time**, typically 30 days post-release. On that date, two questions are answered against what the card claimed: did the value line move, and was the behaviour delta what was declared?

Setting the date at commit is the mechanism. It is asked for when the client is most enthusiastic and least able to argue that measurement belongs to someone else.

### Who writes cards

Agents draft, humans contest, one named human commits. Card-writing must stay near-free or the system silts up. A card should usually be an agent's summary of a conversation that a human then argues with — never a document authored from nothing.

---

## 5. Instrumentation and division of labour

### Three meters, one scoreboard

| | Meter | Definition | Constraint |
|---|---|---|---|
| **M1** | **Decision latency** | Time cards spend in Contest→Commit, attributed to the named Decider | C1 |
| **M2** | **Eval coverage** | Share of committed cards with an eval that can fail; share of shipped behaviour under continuous eval | C2 |
| **M3** | **Behaviour-delta debt** | Live cards with non-zero delta, and how much is unowned | C3 |

Separately, and never mixed in:

**Scoreboard — value lines moved.** Share of T2 cards past their observation date whose stated number actually moved. This is the *output*, not a constraint meter. Keeping it in its own box preserves the distinction between "is it running" and "did it pay."

### Measurement requires no measurement system

All four numbers already live inside the cards. No pipeline, no scraper, no metrics platform, no connectors.

This is the argument against the prior document. It needed a metrics platform because **its unit of work carries no meaning** — a commit, a PR, or a ticket does not know what it was for, what it was worth, who wanted it, or whether it worked, so you must scrape and infer backwards. If the unit of work carries its own intent, proof, value line, and owner, measurement stops being a system you buy and becomes a property of the artifact.

### Deliberately not measured

- **Per-person throughput, velocity, commits, lines.** When agents build, per-human build throughput measures how many agents someone ran.
- **Cards per week.** Velocity in a new hat; it pays people to inflate counts by splitting.

### Gaming vectors and guards

| Meter | Gamed by | Guard |
|---|---|---|
| M1 | Not writing the card and doing the work anyway | Work without a card is invisible, and therefore uninvoiceable |
| M2 | Evals that cannot fail | An eval that has never been red is presumed broken until it goes red once |
| M3 | Declaring "none" falsely | The observation date checks the claim against reality |

### Roles

Derived from what agents cannot do in 2026.

**Humans only:** carrying accountability with a name attached; acquiring tacit context from rooms and politics; **contesting** a card, saying no, killing something; and judging whether an eval reflects what the business actually cares about. The last is decisive — an eval is only as good as its author's understanding of the client.

**Agents:** drafting cards from transcripts, building, writing and running evals for human approval, migrations, documentation, and pulling value-line data on observation dates.

Which leaves two roles that matter:

- **The Decider** (client-side). Commits cards. Their availability *is* M1. Naming them in the contract is the single highest-leverage clause available.
- **The Spec Owner** (realfast). Writes and contests cards, owns eval quality, holds client context.

**Everything else is elastic.** Firm capacity is measured in spec owners, not engineers, and leverage is per spec owner since each commands effectively unbounded build. This is a different staffing curve from both Thoughtworks and MBB, and it is the hardest element for a competitor to copy, because it requires giving up the pyramid.

---

## 6. Commercial shape and exit

### The reciprocal SLA

Hours cannot be billed in this OS. Hours price the thing that became free, and every efficiency gained becomes a self-inflicted revenue cut.

Sold instead: **spec-owner capacity with a guaranteed delivery cadence, conditional on the client meeting a decision cadence.**

| Side | Commitment | Measured by |
|---|---|---|
| **realfast** | Committed cards move Commit→Verify within N days | Card timestamps |
| **Client** | Cards in Contest clear within M days, by the named Decider | **M1** |

**Breach of the client's side voids realfast's, automatically and visibly.**

This is the only honest way to sell speed of execution. Half the clock sits inside the client's organisation; when an engagement runs late, the argument is unwinnable because nobody instrumented whose clock ran out. M1 makes that clock a contractual object. It is the most differentiated element of the design — not because it is clever, but because copying it first requires an artifact carrying a named decider and a timestamp, which is exactly what a ticket does not have.

A value-line bonus on T2 cards is an optional layer for outcome exposure. Hold it until observation data exists to price it.

### Estimation is rebuilt

Build time approaches zero, so a schedule is no longer a function of effort:

> **elapsed time ≈ number of decisions × decision latency**

Estimate **how many decisions a piece of work requires**, not how long it takes to build. The number is countable up front, honest about who controls the timeline, and converts the sales conversation from a day-rate haggle into arithmetic about the client's own decision cadence.

### Exit is native

Handover is a card like any other. Its acceptance eval: **the suite runs green in the client's CI, operated by their named person.** Not a runbook, not goodwill, not a knowledge-transfer week.

The client leaves with the card corpus, the eval suite, and the harness. There is nothing to "transfer" because the artifact is the knowledge.

**Objection — does this give away the business?** No. What does not transfer is the spec owner's judgment about what the *next* card should be. That is the scarce thing, and holding it is more defensible than holding a codebase hostage.

---

## 7. What this OS deliberately does not have

- **No phase model.** Cards have states; projects do not have stages. A twelve-phase lifecycle describes how work was scheduled around expensive building.
- **No estimates, points, velocity, or burndown.**
- **No separate governance layer.** The T2 contest *is* the stage gate — per-card, pre-agreed evidence, explicit kill criterion.
- **No purchased tooling in v1.** Not DevLake, Backstage, Copier, or a technology radar. Each instruments the band that stopped being scarce. If something later proves genuinely needed, it is bought then, with evidence.

---

## 8. Failure modes and the bet

| Risk | Signal | Guard |
|---|---|---|
| **Bureaucracy creep** — cards grow fields | T1 cards carrying more than three fields | T1 is three fields, hard-enforced. The most likely way this OS dies |
| **Eval theatre** — tests that cannot fail | An eval that has never been red | Never-red evals are presumed broken |
| **Client will not name a Decider, or will not decide** | M1 climbing with no owner | The OS cannot fix this. It converts a hidden problem into a contractual one, which is the most any system can do |
| **Spec Owner is a hard hire** | Cannot staff engagement two | Real, and the firm's actual scaling ceiling. Better discovered early |
| **The core bet is wrong** | Models become good enough to act on vague intent | Degrades gracefully — someone must still decide what is wanted and verify it arrived. The card gets shorter |

### The bet, stated plainly

**When building is free, the scarce good is precision about what should exist and proof that it arrived.**

Everything above follows from that one sentence. If it holds, this OS is a structural advantage over both Thoughtworks — who optimise building — and MBB — who optimise deciding but cannot build fast enough for it to matter. If it does not hold, this is paperwork.

---

## 9. Deliberately unresolved

These are empirical and are answered by running the OS, not by reasoning further. Each is assigned rather than left open.

| # | Question | Resolved by |
|---|---|---|
| U1 | How many spec owners does one engagement need? | Measured in engagements one and two; no number invented in advance |
| U2 | What are N and M in the reciprocal SLA? | Set from observed Commit→Verify and Contest→Commit distributions after the first engagement; provisional values used until then |
| U3 | Do clients accept a named Decider clause? | Tested in the next commercial negotiation. If refused, the speed promise cannot be honestly made and the positioning needs revisiting |
| U4 | Does the T1/T2 binary sort real work cleanly? | Reviewed after the first fifty cards; a third tier is added only if mis-tiering is observed, not anticipated |
| U5 | Can behaviour delta actually be driven to zero in practice? | Measured by M3 across the first engagement. If deltas are routinely non-zero, the adoption answer needs rework |

---

## Appendix — relationship to the prior document

What that assessment got right and this design keeps:

- Separating continuous spines from sequential phases was a genuine analytical contribution, and the observation that mixing them makes delivery models feel arbitrary is correct.
- The distinction between "is it running" and "did it pay" is preserved here as the meter/scoreboard split.
- The distinction between deploying software and getting an organisation to change is preserved as the behaviour-delta field.
- Its rejection of individual-developer-productivity measurement is preserved and made structural.
- Its closing observation — that artefacts and rituals are "cheaper than any tool in this document and worth more" — is the seed of this design. It was correct and unacted upon.

What this design discards:

- The twelve-phase, four-spine lifecycle as an organising model.
- All four recommended tools, in v1.
- The framing of realfast's profile as a coverage gap against incumbent consultancies.
