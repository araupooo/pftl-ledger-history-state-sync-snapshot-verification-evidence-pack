# Gap register

Gaps are things this pack could not establish. They are recorded here
rather than papered over; each one names what would close it.

| ID | Gap | What would close it |
|----|-----|---------------------|
| G-01 | The 86785 bulk-activation event has no node-side evidence: ledger 86785 returns `lgrNotFound` and its activation transaction returns `txnNotFound`. The event is known only from the VHS. | An archive node holding ledger 86785, or a preserved ledger file for that sequence. |
| G-02 | No live fresh-node join was run. State-sync claims (C-19, C-30) are code-specified and drill-verified on fetched data, not measured on a joining node. | Spin up a fresh node against the testnet, record the join (fetch-pack traffic, sync time, first validated ledger) and re-run drill A against it. |
| G-03 | The validator-list blob signature was not verified (no Ed25519 in the Python standard library). | Verify the DER signature over the decoded blob with an Ed25519-capable tool and the publisher key `ED3F1E0DA736FCF99BE2880A60DBD470715C0E04DD793FB862236B070571FC09E2`. |
| G-04 | No transaction-bearing ledger was sampled in the probe window, so a successful live transaction lookup was not demonstrated. | Re-run `scripts/probe_all.sh` when the network carries transactions and confirm a `tx` call returns a transaction object. |
| G-05 | History before 8200054 (8,200,053 ledgers) was not probed ledger by ledger; absence is inferred from the `complete_ledgers` range plus spot probes at 8200053, 86784 and 86785. | A full sweep is infeasible (8.2M calls); a denser spot sweep (e.g. every 100,000th ledger below the floor) would strengthen the inference. |
| G-06 | The public node's `LEDGER_HISTORY` and `online_delete` values are not visible; they are configuration, not exposed over RPC. | Ask the node operator, or infer retention from a longer observation of the `complete_ledgers` floor over days. |
| G-07 | The `subscribe` `snapshot` flag (the only `snapshot` hit in the RPC surface) was not exercised live; it is a subscription option, not a ledger snapshot. | Call `subscribe` with `snapshot: true` on a test account and record the returned state snapshot. |

## Counts

- Total: 7
