"""reviewkit: let an LLM *propose* (facts, rules, findings with quotes) and let code *judge*.
Stdlib only. Blocks are {id: text}. Every LLM claim must carry a quote that exists verbatim in one block."""
import hashlib, json, re, unicodedata
from datetime import date

# ---------- 1. quote verification -------------------------------------------------------------
def norm(s):
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"\s+", " ", s).strip().lower()

def quote_in_block(quote, block_text):
    return bool(quote.strip()) and norm(quote) in norm(block_text)

MIN_QUOTE = 4          # normalised characters: a one-letter "quote" is found everywhere and proves nothing

DATE_RE = re.compile(r"(?<!\d)\d{4}[-./]\d{1,2}[-./]\d{1,2}(?!\d)")
NUM_TOKEN = r"\(?(?<![\w])-?\d[\d.,]*\)?-?"          # optional parentheses or a sign (leading or trailing); a '-' glued to a letter ("Item-5") is not a sign

def value_in_quote(value, quote):
    """A fact is verified only if its VALUE is actually in the quote that supports it (otherwise a true quote can carry a false value). An empty value verifies nothing."""
    if not str(value).strip(): return False
    d = parse_date(value)
    if d is not None: return any(parse_date(m.group(0)) == d for m in DATE_RE.finditer(quote))
    n = parse_number(value)
    if n is not None:
        rest = DATE_RE.sub(" ", quote.replace("\u2212", "-").replace("\u2013", "-"))
        if SCALE_WORDS.search(rest): return False                 # never detach a number from an unsupported scale
        return any(parse_number(t) is not None and abs(parse_number(t) - n) < 1e-9 for t in re.findall(NUM_TOKEN, rest))
    return norm(str(value)) in norm(quote)

def verify_claims(claims, blocks):
    """claims: [{block, quote, value?, ...}] -> (verified, rejected). Unverified claims never reach a verdict.
    A claim is verified when its quote occurs verbatim in its block, the quote is not trivially short, and (if the claim carries a value) the value appears in the quote."""
    ok, bad = [], []
    for c in claims:
        q = c.get("quote", "")
        good = (c.get("block") in blocks and isinstance(q, str) and len(norm(q)) >= MIN_QUOTE and quote_in_block(q, blocks[c["block"]])
                and ("value" not in c or value_in_quote(c["value"], q)))
        (ok if good else bad).append(c)
    return ok, bad

# ---------- 2. value parsing (code, not model) ------------------------------------------------
SCALE_WORDS = re.compile(r"thousand|million|billion|trillion|\d\s*(?:k|m|mm|bn?|tn)\b|\b(?:k|m|mm|bn?|tn)\b|만|억|천|조", re.I)      # "12k", "$1.5M", "3 bn" are scaled numbers: unsupported, so None

def parse_number(s):
    """Exactly ONE numeric token or None. Handles 1,200 / 1,200.50 / 1.200,50 / unicode minus / (3,600) as negative. Returns None for several numbers
    ('12 items, 3 pending'), scale words ('3.5 million') and ambiguous separators, instead of gluing digits together."""
    t = str(s).replace("\u2212", "-").replace("\u2013", "-")
    toks = re.findall(NUM_TOKEN, t)
    if len(toks) != 1 or SCALE_WORDS.search(t): return None
    tok = toks[0]; neg = tok.startswith("(") or tok.startswith("-") or tok.endswith("-"); num = tok.strip("()-").rstrip(".,")
    if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", num): num = num.replace(",", "")                 # 1,200 or 1,200.50
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+,\d+", num): num = num.replace(".", "").replace(",", ".")   # 1.200,50
    elif not re.fullmatch(r"\d+(\.\d+)?", num): return None                                         # ambiguous, e.g. 1,20 or 1.2.3
    return -float(num) if neg else float(num)

def parse_date(s):
    m = re.search(r"(?<!\d)(\d{4})[-./](\d{1,2})[-./](\d{1,2})(?!\d)", str(s))
    if not m: return None
    try: return date(int(m[1]), int(m[2]), int(m[3]))      # impossible dates (2026-02-30) -> None
    except ValueError: return None

PLACEHOLDERS = {"", "tbd", "tba", "todo", "xxx", "xx", "n a", "na", "none", "null", "nil", "unknown", "pending", "not applicable", "to be decided", "to be determined", "미정", "없음", "해당 없음", "해당없음", "추후 협의", "별도 협의"}

# ---------- 3. rule DSL evaluated by code -----------------------------------------------------
def evaluate(rule, facts):
    """facts: {'F1': {'value': '1,200', 'quote': ..., 'block': ...}}. Unknown fact ids => rule dropped (None)."""
    ID_KEYS = ("parts", "total", "factors", "result", "refs", "ref")                     # keys that hold fact ids (a, b, items hold literal values)
    refs = [r for k in ID_KEYS for r in (rule.get(k) if isinstance(rule.get(k), list) else [rule.get(k)] if rule.get(k) else [])]
    if any(not isinstance(r, str) or r not in facts for r in refs): return None            # any unknown id drops the rule
    v = lambda r: facts[r]["value"]
    t = rule["type"]
    if t == "sum_equals":
        if not rule.get("parts"): return None
        parts = [parse_number(v(r)) for r in rule["parts"]]; total = parse_number(v(rule["total"]))
        return None if None in parts or total is None else abs(sum(parts) - total) < 1e-6
    if t == "product_equals":
        fs = [parse_number(v(r)) for r in rule["factors"]]; res = parse_number(v(rule["result"]))
        if None in fs or res is None: return None
        p = 1.0
        for f in fs: p *= f
        return abs(p - res) < 1e-6
    if t == "value_equal":
        if len(set(rule["refs"])) < 2: return None                                         # one value (or one id twice) cannot disagree with itself
        vals = {norm(str(v(r))) for r in rule["refs"]}; return len(vals) == 1
    if t == "set_equal":
        a = {norm(x) for x in rule["a"]}; b = {norm(x) for x in rule["b"]}
        return None if not a and not b else a == b
    if t == "date_within":
        d = parse_date(v(rule["ref"])); s, e = parse_date(rule["start"]), parse_date(rule["end"])
        return None if None in (d, s, e) else s <= d <= e
    if t == "required_nonempty":
        val = v(rule["ref"])
        if val is None: return False
        return norm(re.sub(r"[\W_]+", " ", str(val))) not in PLACEHOLDERS
    if t == "count_equals":
        if not isinstance(rule.get("items"), list) or isinstance(rule.get("n"), bool): return None
        try: return len(rule["items"]) == int(rule["n"])
        except (TypeError, ValueError): return None
    return None                                              # unknown rule type: dropped, not guessed

# ---------- 4. issue ledger with stable identity ----------------------------------------------
def issue_key(check, doc, block, quote, name=""):
    """Identity = what and where, NOT the number the model happened to print. Editing the text changes the key."""
    raw = json.dumps([check, doc, block, norm(quote), name], ensure_ascii=False)       # JSON, so a '|' inside a field cannot make two issues collide
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

SEV_RANK = {"I": 0, "W": 1, "E": 2}

def merge(ledger, candidates):
    """ledger: {key: issue}; candidates: [issue]. Re-review reconciliation. Returns new ledger (copy)."""
    new = {k: dict(v) for k, v in ledger.items()}; seen = set()
    for c in candidates:
        if not isinstance(c, dict) or not c.get("key"): raise ValueError("every candidate issue needs a 'key' (use issue_key(...))")
        k = c["key"]; seen.add(k)
        if k not in new: new[k] = dict(c, status="open")
        else:
            if SEV_RANK.get(c.get("severity"), 99) > SEV_RANK.get(new[k].get("severity"), 99): new[k]["severity"] = c["severity"]     # never downgrade a re-found issue
            if new[k]["status"] in ("resolved", "applied"): new[k]["status"] = "open"; new[k]["reopened"] = True
        # open stays open; untracked STAYS untracked (the user said "not a problem" with a reason)
    for k, i in new.items():
        if k not in seen and i["status"] == "open": i["status"] = "resolved"      # re-review confirms it's gone
    return new

def untrack(ledger, key, reason):
    if not str(reason).strip(): raise ValueError("untrack requires a reason")
    ledger[key]["status"] = "untracked"; ledger[key]["reason"] = reason

CLOSED_STATUS = {"resolved", "applied", "untracked"}      # anything else, including "OPEN", "pending" or a missing status, blocks confirmation

def can_confirm(ledger, docs_reviewed_at_current_rev):
    """Final confirmation gate decided by code. Fails closed: an unknown severity or an unknown status counts as blocking, and the review evidence must be explicit."""
    if docs_reviewed_at_current_rev is not True and not (isinstance(docs_reviewed_at_current_rev, (list, tuple, set, dict)) and docs_reviewed_at_current_rev):
        return False, "no document was reviewed at its current revision (pass True or the non-empty list of reviewed documents)"
    for i in ledger.values():
        status = i.get("status"); status = status.strip().lower() if isinstance(status, str) else None
        if status == "open" and i.get("severity") == "I": continue                          # informational findings may stay open
        if status not in CLOSED_STATUS: return False, f"issue with status {i.get('status')!r} and severity {i.get('severity')!r} is not closed (closed = {sorted(CLOSED_STATUS)}; only 'open' severity 'I' may remain)"
        if status == "untracked" and (not isinstance(i.get("reason"), str) or not i["reason"].strip()): return False, "untracked issue without reason"
    return True, "ok"
