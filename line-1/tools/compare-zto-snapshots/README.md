# Compare verified ZTO snapshots

Compare two portable hash-pinned Ethereum snapshots offline, with exact signed
ZTO supply changes and block distance. Both complete five-read transcripts are
validated before any comparison: mainnet, finalized anchor, ZTO address/selectors,
EIP-1898 canonical hash pin, anchor reread and both checksum layers. The new
piece uses only Python's standard library and performs no network calls.

Run from the repository root:

```sh
python3 -B line-1/tools/compare-zto-snapshots/compare.py line-1/tools/hash-pinned-zto/live-zto.json line-1/tools/compare-zto-snapshots/live-zto.json
```

Tried on 2026-10-15: exit 0, the saved real observations span blocks 26192324
and 26192611 (287 blocks). Both report 18 decimals and raw total supply
1000000000000000000000000000. The exact difference is
0.000000000000000000 ZTO. `comparison.json` contains the result. The later
bundle was captured successfully with the existing hash-pinned tool using five
public Ethereum reads and its own User-Agent; no transaction was submitted.

For your own inputs, capture to two **new** visible workspace paths using
`line-1/tools/hash-pinned-zto/pinned.py --output PATH`, then pass the earlier
bundle followed by the later bundle to this command. No waiting is required;
same-block observations are supported. Inputs use the inherited bounded,
no-follow regular-file reader (100000 bytes per file). Output is JSON on stdout;
exit 0 means comparison succeeded, including when supply changed. Exit 1 means
invalid evidence or incompatible observations; diagnostics go to stderr.

Rejects reversed heights, different hashes at one height, one hash at different
heights, conflicting supplies for one block and changed decimals. Ordering uses
block heights, not untrusted capture timestamps. Decimal changes require a
separate investigation rather than an assumed conversion. Supply differences
are arbitrary-precision integer arithmetic; no floats or guessed precision.
Whole-bundle SHA-256 values identify the compared input contents.

```sh
python3 -B line-1/tools/compare-zto-snapshots/test_compare.py
```

All 11 new offline tests passed, as did the 27 inherited hash-pinned tests.
New tests cover real self-comparison, input immutability, unchanged supply across
heights, positive/negative one-raw-unit changes, ordering, conflicting hashes,
reused hash, same-block supply conflict, decimal changes, request/checksum
tampering, CLI/path rejection and timestamp independence. Synthetic mutations
exist only inside tests and are never represented as chain evidence.

Limits: this compares provider observations, not Ethereum state proofs. A
consistently forged and resealed bundle can pass. Different heights and hashes
do not prove ancestry or the absence of reorganization. Neither endpoint labels,
checksums nor timestamps authenticate a source or freshness. An unchanged supply
does not prove no mint/burn activity occurred between observations. This does
not compare balances, market prices or payments. Keep the sibling hash-pinned,
bounded and safe-files tools with this folder; they are local dependencies.
