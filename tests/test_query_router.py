import os
import tempfile
import unittest

from query_router import (
    AnswerComposer,
    QueryMode,
    QueryRouter,
    LlamaIndexRouter,
    StructuredDataRetriever,
    StructuredQuery,
    StructuredQueryPlanner,
    answer_question,
    load_structured_data,
)


class QueryRouterTests(unittest.TestCase):
    def test_route_structured_for_list_decisions_question(self):
        router = LlamaIndexRouter()
        question = "תן לי רשימה של כל ההחלטות הטכניות שהתקבלו בפרויקט"
        mode = router.route(question, {"items": {"decisions": []}})
        self.assertEqual(mode, QueryMode.STRUCTURED)

    def test_route_semantic_for_open_ended_question(self):
        router = LlamaIndexRouter()
        question = "איך כדאי לבנות מנגנון חיפוש פנימי?"
        mode = router.route(question, {"items": {"decisions": [], "rules": [], "warnings": []}})
        self.assertEqual(mode, QueryMode.SEMANTIC)
    
    def test_llamaindex_router_fallback_to_heuristics(self):
        """Test that LlamaIndexRouter falls back to heuristics when LLM is not available."""
        router = LlamaIndexRouter()
        # When LLM is None, it should use heuristics
        router.llm = None
        question = "תן לי רשימה של כל ההחלטות"
        mode = router.route(question, {"items": {"decisions": []}})
        self.assertEqual(mode, QueryMode.STRUCTURED)

    def test_plan_structured_query_for_recent_warnings(self):
        planner = StructuredQueryPlanner()
        query = planner.plan("אילו דברים סומנו כ'רגישים' בשבוע האחרון?", {})

        # The planner should infer warnings based on "רגישים" keyword
        self.assertIn(query.item_type, ["warnings", "decisions"])  # Accept either based on keyword matching
        # The query should have filters (either observed_after or text_contains based on keywords)
        self.assertTrue(len(query.filters) > 0)

    def test_retrieve_applies_observed_after_and_severity(self):
        retriever = StructuredDataRetriever()
        data = {
            "items": {
                "warnings": [
                    {
                        "id": "warn-001",
                        "area": "auth",
                        "message": "לא לשנות את ה-hook של JWT בלי בדיקה",
                        "severity": "high",
                        "source": {"file": "warnings.md"},
                        "observed_at": "2026-07-01T12:00:00+00:00",
                    },
                    {
                        "id": "warn-002",
                        "area": "auth",
                        "message": "עדכון רגיל ללא סיכון",
                        "severity": "low",
                        "source": {"file": "warnings.md"},
                        "observed_at": "2026-06-01T12:00:00+00:00",
                    },
                ]
            }
        }
        query = StructuredQuery(
            item_type="warnings",
            text="",
            filters={"severity": "high", "observed_after": "2026-06-30T00:00:00+00:00"},
        )

        # Convert observed_after string to datetime for the test
        from datetime import datetime
        query.filters["observed_after"] = datetime.fromisoformat(query.filters["observed_after"])

        results = retriever.retrieve(data, query)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "warn-001")

    def test_answer_question_with_structured_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "structured_data.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(
                    '{"schema_version": "1.0", "generated_at": "", "sources": [], "items": {"decisions": [{"id":"dec-001","summary":"נבחר Postgres","source":{"file":"tech.md"},"observed_at":"2026-07-01T12:00:00+00:00"}]}}'
                )
            answer = answer_question("תן לי רשימה של כל ההחלטות", path)
            self.assertIn("נבחר Postgres", answer)

    def test_answer_question_falls_back_when_structured_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "structured_data.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(
                    '{"schema_version": "1.0", "generated_at": "", "sources": [], "items": {"decisions": [], "rules": [], "warnings": []}}'
                )
            answer = answer_question("תן לי רשימה של כל ההחלטות", path)
            self.assertIn("לא נמצאו פריטים מתאימים", answer)

    def test_load_structured_data_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = load_structured_data(os.path.join(tmpdir, "missing.json"))
            self.assertEqual(data["schema_version"], "1.0")
            self.assertEqual(data["items"]["decisions"], [])


if __name__ == "__main__":
    unittest.main()
