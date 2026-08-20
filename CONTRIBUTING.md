# Contributing

Python 3.11 or newer is required. A source checkout runs directly and does not need
an editable package install:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m delivery_os doctor
python3 -m delivery_os lint
python3 -m ruff check delivery_os
python3 -m ruff format --check delivery_os
python3 -m mypy delivery_os
python3 -m build
```

Keep domain rules in their owning modules; do not duplicate them in the CLI or
workflows. Preserve backward compatibility for card files, use atomic writes for
mutations, and update the relevant reference document when behavior changes.

Use Conventional Commit-style summaries where practical. Changes to card, metric,
or configuration semantics must update their schema version or explicitly explain
why compatibility is preserved.

## Architecture

Cards are the database; there is no server or hidden remote state. Policy is kept
separate from adapters:

- `card.py` owns schema parsing, serialization, migration, and safe writes.
- `lint.py` owns static card and collection policy.
- `machine.py` owns legal state transitions and evidence history.
- `eval_runner.py`, `meters.py`, and `gh.py` own execution, metrics, and GitHub
  event translation respectively.
- `commands/` contains focused user operations and shared presentation helpers.
- `cli.py` only parses arguments, builds context, and dispatches commands.
- `config.py` owns project discovery and configuration.

GitHub remains an optional adapter; local commands support the complete lifecycle.

By contributing, you agree that your contribution is licensed under the
[Apache License 2.0](LICENSE).
