# Ledger history inventory

Pinned source: postfiatd `0085a1ff885d6a446369cf73a4430f75af22be55`
(2026-10-10, PR #50 merge, v1.0.9). Live probe: 2026-11-23 00:45:48 UTC
against `https://rpc.testnet.postfiat.org/` (network ID 2025).

## What the node holds

| Measure | Value | Source |
|---------|-------|--------|
| Build version | 1.0.9 | `outputs/server_info.json` |
| Network ID | 2025 | `outputs/server_info.json` |
| Peers | 21 | `outputs/server_info.json` |
| Validation quorum | 17 | `outputs/server_info.json` |
| Server state | `full` | `outputs/server_info.json` |
| Uptime | 2,275,134 s (~26.3 days) | `outputs/server_info.json` |
| Complete ledgers | 8200054-8284498 | `outputs/server_info.json` |
| Validated ledger | 8284498, hash `1F1A016884FA0A7458BF11BE71F7ADEABD740961643DD8466996E213A5D91499` | `outputs/server_info.json` |
| Earliest held ledger | 8200054, hash `370CE545196307071AE272FB26EDDCB90BDD3CA0FA5C395744FD53E287500CDD` | `outputs/ledger_earliest.json` |
| Ledgers in range | 84,445 | `outputs/derived/history-range.json` |
| Ledgers before the floor | 8,200,053 | `outputs/derived/history-range.json` |
| Earliest close time | 2026-11-20 01:46:50 UTC | `outputs/ledger_header_earliest.json` |
| Validated close time | 2026-11-23 00:45:50 UTC | `outputs/ledger_header_validated.json` |
| Window span | 255,540 s (2.96 days) | `outputs/derived/history-range.json` |
| Ledger cadence | 3.042 s/ledger (20 ledgers in 60.8 s) | `outputs/derived/cadence.json` |

The node holds 84,445 of 8,284,498 ledgers — about 1.02% of the chain.
Everything before 8200054 is absent from this node, not merely slow to
fetch: `ledger` calls for 8200053, 86784 and 86785 all return
`lgrNotFound` (error_code 21), and the same result was seen on repeat
calls. The retention window is a property of this node's configuration,
not of the protocol: `LEDGER_HISTORY` and `online_delete` are operator
settings (`Config.cpp` lines 652-661; `SHAMapStoreImp.cpp` lines 121-163),
and they are not exposed over RPC (see G-06).

## What can be re-derived from the node

Inside the complete range, everything is re-derivable and was verified
live:

- **Header hashes**: 17 sampled headers recompute exactly
  (`outputs/derived/snapshot-verification.json`, 17/17 MATCH). The
  formula is `sha512Half` of the `ledgerMaster` prefix `0x4C575200` plus
  the nine header fields, in the order of `LedgerHeader::addRaw`
  (`fixtures/source-excerpts/ledger-hash-calc.txt`).
- **Parent chains**: 7/7 parent links hold across two runs (6 consecutive
  validated ledgers, 3 earliest ledgers).
- **Skip-list hashes**: 5/5 rolling-window hashes and 3/3 anchor-skip
  positions match the fetched headers. The rolling entry (keylet
  `B4979A36CDC7F3D3D5C31A4EAE2AC7D7209DDA877588B9AFC66799692AB0D66B`)
  holds 256 hashes ending at the validated ledger minus one; the anchor
  entry for the 65536-ledger block (keylet
  `A89F167EF93B8E615074E3043133600DDAB076E24C87D0336BA5F9FAB0F9C627`)
  holds 106 hashes, with `LastLedgerSequence` 8284416. A flag hash sits
  at index len-1-(LastSeq-seq)/256 — not at the tail unless it is the
  newest flag ledger (verified live: hash(8284160) at tail-1,
  hash(8283904) at tail-2, hash(8283648) at tail-3).
- **Account state**: the genesis account
  `r4vhrMChCsaoFsBoCkRTRGUuc1njfr7bmA` holds 96999999999999880 drops at
  both the validated and the earliest ledger (`account_info` probes).
  `ledger_data` with limit 5 returns 5 `AccountRoot` entries at both ends
  of the range.
- **Amendment state**: `feature_list` reports 101 amendments, 64 enabled
  and 37 disabled. The 64 enabled names are exactly the 64 names in the
  VHS bulk-activation record — the current enabled set corroborates the
  VHS record even though the node cannot show the activation itself.

## What cannot be re-derived from the node

| Event | Node result | What is known instead |
|-------|-------------|----------------------|
| Ledger 86785 (bulk activation of 64 amendments) | `ledger` → `lgrNotFound` (21); activation tx → `txnNotFound` (29) | VHS vote record: all 64 amendments at ledger 86785, 2026-02-09T14:31:12.000Z |
| Any ledger below 8200054 | `lgrNotFound` | Only the ledger count (8,200,053) and the cadence back-projection |
| Any transaction before 8200054 | Not lookable up (no ledger, no tx) | VHS amendment records only |

### Worked case: the 86785 bulk activation

The Validator History Service records 64 amendments — among them
`fixEnforceNFTokenTrustlineV2`, `AMM`, `PriceOracle`, `TicketBatch`,
`Clawback`, `DeepFreeze`, `DID`, `Credentials`, `Checks`, `DepositAuth`,
`Flow`, `XRPFees` — all sharing ledger index 86785, transaction hashes
distinct per amendment, and the single timestamp 2026-02-09T14:31:12.000Z
(`outputs/vhs-amendments-vote-test.json`, count 64). The node holds
none of it:

- `ledger` 86785 → `lgrNotFound`, error_code 21
  (`outputs/ledger_86785.json`).
- `ledger_header` 86785 → `lgrNotFound`
  (`outputs/ledger_header_86785.json`).
- `tx` `0E373029EEF6AB43E24D5F1EAFBAEB80BBA9B94610BCE1A3D004101CCFAE7048`
  (the `fixEnforceNFTokenTrustlineV2` activation transaction) →
  `txnNotFound`, error_code 29 (`outputs/tx_86785.json`).

A cadence back-projection is consistent with the VHS date but does not
prove it: at 3.042 s/ledger, ledger 86785 projects to 2026-02-07 ~09:41
UTC from the validated ledger (2026-02-07 ~10:04 UTC from the earliest
ledger) — about two days before the VHS timestamp, within cadence drift.
The back-projection is an approximate consistency check, not a
derivation. The activation date is known only from the VHS.

## Transaction activity in the window

All 9 ledgers sampled in this pack (6 validated-chain, 3 earliest, plus
the flag ledger) carried zero transactions. The network was idle during
the probe window (`fee` reports `current_ledger_size` 0,
`current_queue_size` 0, base fee 10 drops, median fee 5000 drops). No
live recent-transaction lookup could be demonstrated; see G-04.

## Cross-checks

- **Enabled set vs VHS**: the 64 enabled amendments in `feature_list`
  are exactly the 64 VHS-activated names (no differences either way).
- **Cadence vs floor**: 8,200,053 pre-floor ledgers at 3.042 s/ledger
  span 288.71 days; the validated ledger minus that span lands
  ~2026-02-07, days before the 2026-02-09 activation — consistent.
- **Full-history replay**: 8,284,498 ledgers at 3.042 s/ledger would
  take ~291.68 days to replay from genesis.
