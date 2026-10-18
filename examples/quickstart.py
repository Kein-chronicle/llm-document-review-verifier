"""The model proposes facts with quotes; code verifies the quotes and judges the arithmetic."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from reviewkit import verify_claims, evaluate, issue_key, merge, can_confirm

blocks = {"p1": "Unit price: 1,200 won. Quantity: 3. Total: 3,600 won.", "p2": "Delivery by 2026-03-10."}

# What an LLM might return. The second claim is invented: its quote is not in the document.
claims = [
    {"id": "F1", "block": "p1", "quote": "Unit price: 1,200 won", "value": "1,200"},
    {"id": "F2", "block": "p1", "quote": "Quantity: 3", "value": "3"},
    {"id": "F3", "block": "p1", "quote": "Total: 3,600 won", "value": "3,600"},
    {"id": "F4", "block": "p2", "quote": "Delivery by March 12", "value": "2026-03-12"},
]
verified, rejected = verify_claims(claims, blocks)
print("verified:", [c["id"] for c in verified], " rejected (never reach a verdict):", [c["id"] for c in rejected])

facts = {c["id"]: c for c in verified}
print("1,200 x 3 = 3,600 ?", evaluate({"type": "product_equals", "factors": ["F1", "F2"], "result": "F3"}, facts))
print("rule about a rejected fact is dropped:", evaluate({"type": "date_within", "ref": "F4", "start": "2026-03-01", "end": "2026-03-31"}, facts))

# Issues have stable identity, so a re-review does not renumber or resurrect them.
key = issue_key("total-mismatch", "quote.pdf", "p1", "Total: 3,600 won")
ledger = merge({}, [{"key": key, "severity": "E", "status": "open"}])
print("can confirm with an open error:", can_confirm(ledger, True))
ledger = merge(ledger, [])            # the next review no longer finds it
print("after the fix is re-reviewed:  ", can_confirm(ledger, True))
