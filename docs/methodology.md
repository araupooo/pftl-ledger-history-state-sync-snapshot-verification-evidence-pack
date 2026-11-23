# Methodology

## Pinned source

postfiatd commit `0085a1ff885d6a446369cf73a4430f75af22be55`
(2026-10-10, PR #50 merge, v1.0.9). A local checkout at
`/tmp/postfiatd-pin` was verified with `git rev-parse HEAD` before any
excerpt was taken. Every line number in this pack was verified with
`grep -n` on that checkout; no line number was taken from a web fetch.
`scripts/extract_excerpts.py` re-derives all excerpts from the checkout
and records SHA-256 digests plus git blob SHAs in
`fixtures/source-hashes.json`.

## Live probes

`scripts/probe_all.sh` ran 2026-11-23 00:45:48–00:47:34 UTC against
`https://rpc.testnet.postfiat.org/` (network ID 2025). It made ~43
read-only RPC POSTs and 10 read-only GETs, plus a 60.8 s cadence
measurement. No transaction was submitted, no vote cast, no key
material used. Each response was written unedited to `outputs/` with
its HTTP status, duration and SHA-256 recorded in
`outputs/probe-run.log`.

Retries: a probe that returns an error is retried twice (8 s apart)
unless the error is the expected result (e.g. `lgrNotFound` for
8200053/86784/86785, `txnNotFound` for the 86785 transaction, HTTP 403
for admin methods). No probe needed a retry in this run.

## Derived analysis

`scripts/analyze.py` reads only the probe outputs (no network access)
and writes `outputs/derived/`:

- `history-range.json` — earliest/validated ledgers, span, cadence.
- `chain-check.json` — `verify_chain` over 6 consecutive and 3
  earliest headers (the earliest run is reversed to newest-first
  before checking; the first draft of this pack passed it
  oldest-first and produced false link failures, which the live data
  exposed and the fix corrected).
- `skip-list-check.json` — rolling-window and anchor-skip checks. The
  anchor position rule (index len-1-(LastSeq-seq)/256) was corrected
  from a naive tail-reading after the live anchor entry showed
  `LastLedgerSequence` 8284416, not 8284160.
- `snapshot-verification.json` — 17 header-hash recomputations.
- `history-gaps.json` — what resolves and what does not, including the
  VHS bulk-activation count (64 amendments at 86785).
- `run-manifest.json` — counts recomputed from the authored tables
  (`findings.json`, `docs/claim-index.md`, `docs/risk-register.md`,
  `docs/gap-register.md`).

## Drills

`scripts/drill.py` runs 21 cases in 3 drills (A fresh-node join, B
history-gap encounter, C corrupted-snapshot detection). Every case
records its own measured elapsed time with `time.monotonic()` around
the case, printed on its PASS/FAIL line and stored as `elapsed_ms` in
`outputs/derived/drill-results.json`. Per-drill and total wall-time
lines are also printed. Drill B makes at most 3 additional read-only
RPC calls (one cold ledger, 8201001); drills A and C work from the
fetched probe outputs only. Exit code is 0 only if every case passes.

## Reproduction

`scripts/clean_reproduce.sh` copies the pack to a throwaway directory,
drops all generated outputs, re-runs probe → analyze → drill →
excerpts, and compares the fresh numbers with the shipped manifest via
`scripts/compare_reproduce.py` (13 checks, exit 0 only if all pass).
The fresh outputs are copied back as `outputs/fresh-clone-*` and the
comparison is recorded in `outputs/fresh-clone-compare.log`.

## Digests

`scripts/make_sha256sums.sh` writes `SHA256SUMS` over every pack file
except `SHA256SUMS` itself and the internal-only `PACK-READY.md`.
`scripts/verify_digests.sh` verifies them (`sha256sum -c`).

## Boundaries

- Read-only probes only; no transactions, no votes, no flood traffic.
- No live key material; no credentials anywhere in the pack.
- No fresh node was spun up (G-02); no Ed25519 verification (G-03).
- The VHS and the explorer are third-party services: their data is
  recorded as fetched, not as node-verified fact.
- Upstream XRPL is cited where postfiatd inherits a mechanism (ledger
  hashing, skip lists, validator lists); divergences are flagged where
  found — none were found in the mechanisms this pack covers, and the
  PFTL-specific facts (network 2025, 25 validators, quorum 17, the
  86785 bulk activation) are all measured, not inherited.
