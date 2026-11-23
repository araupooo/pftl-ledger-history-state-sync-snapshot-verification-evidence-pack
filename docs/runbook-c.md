# Runbook C — corrupted-snapshot detection

How to detect a tampered ledger snapshot from hashes alone. Run with
`python3 scripts/drill.py` (cases C-01 to C-07). All cases are local
computations on the fetched validated header; no network access. Measured
timings are from the 2026-11-23 run (`outputs/drill-run.log`).

## Decision tree

```
1. You have a snapshot: a ledger header (claimed hash H) plus, for a
   full check, the state map and transaction map it commits to.
2. Recompute the header hash from the header fields (§1 of
   docs/snapshot-verification.md).
   ├─ Recomputed != H → the snapshot is CORRUPT (or the claimed hash
   │  is wrong). Reject it. Do not use any data from it.
   └─ Recomputed == H → the header is internally consistent. Continue.
3. Check the parent link: fetch the parent ledger (or its hash from
   the skip list) and compare with the header's parentHash.
   ├─ Mismatch → the snapshot's chain position is wrong. Reject it.
   └─ Match → continue.
4. Cross-check the skip list: resolve the ledger's hash via
   hashOfSeq from the rolling or anchor skip entry.
   ├─ Mismatch → the skip list and the snapshot disagree. Reject it
   │  (or the skip entry is the corrupt one — fetch the same entry
   │  from a second node before deciding which is wrong).
   └─ Match → continue.
5. Check the state and transaction roots: the state map root must
   equal accountHash, the transaction map root must equal txHash.
   ├─ Either mismatch → the snapshot's data does not match its
   │  header. Reject it.
   └─ Both match → continue.
6. Check the validator list: the ledger must be validated by quorum
   (17 of 25) and the list itself must decode with the expected
   publisher key.
   ├─ Not validated / list wrong → do not trust the snapshot as
   │  network state, even if its hashes are internally consistent.
   └─ Validated → ACCEPT the snapshot.
```

## Cases and measured timings (2026-11-23 run, 7/7 PASS)

| Case | Tamper | Detection | Time |
|------|--------|-----------|------|
| C-01 | `total_coins` +1 | Recomputed hash differs from claimed hash | 0.08 ms |
| C-02 | `parentHash` bit flip | Recomputed hash differs | 0.07 ms |
| C-03 | `accountHash` bit flip | Recomputed hash differs | 0.05 ms |
| C-04 | `parentHash` byte flip in the chain | Parent link V → V-1 reported False | 0.31 ms |
| C-05 | Skip-list hash byte flip | `hashOfSeq` result no longer matches the chain header | 0.52 ms |
| C-06 | `close_flags` flip | Recomputed hash differs | 0.07 ms |
| C-07 | Hash of V-1 claimed for V | Recomputation differs | 0.08 ms |

Drill C wall time: 0.00 s (all cases sub-millisecond).

## What a hash check cannot detect

A snapshot whose fields are internally consistent but which was never
validated by quorum passes the hash checks. That is why step 6 of the
decision tree exists: hashes prove internal consistency, only the
validator list and quorum tie a ledger to the network. The blob
signature check itself is UNTESTABLE in this pack (G-03).
