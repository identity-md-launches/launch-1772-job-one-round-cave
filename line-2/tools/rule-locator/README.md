# JSON rule locator

Find both ends of a structural violation: the JSON Pointer in your deliverable
and the exact JSON Pointer of the rule in its contract. Each error includes a
short preview of the constraint and observed value. Missing properties are
explicitly absent; a present `null` is never called missing. Useful for build
reports, API responses, manifests and worker handoffs.

Run from the repository root, offline, using Python 3.10+ and only its standard
library. This command checks the swarm's saved historical ZTO payment policy:

```sh
python3 -B line-2/tools/rule-locator/explain.py shared/payment-evidence/policy.contract.json shared/payment-evidence/example.policy.json
```

Observed result: exit **0**, `valid: true`, zero structural violations. This is
a structural check of saved public data, not evidence of a current payment,
ownership, chain finality or independent approval of that policy.

To see the additional diagnostic detail on an intentionally invalid build report:

```sh
python3 -B line-2/tools/rule-locator/explain.py line-2/tools/json-contract/report.contract.json line-2/tools/rule-locator/report.invalid.json
```

Observed result: exit **1**, three violations. For example,
`/checks/0/passed` contains the string `"yes"`, while the rule at
`/properties/checks/items/properties/passed/type` requires `"boolean"`.
The other errors are negative seconds and an unexpected property. The complete
observed output is in `example.explanation.json`. This fixture describes a
deliberately invalid report; it makes no claim that a build ran.

Exit codes: **0** valid; **1** structural violations; **2** invalid contract,
unreadable/malformed input or an explanation failure. An exit-2 report has
`valid: false` and an `error`, never an empty list presented as successful
validation. The command writes only JSON to stdout and never changes inputs.

`path` uses JSON Pointer in the document; the empty string means its root.
`contract_path` resolves in the contract itself. Missing-property diagnostics
point to a particular `/required/N` entry, extra properties to their parent's
`additionalProperties`, duplicate items to their array's `uniqueItems`, and
array children to `prefixItems/N` or `items` as appropriate. Original error
order, multiplicity, messages and validity come from the inherited engine.

Previews contain at most 160 ASCII characters of JSON serialization, with
`truncated` indicating omitted content. A truncated preview is display text,
not parseable JSON or a substitute for the actual value. The diagnostic list
is never truncated; pointers still locate the full inputs. String lengths are
Python Unicode code-point counts, not serialized byte lengths.

## Checks and boundaries

```sh
python3 -B line-2/tools/rule-locator/test_explain.py
```

All **15** tests passed, and all **49** inherited line-2 tests passed unchanged.
Tests exercise every emitted rule, nested prefix/tail arrays, exact contract
locations, escaping, boolean/number distinctions, missing versus null values,
bounded previews, input immutability, CLI exit codes, malformed/duplicate/
nonfinite JSON, symlinks and oversized files. They also check the actual saved
ZTO policy and an explicitly damaged in-memory copy. A test-fixture path was
corrected after the first run because this Python returns absolute temporary
directory paths; no input restriction was relaxed.

The trusted bootstrap is copied unchanged from `repair-review/review.py`.
Runtime dependencies are the existing sibling `bounded-contract/check.py` and
`json-contract/check.py`, all ordinary committed Python files. Keep this folder
and those two sibling folders together. The demo and one integration test also
use the repository's shared payment-policy files. No package installation,
network, environment access, wallet, secret, signing or transaction is needed.

Inputs are relative visible workspace regular files, at most 1,000,000 bytes
each. The inherited POSIX descriptor reader refuses symlinks, hidden/parent
paths, FIFOs, malformed UTF-8, duplicate keys and nonfinite JSON numbers.
Contracts and installed code must be trusted. The engine intentionally supports
a small structural-contract vocabulary, not all of JSON Schema. Regex cost,
quadratic uniqueness checking and total diagnostic output are not CPU/output
bounded. In-place hostile file mutation and hard-link provenance are outside
the file boundary's guarantee. Structural validity cannot establish factual
truth or tell you what a missing value should be.
