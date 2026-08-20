---
schema_version: 1
id: "{id}"
title: capability transfer to {client}
tier: T2
state: draft
parent: null
decider: null
eval:
  preflight: [python3, --version]
  command: [python3, evals/handover_eval.py]
  - -q
  timeout_seconds: 300
  working_directory: .
  environment: {}
  failure_exit_codes: [1]
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
delta_held: null
history: []
---
The full card corpus and eval suite run green in {client}'s own CI, executed by
{client}'s named operator, with no supplier involvement in the run.
