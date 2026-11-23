# Decision memo

## Verdict

**The PFTL testnet's ledger history is verifiable inside a ~2.96-day
window and not re-derivable outside it; state sync is verifiable from
hashes and the validator list, but there is no snapshot mechanism to
verify — a fresh node must re-fetch state from peers.**

## Reasoning

1. **Inside the window, verification works end to end.** The public
   node holds ledgers 8200054-8284498 (84,445 ledgers). 17 sampled
   header hashes recompute exactly, 7/7 parent links hold, 5/5
   rolling skip-list hashes and 3/3 anchor skip positions match. The
   formulas are implemented in stdlib-only Python
   (`src/snapshot_verifier.py`) and the drills pass 21/21 with
   per-case timings. A fresh node can verify synchronized state from
   header hashes plus the validator list (25 validators, quorum 17)
   without trusting the RPC endpoint.
2. **Outside the window, nothing is re-derivable.** 8,200,053 ledgers
   before 8200054 are absent. The worked case is decisive: the 86785
   bulk activation of 64 amendments (2026-02-09) returns `lgrNotFound`
   for the ledger and `txnNotFound` for its activation transaction.
   The event is known only from the Validator History Service, and
   the only corroboration the node offers is that the 64 enabled
   amendments in `feature_list` are exactly the 64 VHS-activated
   names.
3. **There is no snapshot to verify.** The pinned code contains no
   ledger-snapshot export or import. The only `snapshot` in the RPC
   surface is the `subscribe` flag. State sync is SHAMap fetch from
   peers, bounded by a 3000 ms timeout and 6 retries. Any plan that
   assumes an offline snapshot bootstrap is planning against a
   mechanism that does not exist.
4. **Two honest limits.** The validator-list blob signature is not
   verified in this pack (no Ed25519 in the Python standard library),
   and no live fresh-node join was run — the sync claims are
   code-specified and drill-verified on fetched data. Both are recorded
   as gaps (G-03, G-02), not hidden.

## What this changes

- Do not quote the public RPC as holding full history: it holds the
  last ~2.96 days. Audits of older events need the VHS or an archive
  node.
- Do not treat a first `lgrNotFound` as final for cold ledgers inside
  the range; retry up to 3 times.
- Do not trust an `account_tx` range at face value; read the echoed
  `ledger_index_min`/`ledger_index_max`.
- Do not plan a snapshot-based bootstrap; plan around peer fetch and
  the acquisition retry budget.
- Verify the validator-list blob signature with Ed25519-capable
  tooling before relying on a list fetched outside this pack.

## Counts

- Findings: 12 (HIGH 3, MEDIUM 5, LOW 4), all VERIFIED.
- Claims: 30 (VERIFIED 23, SPECIFIED 6, UNVERIFIED 0, UNTESTABLE 1).
- Risks: 14 (HIGH 3, MEDIUM 6, LOW 5).
- Gaps: 7.
- Drills: 21/21 cases PASS (A 8, B 6, C 7), each with a measured
  per-case elapsed time.
