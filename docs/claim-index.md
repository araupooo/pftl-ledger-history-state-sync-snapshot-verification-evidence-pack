# Claim-to-evidence index

Every claim in this pack, its status, its primary source, and the evidence
file that supports it. Status meanings: **VERIFIED** — checked against a
live probe or a pinned-source excerpt in this pack; **SPECIFIED** — defined
by the pinned code but not exercised live in this pack; **UNVERIFIED** — no
supporting evidence was obtained; **UNTESTABLE** — the claim cannot be
tested with the tooling in this pack.

| ID | Status | Claim | Primary source | Evidence |
|----|--------|-------|----------------|----------|
| C-01 | VERIFIED | The earliest ledger held by the public node is 8200054. | `server_info` `complete_ledgers` | `outputs/server_info.json`, `outputs/derived/history-range.json` |
| C-02 | VERIFIED | The validated ledger at probe time (2026-11-23 00:45:48 UTC) was 8284498, hash `1F1A016884FA0A7458BF11BE71F7ADEABD740961643DD8466996E213A5D91499`. | `server_info` `validated_ledger` | `outputs/server_info.json` |
| C-03 | VERIFIED | 84,445 ledgers are inside the complete range 8200054-8284498. | Arithmetic on C-01, C-02 | `outputs/derived/history-range.json` |
| C-04 | VERIFIED | 8,200,053 ledgers before 8200054 are absent from this node. | `ledger` calls for 8200053, 86784, 86785 all return `lgrNotFound` | `outputs/ledger_8200053.json`, `outputs/ledger_86784.json`, `outputs/ledger_86785.json` |
| C-05 | VERIFIED | The held window spans 2026-11-20 01:46:50 UTC to 2026-11-23 00:45:50 UTC (255,540 s, 2.96 days). | `ledger_header` `close_time_human` for earliest and validated | `outputs/ledger_header_earliest.json`, `outputs/ledger_header_validated.json` |
| C-06 | VERIFIED | Ledger cadence is 3.042 s/ledger (20 ledgers in a 60.8 s window, 8284512-8284532). | `measure_cadence.py` live measurement | `outputs/derived/cadence.json` |
| C-07 | VERIFIED | A ledger hash recomputes as sha512Half(prefix `0x4C575200`, seq, drops, parentHash, txHash, accountHash, parentCloseTime, closeTime, closeTimeResolution, closeFlags). | `Ledger.cpp` `calculateLedgerHash`, lines 53-68 | `fixtures/source-excerpts/ledger-hash-calc.txt`, `outputs/derived/snapshot-verification.json` (17/17 MATCH) |
| C-08 | VERIFIED | Parent-hash links hold across consecutive ledgers. | `Ledger::setImmutable` + chain check | `fixtures/source-excerpts/ledger-set-immutable.txt`, `outputs/derived/chain-check.json` (7/7) |
| C-09 | VERIFIED | The rolling skip list resolves `hashOfSeq` for the previous 256 ledgers. | `View.cpp` `hashOfSeq`, lines 1040-1102 | `fixtures/source-excerpts/hash-of-seq.txt`, `outputs/derived/skip-list-check.json` (5/5) |
| C-10 | VERIFIED | Anchor skip entries hold every 256th ledger hash, located by `LastLedgerSequence` at index len-1-(LastSeq-seq)/256. | `Ledger.cpp` `updateSkipList`, lines 900-968 | `fixtures/source-excerpts/ledger-skip-list.txt`, `outputs/derived/skip-list-check.json` (3/3) |
| C-11 | SPECIFIED | A cold lookup acquires the candidate flag ledger at `(requested + 255) & ~255` (the next multiple of 256). | `View.h` `getCandidateLedger`, lines 505-524 | `fixtures/source-excerpts/candidate-ledger.txt` |
| C-12 | VERIFIED | A cold old-ledger lookup inside the complete range resolves within 3 attempts (ledger 8201001, attempt 1, 1,313.90 ms). | Drill B-01 | `outputs/derived/drill-results.json` |
| C-13 | VERIFIED | `account_tx` with `ledger_index_min` 1 is silently clamped: the node echoes `ledger_index_min` 8200054. | `account_tx` live probe | `outputs/account_tx_genesis.json` |
| C-14 | VERIFIED | A ledger below the earliest held ledger returns an error (`lgrNotFound`, error_code 21), never a ledger object. | `ledger` live probe for 8200053 | `outputs/ledger_8200053.json` |
| C-15 | VERIFIED | The 86785 activation transaction lookup returns `txnNotFound` (error_code 29). | `tx` live probe | `outputs/tx_86785.json` |
| C-16 | VERIFIED | 64 amendments activated at ledger 86785 on 2026-02-09T14:31:12.000Z, per the Validator History Service vote record. | VHS `/v1/network/amendments/vote/test` | `outputs/vhs-amendments-vote-test.json` |
| C-17 | VERIFIED | The 86785 activation event is not re-derivable from node data (ledger and transaction both unresolvable). | C-04, C-15 | `outputs/derived/history-gaps.json` |
| C-18 | VERIFIED | No native ledger-snapshot export/import exists in the pinned code; the only `snapshot` hit in the RPC handlers is the `subscribe` flag. | grep over `src/xrpld/rpc/handlers/`, `InboundLedger` files | `fixtures/source-hashes.json` (absence checks) |
| C-19 | SPECIFIED | A fresh node synchronizes state by fetching SHAMap roots and needed hashes from peers (`fetchRoot`, `getNeededHashes`). | `InboundLedger.cpp` lines 300-361, 1007-1041 | `fixtures/source-excerpts/inbound-ledger-fetch-root.txt`, `fixtures/source-excerpts/inbound-ledger-needed-hashes.txt` |
| C-20 | SPECIFIED | Inbound ledger acquisition times out after 3000 ms and gives up after 6 retries. | `InboundLedger.cpp` lines 48-74, 376-391 | `fixtures/source-excerpts/inbound-ledger-timeouts.txt` |
| C-21 | SPECIFIED | `LEDGER_HISTORY` `full` means maximum retention; any other value is a ledger count; default is 0. | `Config.cpp` lines 652-661 | `fixtures/source-excerpts/config-ledger-history.txt` |
| C-22 | SPECIFIED | `online_delete` requires `LEDGER_HISTORY` to be at most `deleteInterval_`; retention is enforced by SHAMapStore rotation. | `SHAMapStoreImp.cpp` lines 121-163, 323-333 | `fixtures/source-excerpts/shamapstore-online-delete.txt` |
| C-23 | VERIFIED | The validator list decodes to sequence 30, 25 validators, publisher key `ED3F1E0DA736FCF99BE2880A60DBD470715C0E04DD793FB862236B070571FC09E2`, manifest 288 chars. | `https://postfiat.org/testnet_vl.json` | `outputs/testnet_vl.json`, drill A-08 |
| C-24 | UNTESTABLE | The validator-list blob signature verifies against the publisher key. | `ValidatorList.h` `verify`, lines 880-895 | `fixtures/source-excerpts/validator-list-verify.txt` — signature math needs Ed25519, which Python's standard library does not provide |
| C-25 | VERIFIED | Validation quorum is 17 of 25 validators. | `server_info` `validation_quorum` + C-23 count | `outputs/server_info.json`, `outputs/testnet_vl.json` |
| C-26 | VERIFIED | The node is in `full` state with a validated ledger age of 1 s at probe time. | `server_info` `server_state`, `validated_ledger.age` | `outputs/server_info.json`, drill A-07 |
| C-27 | VERIFIED | The genesis account `r4vhrMChCsaoFsBoCkRTRGUuc1njfr7bmA` holds 96999999999999880 drops, identical at the validated and earliest ledgers. | `account_info` live probes | `outputs/account_info_genesis.json`, `outputs/account_info_genesis_earliest.json` |
| C-28 | VERIFIED | `feature_list` reports 101 amendments: 64 enabled, 37 disabled; the 64 enabled names are exactly the 64 VHS-activated names. | `feature_list` live probe + VHS vote record | `outputs/feature_list.json`, `outputs/vhs-amendments-vote-test.json` |
| C-29 | VERIFIED | The explorer health endpoint returns HTTP 500 (`rippled unreachable`). | `https://explorer.testnet.postfiat.org/api/v1/health` | `outputs/explorer_health.json` |
| C-30 | SPECIFIED | A fresh node can verify synchronized state from header hashes and the validator list alone, without trusting the RPC endpoint. | Runbook A (drills A-01 to A-08) | `docs/runbook-a.md`, `outputs/derived/drill-results.json` — the live join itself was not run (see G-02) |

## Counts

- VERIFIED: 23
- SPECIFIED: 6
- UNVERIFIED: 0
- UNTESTABLE: 1
- Total: 30
