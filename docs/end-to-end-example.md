# End-to-end example: recover a checkout after a transient failure

This walkthrough takes one change through the complete delivery-os loop:

```text
problem -> draft -> contest -> commit -> build -> verify -> observe -> closed
```

The example starts with an existing checkout function that makes one payment
attempt. A transient provider timeout therefore abandons the checkout. The desired
change is to retry once, without creating a duplicate order.

## What the repository is tracking

A **card** is a Markdown file that keeps a proposed change, its approval, its test,
and its measured result together. The `cards/` directory is the card collection;
the code sometimes calls this collection the **corpus**.

Each card moves through these states:

| State | Plain-language meaning |
| --- | --- |
| `draft` | The change is still being written. |
| `contest` | The proposal is waiting for the named decision-maker to review it. |
| `commit` | The decision-maker has accepted the proposal. This is not a Git commit. |
| `build` | The team is implementing the accepted change. |
| `verify` | The acceptance test is being run. |
| `observe` | The team is measuring whether the promised business result happened. |
| `closed` | The result is recorded and the card is finished. |

Cards also have one of two review levels:

- **T1** is the fast lane for small, reversible changes linked to a larger parent
  card. It does not require the separate `contest` approval step.
- **T2** is the reviewed lane for changes with more risk or wider consequences. It
  requires a named decision-maker and the `contest` approval step.

You normally do not decide the level yourself. delivery-os derives it from the
card. A top-level card with no parent is always T2 because it makes the business
promise that its child work should support. Changes involving authentication,
production data, external commitments, user-visible behavior, or no feature flag
are also T2.

A **feature flag** is a switch that can disable a change without deploying new
code. A change without that safety switch receives the reviewed level.

In this example, **Priya is the decision-maker**, the checkout test is the
**acceptance eval** (short for evaluation), and reducing abandoned checkouts is the
**business result**. Those ideas matter more than remembering the labels T1 and T2.

The commands below run from the repository root. They assume the `cards/`
collection is empty, so the first generated ID is `C-0001`. If
`python3 -m delivery_os new` prints another ID, use that ID and filename everywhere
below.

## 1. Prepare the repository

delivery-os requires Python 3.11 or newer.

```bash
python3 -m pip install -r requirements.txt
```

This installs the two libraries used by the repository: PyYAML reads card metadata,
and pytest runs acceptance tests. Python's standard `-m` option runs the
`delivery_os` package directly from this repository:

```bash
python3 -m delivery_os lint
```

`lint` checks cards for missing or inconsistent information. An empty card
collection is valid, so this first check prints nothing and exits successfully.

## 2. Establish the behavior before the change

For this self-contained example, create `example_checkout.py` with the product's
current behavior:

```python
def place_order(payment_gateway, order_id):
    """Charge for an order, using the existing single-attempt behavior."""
    return payment_gateway.charge(order_id)
```

This is intentionally the behavior that exposes the problem: a timeout is returned
to the customer without a retry.

## 3. Draft the outcome card

Create a top-level card for the Acme client project:

```bash
python3 -m delivery_os new acme "recover checkout after a transient payment failure"
```

Expected output:

```text
cards/acme/C-0001-recover-checkout-after-a-transient-payment-failure.md
```

The command creates a card with `parent: null`, meaning it does not sit under
another card. delivery-os therefore gives it the T2 reviewed level. In plain
language: this card makes a business promise, so a named person must approve it
before implementation begins.

Replace the generated card with the following content. Choose a real future date
for `observation_date` in actual work; the example date is illustrative.

```yaml
---
id: C-0001
title: recover checkout after a transient payment failure
tier: T2
state: draft
parent: null
decider: Priya Raman <priya@client.example>
eval: evals/C-0001_checkout_recovery_test.py
behaviour_delta: checkout retries once after a transient provider timeout
delta_owner: Payments team
value_line: 'checkouts abandoned after a transient provider failure: 4% -> below 1%'
kill_criterion: any retry creates a duplicate charge or duplicate order
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
When the first payment attempt times out, checkout retries it once. The retry uses
the same order identifier so the payment provider recognizes it as the same request
and does not charge the customer or create the order twice.
```

Here is what every field means:

| Field | Meaning |
| --- | --- |
| `id` and `title` | The stable card identifier and a human-readable summary. |
| `tier` | The review level. T2 means this card needs explicit approval. |
| `state` | The card's current position in the workflow. It starts as `draft`. |
| `parent` | The larger card this work supports. `null` means this is a top-level business outcome. |
| `decider` | The person authorized to accept the promise and its tradeoffs. |
| `eval` | The pytest acceptance-test file, relative to the repository root. |
| `behaviour_delta` | The externally noticeable behavior that will change. `none` means no behavior should change. |
| `delta_owner` | The team responsible for that behavior change. |
| `value_line` | The measurable business number expected to improve: starting value followed by target value. |
| `kill_criterion` | Evidence that would make the team stop, disable, or reverse the change. |
| `observation_date` | The date on which the business result will be measured. |
| `blocked_on` | A named unresolved dependency. `null` means the card is not blocked. |
| `touches_production_data` | Whether the change alters the shape of stored production data. |
| `touches_auth` | Whether it changes authentication, permissions, or security. |
| `external_commitment` | Whether it creates a new promise to a client or another outside party. |
| `flag_off` | Whether a feature flag can turn the behavior off. |
| `value_moved` and `delta_held` | The two outcome answers. They remain `null` until observation. |
| `history` | The timestamped audit trail. Commands append to it automatically. |

After filling in the draft, use commands to change `state`, `value_moved`,
`delta_held`, and `history`; do not maintain those fields by hand.

## 4. Write the acceptance eval before building

Create `evals/C-0001_checkout_recovery_test.py`:

```python
from example_checkout import place_order


class TransientFailureGateway:
    def __init__(self):
        self.attempts = 0

    def charge(self, order_id):
        self.attempts += 1
        if self.attempts == 1:
            raise TimeoutError("temporary provider timeout")
        return {"order_id": order_id, "status": "paid"}


def test_checkout_retries_one_transient_failure():
    gateway = TransientFailureGateway()

    result = place_order(gateway, "order-123")

    assert result == {"order_id": "order-123", "status": "paid"}
    assert gateway.attempts == 2
```

Now validate the card structure:

```bash
python3 -m delivery_os lint
```

No output means the card collection is valid. Lint proves that the card is
structurally valid at its current state; it does not prove the eval is relevant or
green. At `commit` and later, lint also requires the eval path to resolve to a real
file.

Commit the draft and eval to version control as you normally would. The card, test,
and implementation history are intended to travel together.

## 5. Ask the named person to approve the proposal

Move the reviewed card to `contest` when it is ready for Priya's decision. Here,
`contest` means the proposal is open for examination; it does not mean the people
involved are having a dispute.

```bash
python3 -m delivery_os move C-0001 contest --by delivery-lead
python3 -m delivery_os report
```

The move appends a timestamped history entry. While the card remains in `contest`,
the report shows how long it has been waiting on Priya. The report calls this
elapsed time **M1 decision latency**.

Discuss the eval, value line, behavior change, and kill criterion with the named
decider. If Priya accepts them, record the commitment:

```bash
python3 -m delivery_os move C-0001 commit --by priya
```

The local command trusts the `--by` value; it does not check the person's identity.
Use the GitHub approval automation described later when this approval must be
enforced rather than recorded by team convention.

## 6. Prove that the acceptance test detects the problem

Start the build and move to verification without changing the existing checkout
implementation:

```bash
python3 -m delivery_os move C-0001 build --by delivery-lead
python3 -m delivery_os move C-0001 verify --by delivery-lead
python3 -m delivery_os verify C-0001
```

The command should print `C-0001 verify fail` and exit with status 1 because the
existing function lets the timeout escape. This deliberate first failure proves
that the test detects the behavior it is supposed to prevent. Test output is often
called **red** when it fails and **green** when it passes.

The report calls this evidence **M2 eval fallibility**. Despite the unusual name,
the question is simple: has the test demonstrated that it is capable of failing?
A test that has only ever passed might be testing nothing useful.

`python3 -m delivery_os verify` records the failure in the card's history but
deliberately leaves the card in `verify`. Send it back to the build state:

```bash
python3 -m delivery_os move C-0001 build --by delivery-lead
```

If pytest cannot collect or run the eval, `python3 -m delivery_os verify` reports
`ERROR` and records nothing. Fix the eval configuration and run it again; an
execution error is not a failed acceptance test.

## 7. Build the smallest passing change

Update `example_checkout.py`:

```python
def place_order(payment_gateway, order_id):
    """Charge for an order, retrying one transient provider timeout."""
    try:
        return payment_gateway.charge(order_id)
    except TimeoutError:
        return payment_gateway.charge(order_id)
```

Move back to verification and run the card's eval:

```bash
python3 -m delivery_os move C-0001 verify --by delivery-lead
python3 -m delivery_os verify C-0001
python3 -m delivery_os lint
```

Expected verification output:

```text
C-0001 verify pass
```

At this point the acceptance behavior is green. The history contains both the
earlier meaningful failure and the new pass, and the card remains in `verify` until
the business result is due to be measured.

In a production system, also run the application's normal unit, integration, and
security checks. A card eval is an acceptance test for this promise, not a
replacement for the rest of the test suite.

## 8. Observe the business result

On the agreed observation date, measure the actual checkout-abandonment rate and
check for duplicate charges or orders. If abandonment fell below 1% and the declared
behavior delta held, record both answers:

```bash
python3 -m delivery_os move C-0001 observe --by delivery-lead
python3 -m delivery_os observe C-0001 --by priya --moved --delta-held
python3 -m delivery_os move C-0001 closed --by delivery-lead
```

If the target business number did not improve, use `--not-moved`. If the actual
behavior change differed from the card's claim, use `--delta-broken`. These are
independent answers: the code can behave as planned without producing business
value, or produce value while also causing an unexpected behavior change.

`python3 -m delivery_os observe` warns but permits early observation. In real work,
record the result on or after the agreed date unless there is a documented reason
to measure early.

## 9. Read the final report

Run:

```bash
python3 -m delivery_os report
```

The report uses four measures. The exact durations and totals depend on the other
cards in the repository:

- **M1 — decision latency:** how long reviewed cards wait between requesting a
  decision (`contest`) and receiving it (`commit`). This example attributes that
  time to Priya.
- **M2 — acceptance-test evidence:** how many accepted cards have a test that has
  demonstrably failed at least once. This example records a meaningful failure and
  then a pass.
- **M3 — live behavior-change debt:** how many unfinished cards change external
  behavior, and whether each change has an owner. This example contributes zero
  after it is closed.
- **Scoreboard — business results:** how many due, measured business targets
  actually improved. This example records one improved result.

The card's `history` is the audit trail. Do not delete a completed card merely to
make the live corpus look tidy; closing preserves the decision, verification, and
outcome evidence without counting its behavior delta as live debt.

## 10. Optional: enforce the decision gate with GitHub

The repository includes `.github/workflows/cards.yml` for linting and
`.github/workflows/card-sync.yml` for state synchronization.

First map the decision-maker's GitHub username to the exact `decider` value in
`contract/deciders.yml`:

```yaml
priya-r: "Priya Raman <priya@client.example>"
```

Then use this flow instead of the manual contest and commit commands. A pull
request is GitHub's review page for a proposed set of code and card changes.

1. Push the draft card and open a pull request. `card-sync` moves a T2 (reviewed)
   card from `draft` to `contest` on the pull-request branch.
2. Priya reviews and approves the pull request using the mapped `priya-r` account.
3. Merge the pull request. `card-sync` moves a card already in `contest` to
   `commit` only when its named decider is among the approving reviewers.
4. Continue locally or in another PR with `build`, the red/green verification
   cycle, observation, and closure.

An unmapped handle cannot count as the required approval. A T2 card first
discovered only when a pull request merges moves to `contest`, not directly to
`commit`, because the repository has not yet recorded a review period for it.

## Transition reference

The normal path for a T2 reviewed card is:

```text
draft -> contest -> commit -> build -> verify -> observe -> closed
```

The supported rework paths are:

```text
contest -> draft       decision needs reframing
verify  -> build       implementation is wrong
verify  -> contest     the eval/specification is wrong and needs a new decision
```

T1 fast-lane cards are reserved for reversible work that supports a parent card;
they may move directly from `draft` to `commit`. delivery-os automatically requires
T2 review for any top-level card, authentication or production-data change,
external commitment, user-visible behavior change, or change that cannot be turned
off with a feature flag. Writing `tier: T1` does not bypass those safety rules.
