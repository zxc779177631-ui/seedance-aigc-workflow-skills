#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MaxForAI 通用视频提交器（maxforai-video-submit 技能配套）

用法示例:
  python3 submit.py --tier sd25 --model wf-sd2-5-720p \
      --prompt-file shot1.txt --ratio 9:16 --duration 10 --resolution 720p \
      --images https://ziyuai.vip/uploads/xxx.png \
      --video-url https://ziyuai.vip/uploads/xxx.mp4 \
      --audio-url https://ziyuai.vip/uploads/xxx.mp3 \
      --name G01-shot1 --outdir ./original

  # 本地素材自动上传
  python3 submit.py --tier sd20-ft --model 特价ft-sd2.0fast \
      --prompt "@image1 保持人物" --ratio 9:16 --duration 5 \
      --images /tmp/a.png --name test

铁律：本脚本不替你做成本确认。执行前必须先报账并拿到用户 OK。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://maxforai.top/v1"
KEYCHAIN = {
    "sd25": "seedance-workflow-maxforai-sd25",
    "sd20-zy": "seedance-workflow-maxforai-sd20-zy",
    "sd20-ft": "seedance-workflow-maxforai-sd20-ft",
}
ENV_KEY = {
    "sd25": "MAXFORAI_SD25_KEY",
    "sd20-zy": "MAXFORAI_SD20_ZY_KEY",
    "sd20-ft": "MAXFORAI_SD20_FT_KEY",
}


def get_key(tier: str) -> str:
    env_name = ENV_KEY[tier]
    if os.environ.get(env_name):
        return os.environ[env_name].strip()
    svc = KEYCHAIN[tier]
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-a", os.environ.get("USER", ""),
             "-s", svc, "-w"],
            capture_output=True, text=True, timeout=20,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    raise SystemExit(f"未取到 MaxForAI key（钥匙串 {svc} 或 env {env_name}）")


def opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def req(key: str, method: str, path: str, payload=None, raw=False, timeout=180, retries=3):
    headers = {"Authorization": "Bearer " + key}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    last_err = None
    for attempt in range(1, retries + 1):
        r = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
        try:
            with opener().open(r, timeout=timeout) as resp:
                body = resp.read()
                if raw:
                    return body, resp.headers
                return json.loads(body.decode("utf-8"))
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", "replace")[:800]
            raise SystemExit(f"HTTP {e.code} {method} {path}: {err}")
        except (urllib.error.URLError, TimeoutError, ConnectionResetError, BrokenPipeError) as e:
            last_err = e
            print(f"[retry {attempt}/{retries}] {method} {path}: {e}")
            time.sleep(2 * attempt)
    raise SystemExit(f"网络失败 {method} {path}: {last_err}")


def upload_local(key: str, path: str) -> str:
    import uuid
    boundary = "----maxforai" + uuid.uuid4().hex
    raw = Path(path).read_bytes()
    name = os.path.basename(path)
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    tail = f"\r\n--{boundary}--\r\n".encode()
    body = head + raw + tail
    headers = {
        "Authorization": "Bearer " + key,
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    r = urllib.request.Request(BASE + "/assets", data=body, headers=headers, method="POST")
    with opener().open(r, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    url = data.get("url")
    if not url:
        raise SystemExit("上传失败: " + json.dumps(data, ensure_ascii=False)[:400])
    print("[upload]", name, "->", url)
    return url


def transfer_url(key: str, url: str, file_name: str) -> str:
    data = req(key, "POST", "/assets/url", {"url": url, "file_name": file_name})
    out = data.get("url")
    if not out:
        raise SystemExit("转存失败: " + json.dumps(data, ensure_ascii=False)[:400])
    print("[transfer]", url, "->", out)
    return out


def resolve_spec(key: str, spec: str, transfer_https: bool) -> str:
    if spec.startswith("http://") or spec.startswith("https://"):
        if transfer_https:
            return transfer_url(key, spec, os.path.basename(spec.split("?")[0]) or "asset.bin")
        return spec
    return upload_local(key, spec)


def list_models(key: str):
    data = req(key, "GET", "/models")
    models = data.get("data") or data.get("models") or data
    if isinstance(models, dict):
        models = models.get("data") or models.get("models") or []
    ids = []
    if isinstance(models, list):
        for m in models:
            if isinstance(m, dict):
                ids.append(str(m.get("id") or m.get("name") or m.get("model")))
            else:
                ids.append(str(m))
    return ids


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tier", required=True, choices=["sd25", "sd20-zy", "sd20-ft"])
    p.add_argument("--model", required=True)
    p.add_argument("--prompt")
    p.add_argument("--prompt-file")
    p.add_argument("--ratio", default="9:16")
    p.add_argument("--duration", default="10")
    p.add_argument("--resolution", default="720p")
    p.add_argument("--images", nargs="*", default=[])
    p.add_argument("--videos", nargs="*", default=[])
    p.add_argument("--audios", nargs="*", default=[])
    p.add_argument("--video-url", action="append", default=[])
    p.add_argument("--audio-url", action="append", default=[])
    p.add_argument("--transfer", action="store_true", help="公网 HTTPS 也先转存到 MaxForAI")
    p.add_argument("--name", default="maxforai_out")
    p.add_argument("--outdir", default=".")
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("--poll", type=int, default=15)
    p.add_argument("--list-models", action="store_true")
    args = p.parse_args()

    key = get_key(args.tier)
    print("[KEY_PREFIX]", key[:8])

    ids = list_models(key)
    print("[models]", ", ".join(ids) or "(empty)")
    if args.list_models:
        return
    if args.model not in ids:
        print(f"[WARN] 模型 {args.model} 不在该 Key 当前清单里：{ids}", file=sys.stderr)

    prompt = args.prompt
    if not prompt and args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    if not prompt:
        raise SystemExit("需要 --prompt 或 --prompt-file")

    images = [resolve_spec(key, s, args.transfer) for s in args.images]
    videos = [resolve_spec(key, s, args.transfer) for s in (args.videos + args.video_url)]
    audios = [resolve_spec(key, s, args.transfer) for s in (args.audios + args.audio_url)]

    payload = {"model": args.model, "prompt": prompt}
    # 渠道字段分流
    if args.model.startswith("特价ft-"):
        payload["ratio"] = args.ratio
        payload["duration"] = int(args.duration)
        payload["resolution"] = args.resolution
    elif args.model == "zy-特价豆包900":
        payload["aspect_ratio"] = args.ratio
        payload["duration"] = str(args.duration)
        payload["resolution"] = args.resolution
    else:
        payload["aspect_ratio"] = args.ratio
        payload["duration"] = int(args.duration)
        payload["resolution"] = args.resolution
    if images:
        payload["images"] = images
    if videos:
        payload["videos"] = videos
    if audios:
        payload["audios"] = audios

    print("[提交]", json.dumps({k: (v if k != "prompt" else v[:80] + "...") for k, v in payload.items()},
                              ensure_ascii=False))
    created = req(key, "POST", "/videos", payload)
    task_id = created.get("task_id") or created.get("id")
    if not task_id:
        raise SystemExit("创建失败: " + json.dumps(created, ensure_ascii=False)[:600])
    print("[TASK_ID]", task_id, "status=", created.get("status"))

    deadline = time.time() + args.timeout
    job = created
    while time.time() < deadline:
        job = req(key, "GET", f"/videos/{task_id}")
        status = (job.get("status") or "").lower()
        print(f"[status] {status} progress={job.get('progress')}")
        if status in {"completed", "succeeded", "success", "failed", "error", "cancelled", "canceled"}:
            break
        time.sleep(args.poll)
    else:
        raise SystemExit("轮询超时: " + json.dumps(job, ensure_ascii=False)[:600])

    if (job.get("status") or "").lower() not in {"completed", "succeeded", "success"}:
        raise SystemExit("任务失败: " + json.dumps(job, ensure_ascii=False)[:800])

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    out_path = outdir / f"{args.name}.mp4"
    body, headers = req(key, "GET", f"/videos/{task_id}/content", raw=True, timeout=180)
    out_path.write_bytes(body)
    print("[downloaded]", out_path, f"{len(body)} bytes", "ctype=", headers.get("Content-Type"))


if __name__ == "__main__":
    main()
