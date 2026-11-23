# Risk register

| ID | Severity | Risk | Evidence | Mitigation / note |
|----|----------|------|----------|-------------------|
| R-01 | HIGH | History older than ~2.96 days is unavailable from the public node. Any audit needing pre-2026-11-20 ledgers must use another source or fail. | F-01, `outputs/derived/history-range.json` | Use the Validator History Service or an archive node; do not assume the public RPC holds full history. |
| R-02 | HIGH | The 86785 bulk activation cannot be independently re-derived from node data; the VHS is a single point of trust for that event. | F-02, `outputs/derived/history-gaps.json` | Cross-check the VHS record against the `feature_list` enabled set (they match exactly — 64 names). |
| R-03 | HIGH | No snapshot export/import exists: a fresh node must re-fetch all state via SHAMap from peers; there is no offline snapshot to bootstrap from. | F-06, `fixtures/source-hashes.json` | Plan joins around peer availability and the 3000 ms / 6-retry acquisition budget (C-20). |
| R-04 | MEDIUM | Cold-ledger first-call `lgrNotFound`: clients that treat the first error as final wrongly conclude a ledger does not exist. | F-04, drill B-01 | Retry cold lookups up to 3 times with a delay; see runbook B. |
| R-05 | MEDIUM | `account_tx` silently clamps `ledger_index_min` below the earliest held ledger, so a caller can believe it queried from ledger 1. | F-05, `outputs/account_tx_genesis.json` | Always read the echoed `ledger_index_min`/`ledger_index_max` and compare with the requested range. |
| R-06 | MEDIUM | The validator-list blob signature is unverified in this pack; a replaced list would not be caught by stdlib-only verification. | F-07, C-24 | Verify the blob signature with an Ed25519-capable tool before trusting a list fetched outside this pack. |
| R-07 | MEDIUM | The explorer is down (HTTP 500), so there is no independent web corroboration of ledger data. | F-09, `outputs/explorer_health.json` | Corroborate against a second RPC node or the VHS instead of the explorer. |
| R-08 | MEDIUM | Admin RPC methods return HTTP 403, so peer and validator-list detail is not visible from the public RPC. | F-08 | Use `server_info`/`server_state`/`feature_list` for sync-state visibility; do not assume the 403 means the node is unhealthy. |
| R-09 | LOW | Idle ledgers (0 transactions in all 9 sampled) mean transaction-lookup success paths were not demonstrated live in this window. | F-03 | Re-run the probe when the network carries transactions; do not treat the empty ledgers as a fault. |
| R-10 | LOW | The validator-list blob carries an expiration (891447293 Ripple-epoch seconds) that this pack does not monitor. | F-10, `outputs/testnet_vl.json` | Re-fetch the list on a schedule and check `expiration` before relying on it. |
| R-11 | LOW | Cadence was measured over a 60 s window; longer windows may drift. | F-12, `outputs/derived/cadence.json` | Re-measure cadence for any planning that depends on it. |
| R-12 | LOW | Skip-list reach-back for direct `hashOfSeq` is ~65,536 ledgers (~2.3 days); deeper hashes need the anchor chain. | C-09, C-10 | Walk anchors (every 256th ledger) for older hashes; see `docs/snapshot-verification.md`. |
| R-13 | MEDIUM | Inbound acquisition is bounded (3000 ms timeout, 6 retries); a slow peer can delay cold-ledger resolution beyond the retry budget. | C-20 | Prefer the highest-score peer and retry with backoff; see runbook B. |
| R-14 | LOW | History retention depends on operator config (`LEDGER_HISTORY` / `online_delete`); the 84,445-ledger window is a property of this node, not the protocol. | C-21, C-22 | Do not quote the window as a network guarantee; measure it per node. |

## Counts

- HIGH: 3
- MEDIUM: 6
- LOW: 5
- Total: 14
