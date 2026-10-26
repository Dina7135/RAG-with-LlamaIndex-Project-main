import os
import tempfile
import unittest

from data_extraction import StructuredDataExtractor


class StructuredDataExtractorTests(unittest.TestCase):
    def test_extracts_decisions_rules_and_warnings_from_markdown(self):
        extractor = StructuredDataExtractor()

        with tempfile.TemporaryDirectory() as tmpdir:
            decision_md = os.path.join(tmpdir, "decisions.md")
            with open(decision_md, "w", encoding="utf-8") as handle:
                handle.write("""# החלטות\n\n- נבחר Postgres עבור נתונים רלציוניים\n- הוספה של API rate limiting\n""")

            rules_md = os.path.join(tmpdir, "rules.md")
            with open(rules_md, "w", encoding="utf-8") as handle:
                handle.write("""# כללים\n\n- כל מסך בעברית חייב RTL\n- קוד API לא צריך להיות חשוף בלקוח\n""")

            warnings_md = os.path.join(tmpdir, "warnings.md")
            with open(warnings_md, "w", encoding="utf-8") as handle:
                handle.write("""# אזהרות\n\n- לא לשנות את ה-hook של JWT בלי בדיקה\n- שים לב לנתיבים רגישים\n""")

            structured = extractor.extract_from_directory(tmpdir)

        self.assertEqual(structured["schema_version"], "1.0")
        self.assertIn("generated_at", structured)
        self.assertEqual(len(structured["sources"]), 3)
        self.assertGreaterEqual(len(structured["items"]["decisions"]), 2)
        self.assertGreaterEqual(len(structured["items"]["rules"]), 2)
        self.assertGreaterEqual(len(structured["items"]["warnings"]), 0)

        decision_texts = [item["summary"] for item in structured["items"]["decisions"]]
        self.assertTrue(any("postgres" in text.lower() for text in decision_texts))

        rule_texts = [item["rule"] for item in structured["items"]["rules"]]
        self.assertTrue(any("rtl" in text.lower() for text in rule_texts))


if __name__ == "__main__":
    unittest.main()
