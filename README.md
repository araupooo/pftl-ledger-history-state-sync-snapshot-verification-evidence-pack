# PFTL Ledger History, State-Sync, and Snapshot Verification Evidence Pack

## Verdict

**The PFTL testnet's ledger history is verifiable inside a ~2.96-day
window and not re-derivable outside it; state sync is verifiable from
hashes and the validator list, but there is no snapshot mechanism to
verify — a fresh node must re-fetch state from peers.**

## Key numbers (live probe 2026-11-23 00:45:48 UTC)

- Pinned source: postfiatd `0085a1ff885d6a446369cf73a4430f75af22be55`
  (2026-10-10, PR #50 merge, v1.0.9), network ID 2025.
- Complete ledgers: 8200054-8284498 (84,445 ledgers, 2.96 days).
  8,200,053 ledgers before 8200054 are absent from this node.
- Ledger cadence: 3.042 s/ledger (20 ledgers in 60.8 s).
- Hash recomputation: 17/17 MATCH. Parent links: 7/7. Rolling
  skip-list: 5/5. Anchor skip positions: 3/3.
- The 86785 bulk activation (64 amendments, 2026-02-09) is not
  re-derivable from the node: ledger `lgrNotFound`, activation
  transaction `txnNotFound`. The event is known only from the Validator
  History Service — corroborated by the fact that the 64 enabled
  amendments in `feature_list` are exactly the 64 VHS-activated names.
- No native ledger-snapshot export/import exists in the pinned code.
- Drills: 21/21 cases PASS (A 8, B 6, C 7), each with a measured
  per-case elapsed time.

## Counts

- Findings: 12 (HIGH 3, MEDIUM 5, LOW 4), all VERIFIED.
- Claims: 30 (VERIFIED 23, SPECIFIED 6, UNVERIFIED 0, UNTESTABLE 1).
- Risks: 14 (HIGH 3, MEDIUM 6, LOW 5).
- Gaps: 7.

## Reproduce

```bash
bash scripts/probe_all.sh        # read-only live probe (~43 RPC calls + 60 s cadence)
python3 scripts/analyze.py       # derived JSONs (no network)
python3 scripts/drill.py         # 21 timed drill cases, exit 0 only if all pass
python3 scripts/extract_excerpts.py  # verbatim pinned-source excerpts + hashes
bash scripts/clean_reproduce.sh  # full fresh-environment check (13 comparisons)
bash scripts/verify_digests.sh   # sha256sum -c SHA256SUMS
```

Only read-only public probes run. No transactions, no votes, no live
key material, no credentials anywhere in the pack.

## File map

- `README.md` — this file.
- `findings.json` — 12 findings with severity, status, evidence.
- `run-manifest.json` — pinned commit, validated/earliest ledgers,
  counts recomputed from the tables.
- `docs/` — decision memo, ledger-history inventory, state-sync
  specification, snapshot-verification procedures, runbooks A/B/C
  (each with a decision tree and measured timings), methodology,
  claim-to-evidence index, risk register, gap register, evidence
  index, citations, `index.html`.
- `src/snapshot_verifier.py` — stdlib-only ledger-hash recomputation,
  skip-list keylets, chain check, `hashOfSeq` emulation.
- `scripts/` — probe, cadence, analyze, drill, excerpts, reproduce,
  compare, digests.
- `configs/sync-thresholds.json` — sync thresholds used by the drills.
- `fixtures/source-excerpts/` — 26 verbatim pinned-source excerpts
  with file paths and grep-verified line numbers.
- `fixtures/source-hashes.json` — SHA-256 digests and git blob SHAs
  for every cited source file, plus snapshot absence checks.
- `outputs/` — unedited live probe outputs, derived JSONs,
  drill-run.log, fresh-clone reproduction evidence.
- `SHA256SUMS` — digests of every pack file except itself and the
  internal-only `PACK-READY.md`.
