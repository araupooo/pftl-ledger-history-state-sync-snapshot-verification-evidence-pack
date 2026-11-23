# Citations

Pinned source for all code citations: postfiatd commit
`0085a1ff885d6a446369cf73a4430f75af22be55` (2026-10-10, PR #50 merge,
v1.0.9). Line numbers were verified with `grep -n` on a local checkout
of that commit. Excerpt files live in `fixtures/source-excerpts/`;
digests and blob SHAs are in `fixtures/source-hashes.json`.

## Pinned-source excerpts

| Excerpt file | Source file and lines | Subject |
|--------------|----------------------|---------|
| `ledger-hash-calc.txt` | `src/xrpld/app/ledger/Ledger.cpp` 53-68 | `calculateLedgerHash` |
| `ledger-header-fields.txt` | `include/xrpl/protocol/LedgerHeader.h` 40-73 | Ledger header fields |
| `ledger-hash-prefix.txt` | `include/xrpl/protocol/HashPrefix.h` 31-37, 66-70 | `make_hash_prefix`, `ledgerMaster` = 0x4C575200 |
| `ledger-set-immutable.txt` | `src/xrpld/app/ledger/Ledger.cpp` 357-374 | `setImmutable` (tx/state roots, hash) |
| `ledger-skip-list.txt` | `src/xrpld/app/ledger/Ledger.cpp` 900-968 | `updateSkipList` (anchor + rolling) |
| `hash-of-seq.txt` | `src/libxrpl/ledger/View.cpp` 1040-1102 | `hashOfSeq` |
| `candidate-ledger.txt` | `include/xrpl/ledger/View.h` 505-524 | `getCandidateLedger` |
| `flag-ledger-interval.txt` | `src/xrpld/app/ledger/Ledger.h` 426-430 | `FLAG_LEDGER_INTERVAL` = 256 |
| `ledger-complete-range.txt` | `src/xrpld/app/ledger/detail/LedgerMaster.cpp` 1612-1620, 826-886 | `getCompleteLedgers`, `setFullLedger` |
| `fetch-for-history.txt` | `src/xrpld/app/ledger/detail/LedgerMaster.cpp` 1825-1936 | `fetchForHistory` |
| `fetch-pack-request.txt` | `src/xrpld/app/ledger/detail/LedgerMaster.cpp` 723-768 | `getFetchPack` |
| `get-ledger-hash-for-history.txt` | `src/xrpld/app/ledger/detail/LedgerMaster.cpp` 1208-1227 | `getLedgerHashForHistory` |
| `do-advance-history-fill.txt` | `src/xrpld/app/ledger/detail/LedgerMaster.cpp` 1940-2028 | `doAdvance` history fill |
| `should-acquire.txt` | `src/xrpld/app/ledger/detail/LedgerMaster.cpp` 75-99 | `shouldAcquire` |
| `inbound-ledger-timeouts.txt` | `src/xrpld/app/ledger/detail/InboundLedger.cpp` 48-74, 376-391 | 3000 ms timeout, 6 retries |
| `inbound-ledger-fetch-root.txt` | `src/xrpld/app/ledger/detail/InboundLedger.cpp` 300-361 | `fetchRoot` for tx/state maps |
| `inbound-ledger-needed-hashes.txt` | `src/xrpld/app/ledger/detail/InboundLedger.cpp` 1007-1041 | `getNeededHashes` |
| `shamapstore-online-delete.txt` | `src/xrpld/app/misc/SHAMapStoreImp.cpp` 121-163, 323-333 | `online_delete`, rotation |
| `ledger-cleaner.txt` | `src/xrpld/app/ledger/detail/LedgerCleaner.cpp` 382-456 | `doLedgerCleaner` |
| `get-ledger-by-context.txt` | `src/xrpld/rpc/detail/RPCHelpers.cpp` 1030-1145 | `getLedgerByContext` |
| `ledger-replay-hash-check.txt` | `src/xrpld/app/ledger/detail/LedgerReplayMsgHandler.cpp` 134-154 | Hash check on replay |
| `validator-list-verify.txt` | `src/xrpld/app/misc/ValidatorList.h` 880-895 | `ValidatorList::verify` |
| `ledger-request-rpc.txt` | `src/xrpld/rpc/handlers/LedgerRequest.cpp` 36-49 | `doLedgerRequest` |
| `txn-not-found.txt` | `src/libxrpl/protocol/ErrorCodes.cpp` 113-117 | `txnNotFound`, error_code 29, HTTP 404 |
| `config-ledger-history.txt` | `src/xrpld/core/detail/Config.cpp` 652-661 | `LEDGER_HISTORY` config |
| `ledger-master-get-by-seq.txt` | `src/xrpld/app/ledger/detail/LedgerMaster.cpp` 1730-1763 | `getLedgerBySeq` |

## Live sources (fetched 2026-11-23 00:45-00:47 UTC)

- RPC: `https://rpc.testnet.postfiat.org/` — `server_info`,
  `ledger`, `ledger_header`, `ledger_data`, `ledger_entry`,
  `account_info`, `account_tx`, `tx`, `fee`, `feature_list`,
  `server_state`, `ledger_current`, `ledger_closed`.
- Validator list: `https://postfiat.org/testnet_vl.json`.
- Validator History Service: `https://vhs.testnet.postfiat.org/v1/`
  (`health`, `amendments`, `amendment/info`,
  `amendments/vote/test`, `validators`, `topology`).
- Explorer health: `https://explorer.testnet.postfiat.org/api/v1/health`
  (HTTP 500 at probe time).
- Project site and whitepaper: `https://postfiat.org/`,
  `https://postfiat.org/whitepaper` (fetched as
  `outputs/postfiat_org.html`, `outputs/postfiat_whitepaper.html`).

## Absence checks (recorded in `fixtures/source-hashes.json`)

- `snapshot` (case-insensitive) in `src/xrpld/rpc/handlers/`: 1 match
  — `Subscribe.cpp:339`, the `snapshot`/`state_now` flag of the
  `subscribe` call. Not a ledger snapshot mechanism.
- `snapshot` (case-insensitive) in `InboundLedger.h` and
  `InboundLedger.cpp`: 0 matches.
