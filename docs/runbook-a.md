# Runbook A — fresh-node join

How a fresh node verifies synchronized state on joining, using only
public data. Run with `python3 scripts/drill.py` (cases A-01 to A-08).
Measured timings are from the 2026-11-23 run
(`outputs/drill-run.log`); re-runs vary, mainly the two live RPC cases.

## Decision tree

```
1. Fetch server_info.
   ├─ server_state != "full" → DO NOT TRUST the node's data yet.
   │  Wait for "full" (state_accounting shows the time in each state).
   └─ server_state == "full" → continue.
2. Read complete_ledgers (e.g. 8200054-8284498).
   ├─ Empty or a single ledger → the node has no history to verify;
   │  treat all history claims as unverified.
   └─ A range → continue.
3. Fetch the earliest and validated headers; recompute both hashes
   with src/snapshot_verifier.py.
   ├─ Either hash mismatches → the node served bad headers. STOP;
   │  fetch the same headers from a second node.
   └─ Both MATCH → continue.
4. Fetch 6 consecutive validated headers; check the 5 parent links
   and recompute all 6 hashes.
   ├─ Any link fails or hash mismatches → the chain is broken.
   │  STOP; do not use this node's ledgers.
   └─ All OK → continue.
5. Fetch the rolling skip-list entry (keylet sha512Half(0x73));
   check 5 hashOfSeq results against the chain headers.
   ├─ Any mismatch → the skip list disagrees with the headers.
   │  STOP; the node is serving inconsistent state.
   └─ All match → continue.
6. Fetch the anchor skip entry for the newest flag ledger;
   check 3 flag hashes at their LastLedgerSequence positions.
   ├─ Any mismatch → anchor data is inconsistent. STOP.
   └─ All match → continue.
7. Check validated age (≤ 30 s) and quorum (17).
   ├─ Age > 30 s → the node is stale; wait for a fresh validation.
   └─ Age ≤ 30 s, quorum 17 → continue.
8. Fetch and decode the validator list (postfiat.org/testnet_vl.json):
   sequence, 25 validators, ED publisher key, manifest present.
   ├─ Decode fails, count != 25, or key is not ED → DO NOT TRUST
   │  the list; fetch it from a second source.
   └─ All present → the node is verified as synchronized.
      (Blob signature verification is UNTESTABLE in this pack — see G-03.)
```

## Cases and measured timings (2026-11-23 run, 8/8 PASS)

| Case | Check | Result | Time |
|------|-------|--------|------|
| A-01 | `complete_ledgers` is a single contiguous range | 8200054-8284498 (84,445 ledgers) | 0.24 ms |
| A-02 | Earliest header hash recomputes | seq 8200054 MATCH | 0.20 ms |
| A-03 | Validated header hash recomputes | seq 8284498 MATCH | 0.11 ms |
| A-04 | Parent chain links hold (6 ledgers) | 5/5 links OK, 6/6 hashes MATCH | 0.49 ms |
| A-05 | Skip-list `hashOfSeq` matches chain headers | 5/5 match | 0.68 ms |
| A-06 | Flag-ledger skip anchor matches flag headers | LastSeq 8284416; 3/3 positions match | 0.30 ms |
| A-07 | Node in full state, fresh validated ledger | state full, age 1 s, quorum 17 | 0.08 ms |
| A-08 | Validator list parses, names the trusted set | sequence 30, 25 validators, ED publisher key, manifest present | 14.73 ms |

Drill A wall time: 0.02 s. The local checks are sub-millisecond; A-08
is dominated by the base64 JSON decode of the 14,204-char blob.

## What the drill does not cover

The drill verifies fetched data; it does not spin up a node (G-02).
A real join also involves fetch-pack acquisition, SHAMap fetching, and
the `doAdvance` history-fill gates — see `docs/state-sync-spec.md` §2.
