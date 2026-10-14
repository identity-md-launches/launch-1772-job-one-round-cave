"""Offline tests; mutated observations are rejection fixtures, never chain claims."""
import copy
import hashlib
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import unittest
from unittest.mock import patch

import recheck as r


def samples():
    baseline = r.w.load_workspace_json("line-3/tools/payment-witness/live-evidence.json")
    current = r.w.load_workspace_json("line-3/tools/payment-recheck/current-evidence.json")
    return baseline, current


def fixture_hash(label):
    return "0x" + hashlib.sha256(("test fixture only: " + label).encode()).hexdigest()


class MutatedRPC:
    """Small deterministic provider built from real observations, then mutated."""
    def __init__(self, mode):
        baseline, current = samples()
        self.mode = mode
        self.policy = current["policy"]
        reads = current["reads"]
        self.receipt = copy.deepcopy(next(x["result"] for x in reads if x["method"] == "eth_getTransactionReceipt"))
        self.head = copy.deepcopy(next(x["result"] for x in reads if x["params"] == ["latest", False]))
        self.final = copy.deepcopy(next(x["result"] for x in reads if x["params"] == ["finalized", False]))
        self.blocks = {x["result"]["number"]: copy.deepcopy(x["result"]) for x in reads
                       if x["method"] == "eth_getBlockByNumber"}
        old = r.checkpoint(baseline)[1]
        if mode == "reinclude":
            self.receipt["blockHash"] = fixture_hash("reorganized inclusion")
            for event in self.receipt["logs"]:
                event["blockHash"] = self.receipt["blockHash"]
            self.blocks[self.receipt["blockNumber"]]["hash"] = self.receipt["blockHash"]
        if mode in ("events", "shortfall", "event_order"):
            event = next(x for x in self.receipt["logs"] if x["address"].lower() == r.w.TOKENS["ZTO"])
            if mode == "events": event["topics"][1] = "0x" + "0" * 24 + fixture_hash("other sender")[-40:]
            if mode == "shortfall": event["data"] = "0x" + format(int(event["data"], 16)-1, "064x")
            if mode == "event_order": self.receipt["logs"].reverse()
        if mode == "revert": self.receipt["status"] = "0x0"
        if mode == "finality_loss":
            self.final = {"number": hex(int(self.receipt["blockNumber"],16)-1), "hash": fixture_hash("older final")}
        if mode == "finality_regression":
            self.final = {"number": hex(old["finalizedHead"]["number"]-1), "hash": fixture_hash("regressed final")}
        if mode == "finality_hash":
            self.final = {"number": hex(old["finalizedHead"]["number"]), "hash": fixture_hash("conflicting final")}
        if mode in ("head_regression", "head_hash"):
            self.head = {"number": hex(old["head"]["number"]-(mode == "head_regression")),
                         "hash": fixture_hash(mode)}
            self.final = {"number": hex(old["finalizedHead"]["number"]), "hash": old["finalizedHead"]["hash"]}
        self.blocks[self.head["number"]] = self.head
        self.blocks[self.final["number"]] = self.final

    def call(self, method, params):
        if self.mode == "failure": raise r.s.ReadFailure(method, "transport", "fixture")
        if method == "eth_chainId": return "0x1"
        if method == "eth_getTransactionReceipt":
            return None if self.mode == "missing" else copy.deepcopy(self.receipt)
        if method == "eth_getBlockByNumber":
            tag = params[0]
            if tag == "latest": return copy.deepcopy(self.head)
            if tag == "finalized": return copy.deepcopy(self.final)
            block = copy.deepcopy(self.blocks[tag])
            if self.mode == "unstable" and tag == self.receipt["blockNumber"]:
                block["hash"] = fixture_hash("orphan")
            return block
        raise AssertionError(method)


class RecheckTests(unittest.TestCase):
    def mutated(self, mode, baseline=None):
        baseline = baseline or samples()[0]
        return r.collect(baseline, rpc_factory=lambda source: MutatedRPC(mode))

    def test_real_observations_advance_without_changing_payment(self):
        baseline, current = samples()
        untouched = copy.deepcopy((baseline, current))
        result = r.compare(baseline, current)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["state"], "continued")
        self.assertGreater(result["current"]["confirmations"], result["baseline"]["confirmations"])
        self.assertEqual((baseline, current), untouched)

    def test_same_observation_does_not_count_as_recheck(self):
        baseline, _ = samples()
        result = r.compare(baseline, baseline)
        self.assertEqual(result["state"], "no_new_head")
        self.assertEqual(result["alerts"], ["head_unchanged"])
        self.assertEqual(r.exit_code(result), 1)

    def test_reincluded_payment_needs_review_even_when_policy_passes(self):
        result = self.mutated("reinclude")
        self.assertTrue(result["current"]["accepted"])
        self.assertFalse(result["accepted"])
        self.assertIn("inclusion_changed", result["alerts"])

    def test_same_amount_changed_sender_needs_review(self):
        result = self.mutated("events")
        self.assertTrue(result["current"]["accepted"])
        self.assertIn("payment_events_changed", result["alerts"])
        self.assertFalse(result["accepted"])

    def test_missing_receipt_revokes_reliance(self):
        result = self.mutated("missing")
        self.assertIn("receipt_missing", result["alerts"])
        self.assertIn("payment_policy_not_met", result["alerts"])
        self.assertFalse(result["accepted"])

    def test_revert_and_unstable_chain(self):
        for mode, alert in (("revert", "execution_changed"), ("unstable", "canonicality_unstable")):
            result = self.mutated(mode)
            self.assertIn(alert, result["alerts"])
            self.assertFalse(result["accepted"])

    def test_finality_loss_and_anchor_regressions(self):
        for mode, alert in (("finality_loss", "finality_not_reestablished"),
                            ("finality_regression", "finalized_head_regressed"),
                            ("finality_hash", "finalized_head_hash_changed")):
            result = self.mutated(mode)
            self.assertIn(alert, result["alerts"])
            self.assertFalse(result["accepted"])

    def test_head_regressions(self):
        for mode, alert in (("head_regression", "head_regressed"), ("head_hash", "head_hash_changed")):
            result = self.mutated(mode)
            self.assertIn(alert, result["alerts"])
            self.assertFalse(result["accepted"])

    def test_shortfall_rejects_and_event_order_is_normalized(self):
        result = self.mutated("shortfall")
        self.assertIn("payment_policy_not_met", result["alerts"])
        self.assertFalse(result["accepted"])
        self.assertTrue(self.mutated("event_order")["accepted"])

    def test_policy_changes_refused(self):
        for key, value in (("minimum_raw", "1"), ("confirmations", 1), ("finalized", False),
                           ("recipient", "0x" + fixture_hash("recipient")[-40:]), ("token", "IMD")):
            baseline, current = samples()
            current["policy"][key] = value
            with self.subTest(key=key), self.assertRaises(r.w.Error): r.compare(baseline, current)

    def test_invalid_or_unaccepted_baseline_never_constructs_transport(self):
        for change in ("shortfall", "boolean_version", "extra_flag", "bad_policy"):
            baseline, _ = samples()
            if change == "shortfall": baseline["policy"]["minimum_raw"] = str(int(baseline["policy"]["minimum_raw"])+1)
            if change == "boolean_version": baseline["version"] = True
            if change == "extra_flag": baseline["accepted"] = True
            if change == "bad_policy": baseline["policy"]["confirmations"] = True
            with self.subTest(change=change), self.assertRaises(r.w.Error):
                r.collect(baseline, rpc_factory=lambda source:self.fail("unexpected network"))

    def test_failed_provider_has_no_sample_or_fallback(self):
        result = self.mutated("failure")
        self.assertEqual(result["state"], "provider_error")
        self.assertEqual(r.exit_code(result), 2)
        self.assertNotIn("currentSample", result)

    def test_exact_transcript_requests_and_consumption(self):
        for mode in ("extra_read", "missing_read", "reordered", "extra_key", "bool_equivalence"):
            baseline, current = samples()
            reads = current["reads"]
            if mode == "extra_read": reads.append(copy.deepcopy(reads[-1]))
            if mode == "missing_read": reads.pop()
            if mode == "reordered": reads.reverse()
            if mode == "extra_key": reads[0]["accepted"] = True
            if mode == "bool_equivalence": next(x for x in reads if x["method"] == "eth_getBlockByNumber")["params"][1] = 0
            with self.subTest(mode=mode), self.assertRaises(r.w.Error): r.compare(baseline, current)

    def test_live_sample_replays_to_same_decision(self):
        for mode in ("normal", "missing", "reinclude", "shortfall"):
            result = self.mutated(mode)
            replay = r.compare(samples()[0], result["currentSample"])
            for key in ("accepted", "alerts", "state", "currentSha256"):
                self.assertEqual(result[key], replay[key])

    def test_cli_demo_and_rejections(self):
        output = io.StringIO()
        with redirect_stdout(output): self.assertEqual(r.main(["--demo"]), 0)
        self.assertTrue(json.loads(output.getvalue())["accepted"])
        for args in (["--demo", "--baseline", "anything"], ["--live"],
                     ["--demo", "--rpc", r.s.RPC_URL],
                     ["--current", "anything", "--baseline", "../outside.json"]):
            with self.subTest(args=args), redirect_stdout(io.StringIO()):
                self.assertEqual(r.main(args), 2)

    def test_file_reader_and_transport_do_not_discover_environment(self):
        with patch.object(r.s.urllib.request, "getproxies", side_effect=AssertionError("environment")):
            r.s.RPC(r.s.RPC_URL)
            r.w.load_workspace_json("line-3/tools/payment-recheck/current-evidence.json")


if __name__ == "__main__":
    unittest.main()
