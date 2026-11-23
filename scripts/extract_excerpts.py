#!/usr/bin/env python3
"""extract_excerpts.py — pull verbatim pinned-source excerpts into fixtures/.

Usage: python3 scripts/extract_excerpts.py [PACK_ROOT]
The pinned postfiatd checkout must be at /tmp/postfiatd-pin (or
$POSTFIATD_PIN). The script verifies `git rev-parse HEAD` equals the
pinned commit, extracts the listed line ranges (each range is asserted to
contain its anchor text), writes fixtures/source-excerpts/*.txt with a
header giving the file path and line numbers, and writes
fixtures/source-hashes.json with SHA-256 digests and git blob SHAs.

Line numbers are never taken from a web fetch: they come from grep -n on
the local checkout of the pinned commit.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

PACK_ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
PIN = os.environ.get("POSTFIATD_PIN", "/tmp/postfiatd-pin")
COMMIT = "0085a1ff885d6a446369cf73a4430f75af22be55"

# (output file, [(source path, first line, last line, anchor text), ...])
EXCERPTS = [
    ("ledger-hash-calc.txt", [
        ("src/xrpld/app/ledger/Ledger.cpp", 53, 68, "calculateLedgerHash"),
    ]),
    ("ledger-header-fields.txt", [
        ("include/xrpl/protocol/LedgerHeader.h", 40, 73, "uint256 txHash"),
    ]),
    ("ledger-hash-prefix.txt", [
        ("include/xrpl/protocol/HashPrefix.h", 31, 37, "make_hash_prefix"),
        ("include/xrpl/protocol/HashPrefix.h", 66, 70, "ledgerMaster"),
    ]),
    ("ledger-set-immutable.txt", [
        ("src/xrpld/app/ledger/Ledger.cpp", 357, 374, "setImmutable"),
    ]),
    ("ledger-skip-list.txt", [
        ("src/xrpld/app/ledger/Ledger.cpp", 900, 968, "updateSkipList"),
    ]),
    ("hash-of-seq.txt", [
        ("src/libxrpl/ledger/View.cpp", 1040, 1102, "hashOfSeq"),
    ]),
    ("candidate-ledger.txt", [
        ("include/xrpl/ledger/View.h", 505, 524, "getCandidateLedger"),
    ]),
    ("flag-ledger-interval.txt", [
        ("src/xrpld/app/ledger/Ledger.h", 426, 430, "FLAG_LEDGER_INTERVAL"),
    ]),
    ("ledger-complete-range.txt", [
        ("src/xrpld/app/ledger/detail/LedgerMaster.cpp", 1612, 1620, "getCompleteLedgers"),
        ("src/xrpld/app/ledger/detail/LedgerMaster.cpp", 826, 886, "setFullLedger"),
    ]),
    ("fetch-for-history.txt", [
        ("src/xrpld/app/ledger/detail/LedgerMaster.cpp", 1825, 1936, "fetchForHistory"),
    ]),
    ("fetch-pack-request.txt", [
        ("src/xrpld/app/ledger/detail/LedgerMaster.cpp", 723, 768, "getFetchPack"),
    ]),
    ("get-ledger-hash-for-history.txt", [
        ("src/xrpld/app/ledger/detail/LedgerMaster.cpp", 1208, 1227, "getLedgerHashForHistory"),
    ]),
    ("do-advance-history-fill.txt", [
        ("src/xrpld/app/ledger/detail/LedgerMaster.cpp", 1940, 2028, "doAdvance"),
    ]),
    ("should-acquire.txt", [
        ("src/xrpld/app/ledger/detail/LedgerMaster.cpp", 75, 99, "shouldAcquire"),
    ]),
    ("inbound-ledger-timeouts.txt", [
        ("src/xrpld/app/ledger/detail/InboundLedger.cpp", 48, 74, "ledgerAcquireTimeout"),
        ("src/xrpld/app/ledger/detail/InboundLedger.cpp", 376, 391, "ledgerTimeoutRetriesMax"),
    ]),
    ("inbound-ledger-fetch-root.txt", [
        ("src/xrpld/app/ledger/detail/InboundLedger.cpp", 300, 361, "fetchRoot"),
    ]),
    ("inbound-ledger-needed-hashes.txt", [
        ("src/xrpld/app/ledger/detail/InboundLedger.cpp", 1007, 1041, "getNeededHashes"),
    ]),
    ("shamapstore-online-delete.txt", [
        ("src/xrpld/app/misc/SHAMapStoreImp.cpp", 121, 163, "online_delete"),
        ("src/xrpld/app/misc/SHAMapStoreImp.cpp", 323, 333, "deleteInterval_"),
    ]),
    ("ledger-cleaner.txt", [
        ("src/xrpld/app/ledger/detail/LedgerCleaner.cpp", 382, 456, "doLedgerCleaner"),
    ]),
    ("get-ledger-by-context.txt", [
        ("src/xrpld/rpc/detail/RPCHelpers.cpp", 1030, 1145, "getLedgerByContext"),
    ]),
    ("ledger-replay-hash-check.txt", [
        ("src/xrpld/app/ledger/detail/LedgerReplayMsgHandler.cpp", 134, 154, "calculateLedgerHash"),
    ]),
    ("validator-list-verify.txt", [
        ("src/xrpld/app/misc/ValidatorList.h", 880, 895, "verify("),
    ]),
    ("ledger-request-rpc.txt", [
        ("src/xrpld/rpc/handlers/LedgerRequest.cpp", 36, 49, "doLedgerRequest"),
    ]),
    ("txn-not-found.txt", [
        ("src/libxrpl/protocol/ErrorCodes.cpp", 113, 117, "txnNotFound"),
    ]),
    ("config-ledger-history.txt", [
        ("src/xrpld/core/detail/Config.cpp", 652, 661, "LEDGER_HISTORY"),
    ]),
    ("ledger-master-get-by-seq.txt", [
        ("src/xrpld/app/ledger/detail/LedgerMaster.cpp", 1730, 1763, "getLedgerBySeq"),
    ]),
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob_sha(path):
    out = subprocess.run(["git", "-C", PIN, "hash-object", path],
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


def main():
    head = subprocess.run(["git", "-C", PIN, "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    assert head == COMMIT, f"pinned checkout HEAD {head} != {COMMIT}"
    print(f"pinned checkout verified: {head}")

    outdir = PACK_ROOT / "fixtures" / "source-excerpts"
    outdir.mkdir(parents=True, exist_ok=True)
    hashes = {"pinned_commit": COMMIT, "files": {}, "excerpts": {},
              "absence_checks": {}}

    for name, blocks in EXCERPTS:
        parts = []
        for src, first, last, anchor in blocks:
            lines = Path(PIN, src).read_text().splitlines()
            assert first >= 1 and last <= len(lines), f"{src} range out of bounds"
            chunk = lines[first - 1:last]
            assert any(anchor in ln for ln in chunk), \
                f"anchor {anchor!r} not in {src}:{first}-{last}"
            parts.append(
                f"# --- {src} lines {first}-{last} ---\n" + "\n".join(chunk))
            f = hashes["files"].setdefault(src, {})
            f["sha256"] = sha256_file(Path(PIN, src))
            f["git_blob_sha"] = git_blob_sha(src)
            f["lines"] = len(lines)
        text = (f"# Source excerpts — postfiatd {COMMIT} "
                f"(2026-10-10, PR #50 merge, v1.0.9).\n"
                f"# Line numbers verified with grep -n on a local checkout "
                f"of the pinned commit.\n\n" + "\n\n".join(parts) + "\n")
        (outdir / name).write_text(text)
        hashes["excerpts"][name] = {
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "blocks": [{"file": s, "lines": f"{a}-{b}"} for s, a, b, _ in blocks],
        }
        print(f"wrote fixtures/source-excerpts/{name}")

    # Absence checks: no native ledger-snapshot export/import in the RPC
    # surface or ledger code (state sync is SHAMap fetch from peers only).
    for label, args in [
        ("snapshot RPC handler", ["grep", "-ril", "snapshot",
                                  "src/xrpld/rpc/handlers/"]),
        ("snapshot in ledger acquisition", ["grep", "-ril", "snapshot",
                                           "src/xrpld/app/ledger/InboundLedger.h",
                                           "src/xrpld/app/ledger/detail/InboundLedger.cpp"]),
    ]:
        out = subprocess.run(args, cwd=PIN, capture_output=True, text=True)
        matches = [ln for ln in out.stdout.splitlines() if ln.strip()]
        hashes["absence_checks"][label] = {
            "pattern": "snapshot (case-insensitive)",
            "matches": len(matches),
            "files": matches,
        }
        print(f"absence check {label}: {len(matches)} matches")

    with open(PACK_ROOT / "fixtures" / "source-hashes.json", "w") as fh:
        json.dump(hashes, fh, indent=1)
        fh.write("\n")
    print("wrote fixtures/source-hashes.json")


if __name__ == "__main__":
    main()
