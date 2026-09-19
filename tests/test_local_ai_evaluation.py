"""Offline checks for the evaluation harness, not for model quality."""

import unittest
from unittest.mock import patch

from scripts.evaluate_local_ai import evaluate_case


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        """Prepare an evaluation case with a missing negation for each test."""
        self.case = {
            "id": "negation",
            "transcript": "We do not deploy on Friday.",
            "answer": "We do deploy on Friday.",
            "expected_pairs": [["not", ""]],
            "review_note": "Missing negation reverses the meaning.",
        }

    @patch("scripts.evaluate_local_ai.api")
    def test_blank_answer_never_calls_model(self, api):
        """Reject empty answers locally without sending a model request."""
        for answer in ("", " \n\t "):
            result = evaluate_case({**self.case, "answer": answer}, "test-model", 1)
            self.assertEqual(result["status"], "rejected_empty")
            self.assertFalse(result["request_sent"])
        api.assert_not_called()

    @patch("scripts.evaluate_local_ai.api")
    def test_expected_answers_are_not_sent_to_model(self, api):
        """Keep expected results and review notes out of the model prompt."""
        api.return_value = {
            "done": True,
            "done_reason": "stop",
            "message": {
                "content": '{"summary_ru":"Пропущено отрицание.","issues":['
                '{"expected":"not","heard":"","explanation_ru":"Смысл изменился на противоположный."}]'
                "}"
            },
        }
        result = evaluate_case(self.case, "test-model", 1)
        self.assertTrue(result["pairs_match"])
        request = api.call_args.args[1]
        self.assertNotIn("expected_pairs", request["messages"][1]["content"])
        self.assertNotIn(self.case["review_note"], request["messages"][1]["content"])
        self.assertFalse(request["think"])

    @patch("scripts.evaluate_local_ai.api")
    def test_truncated_response_is_not_accepted(self, api):
        """Record an error when the model stops before completing its response."""
        api.return_value = {
            "done": True,
            "done_reason": "length",
            "message": {"content": '{"summary_ru":"Всё верно.","issues":[]}'},
        }
        result = evaluate_case(self.case, "test-model", 1)
        self.assertEqual(result["status"], "error")
        self.assertIn("truncated", result["error"])

    @patch("scripts.evaluate_local_ai.api")
    def test_invalid_contract_is_not_accepted(self, api):
        """Reject feedback whose fields violate the expected response contract."""
        api.return_value = {
            "done": True,
            "done_reason": "stop",
            "message": {"content": '{"summary_ru":"Всё верно.","issues":"none"}'},
        }
        result = evaluate_case(self.case, "test-model", 1)
        self.assertEqual(result["status"], "error")

    @patch("scripts.evaluate_local_ai.api")
    def test_correct_json_can_still_miss_a_real_error(self, api):
        """Distinguish valid response structure from correct error detection."""
        api.return_value = {
            "done": True,
            "done_reason": "stop",
            "message": {"content": '{"summary_ru":"Всё верно.","issues":[]}'},
        }
        result = evaluate_case(self.case, "test-model", 1)
        self.assertEqual(result["status"], "valid")
        self.assertFalse(result["pairs_match"])

    @patch("scripts.evaluate_local_ai.api", side_effect=TimeoutError("Timed out"))
    def test_timeout_is_recorded_without_automatic_retry(self, api):
        """Record a timed-out request once without retrying the model call."""
        result = evaluate_case(self.case, "test-model", 1)
        self.assertEqual(result["status"], "error")
        self.assertIn("elapsed_seconds", result)
        api.assert_called_once()


if __name__ == "__main__":
    unittest.main()
