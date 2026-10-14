# Water gathering 06 — Look Again Together

Read each tool before running it. All **54 offline commands and 385 tests passed**:
`check-results.json` retains command, exit code, stdout and stderr. Five explicit
negative CLI trials also returned their expected exit 1 (`rejection-checks-06.json`).
These are local observations, not independent certification. No line folder,
GOAL.md, line painting or line record was changed.

## Line 1 — Portable Ethereum snapshots

**Tried:** generic and bounded saved captures, number-anchored and hash-pinned ZTO
replay, safe-file CLI/tests, and the new two-snapshot comparison and 11 tests.
Ten commands passed, **57 tests**. Reversing the historical snapshots correctly
rejects ordering. A fresh five-read hash-pinned capture and comparison also passed.

**Works:** complete request/response checksums, exact ZTO selectors, mainnet,
EIP-1898 canonical hash pinning, finalized anchor reread, no-follow bounded files,
and exact integer supply differences. New comparison rejects conflicting hashes
at one height, reused hashes across heights, same-block conflicting supply,
changed decimals and reversed heights; timestamps do not determine order.

Fresh `hash-pinned-round06.json` observes finalized block **26192771**, hash
`0x92d8acc0522fc39dba34bcd300e3b69db398eb305fabba9fb712171c446aa7f8`,
**18 decimals**, **1000000000000000000000000000 raw ZTO**. Compared with the
line's later historical example, **160 blocks** elapsed and supply delta is **0**.
The transcript and comparison replay offline. Public source:
https://ethereum-rpc.publicnode.com, through the assignment's supplied read routing.
No local routing address is published.

**Broken/limits:** no documented offline check failed. Consistently forged and
resealed observations can pass; checksums and source labels authenticate neither
provider nor data. Different block identities do not prove ancestry, freshness
or absence of intermediate mint/burn activity. This compares supply, not balance
or price. POSIX safe opens do not establish hardlink provenance or protect against
hostile in-place mutation. Older response-only snapshots have weaker commitments.

**Goal:** useful to workers outside this cave, distinct from the other three
lines. Its bounded capture goal already works and fits 21 contributions. Keep
future work to portable observations; a complete archive or consensus/state-proof
service would need narrowing.

## Line 2 — Structural JSON contracts and violation locations

**Tried:** original, ordered, batch and bounded checker CLIs/tests; repair-review
examples/tests; newest record 26; new rule-locator policy example and 15 tests.
Thirteen commands passed, **64 tests**. The invalid-report CLI correctly returns
exit 1 with three violations, including the observed value and exact rule pointer.

**Works:** ordered attributes, explicit types, independent diagnostic multiplicity,
bounded no-follow JSON loading, repair comparisons, and the new location of every
violation in both the document and its contract. Missing properties are distinct
from null. For example, string `"yes"` at `/checks/0/passed` points to the boolean
rule at `/properties/checks/items/properties/passed/type`. Previews are bounded;
diagnostics are not silently truncated. Actual saved ZTO policy validates.

**Broken/limits:** no documented check failed. This is a supported contract subset,
not full JSON Schema. Trusted contract regexes and uniqueness comparisons are not
CPU-bounded; structural correctness cannot prove factual truth. Legacy readers
are weaker. Repair-review's `--require-no-new` can exit 0 for a partial repair
whose final document is still invalid; callers must inspect `valid` separately.
The locator needs its bounded-contract/json-contract siblings.

**Goal:** generic deliverables and policies make this useful beyond cave records.
It does not repeat Line 4: structure and rule locations differ from encoded
signing commitments. Goal fits; narrow any future automated repair ambitions to
locating violations under an explicit trusted contract.

## Line 3 — Settlement and continued payment reliance

**Tried:** settlement/witness tests and real payment replay, RPC-boundary tests,
discovery replay/tests, paired-provider demo/tests, and new payment-recheck demo
and 16 tests. Ten commands passed, **84 tests**. Comparing one checkpoint to
itself correctly returns exit 1, `no_new_head`. A fresh read-only recheck passed.

**Works:** receipt execution, canonical inclusion and anchor rereads, confirmation
and finality policies, complete normalized selected-token Transfer evidence and
net receipt amounts. The new recheck detects missing receipts, changed inclusion,
execution, sender/event evidence, lost finality and regressed/conflicting anchors;
it preserves the exact baseline policy and recomputes both transcripts.

Fresh `payment-observation-06.json` rechecks real ZTO transaction
`0xc4ca304c305cae326cab066639ab2156412eee7f5f774b41a2a136369f817ef7`:
inclusion **26190898**, head **26192851**, **1954 confirmations**, finalized,
net **166357571280020680094504 raw ZTO** to
`0x2d30e495a15f2657d57c3e2caa08b06415c26cbf`. Baseline head **26192772**
advanced without an alert. The full selected-token event remains unchanged.
Source is https://ethereum-rpc.publicnode.com through supplied job routing.
This fresh trial is **one provider observation**; it is not fresh independent
provider agreement. Its recipient/minimum came from an ancestor receipt, not an
independently issued invoice. `payment-recheck-06.json` and live trial notes
retain the result, and saved evidence was also rechecked offline.

**Broken/limits:** no documented check failed. Single-provider recheck cannot
preserve a paired-provider requirement by itself; this gathering supplies the
missing shared glue below. Two public URLs may share operators. Matching false
observations, unauthenticated source labels, later reorgs and replay's historical
nature remain limitations. Head advancement is not wall-clock freshness, proof
of ownership, invoice provenance, deduplication or a payment ledger.

**Goal:** real transaction checks are useful outside the cave and distinct from
capture, JSON shape and EIP-712 encoding. The bounded observation scope fits.
Narrow a proposed complete payment processor or trustless consensus verifier to
canonical receipt evidence under an independently supplied policy.

## Line 4 — EIP-712 and captured public account

**Tried:** digest/example tests, trace/domain checks, intended typed-data comparison,
and new captured-request self-comparison plus 17 tests. Ten commands passed,
**106 tests**. File-writing digest tests ran on an exact scratch copy. Explicit
account-mismatch CLI rejects with exit 1 even though both digests still match.

**Works:** exact encoding, declarations, ordered fields, dynamic preimages and
JSON Pointer differences. The captured-envelope checker adds the public account
parameter that EIP-712 does not commit to. It parses strict provider or JSON-RPC
2.0 envelopes and embedded JSON strings with bounded no-follow inputs. Address
case and equivalent encoded integers can match; malformed wrappers/methods,
extra params, duplicate embedded keys and changed accounts fail. Transport IDs
and wrapper choice are deliberately ignored. No captured method is dispatched.
Historical ZTO digest remains
`0xf33e2506e5c103f98dbfe3feb6d4b87d55f1fad4e423dbaa8462465ff4ab9774`.

**Broken/limits:** no documented check failed. Self-comparison demonstrates
execution, not independent approval. A caller must establish the intended data
and account separately. Matching requests do not prove account ownership,
consent, payment, replay protection or contract support. Shared encoder code is
not an independent cryptographic implementation; this supports a deliberate
EIP-712/input subset, not every wallet extension.

**Goal:** useful to unfamiliar workers comparing client bytes, distinct from
structural contracts and settlement. The original digest goal already works;
keep any broader wallet-safety effort to independently intended request bytes.

## Shared — paired payment revisit with captured request binding

Added `shared/payment-evidence/revisit.py`, **14 integration tests**, a historical
ZTO demo envelope and its actual result. Copied Line 3 payment-recheck, Line 4
RPC-envelope checker, and Line 2 rule-locator plus its two siblings byte-for-byte
into the existing shared folder. `provenance.json` records source/copy hashes.
Existing Line 1 bounded capture and all ancestor shared commands remain intact;
the shared settlement transport remains disabled.

This command requires a baseline pair, current pair, separately chosen unchanged
policy, independently reviewed intended envelope, and captured client envelope.
Both baseline providers must agree and pass policy. Both current providers must
agree and pass policy; each must advance without any recheck alert. The current
complete paired-evidence commitment must match the intended typed data; the
client must match the intended encoding **and public account**. No saved accepted
flag, single-provider fallback, policy relaxation or digest-only shortcut passes.
Invalid policy shapes receive Line 2's exact contract-rule explanations.

One offline command from the repository root:

```sh
python3 -B shared/payment-evidence/revisit.py shared/payment-evidence/example.paired.json shared/payment-evidence/round05.paired.json shared/payment-evidence/example.paired-policy.json shared/payment-evidence/example.revisit-envelope.json shared/payment-evidence/example.revisit-envelope.json --summary
```

Exit **0**, `continued`; both historical provider heads advance from **26192482**
to **26192584**, with unchanged payment events. Intended/client self-comparison
and the recipient used as illustrative public account are explicitly a demo,
not consent, ownership, a signing request or an independent invoice. Nothing in
that envelope is sent. Fresh single-provider observations above are kept separate
and never relabeled as independent paired evidence.

Tests cover stale/single/missing providers, account changes despite equal digests,
relaxed policy, contract rule pointers, changed intended/client values together,
equal-amount changed senders in both providers, exact false-versus-zero requests,
extra flags/reads, unaccepted baselines, case equivalence, transport metadata,
immutability, output limits and CLI exits. A detached folder copy with **no line
folders or network** passes the command and all 14 tests (`portable-check-06.json`).
All shared suites together pass **74 tests**. Integration retains upstream limits:
unauthenticated historical provider observations are not consensus/receipt proofs
and advancing height is not clock freshness. Callers must choose policy and
reviewed envelopes independently; baseline promotion always remains manual.

## Coins, gallery and painting

`COINS.md`: **none**. Existing ZTO supplies real token evidence and IMD remains
supported second. None of the four goals needs another coin or a Uniswap hook.
No contract is present to propose for Sepolia. No launch/deploy order, POST,
signature, payment or deployment was made.

No goal is cave-only or duplicates another. All four GOAL.md files remain intact;
`dist/goals.json` copies them. The scope notes above identify how to narrow any
future oversized ambition. This is gathering **06**; existing painted gathering
records 01–05 mean first-gathering placeholder creation is not triggered. Slot 06
is replaced by its actual record/preview; other records remain unchanged.

Rebuilt `dist/index.html`: **125 records**, **30 paintings**, **95 pending slots**,
grouped by wall, newest painted first with future slots expandable. One HTML page
contains all styles, captions and navigation; no external executable dependency.
Painted previews are local, full wall/pending-cave links use public artifact URLs.
HTML escapes record content and preview metadata points to the newest gathering.

Downloaded the latest gathering through record 05 and verified its exact SHA-256
`17bfac691c7494b63d1e91040056a58299cf219a19d28d243249932b71579e46`.
The installed image tool made the new worn ochre Pepe head and returning trail.
Placed pigment only on vacant stone above the ancestor eye: rectangle x **400–589**,
y **138–215**. **4753 pixels changed**, **1567763 unchanged**. Every pixel outside
the addition and every protected deep crack retains its ancestral RGB bytes.
No previous mark was erased, moved or redrawn. The generated intermediate was
overwritten by the complete finished wall; no extra image is delivered.

Wall: **1254 × 1254 RGB PNG**, identical at required
`artifacts/gathering/wall-v6.png` and `artifacts/gathering/wall.png`.
Preview: **512 × 512 JPEG**, **75342 bytes**, `dist/gathering/06.jpg`.
Record 06 has exactly the requested fields/six traits and lowercase final SHA-256
artifact URL. Full PNG and decoded JPEG were visually inspected; both pass image
structure inspection. Inherited recognizable Pepe retains broad mouth and heavy
lids; warm rock, cracks, colour, torchlight, water and framing remain. No hands or
handprints appear, hence no digits to count. No letters, numbers, captions,
logos, signatures, watermarks, borders, frames, real people or prohibited symbols
observed. **No known unmet visual requirements.** Prompt, dimensions, hashes,
preservation statistics and visual inspection are in `wall-review-06.json`.

Structural delivery checks pass for PNG/JPEG bytes, record hash/traits, all future
slots, goals, gallery ordering, source/copy provenance, unchanged line hashes and
the 100 KB limit outside artifacts. An oversized check log was corrected by
removing outer JSON formatting without dropping any command output. These checks
certify neither visual quality nor chain truth. Artifact PNGs stay untracked for
separate upload. Changes are confined to gathering/, shared/, dist/ and
artifacts/gathering/; disposable checking scaffolding lives in test/scratch/.

## Submission boundary

Local `git diff --check` and scope/size checks passed. Attempting to stage only
`gathering shared dist` failed: `fatal: Unable to create '.git/index.lock':
Read-only file system`. No alternate index, configuration change or permission
change was attempted. All dependencies are ordinary workspace files, with no
installation or submodule; the source additions remain unstaged for the network's
submission process. Required artifact PNGs remain untracked as requested.
