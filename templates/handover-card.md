---
id: {id}
title: capability transfer to {client}
tier: T2
state: draft
parent: null
decider: null
eval: evals/handover_test.py::test_suite_green_in_client_ci
behaviour_delta: none
delta_owner: null
value_line: "engagements requiring supplier intervention post-exit: 0"
kill_criterion: "client has no named operator by the observation date"
observation_date: null
blocked_on: null
touches_production_data: false
touches_auth: false
external_commitment: true
flag_off: false
value_moved: null
history: []
---
The full card corpus and eval suite run green in {client}'s own CI, executed by
{client}'s named operator, with no supplier involvement in the run.
