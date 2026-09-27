# Third-party rules

`rules.json` is compiled from the [SigmaHQ rule repository](https://github.com/SigmaHQ/sigma), release `r2026-07-01`, package `sigma_core+`. The release tag is pinned in `build_rules.py`.

The Sigma rules are licensed under the [Detection Rule License (DRL) 1.1](https://github.com/SigmaHQ/Detection-Rule-License). The DRL allows private and commercial use, provided the rule authors are credited in reproductions of the rules and in output that shows matches. `rules.json` keeps each rule's `author`, and every `sigma_match` event carries it as `rule_author`, which the Claude Code Security dashboard displays next to each match.

The conversion to SQLite uses [pySigma](https://github.com/SigmaHQ/pySigma) (LGPL-2.1) and [pySigma-backend-sqlite](https://github.com/SigmaHQ/pySigma-backend-sqlite). Both are build-time dependencies only, installed into `.venv` by `make sigma-rules`. Neither is distributed with this repository.
