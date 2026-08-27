#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""紫域 AI 通用视频提交器（ziyu-video-submit 技能配套）

用法示例:
  # 公网 URL 直传，i2v，4秒，最便宜 h3 档
  python3 submit.py --model zy_model_2134621044047793db22 \
      --prompt-file shot1.txt --ratio 16:9 --duration "4秒" \
      --images "https://ziyuai.vip/uploads/asset_upload_xxx.png" \
      --name xianxia-shot1

  # 本地图自动上传再提交
  python3 submit.py --prompt "..." --images /tmp/a.png /tmp/b.png --name test

参数:
  --model     模型 ID（默认 h3 最便宜档 zy_model_2134621044047793db22）
  --mode      i2v / t2v / t2i（默认 i2v）
  --prompt    提示词文本（与 --prompt-file 二选一，prompt 优先）
  --prompt-file  提示词文件路径
  --ratio     16:9 / 9:16（默认 16:9）
  --duration  中文串，如 "4秒" / "13秒"（默认 "4秒"）
  --images    空格分隔：本地路径自动上传，URL 直传
  --video-url 可选参考视频 URL
  --audio-url 可选参考音频 URL
  --name      输出文件名（不含扩展名，默认 ziyu_out）
  --outdir    输出目录（默认当前目录）
  --timeout   单条轮询总时长（秒，默认 1500）

key 从 macOS 钥匙串 seedance-workflow-ziyu 读取。
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

ZIYU_BASE = "https://ziyuai.vip"
KEYCHAIN_SVC = "seedance-workflow-ziyu"
DEFAULT_MODEL = "zy_model_2134621044047793db22"   # h3 最便宜档


def get_key():
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-a", os.environ.get("USER", ""),
             "-s", KEYCHAIN_SVC, "-w"],
            capture_output=True, text=True, timeout=20)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return os.environ.get("ZIYUAI_API_KEY", "")


def _req(key, method, path, payload=None):
    headers = {"Authorization": "Bearer " + key}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(ZIYU_BASE + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))


def upload_image(key, path):
    raw = open(path, "rb").read()
    b64 = "data:image/png;base64," + base64.b64encode(raw).decode()
    payload = {"files": [{"type": "image", "name": os.path.basename(path), "data": b64}]}
    resp = _req(key, "POST", "/api/v1/uploads", payload)
    assets = resp.get("assets") or resp.get("data") or []
    if isinstance(assets, list) and assets:
        return assets[0].get("url") or assets[0].get("fileUrl")
    raise SystemExit("上传失败，响应: " + json.dumps(resp, ensure_ascii=False)[:300])


def resolve_images(key, specs):
    urls = []
    for s in specs:
        if s.startswith("http://") or s.startswith("https://"):
            urls.append(s)
        elif os.path.exists(s):
            urls.append(upload_image(key, s))
        else:
            raise SystemExit("图片找不到也不是 URL: " + s)
    return urls


def submit_and_wait(key, args, image_urls, prompt, outdir):
    payload = {
        "modelId": args.model,
        "mode": args.mode,
        "prompt": prompt,
        "ratio": args.ratio,
        "duration": args.duration,
        "assets": {
            "image": [{"url": u} for u in image_urls],
            "video": [{"url": args.video_url}] if args.video_url else [],
            "audio": [{"url": args.audio_url}] if args.audio_url else [],
        },
    }
    print("[提交] model=%s mode=%s dur=%s imgs=%d" % (args.model, args.mode, args.duration, len(image_urls)))
    resp = _req(key, "POST", "/api/v1/jobs", payload)
    job = resp.get("job") or resp
    job_id = job.get("jobId") or job.get("id") or resp.get("jobId")
    if not job_id:
        raise SystemExit("未返回 jobId: " + json.dumps(resp, ensure_ascii=False)[:500])
    print("[JOB_ID] %s" % job_id)

    deadline = time.time() + args.timeout
    last = ""
    while time.time() < deadline:
        data = _req(key, "GET", "/api/v1/jobs/%s" % job_id)
        job = data.get("job") or data
        st = job.get("status", "processing")
        if st != last:
            print("[status] %s" % st)
            last = st
        if st == "completed":
            url = job.get("previewUrl")
            if not url:
                raise SystemExit("完成但无 previewUrl")
            req = urllib.request.Request(url, headers={"Authorization": "Bearer " + key})
            with urllib.request.urlopen(req, timeout=300) as r:
                video = r.read()
            outp = os.path.join(outdir, args.name + ".mp4")
            open(outp, "wb").write(video)
            print("[下载完成] %s  (%d KB)" % (outp, len(video) // 1024))
            return True
        if st == "failed":
            raise SystemExit("生成失败: " + json.dumps(job, ensure_ascii=False)[:600])
        time.sleep(8)
    raise SystemExit("轮询超时")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--mode", default="i2v")
    ap.add_argument("--prompt", default=None)
    ap.add_argument("--prompt-file", default=None)
    ap.add_argument("--ratio", default="16:9")
    ap.add_argument("--duration", default="4秒")
    ap.add_argument("--images", nargs="*", default=[])
    ap.add_argument("--video-url", default=None)
    ap.add_argument("--audio-url", default=None)
    ap.add_argument("--name", default="ziyu_out")
    ap.add_argument("--outdir", default=os.getcwd())
    ap.add_argument("--timeout", type=int, default=1500)
    args = ap.parse_args()

    if args.prompt:
        prompt = args.prompt
    elif args.prompt_file:
        prompt = open(args.prompt_file, encoding="utf-8").read().strip()
    else:
        raise SystemExit("需提供 --prompt 或 --prompt-file")

    key = get_key()
    if not key:
        raise SystemExit("未取到紫域 key（钥匙串 %s 或 env ZIYUAI_API_KEY）" % KEYCHAIN_SVC)
    print("[KEY_PREFIX] %s" % key[:8])

    os.makedirs(args.outdir, exist_ok=True)
    image_urls = resolve_images(key, args.images)
    submit_and_wait(key, args, image_urls, prompt, args.outdir)


if __name__ == "__main__":
    main()
