"""Deterministic tests; do not call any language model."""
import unittest
import json
from types import SimpleNamespace
from agent_mvp import dispatch, verify, EVAL_TASKS, ENHANCED_PROMPT, run_task

class ScriptedClient:
    """A minimal CS329Z-style fake response client, without API/network."""
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls += 1
        if not self.responses:
            raise RuntimeError("Scripted replies exhausted")
        instruction = self.responses.pop(0)
        if isinstance(instruction, str):
            message = SimpleNamespace(content=instruction, tool_calls=None)
        else:
            calls = [SimpleNamespace(id=f"call_{self.calls}_{i}",
                                     function=SimpleNamespace(name=name, arguments=json.dumps(args)))
                     for i, (name, args) in enumerate(instruction)]
            message = SimpleNamespace(content=None, tool_calls=calls)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class AgentMVPTests(unittest.TestCase):
    def test_scripted_agent_search_loop(self):
        client = ScriptedClient([
            [("search_docs", {"query": "refund", "domain": "policy", "top_k": 2})],
            "Refunds are available within 30 days of purchase.",
        ])
        result = run_task(client, "scripted", EVAL_TASKS[0], ENHANCED_PROMPT)
        self.assertTrue(result["passed"], result["failure_reasons"])
        self.assertEqual(result["tool_calls"], 1)
        self.assertEqual(client.calls, 2)
        self.assertEqual(result["events"][2]["type"], "tool")

    def test_scripted_recovery_loop(self):
        client = ScriptedClient([
            [("search_docs", {"query": "refund", "domain": "calendar"})],
            [("search_docs", {"query": "refund", "domain": "policy"})],
            "Refunds are available within 30 days of purchase.",
        ])
        result = run_task(client, "scripted", EVAL_TASKS[0], ENHANCED_PROMPT)
        self.assertTrue(result["passed"], result["failure_reasons"])
        self.assertEqual(result["tool_calls"], 2)
        self.assertEqual(result["successful_tool_calls"], 1)
        self.assertEqual(client.calls, 3)

    def test_hallucinated_answer_fails_without_tool_evidence(self):
        client = ScriptedClient(["Refunds are available within 30 days."])
        result = run_task(client, "scripted", EVAL_TASKS[0], ENHANCED_PROMPT)
        self.assertFalse(result["passed"])
        self.assertIn("missing_verified_document:policy_refund_001", result["failure_reasons"])

    def test_scripted_multiturn_memory(self):
        client = ScriptedClient([
            [("memory_write", {"key": "timezone", "value": "Asia/Shanghai"})],
            "已保存。",
            [("memory_read", {"key": "timezone"})],
            "保存的时区是 Asia/Shanghai。",
        ])
        result = run_task(client, "scripted", EVAL_TASKS[6], ENHANCED_PROMPT)
        self.assertTrue(result["passed"], result["failure_reasons"])
        self.assertEqual(result["tool_calls"], 2)
        self.assertEqual(result["successful_tool_calls"], 2)

    def test_chinese_alias_answer_grounded(self):
        task = EVAL_TASKS[0]
        events = [{"type": "tool", "name": "search_docs", "ok": True,
                   "output": {"results": [{"doc_id": "policy_refund_001", "snippet": "Refunds available within 30 days."}]}}]
        passed, reasons = verify(task, events, "根据公司政策，购买后30天内可以退款。")
        self.assertTrue(passed, reasons)

    def test_search_dispatch_success(self):
        ok, result = dispatch("search_docs", {"query": "refund", "domain": "policy"}, {})
        self.assertTrue(ok)
        self.assertEqual(result["results"][0]["doc_id"], "policy_refund_001")

    def test_reject_wrong_evidence(self):
        task = EVAL_TASKS[0]
        events = [{"type": "tool", "name": "search_docs", "ok": True,
                   "output": {"results": [{"doc_id": "policy_renewal_001", "snippet": "14 days"}]}}]
        passed, reasons = verify(task, events, "Refunds are available within 30 days")
        self.assertFalse(passed)
        self.assertTrue(any("missing_verified_document" in x for x in reasons))

    def test_accept_correct_evidence(self):
        task = EVAL_TASKS[0]
        events = [{"type": "tool", "name": "search_docs", "ok": True,
                   "output": {"results": [{"doc_id": "policy_refund_001", "snippet": "Refunds: 30 days"}]}}]
        passed, reasons = verify(task, events, "Refunds are allowed within 30 days")
        self.assertTrue(passed, reasons)

    def test_no_unsafe_sql_fields(self):
        ok, result = dispatch("sql_customer_db", {"lookup_key": "email", "lookup_value": "ops@acme.test", "fields": ["ssn"]}, {})
        self.assertFalse(ok)
        self.assertEqual(result["error_code"], "forbidden_query")

    def test_read_only_calendar(self):
        ok, result = dispatch("calendar_lookup", {"action": "book_slot", "participant": "account-team", "date": "2026-05-14", "slot": "10:00"}, {})
        self.assertFalse(ok)
        self.assertEqual(result["error_code"], "read_only_calendar")

    def test_session_memory(self):
        state = {}
        ok, _ = dispatch("memory_write", {"key": "timezone", "value": "Asia/Shanghai"}, state)
        self.assertTrue(ok)
        ok, result = dispatch("memory_read", {"key": "timezone"}, state)
        self.assertTrue(ok)
        self.assertEqual(result["value"], "Asia/Shanghai")

    def test_unknown_tool_denied(self):
        ok, result = dispatch("python_exec", {"code": "print(1)"}, {})
        self.assertFalse(ok)
        self.assertEqual(result["error_code"], "unknown_tool")

    def test_refusal(self):
        task = EVAL_TASKS[-1]
        self.assertTrue(verify(task, [], "抱歉，不能提供任何客户密码或 SSN。")[0])
        self.assertFalse(verify(task, [{"type":"tool", "ok": True, "name":"sql_customer_db", "output":{}}], "不能")[0])

if __name__ == "__main__":
    unittest.main()
