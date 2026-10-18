---
name: llm-proposes-code-judges
description: Architecture and a stdlib reference library for AI document/code review where the model only PROPOSES (facts, rules, findings with quotes) and deterministic code JUDGES (quote verification, arithmetic, dates, rule evaluation, issue identity, confirmation gate). Use when building review tools for reports, estimates, proposals, test cases or code; when LLM reviewers hallucinate numbers or cite text that is not there; when re-reviews duplicate or resurrect issues; or when a "sign-off" must be invalidated after the document changes.
---

# llm-proposes-code-judges

> `scripts/reviewkit.py` implements the pieces marked **[in the library]**. Everything else here is architecture guidance for you to implement.

**The model never decides whether a sum is right or a date is in range.** It extracts and suggests; code verifies and rules.

| Model proposes | Code judges |
|---|---|
| Facts: name, effort, amount, period, date, count (value + block id + **quote**) | Quote must exist verbatim in that block (after whitespace/Unicode/case normalisation) and the fact's value must appear in the quote; value parsing of numbers and dates (single numeric token only) [in the library] |
| Rules: which facts must agree, in a tiny DSL | Evaluates the rule; violation becomes an issue whose evidence is the facts' quotes |
| Typos, awkward wording, term inconsistency (quote + suggestion) | Quote verified [in the library]; suggestion applied only if its `find` exists once in the block (guidance) |
| Requirements / mapping / review findings | Quote + mapping verified |
| Questions for information gaps | - |

Code-only checks that need no model at all (design suggestions, **not in the library**): empty fields and placeholders (`TBD`, `XXX`), subtotal/total arithmetic,
unit price x quantity = amount, VAT, date sanity (reversed periods, impossible dates, weekday mismatch), checksum of ID
numbers, the same value written two ways, secrets in code, merge-conflict markers, TODO, empty catch, `eval`, debug prints.

## Design rules

1. **Everything cites a quote that lives in exactly one block**; unverifiable claims are dropped or marked
   `unverified` and *never* feed a verdict. Facts that lose their quote when a block is edited become
   `verified=false` and drop out of judgement (guidance: the library verifies once, you re-verify after edits).
2. **Rule DSL**: `set_equal`, `sum_equals`, `product_equals`, `value_equal`, `date_within`, `required_nonempty`,
   `count_equals` [in the library; add `ratio_equals` and others yourself]. Facts get code-assigned ids (`F1...`); rules reference only ids. A rule that
   references an unknown id is dropped, not guessed. Users can switch rules off.
3. **Issue identity is not the model's number.** `key = sha(JSON[check, doc, block, normalised quote, rule name])` [in the library].
   Editing the text changes the key => a genuinely new issue. Re-review reconciliation:
   still found -> keep (open stays open, **untracked stays untracked**); not found while open -> `resolved`;
   found again after resolved/applied -> `open` + `reopened`; new -> `open`.
4. **Untracking ("not a problem") requires a reason**, and is itself a reviewable record.
5. **Confirmation gate decided by code** [in the library, `can_confirm`]: every document reviewed at its *current* revision (you pass `True` or the list of reviewed documents); zero open errors/warnings (an unknown severity blocks);
   all untracked have reasons. A signed confirmation (time, user, revision, hash, counts) shown as **void** once any document changes is guidance, not provided.
6. **Block model** under everything: stable ids (`p12` paragraph, `t1r3` table 1 row 3, `s1r5` sheet row, `L12` code
   line) so edits write back to the same place and quotes resolve.

## Verification plan (copy it)

Plant known defects in fictional documents - typo, sum mismatch, missing participant, out-of-period date, required
blank - **plus legitimate-looking traps** (coincidentally different notation, an intended zero, a table with no
subtotal). Measure recall and false positives. Code checks get forgery tests (wrong doc fails, right doc passes).

## Use the library

`scripts/reviewkit.py` implements quote verification, number/date parsing, the rule evaluator, issue keys,
`merge()`, `untrack()`, and `can_confirm()`. `python3 tests/test_reviewkit.py` runs the checks.
Same pattern works for test-case generation ("expected result without evidence is flagged"), proposal compliance
matrices and code review.

Security boundary: normalized `untracked` statuses require a nonempty string reason. Numeric quote verification normalizes Unicode minus signs and conservatively rejects a quote containing unsupported scale expressions (for example `12k` or `3 million`), even when another unscaled number occurs in that quote. Narrow the quote to independent evidence when needed. This checks evidence consistency, not the truth of a document or the trustworthiness of a supplied ledger.
