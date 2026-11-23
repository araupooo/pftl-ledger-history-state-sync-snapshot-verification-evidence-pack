#!/usr/bin/env python3
"""compare_reproduce.py — compare a fresh clean_reproduce.sh run against
the shipped numbers.

Usage: python3 scripts/compare_reproduce.py <shipped-manifest.json>
Exits 0 only if every comparison check passes. Writes
outputs/derived/compare-results.json.
"""
import json
import os
import sys

PACK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    shipped = load(sys.argv[1])
    fresh = load(os.path.join(PACK, "run-manifest.json"))
    snap = load(os.path.join(PACK, "outputs", "derived",
                             "snapshot-verification.json"))
    drill = load(os.path.join(PACK, "outputs", "derived",
                              "drill-results.json"))
    gaps = load(os.path.join(PACK, "outputs", "derived",
                             "history-gaps.json"))
    checks = []

    def check(label, ok, detail=""):
        checks.append({"check": label, "pass": bool(ok), "detail": detail})
        print(("PASS " if ok else "FAIL ") + label +
              ((" — " + detail) if detail else ""))

    sc, fc = shipped["counts"], fresh["counts"]
    check("findings total unchanged",
          fc["findings"]["total"] == sc["findings"]["total"],
          "%d vs shipped %d" % (fc["findings"]["total"], sc["findings"]["total"]))
    check("claims total unchanged",
          fc["claims"]["total"] == sc["claims"]["total"],
          "%d vs shipped %d" % (fc["claims"]["total"], sc["claims"]["total"]))
    check("risks total unchanged",
          fc["risks"]["total"] == sc["risks"]["total"],
          "%d vs shipped %d" % (fc["risks"]["total"], sc["risks"]["total"]))
    check("gaps total unchanged",
          fc["gaps"] == sc["gaps"],
          "%d vs shipped %d" % (fc["gaps"], sc["gaps"]))
    check("history earliest unchanged",
          fresh["earliest_ledger"] == shipped["earliest_ledger"],
          "%d vs shipped %d" % (fresh["earliest_ledger"], shipped["earliest_ledger"]))
    check("validated ledger advanced",
          fresh["validated_ledger"] > shipped["validated_ledger"],
          "%d vs shipped %d" % (fresh["validated_ledger"], shipped["validated_ledger"]))
    check("build version unchanged",
          fresh["build_version"] == shipped["build_version"],
          fresh["build_version"])
    check("hash recomputation still all MATCH",
          snap["hash_matches"] == snap["headers_recomputed"],
          "%d/%d" % (snap["hash_matches"], snap["headers_recomputed"]))
    check("chain links still all OK",
          snap["chain_links_ok"] == snap["chain_links_total"],
          "%d/%d" % (snap["chain_links_ok"], snap["chain_links_total"]))
    check("drill still 21/21 PASS",
          sum(1 for c in drill["cases"] if c["pass"]) == 21 and len(drill["cases"]) == 21,
          drill["summary"])
    check("every drill case has a per-case elapsed time",
          all("elapsed_ms" in c and c["elapsed_ms"] >= 0 for c in drill["cases"]),
          "%d cases" % len(drill["cases"]))
    check("86785 activation tx still txnNotFound",
          gaps["activation_tx_86785"]["error"] == "txnNotFound",
          str(gaps["activation_tx_86785"]))
    check("account_tx still clamps to earliest",
          gaps["account_tx_clamp"]["echoed_min"] == fresh["earliest_ledger"],
          "echoed min %s" % gaps["account_tx_clamp"]["echoed_min"])

    passed = sum(1 for c in checks if c["pass"])
    with open(os.path.join(PACK, "outputs", "derived", "compare-results.json"), "w") as fh:
        json.dump({"checks": checks, "passed": passed, "total": len(checks)},
                  fh, indent=1)
        fh.write("\n")
    print(f"compare: {passed}/{len(checks)} checks PASS")
    if passed != len(checks):
        sys.exit(1)


if __name__ == "__main__":
    main()
