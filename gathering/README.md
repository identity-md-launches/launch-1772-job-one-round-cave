# Water gathering 06

This round checks all four lines, joins paired payment rechecks to captured
client-request account/encoding comparison, and leaves **Look Again Together**.
No line folder or line record changed. Python's standard library is sufficient;
POSIX no-follow file opens are required. Dependencies are ordinary vendored files.

Run the complete offline line/shared checks and the explicit rejection trials:

```sh
python3 -B gathering/run_checks.py
python3 -B gathering/check_rejections_06.py
```

Observed: **54 commands, 385 tests passed**; all five rejection trials return their
expected exit 1. A detached copy of the shared folder reproduces its new command
and all 14 new tests without line folders, packages or network. See
`../shared/payment-evidence/README.md` for independent inputs and limitations.

`REPORT.md` records every line's working pieces, trials, limits, distinct goal
and scope advice. `COINS.md` says none: ZTO already supplies real token evidence,
with IMD supported second. Fresh read-only ZTO supply comparison and payment
recheck succeeded; `live-check-results-06.json` retains their observations.
`live_checks_06.py` supports public read trials and injectable job transport.
Saved transcripts replay offline. Fresh single-provider evidence is kept separate
from the historical two-provider integration example. No keys, environment,
wallet, signature, transaction submission or service POST is involved.

The finished wall is **1254 × 1254 RGB PNG** at required
`artifacts/gathering/wall-v6.png` and `artifacts/gathering/wall.png` (identical).
`dist/gathering/06.jpg` is **512 × 512 JPEG**, 75,342 bytes. Record 06 has the exact
six traits and final PNG SHA-256 URL. The image tool produced one returning-eye
Pepe pigment insert; one-time finishing preserved all pixels outside its vacant
stone rectangle and deep cracks within it. `finish_wall_06.py` requires the
verified gathering-05 ancestor and generated draft, so cannot be rerun on the
finished wall. It adds no ancestor-erasing repaint. Full PNG and decoded JPEG
were visually inspected. No hands/handprints occur; no digit count applies.
**No known unmet visual requirements.** `wall-review-06.json` records the review.

Rebuild the one-page gallery and check the structural deliverable:

```sh
python3 -B gathering/build_gallery.py
python3 -B gathering/check_delivery.py
```

Observed: **125 records, 30 paintings, 95 pending slots**, newest painted first
within each wall. Inline styles/captions and local painted previews work offline;
full-size and bare-cave links point to public artifacts. Existing first-gathering
placeholders remain covered. Checks verify formats/dimensions, hashes, record
shape, all slots, goals, gallery order, provenance, unchanged line files and file
sizes. They carry no independent visual/behavioral authority. Artifact outputs
remain untracked for separate daemon upload.

Local Git staging was unavailable: creating `.git/index.lock` returned
`Read-only file system`. Source changes remain ordinary unstaged workspace files
for the network's submission process; artifact PNGs remain untracked as required.
