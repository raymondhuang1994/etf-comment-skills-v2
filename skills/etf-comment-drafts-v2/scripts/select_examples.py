#!/usr/bin/env python3
"""Select private style examples locally; never send data or change the library."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import unicodedata

CATEGORIES = {"observation", "question", "comparison", "intention", "event", "topic"}
PREFERENCES = {"unrated", "liked", "disliked"}


class LibraryError(ValueError):
    """A safe error message that contains neither case text nor a local path."""


def default_library():
    explicit = os.environ.get("ETF_COMMENT_LIBRARY")
    if explicit:
        return Path(explicit).expanduser()
    base = Path(os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")).expanduser()
    return base / "private" / "etf-comment-drafts-v2" / "cases.jsonl"


def _language(value):
    value = value.strip().replace("_", "-").casefold()
    return {"粤语": "zh-hk", "廣東話": "zh-hk", "广东话": "zh-hk"}.get(value, value)


def _tokens(value):
    value = unicodedata.normalize("NFKC", value).casefold()
    result = set(re.findall(r"[a-z0-9]+", value))
    for run in re.findall(r"[\u3400-\u9fff]+", value):
        result.update(run)
        result.update(run[i:i + 2] for i in range(len(run) - 1))
    return result


def _weight(token):
    return 0.15 if len(token) == 1 and "\u3400" <= token <= "\u9fff" else 1.0


def _load_cases(path):
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        raise LibraryError("无法读取私有案例库，请检查文件权限与 UTF-8 编码。") from None
    cases, ids = [], set()
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            raise LibraryError("案例库第 %d 行不是有效 JSON。" % number) from None
        if not isinstance(row, dict):
            raise LibraryError("案例库第 %d 行必须是 JSON 对象。" % number)
        for key in ("id", "category", "language", "preference", "split", "cluster"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise LibraryError("案例库第 %d 行缺少有效字段：%s。" % (number, key))
        if row["id"] in ids:
            raise LibraryError("案例库第 %d 行出现重复 id。" % number)
        ids.add(row["id"])
        if row["category"] not in CATEGORIES or row["preference"] not in PREFERENCES or row["split"] not in {"reference", "holdout"}:
            raise LibraryError("案例库第 %d 行的类别、偏好或分组值不正确。" % number)
        if not isinstance(row.get("tags"), list) or any(not isinstance(tag, str) for tag in row["tags"]):
            raise LibraryError("案例库第 %d 行的 tags 必须是字符串数组。" % number)
        for key in ("text", "style_text", "notes"):
            if key in row and not isinstance(row[key], str):
                raise LibraryError("案例库第 %d 行字段 %s 必须是字符串。" % (number, key))
        if "source" in row and not isinstance(row["source"], dict):
            raise LibraryError("案例库第 %d 行的 source 必须是对象。" % number)
        cases.append(row)
    return cases


def _load_preferences(path):
    if not path.exists():
        return []
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise LibraryError("无法解析同目录的 profile.json，请检查格式与权限。") from None
    if not isinstance(profile, dict):
        raise LibraryError("profile.json 必须是 JSON 对象。")
    preferences = profile.get("style_preferences", [])
    if not isinstance(preferences, list) or any(not isinstance(value, str) for value in preferences):
        raise LibraryError("profile.json 的 style_preferences 必须是字符串数组。")
    if "feedback" in profile and (not isinstance(profile["feedback"], list) or any(not isinstance(item, dict) for item in profile["feedback"])):
        raise LibraryError("profile.json 的 feedback 必须是对象数组。")
    # Free-form feedback is not a classifier. Only explicit row labels drive ranking.
    return list(dict.fromkeys(value.strip() for value in preferences if value.strip()))


def _public_example(row, negative=False):
    return {
        "id": row["id"], "category": row["category"], "language": row["language"],
        "style_text": row["style_text"].strip(), "tags": row["tags"],
        "preference": row["preference"],
        "use": "用户明确不喜欢的表达参考，避免仿写。" if negative else "只参考表达，不迁移事实或经历。",
    }


def select_examples(library=None, query="", category=None, language=None, limit=6):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 12:
        raise LibraryError("limit 必须是 1–12 的整数。")
    if category and category not in CATEGORIES:
        raise LibraryError("category 必须使用支持的类别 id。")
    path = Path(library).expanduser() if library is not None else default_library()
    result = {"available": False, "examples": [], "avoid_examples": [], "style_preferences": [],
              "counts": {"reference_records": 0, "excluded_holdout": 0, "skipped_without_style_text": 0},
              "selection_note": "未发现私有案例库；使用公开合成示例或当前会话提供的参考。"}
    if not path.exists():
        return result
    rows = _load_cases(path)
    result["available"] = True
    result["style_preferences"] = _load_preferences(path.with_name("profile.json"))
    terms = _tokens(query)
    total = sum(_weight(term) for term in terms) or 1.0
    ranked, rejected = [], []
    for row in rows:
        if row["split"] == "holdout":
            result["counts"]["excluded_holdout"] += 1
            continue
        result["counts"]["reference_records"] += 1
        if not row.get("style_text", "").strip():
            result["counts"]["skipped_without_style_text"] += 1
            continue
        if category and row["category"] != category:
            continue
        if language and _language(row["language"]) != _language(language):
            continue
        content_terms = _tokens(row["style_text"] + " " + " ".join(row["tags"]))
        relevance = sum(_weight(term) for term in terms & content_terms) / total
        # Relevance dominates; explicit likes break close comparisons, not unrelated topics.
        score = relevance * 10 + (1.0 if row["preference"] == "liked" else 0.0)
        target = rejected if row["preference"] == "disliked" else ranked
        target.append((score, relevance, row))

    def choose(candidates, amount, negative=False):
        ordered = sorted(candidates, key=lambda item: (-(item[1] > 0), -item[0], -item[1], item[2]["id"]))
        chosen, clusters = [], set()
        for _, _, row in ordered:
            if row["cluster"] in clusters:
                continue
            chosen.append(_public_example(row, negative))
            clusters.add(row["cluster"])
            if len(chosen) == amount:
                break
        return chosen

    result["examples"] = choose(ranked, limit)
    result["avoid_examples"] = choose(rejected, min(2, limit), negative=True)
    result["selection_note"] = (
        "按字词重合、明确偏好和重复骨架选例；原文及来源未输出。不是语义检索或效果评分。"
        if result["examples"] else
        "库存在，但没有符合条件的可用正例；使用公开合成示例。"
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path)
    parser.add_argument("--query", default="")
    parser.add_argument("--category", choices=sorted(CATEGORIES))
    parser.add_argument("--language")
    parser.add_argument("--limit", type=int, default=6)
    args = parser.parse_args()
    try:
        output = select_examples(args.library, args.query, args.category, args.language, args.limit)
    except LibraryError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
