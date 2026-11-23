#!/usr/bin/env python3
"""measure_cadence.py — measure live ledger cadence over a 60 s window.

Usage: python3 scripts/measure_cadence.py [OUTPUT_DIR]
Reads server_info twice, 60 s apart, and writes outputs/derived/cadence.json.
Read-only; two RPC calls.
"""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone

RPC = "https://rpc.testnet.postfiat.org/"


def server_info():
    out = subprocess.run(
        ["curl", "-s", "-m", "30", "-X", "POST", RPC,
         "-H", "Content-Type: application/json",
         "-d", '{"method":"server_info","params":[{}]}'],
        capture_output=True, text=True, check=True)
    return json.loads(out.stdout)["result"]["info"]


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "outputs"
    t0 = time.time()
    info1 = server_info()
    seq1 = info1["validated_ledger"]["seq"]
    print(f"cadence probe start: seq {seq1} at "
          f"{datetime.fromtimestamp(t0, timezone.utc).isoformat()}")
    time.sleep(60)
    t1 = time.time()
    info2 = server_info()
    seq2 = info2["validated_ledger"]["seq"]
    elapsed = t1 - t0
    ledgers = seq2 - seq1
    cadence = elapsed / ledgers if ledgers else None
    print(f"cadence probe end: seq {seq2} at "
          f"{datetime.fromtimestamp(t1, timezone.utc).isoformat()}")
    print(f"ledger cadence: {cadence:.3f} s/ledger "
          f"({ledgers} ledgers in {elapsed:.1f} s)" if cadence else
          "ledger cadence: no advance in window")
    data = {
        "window_s": round(elapsed, 1),
        "seq_start": seq1,
        "seq_end": seq2,
        "ledgers": ledgers,
        "cadence_s_per_ledger": round(cadence, 3) if cadence else None,
        "validated_hash_end": info2["validated_ledger"]["hash"],
        "build_version": info2["build_version"],
        "network_id": info2["network_id"],
        "peers": info2["peers"],
        "validation_quorum": info2["validation_quorum"],
    }
    with open(f"{outdir}/derived/cadence.json", "w") as fh:
        json.dump(data, fh, indent=1)
        fh.write("\n")
    print("wrote derived/cadence.json")


if __name__ == "__main__":
    main()
