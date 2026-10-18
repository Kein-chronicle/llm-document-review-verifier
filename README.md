# llm-document-review-verifier

**Let the LLM propose, let code judge: quote verification, number and date parsing, a rule evaluator, and a stable issue ledger for document review.**

[![test](https://github.com/Kein-chronicle/llm-document-review-verifier/actions/workflows/test.yml/badge.svg)](https://github.com/Kein-chronicle/llm-document-review-verifier/actions/workflows/test.yml) ![license](https://img.shields.io/badge/license-MIT-blue.svg) ![dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)

## Why

Model-written review findings are only worth anything if each carries a quote that exists verbatim in the source. After that, arithmetic and date rules are decided by code, not by the model, and issues keep a stable identity across re-reviews.

## Install

**As a Claude Code skill** (Claude uses it when the task matches the skill description):

```sh
git clone https://github.com/Kein-chronicle/llm-document-review-verifier.git ~/.claude/skills/llm-proposes-code-judges
```

For a single project, clone into `<project>/.claude/skills/llm-proposes-code-judges` instead, then start a new Claude Code session.

**As a library** (Python 3.10+, standard library only): copy `scripts/reviewkit.py` into your project, or put the `scripts/` folder on `sys.path`:

```python
import sys; sys.path.insert(0, 'path/to/llm-document-review-verifier/scripts')
import reviewkit
```

**From source:**

```sh
git clone https://github.com/Kein-chronicle/llm-document-review-verifier.git
cd llm-document-review-verifier
```

**Requires:** Python 3.10+.

## Quick start

Run the quickstart:

```console
$ python3 examples/quickstart.py
verified: ['F1', 'F2', 'F3']  rejected (never reach a verdict): ['F4']
1,200 x 3 = 3,600 ? True
rule about a rejected fact is dropped: None
can confirm with an open error: (False, "issue with status 'open' and severity 'E' is not closed (closed = ['applied', 'resolved', 'untracked']; only 'open' severity 'I' may remain)")
after the fix is re-reviewed:   (True, 'ok')
```

The output above is real: it is produced by the files in `examples/`.

## What it checks

- `verify_claims(claims, blocks)` splits claims into verified and rejected: the quote must occur verbatim in its block, must not be trivially short, and the fact's `value` must appear in the quote. Rejected claims never reach a verdict.
- `parse_number` (exactly one numeric token: 1,200 / 1.200,50 / (3,600); several numbers or scale words give `None`), `parse_date`, and `evaluate(rule, facts)`: sum, product, equality, date range, non-empty rules (unknown ids drop the rule).
- `issue_key`, `merge`, `untrack`, `can_confirm`: a ledger that reopens regressions, upgrades severity when an issue is re-found, keeps "not a problem" decisions with a reason, and blocks confirmation while errors, warnings or unknown severities are open (fails closed).

## Limits

- Standard library only; no LLM client is included.

## Related projects

These solve neighbouring problems; use them when they fit better.

- **Pydantic / Instructor**: validate the shape of model output; this verifies it against the source

## More from the same collection

Small, tested tools that grew out of running AI agents and game/app pipelines for months:

- [**ai-content-editorial-lint**](https://github.com/Kein-chronicle/ai-content-editorial-lint): Catch AI-content monoculture across a folder of posts and detect silent edits to an approved manuscript.
- [**ai-resume-screening-safeguards**](https://github.com/Kein-chronicle/ai-resume-screening-safeguards): Safeguards for AI-assisted resume screening: lint rubrics for protected attributes, compute career facts in code, flag prompt injection in resumes.

## Development

```sh
python3 tests/test_reviewkit.py
```

The tests include inputs that are supposed to be rejected, so a green run also shows the checks can fail. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).

If this saved you a debugging session, a star helps other people find it. Bug reports and failing test cases are even better.

<sub>Keywords: llm, ai-agents, document-review, verification, python, claude-skills, agent-skills, structured-output</sub>
