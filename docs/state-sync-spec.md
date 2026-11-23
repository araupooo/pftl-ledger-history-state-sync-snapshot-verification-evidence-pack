# State-sync specification

How a fresh node joins the PFTL testnet, what it downloads, and how it
verifies synchronized state. Pinned source: postfiatd
`0085a1ff885d6a446369cf73a4430f75af22be55` (2026-10-10, PR #50 merge,
v1.0.9). Live data: probe of 2026-11-23 00:45:48 UTC against
`https://rpc.testnet.postfiat.org/` (network ID 2025).

## 1. What a fresh node needs before it can join

- The validator list: `https://postfiat.org/testnet_vl.json`. At probe
  time it decodes (base64 JSON) to sequence 30, effective 848261408,
  expiration 891447293 (Ripple-epoch seconds), 25 validators, publisher
  key `ED3F1E0DA736FCF99BE2880A60DBD470715C0E04DD793FB862236B070571FC09E2`,
  manifest 288 chars. Each validator entry carries a
  `validation_public_key` (ED...) and a manifest. The blob signature is
  a 140-hex-char DER value; verifying it needs Ed25519, which Python's
  standard library does not provide (C-24, G-03).
- The genesis ledger and the network ID (2025). The genesis account
  `r4vhrMChCsaoFsBoCkRTRGUuc1njfr7bmA` holds 96999999999999880 drops.
- Peers: the probed node reports 21 peers and validation quorum 17 of
  25. The VHS topology endpoint reports 69 nodes in the network and a
  health count of 8 connected rippled nodes; the VHS validators endpoint
  reports 66 validators.

## 2. What a fresh node downloads

There is **no ledger snapshot to download**. The pinned code has no
native ledger-snapshot export or import: grep for `snapshot`
(case-insensitive) over `src/xrpld/rpc/handlers/` finds exactly one
match, `Subscribe.cpp:339`, which is the `snapshot`/`state_now` flag of
the `subscribe` call (return a live-state snapshot when subscribing) —
not a ledger snapshot. Grep over the ledger-acquisition files finds zero
matches. State sync happens only by SHAMap fetch from peers:

1. **Fetch pack / history acquisition.** `LedgerMaster::fetchForHistory`
   acquires missing ledgers; when more than the earliest known ledger is
   missing it requests a fetch pack from the highest-score peer
   (`getFetchPack` sends `TMGetObjectByHash` with type `otFETCH_PACK`).
   See `fixtures/source-excerpts/fetch-for-history.txt` and
   `fixtures/source-excerpts/fetch-pack-request.txt`.
2. **Inbound ledger acquisition.** `InboundLedger` fetches the
   transaction map root and the state map root of each acquired ledger
   (`fetchRoot` for `txHash` and `accountHash`), then walks the needed
   hashes (`getNeededHashes`) until the maps are complete. Timeout is
   3000 ms per attempt, with up to 6 retries
   (`fixtures/source-excerpts/inbound-ledger-timeouts.txt`).
3. **History fill.** `LedgerMaster::doAdvance` fills history only when
   the node is in sync (validated ledger is the published one, validated
   age below the maximum acquire age, write load low, fewer than 10
   pending old-ledger jobs). `shouldAcquire` gates acquisition on the
   candidate being at or above the current ledger, within
   `ledgerHistory` of it, or at/above `minimumOnline`
   (`fixtures/source-excerpts/do-advance-history-fill.txt`,
   `fixtures/source-excerpts/should-acquire.txt`).
4. **Retention.** `LEDGER_HISTORY` `full` means maximum retention; any
   other value is a ledger count; default is 0
   (`fixtures/source-excerpts/config-ledger-history.txt`). With
   `online_delete` set, `LEDGER_HISTORY` must be at most
   `deleteInterval_`, enforced by SHAMapStore rotation
   (`fixtures/source-excerpts/shamapstore-online-delete.txt`).

## 3. How the node verifies synchronized state

A joining node does not trust a single peer. It verifies, in order:

1. **Ledger hash.** Every acquired ledger's hash is recomputed from its
   header fields (`calculateLedgerHash`: sha512Half of the
   `ledgerMaster` prefix `0x4C575200` plus seq, drops, parentHash,
   txHash, accountHash, parentCloseTime, closeTime, closeTimeResolution,
   closeFlags). This pack recomputed 17 sampled headers with the same
   formula in stdlib-only Python: 17/17 MATCH.
2. **Parent chain.** Each ledger's `parentHash` must equal the previous
   ledger's hash. Verified 7/7 across two runs.
3. **Skip lists.** `hashOfSeq` resolves any ledger hash within the
   rolling 256-ledger window, and anchor entries resolve every 256th
   ledger back ~65,536 ledgers (~2.3 days at 3.042 s/ledger). Verified
   5/5 rolling and 3/3 anchor positions. The anchor lookup needs
   `LastLedgerSequence`: a flag hash sits at index
   len-1-(LastSeq-seq)/256, not at the tail.
4. **State and transaction roots.** `setImmutable` sets `txHash` to the
   transaction-map hash and `accountHash` to the state-map hash, then
   recomputes the ledger hash. A state map fetched from a peer is
   accepted only if its root hash matches the ledger header's
   `accountHash`.
5. **Validator set.** Validations are checked against the validator list
   (`ValidatorList::verify` checks the list blob signature;
   `fixtures/source-excerpts/validator-list-verify.txt`). Quorum is 17
   of 25. The probed node was in `full` state with a validated ledger
   age of 1 s.
6. **Replay check.** `LedgerReplayMsgHandler` rejects a replayed ledger
   whose recomputed hash differs from the claimed hash
   (`fixtures/source-excerpts/ledger-replay-hash-check.txt`) — the same
   check drill C performs locally.

## 4. Measured sync-surface data (live probe, 2026-11-23 00:45:48 UTC)

| Measure | Value |
|---------|-------|
| `complete_ledgers` | 8200054-8284498 |
| `server_state` | `full` (in `full` for 2,274,993,693,022 µs, 1 transition) |
| Validated ledger age | 1 s |
| Last close proposers | 24 |
| Peer disconnects | 103 (resources: 0) |
| Ports | 2559 (peer), 6005 (ws), 50051 (grpc) |
| Base fee / median fee | 10 / 5000 drops |
| Current ledger size / queue size | 0 / 0 |
| Reserve base / increment | 10,000,000 / 2,000,000 drops |
| Node public key | `n9K4AomBUHA8XGwXtZs6qfCjXm5aXre9UchiD6oGuZx1UeRLUweE` |
| `feature_list` | 101 amendments (64 enabled, 37 disabled) |
| Ledger cadence | 3.042 s/ledger |

What the public RPC does **not** expose: `validators`, `peers` and
`ledger_request` all return HTTP 403 Forbidden, so peer and
validator-list detail is not visible from the public endpoint. An
unknown method returns `unknownCmd` (error_code 32), not 403. The
explorer health endpoint returns HTTP 500 (`rippled unreachable`).

## 5. What a fresh node cannot get from this network

- Ledgers before 8200054 (8,200,053 of them) — the history floor. A
  fresh node joining today re-derives at most the last ~2.96 days from
  this node.
- The 86785 bulk activation — VHS-only (see
  `docs/ledger-history-inventory.md`).
- A snapshot file — none exists to download (see §2).

## 6. Sync thresholds (machine-readable)

`configs/sync-thresholds.json` carries the thresholds this pack uses:
quorum 17/25, validated-age limit 30 s, cold-lookup attempts 3, acquire
timeout 3000 ms, acquire retries 6, flag interval 256, skip reach-back
65,536 ledgers, minimum history window 1 day (observed 2.96 days).
