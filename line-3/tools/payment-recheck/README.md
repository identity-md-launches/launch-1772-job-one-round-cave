# Payment recheck

Re-evaluate a previously accepted Ethereum payment before relying on it again.
This standard-library Python tool replays the old checkpoint, applies its exact
policy to a new observation, and reports changes in inclusion, execution,
finality, sampled heads and the complete selected-token Transfer event set.
ZTO is the default token of the supplied real example; IMD policies also work.

Run this from the repository root, without network or packages:

```sh
python3 -B line-3/tools/payment-recheck/recheck.py --demo
```

It returns exit **0**, `accepted: true`, `state: continued`, and no alerts.
The baseline and current observations are both recomputed; neither a saved
acceptance flag nor the saved live-check report can authorize acceptance.
The demo compares historical real ZTO observations. Its recipient and minimum
were originally derived from a receipt, **not an independently supplied invoice**.

## What happened when tried

A read-only Ethereum recheck returned the same successful, finalized inclusion
at block **26190898** for transaction
`0xc4ca304c305cae326cab066639ab2156412eee7f5f774b41a2a136369f817ef7`.
The sampled head advanced from **26191361** to **26192772**, and confirmations
rose from **464** to **1875**. Both observations contain exactly the same ZTO
Transfer: **166357571280020680094504 raw ZTO**, from the supplied Uniswap v4
PoolManager to `0x2d30e495a15f2657d57c3e2caa08b06415c26cbf`, with no outgoing ZTO
in the receipt. There was no policy relaxation and no alert.

[current-evidence.json](current-evidence.json) contains the actual new read
transcript. [live-check.json](live-check.json) records the comparison. The
public source is [Ethereum Publicnode](https://ethereum-rpc.publicnode.com);
the assignment's Ethereum routing was used for the live request. This is one
provider observation, not another claim of independent two-provider agreement.
The ancestor baseline remains in `../payment-witness/live-evidence.json`.

## Use with a payment checkpoint

Choose and review the checkpoint's policy independently: transaction, recipient,
positive raw minimum, ZTO/IMD selection, confirmations and finality. This tool
preserves that policy and cannot tell whether it was the policy you intended.
A checkpoint is the `sample` object emitted by payment-witness, containing
exactly `version`, `policy` and `reads`, not the surrounding CLI report.

For example, recheck the documented historical payment live:

```sh
python3 -B line-3/tools/payment-recheck/recheck.py --baseline line-3/tools/payment-witness/live-evidence.json --live
```

Live mode uses Publicnode by default; `--rpc https://eth.drpc.org` selects the
other documented endpoint. There is no fallback, no polling, no signing or
transaction submission. Live results include `currentSample` when all evidence
can be replayed, even when the comparison rejects reliance. Only an accepted
payment checkpoint can serve as a baseline. Never replace a trusted baseline
automatically after `review_required`; preserve it and review the alert first.

Compare two explicitly saved witness transcripts offline:

```sh
python3 -B line-3/tools/payment-recheck/recheck.py --baseline line-3/tools/payment-witness/live-evidence.json --current line-3/tools/payment-recheck/current-evidence.json
```

Inputs must be visible workspace-relative regular files, at most 90 KB each.
The inherited descriptor-relative reader refuses symlinks, hidden/parent paths,
nonregular files, duplicate JSON keys and nonfinite JSON values. Read order,
parameters, exact request JSON types, envelope keys and full transcript
consumption are checked. No input or output files are written by the CLI;
it prints JSON. Copy this folder with its sibling provider-agreement,
payment-witness and settlement-check folders to use it elsewhere. Python 3.9+
and POSIX safe-file-open support are required; no install or environment setup.

## Decisions

| Result | Meaning | Exit |
| --- | --- | --- |
| `continued` | Head advanced; exact policy still passes; no listed evidence regression or payment change | 0 |
| `no_new_head` | Same sampled head and otherwise unchanged acceptable evidence; no new check established | 1 |
| `review_required` | One or more named alerts; do not continue relying automatically | 1 |
| `provider_error` | Fresh observation failed or could not be fully replayed | 2 |
| `input_error` | Invalid/unaccepted baseline, different policy, unsafe input or malformed evidence | 2 |

Changed inclusion needs review **even if** the transaction has been successfully
included again and its current payment policy passes. A changed sender or event
index needs review even when the net amount is identical. Event order itself
is normalized by log index. Lost finality, an older finalized head, conflicting
same-height anchor hashes, a missing receipt, reverted execution, unstable
canonicality, and payment shortfall all reject automatic continued reliance.
All detected alerts are returned together. If policy evaluation stops before
decoding payment events, absent event evidence is not misreported as a changed
event set; `payment_policy_not_met` rejects reliance instead.

## Checks and limits

```sh
python3 -B -m unittest discover -s line-3/tools/payment-recheck -p 'test_*.py' -v
```

All 16 tests passed, covering actual historical replay, unchanged
heads, new inclusion, equal-amount changed events, missing receipts, reverts,
unstable canonicality, finality/head regressions, shortfall, policy changes,
invalid checkpoints before network construction, provider failure, transcript
tampering, live/replay agreement, CLI boundaries and disabled proxy discovery.
Altered observations in tests are labelled rejection fixtures and never delivered
as real-chain evidence. Round-wide final check totals are in
`../../check-results-26.json`.

This detects inconsistencies in provider observations; it does not prove a reorg
actually occurred. A lagging or dishonest provider can create alerts or return
consistently false observations. An advancing height is **not wall-clock
freshness**, and saved source labels and SHA-256 transcript identifiers are
unauthenticated. Replay cannot establish today's canonicality. No consensus
proof, independent-provider requirement, invoice ownership, deduplication,
balance check or payment-processing ledger is supplied. In particular, this
single-provider tool does not preserve a paired-provider requirement: use
provider-agreement if that is part of your policy. Finality read failures that
cannot be completely replayed are conservatively `provider_error`.

The inherited transport is read-allowlisted, bounded, refuses redirects and
uses its own User-Agent with proxy/environment discovery disabled. Each read
has a 20-second timeout. Safe opens do not prove hardlink provenance or defeat
in-place mutation by another writer. No keys, wallet files, environment variables,
payment, deployment or new coin are needed.
