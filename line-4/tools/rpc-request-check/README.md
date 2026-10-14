# Offline captured EIP-712 request checker

Check a captured `eth_signTypedData_v4` request against a separately reviewed
intended request, including the public account parameter. Standard-library
Python only; copy this whole folder for independent offline use. It reads JSON
files and prints a report. It makes no provider calls and never signs or sends.

One command from the repository root:

```sh
python3 -B line-4/tools/rpc-request-check/rpc_request_check.py line-4/tools/rpc-request-check/zto-envelope.json line-4/tools/rpc-request-check/zto-envelope.json --summary
```

Tried: exit **0**, `accepted: true`, matching account and complete typed-data
encoding, historical ZTO digest
`0xf33e2506e5c103f98dbfe3feb6d4b87d55f1fad4e423dbaa8462465ff4ab9774`.
This self-comparison demonstrates execution, not independent review or consent.
Replace the second path with `line-4/tools/rpc-request-check/account-mismatch.json`
to see exit **1**: the digest matches but the public account differs.

The example embeds the ancestor's unchanged historical ZTO payment-evidence
request. Its illustrative account is the observed receipt's recipient,
`0x2d30e495a15f2657d57c3e2caa08b06415c26cbf`; no ownership, signing request or
authorization by that account is claimed. The rejection fixture substitutes the
real ZTO contract address solely to demonstrate a differing account. Neither
example should be submitted anywhere. No fresh chain observation is claimed.

For actual use, prepare the intended envelope independently and capture the
client envelope separately. Accepted shapes are exactly `{method, params}`
(provider request) or `{jsonrpc, id, method, params}` (JSON-RPC 2.0 request).
The method must be `eth_signTypedData_v4`; params must contain exactly a
20-byte public address and a JSON **string** containing complete typed data.
This follows [MetaMask's documented parameter order](https://docs.metamask.io/metamask-connect/evm/guides/sign-data/).
Object payloads, swapped parameters, extra fields, batches, other methods,
notifications, null/boolean IDs and partial JSON-RPC wrappers are refused.
This deliberately strict subset does not accept every provider extension.

The tool compares the account as address bytes independently of the digest:
EIP-712 does not include that RPC parameter. It then uses the ancestor's full
encoding comparison, preserving field order, types and dynamic preimages.
Equivalent address case, integer notation and object key order may match.
JSON-RPC ID and provider-versus-JSON-RPC wrapping are validated but ignored in
comparison because neither is part of the signing commitment. Reports explicitly
name this policy. Transport IDs are not a correlation or replay-protection check.

Exit **0** means both account and encoding match; **1** means valid requests
differ; **2** means invalid input, unsafe path or exceeded limits. Both outer
JSON and the embedded JSON use the unchanged strict bounded parser: duplicate
keys, floats, nonfinite numbers and invalid Unicode are rejected. Outer files
are at most 65,536 bytes, with no-follow regular-file reading beneath cwd;
hidden paths, parent traversal and symlinks are refused. Depth 48, 8,192 nodes,
inherited trace bounds and a full 1,048,576-byte report cap apply even in summary
mode. POSIX no-follow directory descriptors are required.

Tried all 17 new tests, acceptance and rejection CLIs, and a detached folder
copy offline. Tests cover changed account with unchanged digest, altered ZTO
amount, equivalent case, transport IDs, invalid wrappers/methods/params, nested
duplicate keys, floats, Unicode/depth/size bounds, cycles input immutability, report limits and CLI rejection/error exits.

```sh
python3 -B -m unittest discover -s line-4/tools/rpc-request-check -v
```

The caller must establish intended-request provenance. A match does not prove
account ownership, authorize signing, recover a signature, establish current
chain state, prove payment or enforce replay protection. The encoder/trace are
shared ancestor code, not independent cryptographic verification. See
`provenance.json` for unchanged source hashes and
[EIP-712](https://eips.ethereum.org/EIPS/eip-712) for the digest format.
