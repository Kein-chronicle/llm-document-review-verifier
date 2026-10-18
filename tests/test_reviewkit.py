import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from reviewkit import *
ok = True
def expect(name, got, want):
    global ok; g = got == want; ok &= g; print(("ok   " if g else "FAIL ") + f"{name}: {got!r}" + ("" if g else f" (want {want!r})"))

blocks = {"p1": "Total  fee: 3,000 USD", "p2": "Start 2026-03-01 – End 2026-02-30"}
good, bad = verify_claims([{"block": "p1", "quote": "total fee:  3,000 usd"}, {"block": "p1", "quote": "total fee: 9,999 usd"},
                           {"block": "p9", "quote": "x"}, {"block": "p1", "quote": "  "}], blocks)
expect("whitespace/case-normalised quote verifies", len(good), 1)
expect("invented quote, unknown block, empty quote are rejected", len(bad), 3)

F = {"F1": {"value": "1,000"}, "F2": {"value": "2,000"}, "F3": {"value": "3,000"}, "F4": {"value": "3,500"},
     "F5": {"value": "10"}, "F6": {"value": "30"}, "F7": {"value": "300"}, "F8": {"value": ""}, "F9": {"value": "2026-03-10"}}
expect("sum ok", evaluate({"type": "sum_equals", "parts": ["F1", "F2"], "total": "F3"}, F), True)
expect("sum mismatch", evaluate({"type": "sum_equals", "parts": ["F1", "F2"], "total": "F4"}, F), False)
expect("product ok", evaluate({"type": "product_equals", "factors": ["F5", "F6"], "result": "F7"}, F), True)
expect("empty required field", evaluate({"type": "required_nonempty", "ref": "F8"}, F), False)
expect("date inside period", evaluate({"type": "date_within", "ref": "F9", "start": "2026-03-01", "end": "2026-03-31"}, F), True)
expect("date outside period", evaluate({"type": "date_within", "ref": "F9", "start": "2026-04-01", "end": "2026-04-30"}, F), False)
expect("rule citing unknown fact id is dropped (None), not guessed", evaluate({"type": "sum_equals", "parts": ["F1", "F99"], "total": "F3"}, F), None)
expect("impossible calendar date parses to None", parse_date("2026-02-30"), None)
expect("set_equal ignores case/space", evaluate({"type": "set_equal", "a": ["Kim ", "Lee"], "b": ["lee", "kim"]}, F), True)

k1 = issue_key("sum", "d1", "p1", "Total fee: 3,000"); k2 = issue_key("sum", "d1", "p1", "total  fee: 3,000")
expect("identity ignores whitespace/case", k1, k2)
expect("identity changes when the text changes", issue_key("sum", "d1", "p1", "Total fee: 3,500") != k1, True)

mk = lambda k, sev="E": {"key": k, "severity": sev, "message": "m"}
led = merge({}, [mk("a"), mk("b")])
untrack(led, "b", "intended zero")
led2 = merge(led, [mk("b"), mk("c")])
expect("fixed issue becomes resolved", led2["a"]["status"], "resolved")
expect("untracked stays untracked when found again", led2["b"]["status"], "untracked")
expect("new candidate opens", led2["c"]["status"], "open")
led3 = merge(led2, [mk("a"), mk("c")])
expect("resolved issue that comes back reopens", (led3["a"]["status"], led3["a"].get("reopened")), ("open", True))
try: untrack(led, "a", "  "); expect("untrack without reason must raise", "no error", "ValueError")
except ValueError: expect("untrack without reason raises", True, True)
expect("cannot confirm with open E/W", can_confirm(led3, True)[0], False)
led4 = merge(led3, []); expect("can confirm when nothing open", can_confirm(led4, True)[0], True)
expect("cannot confirm if a doc is stale", can_confirm(led4, False)[0], False)
# --- review findings: each of these used to give a wrong OK
from reviewkit import parse_number, parse_date, verify_claims, evaluate, merge, can_confirm, issue_key
blocks = {"p1": "Unit price: 1,200 won. Quantity: 3. Total: 3,600 won."}
ok_, bad_ = verify_claims([{"block": "p1", "quote": "Total: 3,600 won", "value": "9,999"}], blocks)
def chk(name, got, want):
    g = got == want; print(("ok   " if g else "FAIL ") + f"{name}: {got!r}" + ("" if g else f" (want {want!r})")); return g
res = []
res.append(chk("a true quote cannot carry a false value", (len(ok_), len(bad_)), (0, 1)))
res.append(chk("a one-character quote proves nothing", len(verify_claims([{"block": "p1", "quote": "a", "value": "a"}], blocks)[1]), 1))
res.append(chk("a true quote with the matching value verifies", len(verify_claims([{"block": "p1", "quote": "Total: 3,600 won", "value": "3,600"}], blocks)[0]), 1))
for text, want in [("USD 1.200,50", 1200.5), ("1,200.50", 1200.5), ("\u22125", -5.0), ("(3,600)", -3600.0), ("12 items, 3 pending", None), ("1,200 x 3", None), ("Rev 2 total 3,600", None), ("3.5 million", None), ("1,20", None), ("3,600", 3600.0)]:
    res.append(chk(f"parse_number({text!r})", parse_number(text), want))
res.append(chk("parse_date does not read 12026-03-01", parse_date("12026-03-01"), None))
F = {"F1": {"value": "3,600", "quote": "q"}}
res.append(chk("a rule naming an unknown id (lower-case f1) is dropped, not a KeyError", evaluate({"type": "required_nonempty", "ref": "f1"}, F), None))
res.append(chk("required_nonempty rejects the string 'None' and 'TBD.'", (evaluate({"type": "required_nonempty", "ref": "F1"}, {"F1": {"value": "TBD."}}), evaluate({"type": "required_nonempty", "ref": "F1"}, {"F1": {"value": None}})), (False, False)))
res.append(chk("value_equal with a single ref is undecidable", evaluate({"type": "value_equal", "refs": ["F1"]}, F), None))
res.append(chk("set_equal of two empty sets is undecidable", evaluate({"type": "set_equal", "a": [], "b": []}, F), None))
k = issue_key("c", "d", "b", "x|y", "z"); k2 = issue_key("c", "d", "b", "x", "y|z")
res.append(chk("issue keys do not collide when a field contains the separator", k != k2, True))
led = merge({}, [{"key": "k", "severity": "I", "status": "open"}]); led = merge(led, [{"key": "k", "severity": "E", "status": "open"}])
res.append(chk("a re-found issue is upgraded to the higher severity", led["k"]["severity"], "E"))
for sev in ("error", "ERROR", "e", "critical", "high", None):
    res.append(chk(f"open issue with severity {sev!r} blocks confirmation", can_confirm({"k": {"status": "open", "severity": sev}}, True)[0], False))
res.append(chk("open informational issue (I) does not block", can_confirm({"k": {"status": "open", "severity": "I"}}, True)[0], True))
res.append(chk("a truthy-but-meaningless review flag does not count", can_confirm({}, "yes")[0], False))
res.append(chk("an explicit list of reviewed documents does count", can_confirm({}, ["doc-a"])[0], True))
for st in ("OPEN", "pending", None, "Open "):
    res.append(chk(f"an E issue with status {st!r} blocks confirmation", can_confirm({"k": {"status": st, "severity": "E"}}, True)[0], False))
for text, want in [("$1.5M", None), ("12k", None), ("$3B", None), ("2bn", None), ("3 bn", None), ("3,600-", -3600.0), ("Item-5", 5.0), ("2026-03-04", None)]:
    res.append(chk(f"parse_number({text!r})", parse_number(text), want))
from reviewkit import value_in_quote
res.append(chk("value 3600 is NOT verified by a parenthesised loss (3,600)", value_in_quote("3600", "net loss (3,600)"), False))
res.append(chk("value -3600 is verified by (3,600)", value_in_quote("-3600", "net loss (3,600)"), True))
res.append(chk("an empty value verifies nothing", value_in_quote("", "net loss (3,600) ok"), False))
res.append(chk("a date value matches ANY date in the quote", value_in_quote("2026-03-31", "from 2026-03-01 to 2026-03-31"), True))
res.append(chk("a piece of a date is not a number", value_in_quote("3", "invoice dated 2026-03-04"), False))
F2 = {"F1": {"value": "1"}}
res.append(chk("sum_equals with no parts is undecidable", evaluate({"type": "sum_equals", "parts": [], "total": "F1"}, F2), None))
res.append(chk("value_equal of one id twice is undecidable", evaluate({"type": "value_equal", "refs": ["F1", "F1"]}, F2), None))
res.append(chk("required_nonempty rejects '해당 없음' and 'pending'", (evaluate({"type": "required_nonempty", "ref": "F1"}, {"F1": {"value": "해당 없음"}}), evaluate({"type": "required_nonempty", "ref": "F1"}, {"F1": {"value": "pending"}})), (False, False)))
res.append(chk("count_equals with a non-numeric n is undecidable, not a crash", evaluate({"type": "count_equals", "items": [1], "n": "x"}, F2), None))
try: merge({}, [{"severity": "E"}]); res.append(chk("a candidate without a key is a clear error", "no error", "ValueError"))
except ValueError: res.append(chk("a candidate without a key is a clear error", True, True))
# Independent adversarial audit: numeric context and ledger status normalization.
for quote, value, want in [("net loss −120", "120", False), ("net loss −120", "-120", True),
                            ("loss –120", "120", False), ("price 12k", "12", False),
                            ("price 3.5 million", "3.5", False), ("quantity 3, price 12k", "3", False)]:
    res.append(chk(f"numeric evidence {quote!r} / {value}", value_in_quote(value, quote), want))
for status in ("untracked", "UNTRACKED", " untracked "):
    for reason in (None, "", "   ", [], {"reason": "approved"}):
        res.append(chk(f"untracked needs string reason: {status!r} / {reason!r}", can_confirm({"k": {"status": status, "severity": "E", "reason": reason}}, True)[0], False))
    res.append(chk(f"normalized untracked with reason: {status!r}", can_confirm({"k": {"status": status, "severity": "E", "reason": "reviewed exception"}}, True)[0], True))
sys.exit(0 if ok and all(res) else 1)

