#!/usr/bin/env python3
"""analyze.py — derive the pack's measured results from the live probe outputs.

Usage: python3 scripts/analyze.py [PACK_ROOT]
Reads outputs/*.json (unedited probe responses) and writes derived JSONs
under outputs/derived/:
  history-range.json   — earliest/validated ledgers, span, time span
  chain-check.json     — parent-chain + hash-recomputation results
  skip-list-check.json — skip-list hashOfSeq emulation results
  snapshot-verification.json — aggregate verification summary
  history-gaps.json    — what is / is not re-derivable, with the 86785 case

No network access. All inputs are files already on disk.
"""
import json
import sys
from pathlib import Path

PACK_ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
OUT = PACK_ROOT / "outputs"
sys.path.insert(0, str(PACK_ROOT / "src"))
from snapshot_verifier import (  # noqa: E402
    ledger_hash_from_rpc, verify_chain, hash_of_seq_via_skip_list,
    skip_keylet_for)


def load(name):
    with open(OUT / name) as fh:
        return json.load(fh)


def ledger_of(name):
    return load(name)["result"].get("ledger")


def write(name, data):
    (OUT / "derived").mkdir(exist_ok=True)
    with open(OUT / "derived" / name, "w") as fh:
        json.dump(data, fh, indent=1)
        fh.write("\n")
    print(f"wrote derived/{name}")


def main():
    info = load("server_info.json")["result"]["info"]
    earliest = int(info["complete_ledgers"].split("-")[0])
    validated = info["validated_ledger"]["seq"]
    validated_hash = info["validated_ledger"]["hash"]

    # ---- history range ----
    earliest_led = ledger_of("ledger_earliest.json")
    validated_led = ledger_of("ledger_validated.json")
    cadence = {}
    try:
        cadence = load("derived/cadence.json")
    except FileNotFoundError:
        cadence = {"cadence_s_per_ledger": None}
    span_ledgers = validated - earliest + 1
    time_span_s = None
    if earliest_led and validated_led:
        time_span_s = int(validated_led["close_time"]) - int(earliest_led["close_time"])
    history_range = {
        "earliest_ledger": earliest,
        "validated_ledger": validated,
        "validated_hash": validated_hash,
        "complete_ledgers": info["complete_ledgers"],
        "ledgers_in_range": span_ledgers,
        "ledgers_before_earliest": earliest - 1,
        "time_span_s": time_span_s,
        "time_span_days": round(time_span_s / 86400, 2) if time_span_s else None,
        "cadence_s_per_ledger": cadence.get("cadence_s_per_ledger"),
        "build_version": info["build_version"],
        "network_id": info["network_id"],
        "peers": info["peers"],
        "validation_quorum": info["validation_quorum"],
    }
    write("history-range.json", history_range)

    # ---- chain check: 6 consecutive + 3 earliest headers ----
    headers = []
    for i in range(6):
        h = ledger_of(f"ledger_chain_{i}.json")
        if h:
            headers.append(h)
    chain_results = verify_chain(headers)
    earliest_headers = []
    for i in range(3):
        h = ledger_of(f"ledger_chain_earliest_{i}.json")
        if h:
            earliest_headers.append(h)
    # verify_chain expects newest-first; the earliest run is fetched
    # oldest-first, so reverse it before checking parent links.
    earliest_headers = list(reversed(earliest_headers))
    earliest_results = verify_chain(earliest_headers)
    chain_check = {
        "consecutive_run": {
            "seqs": [r["seq"] for r in chain_results],
            "hash_matches": sum(1 for r in chain_results if r["hash_match"]),
            "hash_total": len(chain_results),
            "parent_links_ok": sum(1 for r in chain_results[:-1]
                                   if r["parent_link_ok"] is True),
            "parent_links_total": max(len(chain_results) - 1, 0),
            "results": chain_results,
        },
        "earliest_run": {
            "seqs": [r["seq"] for r in earliest_results],
            "hash_matches": sum(1 for r in earliest_results if r["hash_match"]),
            "hash_total": len(earliest_results),
            "parent_links_ok": sum(1 for r in earliest_results[:-1]
                                   if r["parent_link_ok"] is True),
            "parent_links_total": max(len(earliest_results) - 1, 0),
            "results": earliest_results,
        },
    }
    write("chain-check.json", chain_check)

    # ---- skip-list check ----
    skip = load("ledger_entry_skip.json")["result"]
    skip_flag = load("ledger_entry_skip_flag.json")["result"]
    flag = ledger_of("ledger_flag.json")
    flag2 = ledger_of("ledger_header_flag2.json")
    flag3 = load("ledger_header_flag3.json")["result"].get("ledger")
    rolling = []
    for h in headers[1:]:
        got = hash_of_seq_via_skip_list(skip, validated, int(h["ledger_index"]))
        rolling.append({
            "seq": int(h["ledger_index"]),
            "skip_list_hash": got,
            "header_hash": h["ledger_hash"].upper(),
            "match": got == h["ledger_hash"].upper(),
        })
    anchor_hashes = [x.upper() for x in skip_flag["node"].get("Hashes", [])]
    # Anchor entries append one hash per flag ledger in the 65536-ledger
    # block and set LastLedgerSequence to the newest flag ledger, so a
    # flag hash sits at index len-1-(LastSeq-seq)/256, NOT at the tail
    # unless it is the newest flag ledger. (Verified live: LastSeq 8284416,
    # hash(8284160) at tail-1, hash(8283904) at tail-2, hash(8283648) at
    # tail-3.)
    last_seq = int(skip_flag["node"].get("LastLedgerSequence", 0))

    def anchor_pos(seq):
        return len(anchor_hashes) - 1 - (last_seq - int(seq)) // 256

    def anchor_matches(seq, ledger):
        if not anchor_hashes or ledger is None:
            return False
        i = anchor_pos(seq)
        return 0 <= i < len(anchor_hashes) and \
            anchor_hashes[i] == ledger["ledger_hash"].upper()

    anchor = {
        "anchor_seq": int(flag["ledger_index"]) if flag else None,
        "anchor_last_seq": last_seq,
        "entries": len(anchor_hashes),
        "tail_matches_flag": anchor_matches(int(flag["ledger_index"]), flag) if flag else False,
        "minus1_matches_flag2": anchor_matches(int(flag2["ledger_index"]), flag2) if flag2 else False,
        "minus2_matches_flag3": anchor_matches(int(flag3["ledger_index"]), flag3) if flag3 else False,
        "skip_keylet_for_flag": skip_keylet_for(int(flag["ledger_index"])) if flag else None,
    }
    skip_check = {"rolling_window": rolling, "anchor": anchor}
    write("skip-list-check.json", skip_check)

    # ---- snapshot verification aggregate ----
    # Every header fetched by either the `ledger` or the `ledger_header`
    # method is recomputed: 12 via `ledger` plus 5 via `ledger_header`
    # (flag, flag-256, flag-512, earliest, validated).
    all_headers = []
    for name in ["ledger_earliest.json", "ledger_validated.json",
                 "ledger_flag.json",
                 "ledger_header_flag.json", "ledger_header_flag2.json",
                 "ledger_header_flag3.json", "ledger_header_earliest.json",
                 "ledger_header_validated.json"] + \
            [f"ledger_chain_{i}.json" for i in range(6)] + \
            [f"ledger_chain_earliest_{i}.json" for i in range(3)]:
        h = ledger_of(name)
        if h:
            all_headers.append(h)
    recomputed = []
    for h in all_headers:
        calc = ledger_hash_from_rpc(h)
        recomputed.append({
            "seq": int(h["ledger_index"]),
            "reported": h["ledger_hash"].upper(),
            "recomputed": calc,
            "match": calc == h["ledger_hash"].upper(),
        })
    snapshot = {
        "headers_recomputed": len(recomputed),
        "hash_matches": sum(1 for r in recomputed if r["match"]),
        "chain_links_ok": chain_check["consecutive_run"]["parent_links_ok"] +
            chain_check["earliest_run"]["parent_links_ok"],
        "chain_links_total": chain_check["consecutive_run"]["parent_links_total"] +
            chain_check["earliest_run"]["parent_links_total"],
        "skip_rolling_matches": sum(1 for r in rolling if r["match"]),
        "skip_rolling_total": len(rolling),
        "anchor_ok": anchor["tail_matches_flag"] and
            anchor["minus1_matches_flag2"] and anchor["minus2_matches_flag3"],
        "results": recomputed,
    }
    write("snapshot-verification.json", snapshot)

    # ---- history gaps: what can / cannot be re-derived ----
    def outcome(name):
        res = load(name)["result"]
        if "ledger" in res:
            return {"resolvable": True,
                    "hash": res["ledger"]["ledger_hash"][:16] + "..."}
        return {"resolvable": False, "error": res.get("error"),
                "error_code": res.get("error_code")}

    gaps = {
        "complete_range": info["complete_ledgers"],
        "below_earliest_unresolvable": earliest - 1,
        "probes": {
            "ledger_8200053": outcome("ledger_8200053.json"),
            "ledger_86784": outcome("ledger_86784.json"),
            "ledger_86785": outcome("ledger_86785.json"),
            "ledger_8200054_earliest": outcome("ledger_earliest.json"),
        },
        "activation_tx_86785": {
            "error": load("tx_86785.json")["result"].get("error"),
            "error_code": load("tx_86785.json")["result"].get("error_code"),
        },
        # VHS-only provenance for the bulk activation: all 64 amendments in
        # the VHS vote record share ledger 86785 and one timestamp. The
        # node holds none of it (see probes above), so the event is not
        # re-derivable from node data.
        "activation_86785_vhs": {
            "amendments_at_86785": sum(
                1 for a in load("vhs-amendments-vote-test.json").get("amendments", [])
                if a.get("ledger_index") == 86785),
            "date": next(
                (a["date"] for a in load("vhs-amendments-vote-test.json").get("amendments", [])
                 if a.get("ledger_index") == 86785), None),
            "node_rederivable": False,
        },
        "account_tx_clamp": {
            "requested_min": 1,
            "echoed_min": load("account_tx_genesis.json")["result"].get("ledger_index_min"),
            "echoed_max": load("account_tx_genesis.json")["result"].get("ledger_index_max"),
        },
    }
    write("history-gaps.json", gaps)

    print(f"history: earliest {earliest}, validated {validated}, "
          f"in-range {span_ledgers} ledgers, "
          f"before-earliest {earliest - 1} ledgers")
    print(f"hash recomputation: {snapshot['hash_matches']}/{snapshot['headers_recomputed']} MATCH")
    print(f"chain links: {snapshot['chain_links_ok']}/{snapshot['chain_links_total']} OK")

    # ---- run manifest: counts recomputed from the authored tables ----
    from collections import Counter
    findings = json.loads((PACK_ROOT / "findings.json").read_text())
    fitems = findings if isinstance(findings, list) else findings.get("findings", findings)
    claim_rows = [ln for ln in (PACK_ROOT / "docs" / "claim-index.md").read_text().splitlines()
                  if ln.startswith("| C-")]
    claim_status = Counter(r.split("|")[2].strip() for r in claim_rows)
    risk_rows = [ln for ln in (PACK_ROOT / "docs" / "risk-register.md").read_text().splitlines()
                 if ln.startswith("| R-")]
    risk_sev = Counter(r.split("|")[2].strip() for r in risk_rows)
    gap_rows = [ln for ln in (PACK_ROOT / "docs" / "gap-register.md").read_text().splitlines()
                if ln.startswith("| G-")]
    manifest = {
        "pack": "PFTL Ledger History, State-Sync, and Snapshot Verification Evidence Pack",
        "pinned_commit": "0085a1ff885d6a446369cf73a4430f75af22be55",
        "validated_ledger": validated,
        "validated_hash": validated_hash,
        "earliest_ledger": earliest,
        "build_version": info["build_version"],
        "network_id": info["network_id"],
        "counts": {
            "findings": {
                "total": len(fitems),
                "by_severity": dict(Counter(i.get("severity") for i in fitems)),
                "by_status": dict(Counter(i.get("status") for i in fitems)),
            },
            "claims": {
                "total": len(claim_rows),
                "by_status": dict(claim_status),
            },
            "risks": {
                "total": len(risk_rows),
                "by_severity": dict(risk_sev),
            },
            "gaps": len(gap_rows),
        },
        "verification": {
            "headers_recomputed": snapshot["headers_recomputed"],
            "hash_matches": snapshot["hash_matches"],
            "chain_links_ok": snapshot["chain_links_ok"],
            "chain_links_total": snapshot["chain_links_total"],
        },
    }
    (PACK_ROOT / "run-manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print("wrote run-manifest.json")


if __name__ == "__main__":
    main()
