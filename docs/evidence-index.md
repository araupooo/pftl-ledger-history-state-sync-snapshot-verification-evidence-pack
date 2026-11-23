# Evidence index

## Documents

| File | Contents |
|------|----------|
| `README.md` | Verdict, reproduction steps, file map, counts |
| `docs/decision-memo.md` | Verdict and reasoning |
| `docs/ledger-history-inventory.md` | What the node holds, what can/cannot be re-derived, the 86785 worked case |
| `docs/state-sync-spec.md` | How a fresh node joins, downloads, and verifies state |
| `docs/snapshot-verification.md` | Hash formula, chain/skip-list/state-root/validator-list checks, tamper table |
| `docs/runbook-a.md` | Fresh-node join drill (A-01 to A-08) with decision tree and timings |
| `docs/runbook-b.md` | History-gap encounter drill (B-01 to B-06) with decision tree and timings |
| `docs/runbook-c.md` | Corrupted-snapshot detection drill (C-01 to C-07) with decision tree and timings |
| `docs/methodology.md` | How each measurement was made, boundaries |
| `docs/claim-index.md` | 30 claims with status and primary source |
| `docs/risk-register.md` | 14 risks with severity and mitigation |
| `docs/gap-register.md` | 7 gaps with what would close each |
| `docs/evidence-index.md` | This file |
| `docs/citations.md` | Primary sources per claim |
| `docs/index.html` | The decision memo as a readable page |

## Code

| File | Contents |
|------|----------|
| `src/snapshot_verifier.py` | Ledger-hash recomputation, skip-list keylets, chain check, `hashOfSeq` emulation (stdlib only) |
| `scripts/probe_all.sh` | Read-only live probe (~43 RPC POSTs, 10 GETs, 60 s cadence window) |
| `scripts/measure_cadence.py` | 60 s cadence measurement → `outputs/derived/cadence.json` |
| `scripts/analyze.py` | Derived JSONs from probe outputs (no network) + `run-manifest.json` |
| `scripts/drill.py` | 21 timed drill cases (A 8, B 6, C 7) with per-case elapsed times |
| `scripts/extract_excerpts.py` | Verbatim pinned-source excerpts + `fixtures/source-hashes.json` |
| `scripts/clean_reproduce.sh` | Full fresh-environment reproduction check |
| `scripts/compare_reproduce.py` | 13 checks comparing a fresh run with the shipped manifest |
| `scripts/verify_digests.sh` | `sha256sum -c SHA256SUMS` |
| `scripts/make_sha256sums.sh` | Regenerate `SHA256SUMS` |

## Live probe outputs (`outputs/`, unedited)

Server and ledger state: `server_info.json`, `server_state.json`,
`ledger_current.json`, `ledger_closed.json`, `fee.json`,
`feature_list.json`. Ledger headers: `ledger_earliest.json`,
`ledger_validated.json`, `ledger_flag.json`, `ledger_header_flag.json`,
`ledger_header_flag2.json`, `ledger_header_flag3.json`,
`ledger_header_earliest.json`, `ledger_header_validated.json`,
`ledger_chain_0.json` … `ledger_chain_5.json`,
`ledger_chain_earliest_0.json` … `ledger_chain_earliest_2.json`.
Below-floor probes: `ledger_8200053.json`, `ledger_86784.json`,
`ledger_86785.json`, `ledger_header_86785.json`. State: `ledger_data_validated.json`,
`ledger_data_earliest.json`, `ledger_entry_skip.json`,
`ledger_entry_skip_flag.json`, `ledger_entry_genesis.json`,
`account_info_genesis.json`, `account_info_genesis_earliest.json`,
`account_tx_genesis.json`. Transactions: `tx_86785.json`. Refusals:
`ledger_request_validated.json`, `validators.json`, `peers.json`
(all HTTP 403), `invalid_method.json` (`unknownCmd`). External
services: `vhs-health.json`, `vhs-amendments.json`,
`vhs-amendments-info.json`, `vhs-amendments-vote-test.json`,
`vhs-validators.json`, `vhs-topology.json`, `testnet_vl.json`,
`explorer_health.json` (HTTP 500), `postfiat_org.html`,
`postfiat_whitepaper.html`. Run log: `probe-run.log`.

Derived: `outputs/derived/cadence.json`, `history-range.json`,
`chain-check.json`, `skip-list-check.json`,
`snapshot-verification.json`, `history-gaps.json`,
`drill-results.json`. The reproduction's comparison is
`outputs/fresh-clone-derived-compare-results.json` (13/13 PASS).
Drill log: `outputs/drill-run.log`. Reproduction evidence:
`outputs/fresh-clone-*` and `outputs/fresh-clone-compare.log`.

## Fixtures

`fixtures/source-excerpts/` holds 26 verbatim pinned-source excerpts
(see `docs/citations.md` for the list). `fixtures/source-hashes.json`
holds SHA-256 digests and git blob SHAs for every cited source file,
plus the snapshot absence checks.

## Machine-readable summaries

| File | Contents |
|------|----------|
| `findings.json` | 12 findings with severity, status, evidence |
| `run-manifest.json` | Pinned commit, validated/earliest ledgers, counts recomputed from the tables |
| `configs/sync-thresholds.json` | Sync thresholds used by the drills |
| `SHA256SUMS` | SHA-256 digests of every pack file except itself and `PACK-READY.md` |
