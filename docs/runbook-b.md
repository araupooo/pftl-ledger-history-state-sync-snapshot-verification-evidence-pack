# Runbook B — history-gap encounter

What to do when a ledger you need is not in the node's held history.
Run with `python3 scripts/drill.py` (cases B-01 to B-06). Measured
timings are from the 2026-11-23 run (`outputs/drill-run.log`).

## Decision tree

```
1. You need ledger N. Fetch server_info; read complete_ledgers (L-H).
2. Is N inside [L, H]?
   ├─ YES → fetch it. If the first call returns lgrNotFound, RETRY:
   │  cold ledgers need candidate-flag acquisition (getCandidateLedger
   │  = next multiple of 256) and may resolve on attempt 2 or 3.
   │  ├─ Resolves within 3 attempts → verify the header hash
   │  │  (drill B-02) and use the ledger.
   │  └─ Still lgrNotFound after 3 attempts → the node cannot serve
   │     it now. Try a second node; if both fail, treat N as
   │     unavailable from this network view.
   └─ NO → N is outside the held range. Do NOT keep retrying the
      same call: the answer is stable.
      ├─ N < L → the ledger is below the history floor. Use the
      │  Validator History Service or an archive node. The VHS
      │  records amendment activations (e.g. all 64 at 86785) that
      │  the node cannot.
      └─ N > H → the ledger does not exist yet (or the node is
         behind). Check the validated ledger age and wait.
3. If you asked account_tx with ledger_index_min below L:
   the node silently clamps it to L. Always read the echoed
   ledger_index_min / ledger_index_max and compare with what you
   requested — a silent truncation is not an error, but believing
   you queried from ledger 1 is.
```

## Cases and measured timings (2026-11-23 run, 6/6 PASS)

| Case | Check | Result | Time |
|------|-------|--------|------|
| B-01 | Cold old-ledger lookup resolves within 3 attempts | ledger 8201001 returned on attempt 1 | 1,313.90 ms |
| B-02 | Cold-lookup ledger hash recomputes | hash MATCH for 8201001 | 807.83 ms |
| B-03 | 86785 activation transaction is `txnNotFound` | error_code 29 | 0.24 ms |
| B-04 | `account_tx` min below earliest is clamped | requested min 1, echoed min 8200054 | 0.17 ms |
| B-05 | Ledger below earliest returns an error, never a ledger | `lgrNotFound` code 21 | 0.06 ms |
| B-06 | 86785 activation event is not re-derivable | VHS records 64 amendments at 86785 on 2026-02-09; none checkable from the node | 0.21 ms |

Drill B wall time: 2.12 s, dominated by the two live RPC calls
(B-01, B-02). The local cases are sub-millisecond.

## Notes

- B-01 uses ledger 8201001 deliberately: it is inside the complete
  range and was never probed by `probe_all.sh`, so the first attempt is
  genuinely cold. It resolved on attempt 1 in this run; earlier packs
  saw first-call `lgrNotFound` for cold ledgers that resolved on
  retry — hence the 3-attempt budget.
- B-03/B-06 are the worked case from
  `docs/ledger-history-inventory.md`: the 86785 bulk activation is
  VHS-only.
