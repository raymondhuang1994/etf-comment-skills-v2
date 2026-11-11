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

    def test_approved_original_is_available_without_style_text_or_preference_inference(self):
        approved = record("approved", approval="approved", text="哦，这张说明图终于看明白了。",
                          platform="平台甲", speech_act="reaction")
        approved.pop("style_text")
        self.write([approved])
        example = selector.select_examples(self.library)["examples"][0]
        self.assertEqual(example["reference_text"], approved["text"])
        self.assertEqual(example["approval"], "approved")
        self.assertEqual(example["preference"], "unrated")
        self.assertEqual(example["platform"], "平台甲")
        self.assertNotIn("style_text", example)

    def test_unreviewed_context_media_and_raw_text_stay_private(self):
        self.write([record("legacy", context={"preceding_text": "PRIVATE_PRECEDING_TEXT"},
                           media=[{"path": "/private/synthetic.png", "description": "PRIVATE_MEDIA_NOTE"}],
                           platform="PRIVATE_PLATFORM", speech_act="PRIVATE_SPEECH_ACT")])
        example = selector.select_examples(self.library, include_media=True)["examples"][0]
        self.assertIn("style_text", example)
        for key in ("reference_text", "context", "media", "platform", "speech_act", "source_location"):
            self.assertNotIn(key, example)
        self.assertNotIn("PRIVATE_", json.dumps(example))

    def test_approved_context_is_preserved_without_inventing_prior_comments(self):
        context = {"discussion_area": "虚构行业区", "link_target": "ETF-A", "context_status": "not_read",
                   "requirements": "配产品卡", "own_products": ["ETF-A", "ETF-B"],
                   "unknown_field": "PRIVATE_UNKNOWN_CONTEXT"}
        self.write([record("approved", approval="approved", context=context,
                           source={"sheet": "合成表", "row": 7, "file": "PRIVATE_WORKBOOK", "url": "PRIVATE_URL"})])
        example = selector.select_examples(self.library)["examples"][0]
        self.assertEqual(example["context"]["context_status"], "not_read")
        self.assertEqual(example["context"]["own_products"], ["ETF-A", "ETF-B"])
        self.assertNotIn("preceding_text", example["context"])
        self.assertNotIn("unknown_field", example["context"])
        self.assertEqual(example["source_location"], {"sheet": "合成表", "row": 7})
        self.assertNotIn("source", example)
        for private in ("PRIVATE_WORKBOOK", "PRIVATE_URL", "PRIVATE_UNKNOWN_CONTEXT"):
            self.assertNotIn(private, json.dumps(example))

    def test_media_paths_are_opt_in_and_verification_state_is_not_upgraded(self):
        media = [{"kind": "unreviewed_image", "path": "/private/synthetic.png", "cell": "H7",
                  "description": "尚未检查的示例图", "verified": False, "raw_private": "PRIVATE_UNUSED"}]
        self.write([record("approved", approval="approved", media=media)])
        default = selector.select_examples(self.library)["examples"][0]["media"][0]
        requested = selector.select_examples(self.library, include_media=True)["examples"][0]["media"][0]
        self.assertNotIn("path", default)
        self.assertEqual(requested["path"], "/private/synthetic.png")
        self.assertFalse(default["verified"])
        self.assertFalse(requested["verified"])
        self.assertNotIn("raw_private", requested)

    def test_content_type_separates_articles_and_skips_textless_assets(self):
        self.write([record("short", approval="approved", text="图例看懂了。"),
                    record("article", approval="approved", content_type="article", text="这是完整的合成文章。"),
                    record("asset", approval="approved", content_type="asset_only", text="", style_text="")])
        default = selector.select_examples(self.library)
        self.assertEqual([r["id"] for r in default["examples"]], ["short"])
        articles = selector.select_examples(self.library, content_type="article")
        self.assertEqual([r["id"] for r in articles["examples"]], ["article"])
        all_text = selector.select_examples(self.library, content_type="all")
        self.assertEqual({r["id"] for r in all_text["examples"]}, {"article", "short"})
        self.assertEqual(all_text["counts"]["skipped_without_reference_text"], 1)

    def test_approved_holdout_stays_excluded_even_when_all_types_requested(self):
        self.write([record("reserved", approval="approved", split="holdout", content_type="article"),
                    record("plain")])
        result = selector.select_examples(self.library, content_type="all", include_media=True)
        self.assertEqual([r["id"] for r in result["examples"]], ["plain"])
        self.assertEqual(result["counts"]["excluded_holdout"], 1)

    def test_reference_in_holdout_cluster_is_excluded_from_both_example_lists(self):
        self.write([record("reserved", approval="approved", split="holdout", cluster="reserved-shape"),
                    record("same-shape", approval="approved", cluster="reserved-shape", preference="liked"),
                    record("avoid-same-shape", cluster="reserved-shape", preference="disliked"),
                    record("separate")])
        result = selector.select_examples(self.library, content_type="all", include_media=True)
        self.assertEqual([r["id"] for r in result["examples"]], ["separate"])
        self.assertEqual(result["avoid_examples"], [])
        self.assertEqual(result["counts"]["excluded_holdout"], 1)
        self.assertEqual(result["counts"]["excluded_holdout_cluster"], 2)

    def test_context_can_match_query_without_copying_it_into_reference_text(self):
        self.write([record("a-unrelated", approval="approved", text="哦。", tags=[], context={}),
                    record("b-context", approval="approved", text="原来如此。", tags=[],
                           context={"discussion_area": "imaginarytopic"})])
        example = selector.select_examples(self.library, query="imaginarytopic", limit=1)["examples"][0]
        self.assertEqual(example["id"], "b-context")
        self.assertEqual(example["reference_text"], "原来如此。")

    def test_platform_and_speech_act_prefer_matches_without_filtering_pool(self):
        self.write([record("a-other", approval="approved", platform="平台乙", speech_act="reaction"),
                    record("z-preferred", approval="approved", platform="平台甲", speech_act="question")])
        examples = selector.select_examples(self.library, platform="平台甲", speech_act="question")["examples"]
        self.assertEqual([r["id"] for r in examples], ["z-preferred", "a-other"])
        fallback = selector.select_examples(self.library, platform="没有该平台", speech_act="new-action")
        self.assertEqual(len(fallback["examples"]), 2)

    def test_relevant_unreviewed_reference_precedes_unrelated_approved_preferences(self):
        self.write([record("matched", style_text="specialterm", tags=[]),
                    record("preferred", approval="approved", text="别的话题", tags=[],
                           preference="liked", platform="平台甲", speech_act="question")])
        example = selector.select_examples(self.library, query="specialterm", platform="平台甲",
                                           speech_act="question", limit=1)["examples"][0]
        self.assertEqual(example["id"], "matched")

    def test_matching_approved_reference_is_preferred_without_becoming_liked(self):
        self.write([record("a-unreviewed", style_text="same-query", tags=[]),
                    record("z-approved", approval="approved", text="same-query", tags=[])])
        example = selector.select_examples(self.library, query="same-query", limit=1)["examples"][0]
        self.assertEqual(example["id"], "z-approved")
        self.assertEqual(example["preference"], "unrated")

    def test_invalid_optional_field_errors_do_not_disclose_private_values(self):
        variants = [{"approval": "PRIVATE_APPROVAL"}, {"content_type": "PRIVATE_KIND"},
                    {"context": {"preceding_text": {"PRIVATE_CONTEXT": "secret"}}},
                    {"context": {"own_products": "PRIVATE_PRODUCTS"}},
                    {"media": [{"verified": "PRIVATE_VERIFICATION"}]}, {"media": "PRIVATE_MEDIA"}]
        for fields in variants:
            with self.subTest(fields=fields):
                self.write([record("one", **fields)])
                with self.assertRaises(selector.LibraryError) as error:
                    selector.select_examples(self.library)
                self.assertIn("第 1 行", str(error.exception))
                self.assertNotIn("PRIVATE_", str(error.exception))

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

    def test_cli_accepts_context_selection_and_media_options(self):
        self.write([record("article", approval="approved", content_type="article",
                           media=[{"path": "/private/synthetic.png"}])])
        stdout = io.StringIO()
        arguments = ["select_examples.py", "--library", str(self.library), "--content-type", "article",
                     "--platform", "平台甲", "--speech-act", "explain", "--include-media"]
        with patch("sys.argv", arguments), contextlib.redirect_stdout(stdout):
            self.assertEqual(selector.main(), 0)
        self.assertEqual(json.loads(stdout.getvalue())["examples"][0]["media"][0]["path"], "/private/synthetic.png")


if __name__ == "__main__":
    unittest.main()
