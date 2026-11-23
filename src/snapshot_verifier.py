"""snapshot_verifier.py — recompute PFTL ledger hashes and verify hash chains
from public RPC data, using only the Python standard library.

The formulas implemented here are taken from the pinned postfiatd revision
0085a1ff (2026-10-10, PR #50 merge, v1.0.9) and were verified live against
the testnet before this pack was written:

* Ledger hash (src/xrpld/app/ledger/Ledger.cpp, calculateLedgerHash):
      sha512Half(HashPrefix::ledgerMaster, seq, drops, parentHash, txHash,
                 accountHash, parentCloseTime, closeTime,
                 closeTimeResolution, closeFlags)
  where HashPrefix::ledgerMaster = make_hash_prefix('L','W','R')
  = 0x4C575200 (include/xrpl/protocol/HashPrefix.h), serialized big-endian
  as four bytes, and sha512Half is the first 32 bytes of SHA-512.
  The field order matches addRaw (src/libxrpl/protocol/LedgerHeader.cpp).

* Skip-list keylet (src/libxrpl/protocol/Indexes.cpp):
      keylet::skip()      = sha512Half(uint16(0x73))            # 's'
      keylet::skip(seq)   = sha512Half(uint16(0x73), uint32(seq >> 16))
  Each ledger carries, in the skip-list state entry, the hashes of the
  previous 256 ledgers (Ledger::updateSkipList, src/xrpld/app/ledger/
  Ledger.cpp) and, at every 256th ledger, an anchor entry holding the
  hashes of every 256th prior ledger (hashOfSeq, src/libxrpl/ledger/
  View.cpp). A hash chain can therefore be checked without trusting the
  node: recompute each header hash, check each parentHash link, and check
  the skip-list entries against the recomputed hashes.

No network access happens here: this module only verifies data already
fetched by scripts/probe_all.sh. It never submits transactions.
"""

import hashlib
import struct

LEDGER_MASTER_PREFIX = 0x4C575200  # make_hash_prefix('L', 'W', 'R')
SKIP_LIST_NAMESPACE = 0x73  # LedgerNameSpace::SKIP_LIST = 's'
FLAG_LEDGER_INTERVAL = 256  # src/xrpld/app/ledger/Ledger.h


def sha512half(data: bytes) -> str:
    """First 32 bytes of SHA-512, hex uppercase (the uint256 wire format)."""
    return hashlib.sha512(data).digest()[:32].hex().upper()


def ledger_hash(seq, drops, parent_hash, tx_hash, account_hash,
                parent_close_time, close_time, close_time_resolution,
                close_flags):
    """Recompute a ledger hash from its header fields.

    All integer fields are big-endian; hashes are 32-byte big-endian.
    parent_close_time / close_time are seconds since the Ripple epoch
    (2000-01-01), exactly as the `ledger` RPC returns them.
    """
    pre = struct.pack(">I", LEDGER_MASTER_PREFIX)
    pre += struct.pack(">I", int(seq))
    pre += struct.pack(">Q", int(drops))
    pre += bytes.fromhex(parent_hash)
    pre += bytes.fromhex(tx_hash)
    pre += bytes.fromhex(account_hash)
    pre += struct.pack(">I", int(parent_close_time))
    pre += struct.pack(">I", int(close_time))
    pre += struct.pack(">B", int(close_time_resolution))
    pre += struct.pack(">B", int(close_flags))
    return sha512half(pre)


def ledger_hash_from_rpc(ledger):
    """Recompute the hash of a `ledger` RPC result object."""
    return ledger_hash(
        ledger["ledger_index"],
        ledger["total_coins"],
        ledger["parent_hash"],
        ledger["transaction_hash"],
        ledger["account_hash"],
        ledger["parent_close_time"],
        ledger["close_time"],
        ledger["close_time_resolution"],
        ledger["close_flags"],
    )


def skip_keylet():
    """Index of the rolling past-256 skip-list state entry."""
    return sha512half(struct.pack(">H", SKIP_LIST_NAMESPACE))


def skip_keylet_for(seq):
    """Index of the anchor skip-list entry covering ledger `seq`."""
    return sha512half(
        struct.pack(">H", SKIP_LIST_NAMESPACE) +
        struct.pack(">I", int(seq) >> 16))


def verify_chain(headers):
    """Verify a list of ledger header dicts ordered by descending seq.

    Returns a list of per-link results: for each adjacent pair, whether
    the newer ledger's parent_hash equals the older ledger's hash, and
    whether each header's hash recomputes. `headers` must be ordered
    newest-first with consecutive sequences.
    """
    results = []
    for i, h in enumerate(headers):
        recomputed = ledger_hash_from_rpc(h)
        results.append({
            "seq": int(h["ledger_index"]),
            "reported_hash": h["ledger_hash"].upper(),
            "recomputed_hash": recomputed,
            "hash_match": recomputed == h["ledger_hash"].upper(),
        })
    for i in range(len(headers) - 1):
        newer, older = headers[i], headers[i + 1]
        results[i]["parent_link_ok"] = (
            newer["parent_hash"].upper() == older["ledger_hash"].upper())
        results[i]["parent_seq_gap"] = (
            int(newer["ledger_index"]) - int(older["ledger_index"]))
    if results:
        results[-1]["parent_link_ok"] = None
        results[-1]["parent_seq_gap"] = None
    return results


def hash_of_seq_via_skip_list(skip_entry, validated_seq, target_seq):
    """Emulate hashOfSeq (src/libxrpl/ledger/View.cpp) from a skip-list entry.

    `skip_entry` is the node object returned by `ledger_entry` for the
    rolling skip-list keylet at the validated ledger. Returns the hash of
    `target_seq` if it is within the rolling 256-ledger window, else None.
    """
    hashes = skip_entry["node"].get("Hashes", [])
    last_seq = int(skip_entry["node"].get("LastLedgerSequence", 0))
    diff = validated_seq - target_seq
    if diff < 1 or diff > 256:
        return None
    if last_seq != validated_seq - 1:
        return None
    if len(hashes) < diff:
        return None
    return hashes[len(hashes) - diff].upper()
