# GitHub integration

`dos init --github` installs lint and card-sync workflows. The generated workflows
install delivery-os directly from `main`, so every run uses the current repository
policy.

## Approval mapping

Map GitHub usernames in `contract/deciders.yml`:

```yaml
priya-r: "Priya Raman <priya@example.com>"
```

The value must exactly match the card's `decider`. The latest review from each user
is used, so a dismissed or superseded approval no longer counts.

## Event behavior

- Opening or updating a pull request moves a reviewed draft to `contest`.
- Merging commits fast-lane work.
- Merging commits reviewed work only when the named decision-maker approved it.
- Abandoning a pull request moves a card back to `draft` only when that same pull
  request started its current contest. It cannot erase a decision started elsewhere.
- A reviewed card first discovered at merge moves only to `contest`.

Every automated commit records the pull-request number and approval identity in
card history. Sync jobs are serialized per repository to avoid two pull requests
overwriting the same card.

Fork pull requests are intentionally skipped because the workflow cannot safely
write to the fork. Use the local `dos approve` command with an evidence URL when a
decision-maker cannot approve through GitHub.

The workflow requires `contents: write` and `pull-requests: read`; lint requires
only `contents: read`.
