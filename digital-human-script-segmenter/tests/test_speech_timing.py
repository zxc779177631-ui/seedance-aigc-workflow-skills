import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "speech_timing.py"
SPEC = importlib.util.spec_from_file_location("speech_timing", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class SpeechTimingTests(unittest.TestCase):
    def test_chinese_excludes_punctuation(self):
        result = MODULE.analyze("你好，世界！AI。", {"AI": "A I"})
        self.assertEqual(result["zh_chars"], 4)
        self.assertEqual(result["en_syllables"], 2)
        self.assertEqual(result["ambiguous_tokens"], [])

    def test_ambiguous_tokens_require_readings(self):
        result = MODULE.analyze("2026 年看 ROI", {})
        self.assertEqual(result["ambiguous_tokens"], ["2026", "ROI"])

    def test_english_syllables(self):
        result = MODULE.analyze("Building trust takes time.", {})
        self.assertEqual(result["en_syllables"], 6)

    def test_calibrate_and_estimate_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp) / "profile.json"
            calibrated = subprocess.run(
                [sys.executable, str(SCRIPT), "calibrate", "--speaker", "测试者", "--text", "一二三四五六", "--duration", "3", "--language", "zh", "--output", str(profile)],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(json.loads(calibrated.stdout)["rates"]["zh_chars_per_second"], 2.0)
            estimated = subprocess.run(
                [sys.executable, str(SCRIPT), "estimate", "--profile", str(profile), "--text", "一二三四五六七八九十"],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(estimated.stdout)
            self.assertEqual(payload["estimated_seconds"], 5.0)
            self.assertEqual(payload["status"], "偏短")

    def test_single_language_calibration_rejects_other_language_content(self):
        args = MODULE.argparse.Namespace(
            duration=3,
            tolerance=8,
            reading_map='{"AI":"A I"}',
            text="你好 AI",
            language="zh",
            zh_duration=None,
            en_duration=None,
            speaker="测试者",
            body_language="未确认",
            pose_lock="",
            notes="",
            output=None,
        )
        with self.assertRaisesRegex(ValueError, "仍包含英文发音"):
            MODULE.command_calibrate(args)

    def test_reading_map_does_not_replace_inside_larger_token(self):
        result = MODULE.analyze("AI helps SAIL", {"AI": "A I"})
        self.assertEqual(result["rendered_reading"], "A I helps SAIL")

    def test_tolerance_marks_near_limit_clip_as_critical(self):
        self.assertEqual(MODULE.planning_status(13.8, 8), "理想")
        self.assertEqual(MODULE.planning_status(14.0, 8), "临界")
        self.assertAlmostEqual(MODULE.conservative_duration(14.0, 8), 15.12)

    def test_missing_language_rate_is_explicit(self):
        profile = {"schema_version": 1, "rates": {"zh_chars_per_second": 3, "en_syllables_per_second": None}}
        metrics = MODULE.analyze("hello", {})
        duration, missing = MODULE.estimate_duration(metrics, profile)
        self.assertEqual(duration, 0)
        self.assertEqual(missing, ["英文音节速度"])

    def test_mixed_calibration_requires_per_language_durations(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "calibrate", "--speaker", "测试者", "--text", "你好 hello", "--duration", "3", "--language", "mixed"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--zh-duration", result.stderr)

    def test_timeline_accepts_full_continuous_coverage(self):
        text = "00-02 秒保持坐姿。02-03 秒抬手。03-06 秒保持。06-08 秒放下。08-12 秒保持坐姿。"
        result = MODULE.validate_timeline(text, 12)
        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], [])

    def test_timeline_rejects_gap_and_overrun(self):
        text = "00-02 秒保持坐姿。03-06 秒抬手。06-13 秒保持。"
        result = MODULE.validate_timeline(text, 12)
        self.assertFalse(result["valid"])
        self.assertIn("02-03 秒存在缺口", result["errors"])
        self.assertIn("时间轴超过目标时长 12 秒", result["errors"])

    def test_integrity_ignores_only_spacing_and_punctuation(self):
        valid = MODULE.validate_integrity("大家好。Hello!", ["大家好", "Hello"])
        self.assertTrue(valid["valid"])
        changed = MODULE.validate_integrity("大家好。Hello!", ["大家", "Hi"])
        self.assertFalse(changed["valid"])
        self.assertIsNotNone(changed["mismatch_index"])


if __name__ == "__main__":
    unittest.main()
