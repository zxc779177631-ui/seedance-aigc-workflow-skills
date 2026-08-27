#!/usr/bin/env python3
"""Seedance 2.0 official Ark SDK wrapper.

Create / poll / cancel video tasks, and upload local media to Ark Files.
Uses volcenginesdkarkruntime.Ark — same SDK as the official quickstart package.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.request import urlopen

DEFAULT_MODEL = "doubao-seedance-2-0-260128"
DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
KEYCHAIN_SERVICE = "seedance-workflow-ark"
QUICKSTART_PYTHON = Path.home() / "Developer/ark-seedance2.0-quickstart/.venv/bin/python"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff", ".tif"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".avi", ".mkv", ".m4v"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}

ROLE_ALIASES = {
    "ref": "reference_image",
    "reference": "reference_image",
    "reference_image": "reference_image",
    "first": "first_frame",
    "first_frame": "first_frame",
    "last": "last_frame",
    "last_frame": "last_frame",
    "video": "reference_video",
    "reference_video": "reference_video",
    "audio": "reference_audio",
    "reference_audio": "reference_audio",
}


def fail(message: str, code: int = 1) -> None:
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False), file=sys.stderr)
    raise SystemExit(code)


def resolve_api_key() -> str:
    key = os.environ.get("ARK_API_KEY", "").strip()
    if key:
        return key
    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["security", "find-generic-password", "-a", os.environ.get("USER", ""), "-s", KEYCHAIN_SERVICE, "-w"],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except OSError:
            pass
    fail(
        "缺少 ARK_API_KEY。请 export ARK_API_KEY=xxx，"
        "或用 seedance-workflow 的钥匙串项 seedance-workflow-ark 保存密钥。"
    )
    raise AssertionError


def make_client():
    try:
        from volcenginesdkarkruntime import Ark
    except ImportError:
        fail(
            "未安装官方 SDK。请先装火山接入包（~/Developer/ark-seedance2.0-quickstart），"
            "并用该目录 .venv/bin/python 运行本脚本。"
        )
    return Ark(base_url=os.environ.get("ARK_BASE_URL", DEFAULT_BASE_URL), api_key=resolve_api_key())


def is_remote(value: str) -> bool:
    return value.startswith(("http://", "https://", "asset://", "tos://"))


def guess_media_kind(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in AUDIO_EXTS:
        return "audio"
    fail(f"无法从扩展名判断素材类型: {path}")
    raise AssertionError


def upload_local(client, path: Path) -> str:
    if not path.is_file():
        fail(f"本地文件不存在: {path}")
    with path.open("rb") as handle:
        uploaded = client.files.create(file=handle, purpose="user_data")
    file_id = getattr(uploaded, "id", None)
    if not file_id:
        fail(f"上传成功但未返回文件 ID: {uploaded}")
    return f"asset://{file_id}"


def resolve_media(client, value: str) -> str:
    if is_remote(value):
        return value
    return upload_local(client, Path(value).expanduser())


def parse_media_arg(raw: str, default_role: str) -> tuple[str, str]:
    if "=" in raw:
        role_raw, value = raw.split("=", 1)
        role = ROLE_ALIASES.get(role_raw.strip().lower())
        # 只有左侧是已知 role 才拆，避免把带签名的 https URL 里的 = 误判
        if role:
            return role, value
    return default_role, raw


def task_to_dict(task: Any) -> dict[str, Any]:
    if hasattr(task, "model_dump"):
        data = task.model_dump()
    elif hasattr(task, "to_dict"):
        data = task.to_dict()
    else:
        data = {
            "id": getattr(task, "id", None),
            "status": getattr(task, "status", None),
            "error": getattr(task, "error", None),
        }
    content = data.get("content") or {}
    if not isinstance(content, dict):
        content = {
            "video_url": getattr(content, "video_url", None),
            "last_frame_url": getattr(content, "last_frame_url", None),
            "file_url": getattr(content, "file_url", None),
        }
        data["content"] = content
    error = data.get("error")
    if error and not isinstance(error, dict):
        data["error"] = {
            "code": getattr(error, "code", None),
            "message": getattr(error, "message", None),
        }
    return data


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def build_content(prompt: str, images: list[str], videos: list[str], audios: list[str], client) -> list[dict]:
    content: list[dict] = [{"type": "text", "text": prompt}]
    image_count = video_count = audio_count = 0
    first_count = last_count = 0

    for raw in images:
        role, value = parse_media_arg(raw, "reference_image")
        if role not in {"reference_image", "first_frame", "last_frame"}:
            fail(f"--image 的 role 必须是 reference_image/first_frame/last_frame，收到 {role}")
        if role == "first_frame":
            first_count += 1
        elif role == "last_frame":
            last_count += 1
        else:
            image_count += 1
        content.append({"type": "image_url", "image_url": {"url": resolve_media(client, value)}, "role": role})

    for raw in videos:
        role, value = parse_media_arg(raw, "reference_video")
        if role != "reference_video":
            fail(f"--video 的 role 必须是 reference_video，收到 {role}")
        video_count += 1
        content.append({"type": "video_url", "video_url": {"url": resolve_media(client, value)}, "role": role})

    for raw in audios:
        role, value = parse_media_arg(raw, "reference_audio")
        if role != "reference_audio":
            fail(f"--audio-ref 的 role 必须是 reference_audio，收到 {role}")
        audio_count += 1
        content.append({"type": "audio_url", "audio_url": {"url": resolve_media(client, value)}, "role": role})

    if first_count > 1 or last_count > 1:
        fail("first_frame / last_frame 各自最多 1 张")
    if image_count + first_count + last_count > 9:
        fail("图片合计超过 9 张（含首尾帧）")
    if video_count > 3:
        fail("视频参考超过 3 个")
    if audio_count > 3:
        fail("音频参考超过 3 个")
    if not prompt.strip() and not (images or videos or audios):
        fail("至少需要提示词或素材")
    # 官方：不支持 文本+音频、纯音频
    if audio_count and not (image_count + first_count + last_count + video_count):
        fail("官方不支持「文本+音频」或「纯音频」。请再加参考图/视频，或改走图生/参考任务。")
    return content


def cmd_generate(args: argparse.Namespace) -> None:
    if args.duration < 4 or args.duration > 15:
        fail("--duration 必须在 4–15 秒（Seedance 2.0）")
    client = make_client()
    content = build_content(args.prompt, args.image, args.video, args.audio_ref, client)
    payload = {
        "model": args.model,
        "content": content,
        "generate_audio": args.generate_audio,
        "ratio": args.ratio,
        "duration": args.duration,
        "resolution": args.resolution,
        "watermark": args.watermark,
        "return_last_frame": args.return_last_frame,
        "draft": args.draft,
        "service_tier": "flex" if args.flex else "default",
    }
    if args.seed is not None:
        payload["seed"] = args.seed
    if args.camera_fixed:
        payload["camera_fixed"] = True

    if args.dry_run:
        print_json({"ok": True, "dry_run": True, "payload": payload})
        return

    created = client.content_generation.tasks.create(**payload)
    task_id = created.id
    result = {"ok": True, "id": task_id, "status": getattr(created, "status", "queued")}
    if not args.wait:
        print_json(result)
        return

    task = poll_task(client, task_id, interval=args.interval, timeout=args.timeout)
    data = task_to_dict(task)
    video_url = (data.get("content") or {}).get("video_url")
    local_path = None
    if args.download and video_url:
        dest = Path(args.out).expanduser() if args.out else Path.cwd() / f"{task_id}.mp4"
        dest.parent.mkdir(parents=True, exist_ok=True)
        download_file(video_url, dest)
        local_path = str(dest)
    print_json(
        {
            "ok": data.get("status") == "succeeded",
            "id": task_id,
            "status": data.get("status"),
            "video_url": video_url,
            "last_frame_url": (data.get("content") or {}).get("last_frame_url"),
            "local_path": local_path,
            "error": data.get("error"),
            "duration": data.get("duration"),
            "ratio": data.get("ratio"),
            "resolution": data.get("resolution"),
            "revised_prompt": data.get("revised_prompt"),
        }
    )
    if data.get("status") != "succeeded":
        raise SystemExit(2)


def poll_task(client, task_id: str, interval: int, timeout: int):
    started = time.time()
    last_status = None
    while True:
        task = client.content_generation.tasks.get(task_id=task_id)
        status = task.status
        if status != last_status:
            print(f"[poll] {task_id} -> {status}", file=sys.stderr)
            last_status = status
        if status in {"succeeded", "failed", "cancelled", "expired"}:
            return task
        if time.time() - started > timeout:
            fail(f"轮询超时（{timeout}s），任务仍处于 {status}。可用 status 子命令继续查: {task_id}")
        time.sleep(interval)


def download_file(url: str, dest: Path) -> None:
    with urlopen(url) as response, dest.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 256)
            if not chunk:
                break
            handle.write(chunk)


def cmd_status(args: argparse.Namespace) -> None:
    client = make_client()
    task = client.content_generation.tasks.get(task_id=args.task_id)
    data = task_to_dict(task)
    if args.download:
        video_url = (data.get("content") or {}).get("video_url")
        if not video_url:
            fail("任务尚未成功或没有 video_url，无法下载")
        dest = Path(args.out).expanduser() if args.out else Path.cwd() / f"{args.task_id}.mp4"
        dest.parent.mkdir(parents=True, exist_ok=True)
        download_file(video_url, dest)
        data["local_path"] = str(dest)
    print_json({"ok": data.get("status") == "succeeded", **data})


def cmd_cancel(args: argparse.Namespace) -> None:
    client = make_client()
    client.content_generation.tasks.delete(args.task_id)
    print_json({"ok": True, "id": args.task_id, "action": "deleted"})


def cmd_upload(args: argparse.Namespace) -> None:
    path = Path(args.path).expanduser()
    client = make_client()
    asset_url = upload_local(client, path)
    print_json(
        {
            "ok": True,
            "path": str(path),
            "kind": guess_media_kind(path),
            "url": asset_url,
        }
    )


def cmd_doctor(_: argparse.Namespace) -> None:
    has_key = bool(os.environ.get("ARK_API_KEY", "").strip())
    keychain = False
    if sys.platform == "darwin":
        result = subprocess.run(
            ["security", "find-generic-password", "-a", os.environ.get("USER", ""), "-s", KEYCHAIN_SERVICE, "-w"],
            check=False,
            capture_output=True,
            text=True,
        )
        keychain = result.returncode == 0 and bool(result.stdout.strip())
        if result.returncode == 0:
            has_key = has_key or keychain
    sdk_ok = True
    sdk_error = None
    try:
        from volcenginesdkarkruntime import Ark  # noqa: F401
    except Exception as exc:  # pragma: no cover
        sdk_ok = False
        sdk_error = str(exc)
    print_json(
        {
            "ok": sdk_ok and has_key,
            "python": sys.executable,
            "sdk": sdk_ok,
            "sdk_error": sdk_error,
            "has_api_key": has_key,
            "keychain": keychain,
            "quickstart_python_exists": QUICKSTART_PYTHON.exists(),
            "recommended_python": str(QUICKSTART_PYTHON) if QUICKSTART_PYTHON.exists() else sys.executable,
            "model_default": DEFAULT_MODEL,
        }
    )
    if not (sdk_ok and has_key):
        raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seedance 2.0 官方 Ark SDK 封装")
    sub = parser.add_subparsers(dest="command", required=True)

    generate = sub.add_parser("generate", help="创建视频任务（默认同步轮询）")
    generate.add_argument("--prompt", required=True, help="提示词。编辑任务用「严格编辑视频1…」，参考任务用「参考图片1…」")
    generate.add_argument("--image", action="append", default=[], help="图片。可写 path/url，或 role=path。role: reference_image|first_frame|last_frame")
    generate.add_argument("--video", action="append", default=[], help="参考/待编辑视频。path/url，或 reference_video=path")
    generate.add_argument("--audio-ref", action="append", default=[], help="参考音频。path/url")
    generate.add_argument("--model", default=DEFAULT_MODEL, help="模型 ID，默认 doubao-seedance-2-0-260128")
    generate.add_argument("--ratio", default="16:9", choices=["21:9", "16:9", "4:3", "1:1", "3:4", "9:16"])
    generate.add_argument("--duration", type=int, default=5)
    generate.add_argument("--resolution", default="720p", choices=["480p", "720p", "1080p", "4k"])
    generate.add_argument("--generate-audio", dest="generate_audio", action="store_true", default=True)
    generate.add_argument("--no-audio", dest="generate_audio", action="store_false")
    generate.add_argument("--watermark", action="store_true", default=False)
    generate.add_argument("--no-watermark", dest="watermark", action="store_false")
    generate.add_argument("--draft", action="store_true", help="样片模式，更快更便宜，不要当交付")
    generate.add_argument("--flex", action="store_true", help="service_tier=flex，低优先级")
    generate.add_argument("--return-last-frame", action="store_true")
    generate.add_argument("--camera-fixed", action="store_true")
    generate.add_argument("--seed", type=int)
    generate.add_argument("--wait", action="store_true", default=True)
    generate.add_argument("--no-wait", dest="wait", action="store_false")
    generate.add_argument("--interval", type=int, default=15)
    generate.add_argument("--timeout", type=int, default=900)
    generate.add_argument("--download", action="store_true")
    generate.add_argument("--out", help="下载路径")
    generate.add_argument("--dry-run", action="store_true")
    generate.set_defaults(func=cmd_generate)

    status = sub.add_parser("status", help="查询任务")
    status.add_argument("task_id")
    status.add_argument("--download", action="store_true")
    status.add_argument("--out")
    status.set_defaults(func=cmd_status)

    cancel = sub.add_parser("cancel", help="取消或删除任务")
    cancel.add_argument("task_id")
    cancel.set_defaults(func=cmd_cancel)

    upload = sub.add_parser("upload", help="上传本地素材，返回 asset://ID")
    upload.add_argument("path")
    upload.set_defaults(func=cmd_upload)

    doctor = sub.add_parser("doctor", help="检查 SDK 与 API Key")
    doctor.set_defaults(func=cmd_doctor)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
