# Snapshot verification

How to verify a ledger snapshot's integrity from hashes and the
validator list. Pinned source: postfiatd
`0085a1ff885d6a446369cf73a4430f75af22be55` (2026-10-10, PR #50 merge,
v1.0.9). Live data: probe of 2026-11-23 00:45:48 UTC.

## 0. What "snapshot" means here

There is no native ledger-snapshot export or import in the pinned code
(F-06). A "snapshot" in this pack is a set of ledger headers plus the
state-map and transaction-map roots they commit to — the data a node
holds for a ledger — and verification means recomputing the hashes and
checking them against the validator list, without trusting the node
that served them. The tooling is `src/snapshot_verifier.py`
(stdlib-only Python) and `scripts/drill.py` (drill C).

## 1. The ledger-hash formula

From `Ledger::calculateLedgerHash`
(`fixtures/source-excerpts/ledger-hash-calc.txt`):

```
ledger_hash = sha512Half(
    prefix 0x4C575200,          # HashPrefix::ledgerMaster = make_hash_prefix('L','W','R')
    seq            (uint32, big-endian),
    drops          (uint64, big-endian),   # total_coins
    parentHash     (32 bytes),
    txHash         (32 bytes),   # transaction_hash
    accountHash    (32 bytes),
    parentCloseTime (uint32, big-endian),
    closeTime      (uint32, big-endian),
    closeTimeResolution (uint8),
    closeFlags     (uint8))
```

`sha512Half` is the first 32 bytes of SHA-512. The field order matches
`LedgerHeader::addRaw`
(`fixtures/source-excerpts/ledger-header-fields.txt`). The prefix comes
from `HashPrefix.h` (`make_hash_prefix` shifts the three characters into
the high bytes: `('L'<<24)|('W'<<16)|('R'<<8)` = `0x4C575200`).

Verify it:

```bash
python3 - << 'EOF'
import json, sys
sys.path.insert(0, "src")
from snapshot_verifier import ledger_hash_from_rpc
led = json.load(open("outputs/ledger_validated.json"))["result"]["ledger"]
print(ledger_hash_from_rpc(led) == led["ledger_hash"].upper())
EOF
```

This pack recomputed 17 sampled headers (via the `ledger` and
`ledger_header` methods): 17/17 MATCH
(`outputs/derived/snapshot-verification.json`).

## 2. The chain check

Each ledger's `parentHash` must equal the previous ledger's hash, and
each header must recompute. Verified 7/7 parent links across two runs
(6 consecutive validated ledgers, 3 earliest ledgers).
`src/snapshot_verifier.py:verify_chain` implements the check; drill A-04
runs it.

## 3. The skip-list check

`hashOfSeq` (`View.cpp` lines 1040-1102) resolves a ledger hash three
ways:

- the ledger itself (seq == validated) or its parent (seq ==
  validated-1);
- the rolling skip vector (diff ≤ 256): the past-256 entry at keylet
  `sha512Half(uint16(0x73))` =
  `B4979A36CDC7F3D3D5C31A4EAE2AC7D7209DDA877588B9AFC66799692AB0D66B`,
  whose `Hashes` array ends at `LastLedgerSequence` = validated-1;
- the anchor skip vector (seq a multiple of 256): the entry at keylet
  `sha512Half(uint16(0x73), uint32(seq >> 16))`, whose `Hashes` array
  holds one hash per flag ledger in the 65536-ledger block.

Verified live: 5/5 rolling hashes match the chain headers, and 3/3
anchor positions match (hash(8284160) at tail-1, hash(8283904) at
tail-2, hash(8283648) at tail-3, with `LastLedgerSequence` 8284416 and
106 entries). The anchor position rule is
index = len-1-(LastSeq-seq)/256. A naive "tail equals the flag hash"
reading is wrong — the tail is the *newest* flag ledger in the block
(8284416 at probe time), and this pack's first draft of the check made
exactly that mistake before the live data corrected it.

Reach-back: rolling 256 + anchor 256×256 = ~65,536 ledgers (~2.3 days
at 3.042 s/ledger) for direct `hashOfSeq`; deeper hashes need the anchor
chain walked block by block.

## 4. The state-root check

`Ledger::setImmutable` sets `txHash` to the transaction-map hash and
`accountHash` to the state-map hash, then recomputes the ledger hash
(`fixtures/source-excerpts/ledger-set-immutable.txt`). To verify a state
snapshot:

1. Fetch the ledger header and recompute its hash (§1).
2. Fetch the state map (`ledger_data`) and compute its root; it must
   equal the header's `accountHash`.
3. Fetch the transaction map; its root must equal the header's `txHash`.
4. Recompute the header hash with the fetched roots; it must equal the
   claimed hash.

In this pack the state-map root check is exercised indirectly: the
genesis account balance is identical at the validated and earliest
ledgers (96999999999999880 drops), and `ledger_data` returns the same
first 5 `AccountRoot` entries at both ends of the range. A full
state-map root recomputation from a `ledger_data` dump is not possible
from the public RPC, which pages entries in batches of 5 in this pack's
probes and does not return the map root directly — the check is defined
here, not demonstrated end to end (see G-02).

## 5. The validator-list check

1. Fetch `https://postfiat.org/testnet_vl.json`.
2. Decode `blobs_v2[0].blob` (base64 JSON): sequence 30, effective
   848261408, expiration 891447293, 25 validators, each with a
   `validation_public_key` (ED...) and a manifest.
3. Check the publisher key is
   `ED3F1E0DA736FCF99BE2880A60DBD470715C0E04DD793FB862236B070571FC09E2`
   and the manifest is present (288 chars).
4. Check quorum: 17 of 25 validations are needed
   (`server_info` `validation_quorum`).
5. **Not done in this pack**: verify the blob signature (140-hex-char
   DER) against the publisher key — it needs Ed25519, which Python's
   standard library does not provide (C-24, G-03).

Drill A-08 performs steps 1-4; step 5 is recorded as UNTESTABLE.

## 6. Tamper detection (drill C, 7/7 PASS)

| Case | Tamper | Detection |
|------|--------|-----------|
| C-01 | `total_coins` +1 | Recomputed hash differs from claimed hash |
| C-02 | `parentHash` bit flip | Recomputed hash differs |
| C-03 | `accountHash` bit flip | Recomputed hash differs |
| C-04 | `parentHash` byte flip in the chain | Parent link V → V-1 reported False |
| C-05 | Skip-list hash byte flip | `hashOfSeq` result no longer matches the chain header |
| C-06 | `close_flags` flip | Recomputed hash differs |
| C-07 | Hash of V-1 claimed for V | Recomputation differs |

Every case records its own measured elapsed time
(`outputs/derived/drill-results.json`, `outputs/drill-run.log`).

## 7. What verification cannot catch

- A header whose fields are internally consistent but whose ledger was
  never validated by quorum: the hash recomputes, but only the
  validator list (and quorum 17/25) ties it to the network. Always
  check `validated_ledger` and `server_state` = `full` alongside the
  hash.
- A replaced validator list: the blob signature is the only defence,
  and it is not verified in this pack (G-03).
- Anything before ledger 8200054: no header is available to recompute
  (G-01, G-05).
