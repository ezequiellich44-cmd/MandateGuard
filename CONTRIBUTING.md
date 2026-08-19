# Contributing

Thanks for considering a contribution. This project ships a security-critical
engine, so the bar for correctness and tests is high.

## Setup

```bash
git clone https://github.com/ezequiellich44-cmd/MandateGuard
cd MandateGuard
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Guidelines

- **Determinism first**: the decision path must never depend on the model,
  wall-clock beyond injected windows, or non-deterministic iteration. Any new
  rule must be a pure function returning `RuleResult`.
- **Tests required**: every rule, state transition, and cryptographic edge
  case needs coverage. Aim for the replay property: state commits only on
  approval.
- **No comments unless needed**: prefer expressive names and docstrings over
  inline comments.
- **Pre-commit**: run `python -m pytest -q` before pushing.

## Commit convention

`type: subject` with types `feat`, `fix`, `test`, `docs`, `chore`.

## License

By contributing you agree your work is licensed under the MIT License.
Commercial licensing (Pro/Enterprise) is handled separately by the maintainer;
core contributions remain MIT.
