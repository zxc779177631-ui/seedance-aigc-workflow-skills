#!/usr/bin/env python3
"""Calibrate and estimate bilingual digital-human speech timing."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

HAN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
EN_WORD_RE = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")
AMBIGUOUS_RE = re.compile(r"\b(?:[A-Z]{2,}|[A-Za-z]+\d+[A-Za-z0-9]*)\b|\d+(?:[.,]\d+)*")
TIMELINE_RE = re.compile(r"(?<!\d)(\d{1,2})\s*[-–—至到]\s*(\d{1,2})\s*秒")
VOWEL_GROUP_RE = re.compile(r"[aeiouy]+")

EXCEPTION_SYLLABLES = {
    "ai": 2,
    "business": 2,
    "careless": 2,
    "changed": 1,
    "different": 3,
    "every": 2,
    "failure": 2,
    "people": 2,
    "roi": 3,
    "single": 2,
    "time": 1,
}


def syllables_in_word(word: str) -> int:
    cleaned = re.sub(r"[^a-z]", "", word.lower().replace("’", "'"))
    if not cleaned:
        return 0
    if cleaned in EXCEPTION_SYLLABLES:
        return EXCEPTION_SYLLABLES[cleaned]
    count = len(VOWEL_GROUP_RE.findall(cleaned))
    if cleaned.endswith("e") and not cleaned.endswith(("le", "ye")) and count > 1:
        count -= 1
    if cleaned.endswith("ed") and len(cleaned) > 3 and not cleaned.endswith(("ted", "ded")) and count > 1:
        count -= 1
    return max(1, count)


def parse_reading_map(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"reading-map 不是有效 JSON：{exc}") from exc
    if not isinstance(value, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
        raise ValueError("reading-map 必须是字符串到字符串的 JSON 对象")
    return value


def apply_readings(text: str, readings: dict[str, str]) -> str:
    for token in sorted(readings, key=len, reverse=True):
        if re.fullmatch(r"[A-Za-z0-9]+", token):
            pattern = rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])"
            text = re.sub(pattern, lambda _: readings[token], text)
        else:
            text = text.replace(token, readings[token])
    return text


def analyze(text: str, readings: dict[str, str]) -> dict[str, Any]:
    rendered = apply_readings(text, readings)
    zh_chars = len(HAN_RE.findall(rendered))
    words = EN_WORD_RE.findall(rendered)
    en_syllables = sum(syllables_in_word(word) for word in words)
    ambiguous = sorted({token for token in AMBIGUOUS_RE.findall(text) if token not in readings})
    return {
        "original_text": text,
        "rendered_reading": rendered,
        "zh_chars": zh_chars,
        "en_words": len(words),
        "en_syllables": en_syllables,
        "ambiguous_tokens": ambiguous,
        "reading_map": readings,
    }


def load_profile(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        profile = json.load(handle)
    if profile.get("schema_version") != 1 or not isinstance(profile.get("rates"), dict):
        raise ValueError("人物档案格式无效或版本不受支持")
    return profile


def estimate_duration(metrics: dict[str, Any], profile: dict[str, Any]) -> tuple[float, list[str]]:
    rates = profile["rates"]
    duration = 0.0
    missing: list[str] = []
    if metrics["zh_chars"]:
        rate = rates.get("zh_chars_per_second")
        if not rate:
            missing.append("中文字符速度")
        else:
            duration += metrics["zh_chars"] / float(rate)
    if metrics["en_syllables"]:
        rate = rates.get("en_syllables_per_second")
        if not rate:
            missing.append("英文音节速度")
        else:
            duration += metrics["en_syllables"] / float(rate)
    return duration, missing


def conservative_duration(seconds: float, tolerance_percent: float) -> float:
    """Return the upper planning bound implied by the speaker profile tolerance."""
    return seconds * (1 + tolerance_percent / 100)


def planning_status(seconds: float, tolerance_percent: float) -> str:
    """Classify a clip for cost efficiency and hard-limit safety."""
    if seconds > 15:
        return "超限"
    if seconds < 9:
        return "偏短"
    if conservative_duration(seconds, tolerance_percent) > 15:
        return "临界"
    if seconds < 12:
        return "可接受"
    return "理想"


def command_analyze(args: argparse.Namespace) -> dict[str, Any]:
    return analyze(args.text, parse_reading_map(args.reading_map))


def command_calibrate(args: argparse.Namespace) -> dict[str, Any]:
    if args.duration <= 0:
        raise ValueError("duration 必须大于 0")
    if not 0 <= args.tolerance <= 50:
        raise ValueError("tolerance 必须在 0 到 50 之间")
    readings = parse_reading_map(args.reading_map)
    metrics = analyze(args.text, readings)
    if metrics["ambiguous_tokens"]:
        raise ValueError("请先为歧义词提供实际读法：" + ", ".join(metrics["ambiguous_tokens"]))
    if args.language == "zh" and metrics["en_syllables"]:
        raise ValueError("zh 样本仍包含英文发音；请提供纯中文样本，或改用 mixed 并分别提供两种语言时长")
    if args.language == "en" and metrics["zh_chars"]:
        raise ValueError("en 样本仍包含中文发音；请提供纯英文样本，或改用 mixed 并分别提供两种语言时长")
    if args.language == "mixed":
        if metrics["zh_chars"] and not args.zh_duration:
            raise ValueError("mixed 样本需要 --zh-duration，不能从总时长分离中文速度")
        if metrics["en_syllables"] and not args.en_duration:
            raise ValueError("mixed 样本需要 --en-duration，不能从总时长分离英文速度")
    zh_seconds = args.zh_duration if args.language == "mixed" else (args.duration if args.language == "zh" else None)
    en_seconds = args.en_duration if args.language == "mixed" else (args.duration if args.language == "en" else None)
    if zh_seconds is not None and zh_seconds <= 0:
        raise ValueError("zh-duration 必须大于 0")
    if en_seconds is not None and en_seconds <= 0:
        raise ValueError("en-duration 必须大于 0")
    zh_rate = metrics["zh_chars"] / zh_seconds if metrics["zh_chars"] and zh_seconds else None
    en_rate = metrics["en_syllables"] / en_seconds if metrics["en_syllables"] and en_seconds else None
    profile = {
        "schema_version": 1,
        "speaker": args.speaker,
        "language": args.language,
        "sample": {
            "text": args.text,
            "duration_seconds": args.duration,
            "zh_duration_seconds": args.zh_duration,
            "en_duration_seconds": args.en_duration,
            "reading_map": readings,
            "metrics": metrics,
        },
        "rates": {
            "zh_chars_per_second": round(zh_rate, 4) if zh_rate else None,
            "en_syllables_per_second": round(en_rate, 4) if en_rate else None,
        },
        "tolerance_percent": args.tolerance,
        "performance_preferences": {
            "body_language": args.body_language,
            "pose_lock": args.pose_lock,
        },
        "notes": args.notes,
    }
    if args.output:
        Path(args.output).write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return profile


def command_estimate(args: argparse.Namespace) -> dict[str, Any]:
    profile = load_profile(args.profile)
    readings = dict(profile.get("sample", {}).get("reading_map", {}))
    readings.update(parse_reading_map(args.reading_map))
    metrics = analyze(args.text, readings)
    duration, missing = estimate_duration(metrics, profile)
    tolerance = float(profile.get("tolerance_percent", 8))
    if not 0 <= tolerance <= 50:
        raise ValueError("人物档案中的 tolerance_percent 必须在 0 到 50 之间")
    result = {
        "speaker": profile.get("speaker"),
        "metrics": metrics,
        "estimated_seconds": round(duration, 1) if not missing else None,
        "conservative_seconds": round(conservative_duration(duration, tolerance), 1) if not missing else None,
        "safe_target_seconds": round(15 / (1 + tolerance / 100), 1) if not missing else None,
        "status": planning_status(duration, tolerance) if not missing else "缺少基准",
        "missing_rates": missing,
        "tolerance_percent": tolerance,
    }
    return result


def normalize_content(text: str) -> str:
    """Remove punctuation, spacing and formatting while preserving spoken content."""
    return "".join(char for char in text if unicodedata.category(char)[0] in {"L", "N"})


def validate_integrity(original: str, segments: list[str]) -> dict[str, Any]:
    normalized_original = normalize_content(original)
    normalized_joined = normalize_content("".join(segments))
    mismatch_index = None
    for index, (left, right) in enumerate(zip(normalized_original, normalized_joined)):
        if left != right:
            mismatch_index = index
            break
    if mismatch_index is None and len(normalized_original) != len(normalized_joined):
        mismatch_index = min(len(normalized_original), len(normalized_joined))
    return {
        "valid": normalized_original == normalized_joined,
        "original_units": len(normalized_original),
        "joined_units": len(normalized_joined),
        "mismatch_index": mismatch_index,
    }


def command_validate_integrity(args: argparse.Namespace) -> dict[str, Any]:
    return validate_integrity(args.original, args.segment)


def validate_timeline(text: str, duration: int) -> dict[str, Any]:
    intervals = [(int(start), int(end)) for start, end in TIMELINE_RE.findall(text)]
    errors: list[str] = []
    if duration <= 0:
        errors.append("duration 必须大于 0")
    if not intervals:
        errors.append("未找到形如 00-02 秒的时间段")
    else:
        if intervals[0][0] != 0:
            errors.append(f"时间轴必须从 00 秒开始，当前从 {intervals[0][0]:02d} 秒开始")
        previous_end = 0
        for index, (start, end) in enumerate(intervals, start=1):
            if end <= start:
                errors.append(f"第 {index} 段结束时间必须晚于开始时间")
            if start > previous_end:
                errors.append(f"{previous_end:02d}-{start:02d} 秒存在缺口")
            elif start < previous_end:
                errors.append(f"第 {index} 段与上一段在 {start:02d}-{previous_end:02d} 秒重叠")
            previous_end = max(previous_end, end)
        if intervals[-1][1] < duration:
            errors.append(f"时间轴只到 {intervals[-1][1]:02d} 秒，未覆盖至 {duration:02d} 秒")
        elif intervals[-1][1] > duration:
            errors.append(f"时间轴超过目标时长 {duration:02d} 秒")
    return {"valid": not errors, "duration_seconds": duration, "intervals": intervals, "errors": errors}


def command_validate_timeline(args: argparse.Namespace) -> dict[str, Any]:
    return validate_timeline(args.text, args.duration)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="统计中文字符、英文音节和读音歧义")
    analyze_parser.add_argument("--text", required=True)
    analyze_parser.add_argument("--reading-map")
    analyze_parser.set_defaults(handler=command_analyze)

    calibrate_parser = subparsers.add_parser("calibrate", help="用自然口播样本建立人物档案")
    calibrate_parser.add_argument("--speaker", required=True)
    calibrate_parser.add_argument("--text", required=True)
    calibrate_parser.add_argument("--duration", required=True, type=float)
    calibrate_parser.add_argument("--language", required=True, choices=("zh", "en", "mixed"))
    calibrate_parser.add_argument("--zh-duration", type=float)
    calibrate_parser.add_argument("--en-duration", type=float)
    calibrate_parser.add_argument("--reading-map")
    calibrate_parser.add_argument("--tolerance", type=float, default=8)
    calibrate_parser.add_argument("--body-language", choices=("少量", "适中", "较多", "未确认"), default="未确认")
    calibrate_parser.add_argument("--pose-lock", default="")
    calibrate_parser.add_argument("--notes", default="")
    calibrate_parser.add_argument("--output")
    calibrate_parser.set_defaults(handler=command_calibrate)

    estimate_parser = subparsers.add_parser("estimate", help="用人物档案估算一段口播时长")
    estimate_parser.add_argument("--profile", required=True)
    estimate_parser.add_argument("--text", required=True)
    estimate_parser.add_argument("--reading-map")
    estimate_parser.set_defaults(handler=command_estimate)

    timeline_parser = subparsers.add_parser("validate-timeline", help="检查动作时间轴是否连续覆盖目标时长")
    timeline_parser.add_argument("--text", required=True)
    timeline_parser.add_argument("--duration", required=True, type=int)
    timeline_parser.set_defaults(handler=command_validate_timeline)

    integrity_parser = subparsers.add_parser("validate-integrity", help="检查切分后是否遗漏或改写原文")
    integrity_parser.add_argument("--original", required=True)
    integrity_parser.add_argument("--segment", required=True, action="append")
    integrity_parser.set_defaults(handler=command_validate_integrity)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = args.handler(args)
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
