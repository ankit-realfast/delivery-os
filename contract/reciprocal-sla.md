# Schedule A — Reciprocal delivery and decision windows

| Party | Defined term | Commitment | Measured by |
|---|---|---|---|
| Supplier | **Delivery Window** | Committed cards move Commit to Verify within **N** business days | Card history timestamps |
| Client | **Decision Window** | Cards in Contest are resolved by the Named Decider within **M** business days | M1 |

Breach of the Client commitment suspends the Supplier commitment for the affected
cards, automatically and visibly, without notice or dispute.

**N and M are deliberately unset (spec §9, U2).** Provisional values of N = 5 and
M = 3 business days apply to the first engagement, to be replaced by the observed
Commit-to-Verify and Contest-to-Commit distributions after fifty cards.

Reporting: the `dos report` output is shared with the Client at the agreed cadence.
It contains M1, M2, M3, and the scoreboard, and contains no per-person throughput
measure of any kind.
