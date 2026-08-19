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
kill_criterion: the first client refuses the Named Decider clause (spec U3), in which
  case the speed promise cannot be honestly made and the positioning is revisited
observation_date: 2026-12-01
external_commitment: true
flag_off: false
history:
- state: draft
  at: '2026-08-18T09:00:00+00:00'
  by: akp
- state: contest
  at: '2026-08-18T10:30:00+00:00'
  by: akp
- state: commit
  at: '2026-08-19T02:30:00+00:00'
  by: akp
- state: commit
  at: '2026-08-19T03:49:19.021436+00:00'
  by: cli
  verify: fail
- state: commit
  at: '2026-08-19T03:49:40.699046+00:00'
  by: cli
  verify: pass
---
Every engagement contract names one client-side Decider per workstream and a
Decision Window, so the half of the delivery clock that sits inside the client's
organisation is attributable rather than absorbed. Spec 5: "Naming them in the
contract is the single highest-leverage clause available."
