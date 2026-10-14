#!/usr/bin/env python3
"""Recheck an accepted Ethereum payment checkpoint using read-only evidence."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

_spec = importlib.util.spec_from_file_location(
    "recheck_agreement", Path(__file__).resolve().parent.parent / "provider-agreement" / "agreement.py")
a = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(a)
w, s = a.w, a.s
LIMITATION = ("Provider observations, not a consensus or receipt proof. Advancing block "
              "height does not prove wall-clock freshness. Offline replay is historical.")


class ExactReplay(w.Replay):
    def call(self, method, params):
        if self.index < len(self.reads):
            saved = self.reads[self.index]
            # Python equality equates False with 0; RPC request JSON does not.
            if json.dumps(saved["params"], sort_keys=True, allow_nan=False) != json.dumps(params, sort_keys=True):
                raise w.Error("replay request type or value mismatch")
        return super().call(method, params)


def replay(sample):
    """Recompute one witness transcript; never trust a saved acceptance flag."""
    if not isinstance(sample, dict) or set(sample) != {"version", "policy", "reads"}:
        raise w.Error("expected exactly version, policy and reads")
    if type(sample["version"]) is not int or sample["version"] != 1:
        raise w.Error("unsupported checkpoint version")
    policy = a.validate_policy(sample["policy"])
    reads = sample["reads"]
    if not isinstance(reads, list) or any(
            not isinstance(item, dict) or set(item) != {"method", "params", "result"}
            for item in reads):
        raise w.Error("invalid transcript entries")
    rpc = ExactReplay(reads)
    report = w.verify(rpc, **policy)
    if rpc.index != len(reads):
        raise w.Error("unused checkpoint reads")
    return policy, report


def checkpoint(sample):
    policy, report = replay(sample)
    if report.get("accepted") is not True:
        raise w.Error("baseline must be an accepted payment checkpoint")
    return policy, report


def digest(sample):
    return hashlib.sha256(json.dumps(sample, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def summary(report):
    keys = ("accepted", "state", "head", "inclusion", "execution", "confirmations",
            "finalized", "finalizedHead", "paymentState", "transferEvidence")
    return {key: report[key] for key in keys if key in report}


def compare(baseline, current):
    policy, before = checkpoint(baseline)
    new_policy, after = replay(current)
    if policy != new_policy:
        raise w.Error("current evidence must use the exact baseline policy")
    alerts = []
    old_head, head = before["head"], after["head"]
    if head["number"] < old_head["number"]:
        alerts.append("head_regressed")
    elif head["number"] == old_head["number"]:
        alerts.append("head_unchanged" if head["hash"] == old_head["hash"] else "head_hash_changed")
    if after.get("state") == "not_included":
        alerts.append("receipt_missing")
    elif before["inclusion"] != after.get("inclusion"):
        alerts.append("inclusion_changed")
    if after.get("state") == "unstable":
        alerts.append("canonicality_unstable")
    if after.get("execution") is not None and before["execution"] != after["execution"]:
        alerts.append("execution_changed")
    if before.get("finalized") is True and after.get("finalized") is not True:
        alerts.append("finality_not_reestablished")
    old_final, final = before.get("finalizedHead"), after.get("finalizedHead")
    if old_final is not None and final is not None:
        if final["number"] < old_final["number"]:
            alerts.append("finalized_head_regressed")
        elif final["number"] == old_final["number"] and final["hash"] != old_final["hash"]:
            alerts.append("finalized_head_hash_changed")
    # Compare the full event set, not only a net amount. Missing evidence is
    # handled by policy_not_met, not falsely labelled a changed event set.
    if "transferEvidence" in after:
        old_events = a.fingerprint(before)["transferEvidence"]
        new_events = a.fingerprint(after)["transferEvidence"]
        if old_events != new_events:
            alerts.append("payment_events_changed")
    if after.get("accepted") is not True:
        alerts.append("payment_policy_not_met")
    accepted = not alerts
    state = ("continued" if accepted else "no_new_head" if alerts == ["head_unchanged"]
             else "review_required")
    return {"accepted": accepted, "state": state, "alerts": alerts,
            "policy": policy, "baseline": summary(before), "current": summary(after),
            "baselineSha256": digest(baseline), "currentSha256": digest(current),
            "evidenceMode": "offline historical comparison", "evidenceLimit": LIMITATION}


def collect(baseline, source=s.RPC_URL, rpc_factory=s.RPC):
    policy, before = checkpoint(baseline)  # Validate before constructing a transport.
    if source not in a.PROVIDERS:
        raise w.Error("choose a documented public Ethereum source")
    try:
        recorder = w.Recorder(rpc_factory(source))
        w.verify(recorder, **policy)
        current = {"version": 1, "policy": policy, "reads": recorder.reads}
        # Recompute captured evidence as well: a complete saved transcript is
        # necessary for a repeatable comparison. Errors never become acceptance.
        result = compare(baseline, current)
    except (w.Error, ValueError, TypeError, KeyError, OSError, RecursionError):
        return {"accepted": False, "state": "provider_error", "alerts": ["unverifiable_observation"],
                "policy": policy, "baseline": summary(before), "source": source,
                "evidenceMode": "live read failed", "evidenceLimit": LIMITATION}
    result.update(source=source, evidenceMode="live read-only recheck", currentSample=current)
    return result


def exit_code(report):
    return 0 if report["accepted"] else 2 if report["state"] in ("input_error", "provider_error") else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--demo", action="store_true", help="compare two saved real ZTO observations offline")
    mode.add_argument("--current", help="workspace-relative current witness transcript")
    mode.add_argument("--live", action="store_true", help="collect a fresh single-provider observation")
    parser.add_argument("--baseline", help="workspace-relative accepted witness transcript")
    parser.add_argument("--rpc", choices=a.PROVIDERS, default=None)
    args = parser.parse_args(argv)
    try:
        if args.demo:
            if args.baseline is not None or args.rpc is not None:
                raise w.Error("demo refuses overrides")
            folder = Path(__file__).resolve().parent.relative_to(Path.cwd())
            baseline = w.load_workspace_json(folder.parent / "payment-witness" / "live-evidence.json")
            current = w.load_workspace_json(folder / "current-evidence.json")
            result = compare(baseline, current)
            result["demoNote"] = "Real historical ZTO observations; recipient/amount were observed, not an independent invoice."
        else:
            if args.baseline is None or (args.rpc is not None and not args.live):
                raise w.Error("supply baseline; --rpc applies only to live mode")
            baseline = w.load_workspace_json(args.baseline)
            if args.live:
                result = collect(baseline, args.rpc or s.RPC_URL)
            else:
                result = compare(baseline, w.load_workspace_json(args.current))
        print(json.dumps(result, indent=2, allow_nan=False))
        return exit_code(result)
    except (w.Error, ValueError, TypeError, KeyError, OSError, RecursionError):
        print(json.dumps({"accepted": False, "state": "input_error",
                          "reason": "Invalid or unaccepted checkpoint, mismatched policy, or malformed evidence"}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
