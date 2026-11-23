#!/bin/bash
# probe_all.sh — re-probe every live public endpoint used by this pack and
# retain the unedited responses under outputs/.
#
# Usage: bash scripts/probe_all.sh [OUTPUT_DIR]
#   OUTPUT_DIR defaults to outputs/ relative to the pack root.
# No credentials, sessions, or accounts are used. All endpoints are public.
#
# SAFETY BOUNDARY (non-negotiable, see docs/methodology.md): BOUNDED
# OBSERVATION ONLY. This script performs read-only queries only. It sends no
# transactions, no votes, no flood traffic, and no load of any kind to the
# shared testnet. Total RPC calls: ~43 POSTs; total HTTP GETs: 10.
set -u
PACK_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$PACK_ROOT/outputs}"
mkdir -p "$OUT" "$OUT/derived"
LOG="$OUT/probe-run.log"
: > "$LOG"
log() { echo "$*" | tee -a "$LOG"; }
sha() { sha256sum "$1" | awk '{print $1}'; }

log "probe_all.sh run start: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
log "pack root: $PACK_ROOT"
log "safety boundary: read-only queries only; no transactions, no votes, no flood traffic"

RPC="https://rpc.testnet.postfiat.org/"
post() { # $1 outfile $2 method-json [$3 expect_error=1]
  local expect_error="${3:-0}"
  local attempt=1
  while :; do
    curl -s -m 30 -X POST "$RPC" -H 'Content-Type: application/json' -d "$2" \
      -o "$OUT/$1" -w "%{http_code} %{time_total}s" > "$OUT/$1.http" 2>&1
    log "$1 attempt $attempt -> $(cat "$OUT/$1.http") sha256=$(sha "$OUT/$1")"
    rm -f "$OUT/$1.http"
    # Cold old-ledger lookups return lgrNotFound while the node acquires the
    # candidate flag ledger; retry twice before accepting the result.
    if [ "$expect_error" = "1" ] || ! grep -q '"error"' "$OUT/$1" || [ "$attempt" -ge 3 ]; then
      break
    fi
    log "$1 error on attempt $attempt, retrying in 8s (candidate acquire)"
    sleep 8
    attempt=$(( attempt + 1 ))
  done
}
get() { # $1 url $2 outfile
  curl -s -m 30 "$1" -o "$OUT/$2" -w "%{http_code} %{time_total}s %{size_download}B" > "$OUT/$2.http" 2>&1
  log "$2 -> $(cat "$OUT/$2.http") sha256=$(sha "$OUT/$2")"
  rm -f "$OUT/$2.http"
}

# --- postfiatd JSON-RPC (public proxy) ---
post server_info.json '{"method":"server_info","params":[{}]}'
VALIDATED_SEQ="$(python3 -c "import json;print(json.load(open('$OUT/server_info.json'))['result']['info']['validated_ledger']['seq'])")"
VALIDATED_HASH="$(python3 -c "import json;print(json.load(open('$OUT/server_info.json'))['result']['info']['validated_ledger']['hash'])")"
EARLIEST="$(python3 -c "import json;print(json.load(open('$OUT/server_info.json'))['result']['info']['complete_ledgers'].split('-')[0])")"
log "validated seq: $VALIDATED_SEQ hash: $VALIDATED_HASH earliest: $EARLIEST"
post ledger_current.json "{\"method\":\"ledger\",\"params\":[{\"ledger_index\":$VALIDATED_SEQ,\"transactions\":true,\"expand\":false}]}"
post ledger_closed.json '{"method":"ledger_closed","params":[{}]}'
post fee.json '{"method":"fee","params":[{}]}'
post server_state.json '{"method":"server_state","params":[{}]}'
post feature_list.json '{"method":"feature","params":[{}]}'

# --- history boundary probes ---
# Earliest complete ledger, one below it, and the 86785 bulk-activation
# ledger (the activation event whose transaction cannot be re-derived).
post ledger_earliest.json "{\"method\":\"ledger\",\"params\":[{\"ledger_index\":$EARLIEST,\"transactions\":false}]}"
post ledger_8200053.json '{"method":"ledger","params":[{"ledger_index":8200053,"transactions":false}]}' 1
post ledger_86785.json '{"method":"ledger","params":[{"ledger_index":86785,"transactions":false}]}' 1
post ledger_86784.json '{"method":"ledger","params":[{"ledger_index":86784,"transactions":false}]}' 1

# --- validated ledger with transactions (for the tx-lookup probe) ---
post ledger_validated.json "{\"method\":\"ledger\",\"params\":[{\"ledger_index\":$VALIDATED_SEQ,\"transactions\":true,\"expand\":false}]}"
TX_HASH="$(python3 -c "
import json
led=json.load(open('$OUT/ledger_validated.json'))['result']['ledger']
txs=led.get('transactions',[])
print(txs[0] if txs else '')")"
log "recent tx hash for lookup: ${TX_HASH:-<none in this ledger>}"

# --- flag ledgers (multiples of 256; the skip-list anchors) ---
FLAG=$(( (VALIDATED_SEQ / 256 - 1) * 256 ))
FLAG2=$(( FLAG - 256 ))
FLAG3=$(( FLAG - 512 ))
log "flag ledgers: $FLAG $FLAG2 $FLAG3"
post ledger_flag.json "{\"method\":\"ledger\",\"params\":[{\"ledger_index\":$FLAG,\"transactions\":false}]}"
post ledger_header_flag.json "{\"method\":\"ledger_header\",\"params\":[{\"ledger_index\":$FLAG}]}"
post ledger_header_flag2.json "{\"method\":\"ledger_header\",\"params\":[{\"ledger_index\":$FLAG2}]}"
post ledger_header_flag3.json "{\"method\":\"ledger_header\",\"params\":[{\"ledger_index\":$FLAG3}]}"
post ledger_header_earliest.json "{\"method\":\"ledger_header\",\"params\":[{\"ledger_index\":$EARLIEST}]}"
post ledger_header_86785.json '{"method":"ledger_header","params":[{"ledger_index":86785}]}' 1
post ledger_header_validated.json "{\"method\":\"ledger_header\",\"params\":[{\"ledger_index\":$VALIDATED_SEQ}]}"

# --- consecutive-chain headers (newest first) for parent-link checks ---
for i in 0 1 2 3 4 5; do
  SEQ=$(( VALIDATED_SEQ - i ))
  post "ledger_chain_$i.json" "{\"method\":\"ledger\",\"params\":[{\"ledger_index\":$SEQ,\"transactions\":false}]}"
done
for i in 0 1 2; do
  SEQ=$(( EARLIEST + i ))
  post "ledger_chain_earliest_$i.json" "{\"method\":\"ledger\",\"params\":[{\"ledger_index\":$SEQ,\"transactions\":false}]}"
done

# --- state samples ---
post ledger_data_validated.json "{\"method\":\"ledger_data\",\"params\":[{\"ledger_index\":$VALIDATED_SEQ,\"limit\":5}]}"
post ledger_data_earliest.json "{\"method\":\"ledger_data\",\"params\":[{\"ledger_index\":$EARLIEST,\"limit\":5}]}"

# --- skip-list entries (keylets computed by the verifier module) ---
SKIP_KEY="$(python3 -c "import sys; sys.path.insert(0, '$PACK_ROOT/src'); from snapshot_verifier import skip_keylet; print(skip_keylet())")"
SKIP_FLAG_KEY="$(python3 -c "import sys; sys.path.insert(0, '$PACK_ROOT/src'); from snapshot_verifier import skip_keylet_for; print(skip_keylet_for($FLAG))")"
log "skip keylet: $SKIP_KEY skip($FLAG) keylet: $SKIP_FLAG_KEY"
post ledger_entry_skip.json "{\"method\":\"ledger_entry\",\"params\":[{\"index\":\"$SKIP_KEY\",\"ledger_index\":$VALIDATED_SEQ}]}"
post ledger_entry_skip_flag.json "{\"method\":\"ledger_entry\",\"params\":[{\"index\":\"$SKIP_FLAG_KEY\",\"ledger_index\":$VALIDATED_SEQ}]}"
post ledger_entry_genesis.json "{\"method\":\"ledger_entry\",\"params\":[{\"account_root\":\"r4vhrMChCsaoFsBoCkRTRGUuc1njfr7bmA\",\"ledger_index\":$VALIDATED_SEQ}]}"

# --- transaction lookups ---
if [ -n "$TX_HASH" ]; then
  post tx_recent.json "{\"method\":\"tx\",\"params\":[{\"transaction\":\"$TX_HASH\"}]}"
fi
post tx_86785.json '{"method":"tx","params":[{"transaction":"0E373029EEF6AB43E24D5F1EAFBAEB80BBA9B94610BCE1A3D004101CCFAE7048"}]}' 1

# --- account history (min below the earliest ledger: the clamp test) ---
post account_tx_genesis.json "{\"method\":\"account_tx\",\"params\":[{\"account\":\"r4vhrMChCsaoFsBoCkRTRGUuc1njfr7bmA\",\"ledger_index_min\":1,\"ledger_index_max\":$VALIDATED_SEQ,\"limit\":3}]}"
post account_info_genesis.json "{\"method\":\"account_info\",\"params\":[{\"account\":\"r4vhrMChCsaoFsBoCkRTRGUuc1njfr7bmA\",\"ledger_index\":$VALIDATED_SEQ}]}"
post account_info_genesis_earliest.json "{\"method\":\"account_info\",\"params\":[{\"account\":\"r4vhrMChCsaoFsBoCkRTRGUuc1njfr7bmA\",\"ledger_index\":$EARLIEST}]}"

# --- ledger_request path (getLedgerByContext) ---
post ledger_request_validated.json "{\"method\":\"ledger_request\",\"params\":[{\"ledger_hash\":\"$VALIDATED_HASH\"}]}"

# --- Admin-gated methods: the public proxy is expected to refuse these; the
# refusal body itself is the evidence and is kept unedited.
post validators.json '{"method":"validators","params":[{}]}' 1
post peers.json '{"method":"peers","params":[{}]}' 1
post invalid_method.json '{"method":"no_such_method","params":[{}]}' 1

# --- Validator History Service (public read API) ---
get "https://vhs.testnet.postfiat.org/v1/health" vhs-health.json
get "https://vhs.testnet.postfiat.org/v1/network/amendments" vhs-amendments.json
get "https://vhs.testnet.postfiat.org/v1/network/amendments/info" vhs-amendments-info.json
get "https://vhs.testnet.postfiat.org/v1/network/amendments/vote/test" vhs-amendments-vote-test.json
get "https://vhs.testnet.postfiat.org/v1/network/validators" vhs-validators.json
get "https://vhs.testnet.postfiat.org/v1/network/topology" vhs-topology.json

# --- Validator list (the live UNL publisher document) ---
get "https://postfiat.org/testnet_vl.json" testnet_vl.json

# --- Explorer (expected: API may be degraded; HTTP status is the evidence) ---
get "https://explorer.testnet.postfiat.org/api/v1/health" explorer_health.json

# --- Project site ---
get "https://postfiat.org/" postfiat_org.html
get "https://postfiat.org/whitepaper/" postfiat_whitepaper.html

# --- cadence measurement (60 s window) ---
python3 "$PACK_ROOT/scripts/measure_cadence.py" "$OUT" >> "$LOG" 2>&1 || log "measure_cadence FAILED"

log "probe_all.sh run end: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
