"""Selection tests use only synthetic records inside temporary directories."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "etf-comment-drafts-v2" / "scripts" / "select_examples.py"
SPEC = importlib.util.spec_from_file_location("select_examples", SCRIPT)
selector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(selector)


def record(case_id, **overrides):
    row = {"id": case_id, "text": "PRIVATE_TEXT_DO_NOT_EMIT", "style_text": "比较持仓范围，我更关心覆盖哪些行业。",
           "category": "comparison", "language": "zh-CN", "tags": ["持仓", "比较"],
           "preference": "unrated", "split": "reference", "cluster": case_id,
           "source": {"file": "PRIVATE_SOURCE_DO_NOT_EMIT"}, "notes": "PRIVATE_NOTES_DO_NOT_EMIT"}
    row.update(overrides)
    return row


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.library = self.folder / "cases.jsonl"

    def write(self, rows):
        self.library.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")

    def test_excludes_holdout_and_separates_explicit_dislikes(self):
        self.write([record("plain"), record("reserved", split="holdout"), record("avoid", preference="disliked")])
        result = selector.select_examples(self.library)
        self.assertEqual([r["id"] for r in result["examples"]], ["plain"])
        self.assertEqual([r["id"] for r in result["avoid_examples"]], ["avoid"])
        self.assertEqual(result["counts"]["excluded_holdout"], 1)

    def test_cluster_deduplication_and_explicit_preference(self):
        self.write([record("a", cluster="same"), record("b", cluster="same", preference="liked"), record("c")])
        result = selector.select_examples(self.library)
        self.assertEqual([r["id"] for r in result["examples"]], ["b", "c"])

    def test_query_selects_relevant_example_over_unrelated_like(self):
        self.write([record("coverage"), record("liquidity", preference="liked", style_text="买卖差价有点意思。", tags=["流动性"])])
        result = selector.select_examples(self.library, query="持仓范围 行业覆盖", limit=1)
        self.assertEqual(result["examples"][0]["id"], "coverage")

    def test_any_lexical_match_precedes_unrelated_liked_example(self):
        self.write([record("matched", tags=["alpha"]), record("unrelated", preference="liked", tags=[])])
        result = selector.select_examples(self.library, query="alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu", limit=1)
        self.assertEqual(result["examples"][0]["id"], "matched")

    def test_missing_style_text_never_falls_back_to_raw_text(self):
        missing = record("missing")
        missing.pop("style_text")
        self.write([missing, record("present")])
        result = selector.select_examples(self.library)
        serialized = json.dumps(result)
        self.assertEqual(result["counts"]["skipped_without_style_text"], 1)
        for secret in ("PRIVATE_TEXT_DO_NOT_EMIT", "PRIVATE_SOURCE_DO_NOT_EMIT", "PRIVATE_NOTES_DO_NOT_EMIT", str(self.library)):
            self.assertNotIn(secret, serialized)
        self.assertNotIn("text", result["examples"][0])

    def test_category_and_language_filters(self):
        self.write([record("mandarin"), record("cantonese", category="question", language="zh-HK", style_text="覆盖边啲行业？")])
        result = selector.select_examples(self.library, category="question", language="粤语")
        self.assertEqual([r["id"] for r in result["examples"]], ["cantonese"])

    def test_default_path_uses_configuration(self):
        with patch.dict(os.environ, {"ETF_COMMENT_LIBRARY": str(self.library), "CODEX_HOME": str(self.folder)}, clear=True):
            self.assertEqual(selector.default_library(), self.library)
        with patch.dict(os.environ, {"CODEX_HOME": str(self.folder)}, clear=True):
            self.assertEqual(selector.default_library(), self.folder / "private" / "etf-comment-drafts-v2" / "cases.jsonl")
        with patch.dict(os.environ, {}, clear=True), patch.object(Path, "home", return_value=self.folder):
            self.assertEqual(selector.default_library(), self.folder / ".codex" / "private" / "etf-comment-drafts-v2" / "cases.jsonl")

    def test_missing_library_is_normal_fallback(self):
        result = selector.select_examples(self.library)
        self.assertFalse(result["available"])
        self.assertEqual(result["examples"], [])

    def test_profile_preferences_are_returned_but_feedback_is_not_inferred(self):
        self.write([record("plain")])
        (self.folder / "profile.json").write_text(json.dumps({"style_preferences": ["短句", "短句"], "feedback": [{"note": "PRIVATE_FREEFORM_FEEDBACK"}]}))
        result = selector.select_examples(self.library)
        self.assertEqual(result["style_preferences"], ["短句"])
        self.assertEqual(result["examples"][0]["preference"], "unrated")
        self.assertNotIn("PRIVATE_FREEFORM_FEEDBACK", json.dumps(result))

    def test_malformed_record_error_is_safe_and_actionable(self):
        self.write([record("one"), record("two", category="RAW_SECRET_WRONG_CATEGORY")])
        with self.assertRaises(selector.LibraryError) as error:
            selector.select_examples(self.library)
        self.assertIn("第 2 行", str(error.exception))
        self.assertNotIn("RAW_SECRET", str(error.exception))
        self.assertNotIn(str(self.library), str(error.exception))

    def test_bad_json_and_duplicate_id_are_rejected(self):
        self.library.write_text('{"RAW_SECRET":', encoding="utf-8")
        with self.assertRaises(selector.LibraryError):
            selector.select_examples(self.library)
        self.write([record("same"), record("same")])
        with self.assertRaises(selector.LibraryError):
            selector.select_examples(self.library)

    def test_invalid_limit_is_rejected(self):
        for limit in (0, 13, True, 1.5):
            with self.subTest(limit=limit), self.assertRaises(selector.LibraryError):
                selector.select_examples(self.library, limit=limit)

    def test_cli_missing_library_returns_json_and_success(self):
        stdout = io.StringIO()
        with patch("sys.argv", ["select_examples.py", "--library", str(self.library)]), contextlib.redirect_stdout(stdout):
            self.assertEqual(selector.main(), 0)
        self.assertFalse(json.loads(stdout.getvalue())["available"])


if __name__ == "__main__":
    unittest.main()
