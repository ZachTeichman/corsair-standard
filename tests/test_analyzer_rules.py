from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from corsair.analyzer import analyze_docx

from tests.docx_factory import baseline_resume_paragraphs, make_docx


def _rule_ids(result: dict) -> set[str]:
    return {violation["rule_id"] for violation in result["violations"]}


class AnalyzerRuleTests(unittest.TestCase):
    def test_spelling_guidance_is_review_only_and_does_not_change_score(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            clean_path = make_docx(root / "clean.docx", baseline_resume_paragraphs())
            typo_paragraphs = baseline_resume_paragraphs()
            typo_paragraphs[6] = "Managed stakeholder reporting and recieved teh weekly data."
            typo_path = make_docx(root / "typo.docx", typo_paragraphs)

            clean_result = analyze_docx(clean_path)
            typo_result = analyze_docx(typo_path)
            spelling = [item for item in typo_result["violations"] if item["rule_id"] == "text.spelling_suspected"]

        self.assertTrue(spelling)
        self.assertEqual(spelling[0]["points"], 0)
        self.assertEqual(spelling[0]["category"], "guidance")
        self.assertEqual(typo_result["score"], clean_result["score"])

    def test_section_heading_typo_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paragraphs = baseline_resume_paragraphs()
            paragraphs[4] = "PROFESIONAL EXPERIENCE"
            path = make_docx(Path(temp_dir) / "section-typo.docx", paragraphs)

            result = analyze_docx(path)

        self.assertIn("section.label_spelling", _rule_ids(result))

    def test_invalid_date_range_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paragraphs = baseline_resume_paragraphs()
            paragraphs[5] = "Example Company, Analyst, Athens, GA\tJune 2025 – January 2025"
            path = make_docx(Path(temp_dir) / "bad-date.docx", paragraphs)

            result = analyze_docx(path)

        self.assertIn("entry.date_range_valid", _rule_ids(result))


if __name__ == "__main__":
    unittest.main()
