#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seedance-video-pipeline · 交互式选型问卷

把「需求」翻译成「通道 + 模型 + 预估费用 + 命令骨架」。

两种用法：
  1) 交互式（逐项问答）：      python3 channel_quiz.py
  2) 非交互式（一行出结果）：  python3 channel_quiz.py --ver 2.5 --audio y --duration 15 --res 720p --perf n --budget normal

输出：推荐通道、模型 ID、预估费用、钥匙串条目、命令骨架、卡点提醒。

⚠️ 紫域 / MaxForAI 档位持续漂移，最终提交前务必实拉对应 /models 接口确认；
   命令骨架中的 flag 名以各专项 skill 的 SKILL.md 为准。
"""

import argparse
import sys

ZIYU_POINT_PER_YUAN = 100  # 紫域 100 点 = 1 元


# ----------------------------------------------------------------------------
# 决策核心：输入维度 -> 推荐
# ----------------------------------------------------------------------------
def decide(ver, audio, duration, res, perf, budget):
    d = duration
    if ver == "2.5":
        if perf == "y" and 20 <= d <= 30:
            return {
                "channel": "紫域 AI",
                "model": "zy_model_85b5f6490c0952cc3f68",
                "key": "seedance-workflow-ziyu",
                "points": 1000,
                "why": "2.5 720p 挂表演参考视频，仅 20–30s 档可用",
                "transfer": False,
            }
        if audio == "y":
            if budget == "tight":
                return {
                    "channel": "MaxForAI",
                    "model": "wf-sd2-5-720p",
                    "key": "seedance-workflow-maxforai-sd25",
                    "cny": round(0.30 * d, 2),
                    "why": "2.5 按秒带音频，MaxForAI ≈¥0.30/秒 最便宜；紫域URL须 --transfer 转存",
                    "transfer": True,
                }
            if d <= 16:
                return {
                    "channel": "紫域 AI",
                    "model": "zy_model_beb4bdb66a86f1fc42c7",
                    "key": "seedance-workflow-ziyu",
                    "points": 600,
                    "why": "2.5 720p 15s 带音频，按条 600点/次（最稳带音频档）",
                    "transfer": False,
                }
            return {
                "channel": "紫域 AI",
                "model": "zy_model_2bf90606d3250d5026ce",
                "key": "seedance-workflow-ziyu",
                "points": 60 * d,
                "why": "2.5 720p 按秒带音频，60点/秒",
                "transfer": False,
            }
        # 2.5 不带音频
        return {
            "channel": "紫域 AI",
            "model": "zy_model_2bf90606d3250d5026ce",
            "key": "seedance-workflow-ziyu",
            "points": 60 * d,
            "why": "2.5 静音，按秒 60点/秒",
            "transfer": False,
        }
    # ---- 2.0 ----
    if budget == "tight":
        return {
            "channel": "MaxForAI (sd20)",
            "model": "zy-特价豆包900 / 特价ft-sd2.0fast",
            "key": "seedance-workflow-maxforai-sd20-zy 或 -sd20-ft",
            "why": "2.0 低成本：MaxForAI 特价档最便宜（约 ¥1/次）；紫域URL须 --transfer",
            "transfer": True,
        }
    return {
        "channel": "紫域 AI 2.0",
        "model": "zy_model_2134621044047793db22",
        "key": "seedance-workflow-ziyu",
        "points": 50 + 10 * d,
        "why": "2.0 基础档 50+10/秒（最便宜 H3）",
        "transfer": False,
    }


# ----------------------------------------------------------------------------
# 命令骨架（占位符 + 明确指向专项 skill）
# ----------------------------------------------------------------------------
def cmd_skeleton(rec, ver, audio, d, res, perf):
    ch = rec["channel"]
    name = "G0x-shotN"
    if ch.startswith("紫域"):
        lines = [
            "python3 ~/.workbuddy/skills/ziyu-video-submit/scripts/submit.py \\",
            f"  --model {rec['model']} \\",
            f"  --prompt-file <{name}-prompt.txt> \\",
            "  --images <IDENTITY_URL> <SCENE_URL> <PAINT_URL> \\",
        ]
        if audio == "y":
            lines.append("  --audio-url <MP3_PUBLIC_URL> \\")
        lines.append(f"  --duration {d} --resolution {res}")
        return "\n".join(lines)
    if ch.startswith("MaxForAI"):
        tier = ("sd25" if "wf-sd2-5" in rec["model"]
                else ("sd20-zy" if "zy" in rec["model"] else "sd20-ft"))
        lines = [
            "python3 ~/.workbuddy/skills/maxforai-video-submit/scripts/submit.py \\",
            f"  --tier {tier} --model {rec['model']} \\",
            f"  --prompt-file <{name}-prompt.txt> \\",
            f"  --ratio 9:16 --duration {d} --resolution {res} \\",
            "  --images <IMG1_URL> <IMG2_URL> <IMG3_URL> \\",
        ]
        if perf == "y":
            lines.append("  --video-url <PERF_VIDEO_URL> \\")
        if audio == "y":
            lines.append("  --audio-url </local/path/to/voice.mp3> \\")
        lines += ["  --transfer \\", f"  --name {name} --outdir <OUTDIR>"]
        return "\n".join(lines)
    # Ark
    ark_model = ("doubao-seedance-2-5-260628" if ver == "2.5"
                 else "doubao-seedance-2-0-260128")
    lines = [
        "python3 ~/.workbuddy/skills/seedance-ark-submit/scripts/submit.py \\",
        f"  --model {ark_model} \\",
        f"  --prompt-file <{name}-prompt.txt> \\",
        "  --reference-image <IDENTITY_URL> \\",
    ]
    if perf == "y":
        lines.append("  --reference-video <PERF_VIDEO_URL> \\")
    if audio == "y":
        lines.append("  --reference-audio <AUDIO_URL> \\")
    lines.append(f"  --duration {int(d)}")
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# 输出渲染
# ----------------------------------------------------------------------------
def render(rec, ver, audio, d, res, perf, budget):
    cost = (_cost_str(points=rec.get("points"), cny=rec.get("cny"))
            if (rec.get("points") is not None or rec.get("cny") is not None)
            else "以实拉档位为准")
    print()
    print("=" * 64)
    print("  🎯 推荐通道")
    print("=" * 64)
    print(f"  通道      : {rec['channel']}")
    print(f"  模型/档位 : {rec['model']}")
    print(f"  鉴权钥匙串: {rec['key']}")
    print(f"  预估费用  : {cost}")
    print(f"  选型依据  : {rec['why']}")
    if rec.get("transfer"):
        print("  素材处理  : 紫域/TOS 公网URL须 --transfer 转存（直传会失败）")
    print()
    print("-" * 64)
    print("  📋 命令骨架（占位符需替换；flag 名以专项 skill SKILL.md 为准）")
    print("-" * 64)
    print(cmd_skeleton(rec, ver, audio, d, res, perf))
    print()
    print("-" * 64)
    print("  ⚠️ 提交前卡点")
    print("-" * 64)
    print("  1. 报账确认：把「通道+模型+时长+预估×任务数」报用户等 OK 再交。")
    print("  2. 断线防叠单：重提前先查后台 task 状态，确认无重复在跑单。")
    print("  3. 紫域：本地图先 POST /api/v1/uploads 拿URL；音频用 mp3 非 m4a。")
    if rec.get("transfer"):
        print("  4. MaxForAI：紫域URL必须 --transfer；不需要 TOS。")
    else:
        print("  4. 紫域档位漂移：提交前 GET /api/v1/models 实拉确认 modelId。")
    print("  5. 钥匙串取密钥，绝不写进前端/仓库。")
    print("=" * 64)


def _cost_str(points=None, cny=None):
    if points is not None:
        return f"{points} 点 ≈ ¥{points / ZIYU_POINT_PER_YUAN:.2f}"
    if cny is not None:
        return f"≈ ¥{cny:.2f}"
    return "以实拉档位为准"


# ----------------------------------------------------------------------------
# 交互式问答
# ----------------------------------------------------------------------------
def _ask(prompt, options, default=0):
    print()
    print(prompt)
    for i, (_, label) in enumerate(options, 1):
        mark = "▶" if i - 1 == default else " "
        print(f"    {mark} {i}. {label}")
    while True:
        try:
            raw = input(f"  选择 [1-{len(options)}] (默认 {default + 1}): ").strip()
        except EOFError:
            print()
            return options[default][0]
        if not raw:
            return options[default][0]
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][0]
        print("  ❌ 无效输入，重试")


def interactive():
    print("\n🎬 Seedance 数字人视频 · 通道选型问卷")
    print("   逐项回答，直接回车用默认项。\n")
    ver = _ask("模型版本？", [("2.5", "Seedance 2.5（画质好、带音频成熟）"),
                              ("2.0", "Seedance 2.0（便宜、口播够用）")], default=0)
    audio = _ask("需要音频 / 口型同步吗？", [("y", "是，要带声音和对口型"),
                                            ("n", "否，静音画面")], default=0)
    while True:
        raw = input("\n  时长（秒，整数）: ").strip()
        if raw.isdigit() and int(raw) > 0:
            duration = int(raw)
            break
        print("  ❌ 请输入正整数秒数")
    res = _ask("分辨率？", [("720p", "720p（清晰）"), ("480p", "480p（省点）")], default=0)
    perf = _ask("要挂表演参考视频吗（借神态/肢体）？",
                [("n", "否"), ("y", "是（注意：2.5 挂表演仅 20–30s 档）")], default=0)
    budget = _ask("预算倾向？", [("normal", "质量优先（默认通道）"),
                                 ("tight", "最便宜（走特价/按秒档）")], default=0)
    rec = decide(ver, audio, duration, res, perf, budget)
    render(rec, ver, audio, duration, res, perf, budget)


# ----------------------------------------------------------------------------
# 入口
# ----------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(
        description="Seedance 数字人视频 通道选型问卷（交互或参数）")
    p.add_argument("--ver", choices=["2.5", "2.0"], help="模型版本")
    p.add_argument("--audio", choices=["y", "n"], help="是否带音频/口型")
    p.add_argument("--duration", type=int, help="时长（秒，正整数）")
    p.add_argument("--res", choices=["720p", "480p"], help="分辨率")
    p.add_argument("--perf", choices=["y", "n"], help="是否挂表演参考视频")
    p.add_argument("--budget", choices=["normal", "tight"], help="预算倾向")
    args = p.parse_args()

    if not all([args.ver, args.audio, args.duration, args.res, args.perf, args.budget]):
        if any([args.ver, args.audio, args.duration, args.res, args.perf, args.budget]):
            p.error("交互模式需全部参数；或留空全部参数进入逐项问答。")
        interactive()
        return

    rec = decide(args.ver, args.audio, args.duration, args.res, args.perf, args.budget)
    render(rec, args.ver, args.audio, args.duration, args.res, args.perf, args.budget)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已取消。")
        sys.exit(1)
