#!/usr/bin/env python3
"""drill.py — timed lab drills for the three runbooks.

Usage: python3 scripts/drill.py [PACK_ROOT]
Reads the live probe outputs under outputs/ (produced by probe_all.sh)
plus the derived analysis (analyze.py), performs local verification
computations, and makes a small number of additional read-only RPC calls
for the history-gap drill (at most 3 attempts for one old ledger).

Every case records its own measured elapsed time: time.monotonic() is
taken around each case, printed on its PASS/FAIL line as "(X.XX ms)",
and stored as elapsed_ms in outputs/derived/drill-results.json. The
per-drill and total wall-time lines are also printed. No case invents a
timing: the elapsed value on each line is the measured time of that case.

Drill A — fresh-node join (8 cases): what a new node can verify on join.
Drill B — history-gap encounter (6 cases): old-ledger resolution behavior.
Drill C — corrupted-snapshot detection (7 cases): tamper detection by hash.

Exit code 0 only if every case passes.
"""
import base64
import json
import subprocess
import sys
import time
from pathlib import Path

PACK_ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
OUT = PACK_ROOT / "outputs"
sys.path.insert(0, str(PACK_ROOT / "src"))
from snapshot_verifier import (  # noqa: E402
    ledger_hash_from_rpc, verify_chain, hash_of_seq_via_skip_list,
    skip_keylet_for)

RPC = "https://rpc.testnet.postfiat.org/"
ACTIVATION_TX_HASH = "0E373029EEF6AB43E24D5F1EAFBAEB80BBA9B94610BCE1A3D004101CCFAE7048"
GENESIS = "r4vhrMChCsaoFsBoCkRTRGUuc1njfr7bmA"

CASES = []  # (drill, id, label, fn)


def case(drill, cid, label):
    def deco(fn):
        CASES.append((drill, cid, label, fn))
        return fn
    return deco


def load(name):
    with open(OUT / name) as fh:
        return json.load(fh)


def load_ledger(name):
    d = load(name)
    return d["result"].get("ledger")


def rpc(method, params):
    out = subprocess.run(
        ["curl", "-s", "-m", "30", "-X", "POST", RPC,
         "-H", "Content-Type: application/json",
         "-d", json.dumps({"method": method, "params": [params]})],
        capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def expect(cond, detail=""):
    if not cond:
        raise AssertionError(detail or "expectation failed")
    return detail


# ---------------------------------------------------------------- Drill A
@case("A", "A-01", "complete_ledgers is a single contiguous range")
def _():
    info = load("server_info.json")["result"]["info"]
    rng = info["complete_ledgers"]
    lo, hi = (int(x) for x in rng.split("-"))
    validated = info["validated_ledger"]["seq"]
    expect(hi == validated, f"range end {hi} != validated {validated}")
    expect(lo < hi, "empty range")
    return f"{rng} ({hi - lo + 1} ledgers)"


@case("A", "A-02", "earliest ledger header hash recomputes")
def _():
    led = load_ledger("ledger_earliest.json")
    expect(led is not None, "earliest ledger not returned")
    recomputed = ledger_hash_from_rpc(led)
    expect(recomputed == led["ledger_hash"].upper(),
           f"{recomputed} != {led['ledger_hash']}")
    return f"seq {led['ledger_index']} hash MATCH"


@case("A", "A-03", "validated ledger header hash recomputes")
def _():
    led = load_ledger("ledger_validated.json")
    expect(led is not None, "validated ledger not returned")
    recomputed = ledger_hash_from_rpc(led)
    expect(recomputed == led["ledger_hash"].upper(),
           f"{recomputed} != {led['ledger_hash']}")
    return f"seq {led['ledger_index']} hash MATCH"


@case("A", "A-04", "parent chain links hold for 6 consecutive ledgers")
def _():
    headers = [load_ledger(f"ledger_chain_{i}.json") for i in range(6)]
    expect(all(h is not None for h in headers), "a chain header is missing")
    results = verify_chain(headers)
    bad = [r for r in results[:-1] if r["parent_link_ok"] is not True]
    expect(not bad, f"broken links: {bad}")
    expect(all(r["hash_match"] for r in results), "a header hash mismatches")
    seqs = [r["seq"] for r in results]
    return f"seqs {seqs[0]}..{seqs[-1]}: 5/5 links OK, 6/6 hashes MATCH"


@case("A", "A-05", "skip-list hashOfSeq matches the chain headers")
def _():
    skip = load("ledger_entry_skip.json")["result"]
    validated = load("server_info.json")["result"]["info"]["validated_ledger"]["seq"]
    headers = [load_ledger(f"ledger_chain_{i}.json") for i in range(6)]
    checked = 0
    for h in headers[1:]:
        got = hash_of_seq_via_skip_list(skip, validated, int(h["ledger_index"]))
        expect(got == h["ledger_hash"].upper(),
               f"skip-list hash for {h['ledger_index']}: {got} != {h['ledger_hash']}")
        checked += 1
    return f"{checked}/5 skip-list hashes match chain headers"


@case("A", "A-06", "flag-ledger skip anchor matches fetched flag headers")
def _():
    flag = load_ledger("ledger_flag.json")
    flag2 = load("ledger_header_flag2.json")["result"]["ledger"]
    flag3 = load("ledger_header_flag3.json")["result"]["ledger"]
    skip_flag = load("ledger_entry_skip_flag.json")["result"]
    hashes = [h.upper() for h in skip_flag["node"].get("Hashes", [])]
    expect(hashes, "anchor skip entry has no hashes")
    # The anchor entry appends one hash per flag ledger and records the
    # newest flag ledger in LastLedgerSequence, so a flag hash sits at
    # index len-1-(LastSeq-seq)/256, not at the tail.
    last_seq = int(skip_flag["node"]["LastLedgerSequence"])

    def at(seq):
        i = len(hashes) - 1 - (last_seq - int(seq)) // 256
        return hashes[i]

    expect(at(flag["ledger_index"]) == flag["ledger_hash"].upper(),
           "anchor position != flag ledger hash")
    expect(at(flag2["ledger_index"]) == flag2["ledger_hash"].upper(),
           "anchor position != flag-256 hash")
    expect(at(flag3["ledger_index"]) == flag3["ledger_hash"].upper(),
           "anchor position != flag-512 hash")
    return (f"anchor LastSeq {last_seq}: hash({flag['ledger_index']}) at "
            f"tail-{(last_seq - int(flag['ledger_index'])) // 256}, "
            f"hash({flag2['ledger_index']}) and hash({flag3['ledger_index']}) "
            f"match their positions")


@case("A", "A-07", "node is in full state with a fresh validated ledger")
def _():
    info = load("server_info.json")["result"]["info"]
    expect(info["server_state"] == "full", f"state {info['server_state']}")
    age = info["validated_ledger"]["age"]
    expect(age <= 30, f"validated age {age}s")
    expect(info["validation_quorum"] == 17, "quorum != 17")
    return f"state full, validated age {age}s, quorum 17"


@case("A", "A-08", "validator list parses and names the trusted set")
def _():
    vl = load("testnet_vl.json")
    blobs = vl.get("blobs_v2")
    expect(isinstance(blobs, list) and len(blobs) >= 1,
           "no blobs in VL document")
    expect(isinstance(blobs[0].get("signature"), str) and blobs[0]["signature"],
           "no signature on VL blob")
    # The blob is base64 JSON, not a hex protobuf: decode it in stdlib.
    blob = json.loads(base64.b64decode(blobs[0]["blob"]))
    validators = blob.get("validators", [])
    expect(len(validators) == 25, f"VL validators {len(validators)} != 25")
    expect(all(v.get("validation_public_key", "").startswith("ED")
               for v in validators), "a validator key is not ED")
    expect(isinstance(vl.get("manifest"), str) and vl["manifest"],
           "no manifest in VL document")
    expect(isinstance(vl.get("public_key"), str)
           and vl["public_key"].startswith("ED"),
           "no ED publisher public key in VL document")
    # Blob signature math is NOT checked here: no Ed25519 in the stdlib,
    # so signature verification is recorded as UNTESTABLE in the claim index.
    return (f"VL blob sequence {blob.get('sequence')}: "
            f"{len(validators)} validators, publisher key "
            f"{vl['public_key'][:12]}..., manifest present, blob signature "
            f"present but unverified (no Ed25519 in stdlib)")


# ---------------------------------------------------------------- Drill B
@case("B", "B-01", "cold old-ledger lookup resolves within 3 attempts")
def _():
    # 8201001 is inside the complete range and was never probed by
    # probe_all.sh, so the first attempt is genuinely cold: the node must
    # resolve the hash via the skip lists or acquire the candidate flag
    # ledger (getCandidateLedger = next multiple of 256). Record attempts.
    attempts = 0
    last = None
    for attempts in range(1, 4):
        r = rpc("ledger", {"ledger_index": 8201001, "transactions": False})
        last = r.get("result", {})
        if "ledger" in last:
            break
        time.sleep(5)
    expect("ledger" in last, f"no ledger after {attempts} attempts: {last}")
    return f"ledger 8201001 returned on attempt {attempts}"


@case("B", "B-02", "cold-lookup ledger hash recomputes (no wrong hash served)")
def _():
    r = rpc("ledger", {"ledger_index": 8201001, "transactions": False})
    led = r.get("result", {}).get("ledger")
    expect(led is not None, f"no ledger: {r.get('result', {})}")
    recomputed = ledger_hash_from_rpc(led)
    expect(recomputed == led["ledger_hash"].upper(),
           f"{recomputed} != {led['ledger_hash']}")
    return "hash MATCH for cold-lookup ledger 8201001"


@case("B", "B-03", "86785 activation transaction is txnNotFound")
def _():
    res = load("tx_86785.json")["result"]
    expect(res.get("error") == "txnNotFound",
           f"unexpected result: {res}")
    expect(res.get("error_code") == 29, f"error_code {res.get('error_code')}")
    return "txnNotFound error_code 29"


@case("B", "B-04", "account_tx min below earliest is clamped to earliest")
def _():
    res = load("account_tx_genesis.json")["result"]
    info = load("server_info.json")["result"]["info"]
    earliest = int(info["complete_ledgers"].split("-")[0])
    expect(res.get("ledger_index_min") == earliest,
           f"min {res.get('ledger_index_min')} != earliest {earliest}")
    return f"requested min 1, echoed min {earliest}"


@case("B", "B-05", "ledger below earliest returns an error, never a ledger")
def _():
    res = load("ledger_8200053.json")["result"]
    expect("ledger" not in res, f"unexpected ledger object: {res}")
    expect("error" in res, f"no error field: {res}")
    return f"error {res.get('error')} code {res.get('error_code')}"


@case("B", "B-06", "86785 activation event is not re-derivable from the node")
def _():
    tx = load("tx_86785.json")["result"]
    expect(tx.get("error") == "txnNotFound", "activation tx unexpectedly found")
    # The VHS records the bulk activation: all 64 amendments at ledger
    # 86785 on 2026-02-09. The node has none of it.
    vt = load("vhs-amendments-vote-test.json")
    at = [a for a in vt.get("amendments", []) if a.get("ledger_index") == 86785]
    expect(len(at) == 64, f"VHS amendments at 86785: {len(at)}")
    return (f"activation tx txnNotFound; VHS records {len(at)} amendments "
            f"at 86785 on {at[0]['date']}, none re-derivable from the node")


# ---------------------------------------------------------------- Drill C
def _validated_header():
    return load_ledger("ledger_validated.json")


@case("C", "C-01", "flipping drops changes the recomputed hash")
def _():
    led = dict(_validated_header())
    orig = ledger_hash_from_rpc(led)
    led["total_coins"] = str(int(led["total_coins"]) + 1)
    tampered = ledger_hash_from_rpc(led)
    expect(tampered != orig, "hash unchanged after drops flip")
    expect(tampered != led["ledger_hash"].upper(), "tampered hash matches claim")
    return "drops+1 -> hash differs from claimed hash"


@case("C", "C-02", "flipping parentHash changes the recomputed hash")
def _():
    led = dict(_validated_header())
    orig = ledger_hash_from_rpc(led)
    ph = bytearray(bytes.fromhex(led["parent_hash"]))
    ph[0] ^= 0x01
    led["parent_hash"] = ph.hex().upper()
    tampered = ledger_hash_from_rpc(led)
    expect(tampered != orig, "hash unchanged after parentHash flip")
    return "parentHash bit flip -> hash differs from claimed hash"


@case("C", "C-03", "flipping accountHash changes the recomputed hash")
def _():
    led = dict(_validated_header())
    orig = ledger_hash_from_rpc(led)
    ah = bytearray(bytes.fromhex(led["account_hash"]))
    ah[-1] ^= 0x01
    led["account_hash"] = ah.hex().upper()
    tampered = ledger_hash_from_rpc(led)
    expect(tampered != orig, "hash unchanged after accountHash flip")
    return "accountHash bit flip -> hash differs from claimed hash"


@case("C", "C-04", "tampered parent link is detected by the chain check")
def _():
    headers = [load_ledger(f"ledger_chain_{i}.json") for i in range(6)]
    headers = [dict(h) for h in headers]
    ph = bytearray(bytes.fromhex(headers[0]["parent_hash"]))
    ph[5] ^= 0xFF
    headers[0]["parent_hash"] = ph.hex().upper()
    results = verify_chain(headers)
    expect(results[0]["parent_link_ok"] is False,
           "tampered link not detected")
    return "parent link V -> V-1 reported False after tamper"


@case("C", "C-05", "tampered skip-list entry fails the hashOfSeq cross-check")
def _():
    skip = load("ledger_entry_skip.json")["result"]
    validated = load("server_info.json")["result"]["info"]["validated_ledger"]["seq"]
    headers = [load_ledger(f"ledger_chain_{i}.json") for i in range(6)]
    target = headers[1]
    tampered = json.loads(json.dumps(skip))
    hs = tampered["node"]["Hashes"]
    idx = len(hs) - 1  # position holding hash(V-1)
    bad = bytearray(bytes.fromhex(hs[idx]))
    bad[0] ^= 0x01
    hs[idx] = bad.hex().upper()
    got = hash_of_seq_via_skip_list(tampered, validated, int(target["ledger_index"]))
    expect(got != target["ledger_hash"].upper(),
           "tampered skip entry still matches chain header")
    return "skip-list hash(V-1) no longer matches chain header after tamper"


@case("C", "C-06", "flipping close_flags changes the recomputed hash")
def _():
    led = dict(_validated_header())
    orig = ledger_hash_from_rpc(led)
    led["close_flags"] = int(led["close_flags"]) ^ 0x01
    tampered = ledger_hash_from_rpc(led)
    expect(tampered != orig, "hash unchanged after close_flags flip")
    return "close_flags flip -> hash differs from claimed hash"


@case("C", "C-07", "hash-swap between two headers is detected")
def _():
    h_new = dict(_validated_header())
    h_old = load_ledger("ledger_chain_1.json")
    claimed = h_old["ledger_hash"]
    recomputed = ledger_hash_from_rpc(h_new)
    expect(recomputed != claimed.upper(),
           "swapped hash unexpectedly matches recomputation")
    return "hash of V-1 claimed for V -> recomputation differs"


# ---------------------------------------------------------------- runner
def main():
    log_lines = []
    results = []
    n_pass = 0
    t_start = time.monotonic()
    per_drill = {}

    for drill, cid, label, fn in CASES:
        t0 = time.monotonic()
        try:
            detail = fn()
            status = "PASS"
            n_pass += 1
        except Exception as exc:  # noqa: BLE001 - record the failure, keep going
            detail = f"FAIL: {exc}"
            status = "FAIL"
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        per_drill.setdefault(drill, 0.0)
        per_drill[drill] += elapsed_ms
        line = f"{status} {cid} {label} — {detail} ({elapsed_ms:.2f} ms)"
        log_lines.append(line)
        print(line)
        results.append({
            "drill": drill,
            "id": cid,
            "label": label,
            "pass": status == "PASS",
            "detail": detail,
            "elapsed_ms": round(elapsed_ms, 2),
        })

    total_s = time.monotonic() - t_start
    counts = {}
    for drill, _, _, _ in CASES:
        counts[drill] = counts.get(drill, 0) + 1
    summary = (f"drill result: {n_pass}/{len(CASES)} cases PASS "
               f"({', '.join(f'{d} {counts[d]}' for d in sorted(counts))})")
    wall = (f"drill wall time: {total_s:.2f} s "
            f"({', '.join(f'{d} {per_drill[d] / 1000:.2f} s' for d in sorted(per_drill))})")
    log_lines.append(summary)
    log_lines.append(wall)
    print(summary)
    print(wall)

    (OUT / "drill-run.log").write_text("\n".join(log_lines) + "\n")
    (OUT / "derived").mkdir(exist_ok=True)
    with open(OUT / "derived" / "drill-results.json", "w") as fh:
        json.dump({"cases": results,
                   "summary": summary,
                   "wall_s": round(total_s, 2)}, fh, indent=1)
        fh.write("\n")
    if n_pass != len(CASES):
        sys.exit(1)


if __name__ == "__main__":
    main()
