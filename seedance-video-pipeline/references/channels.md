# 通道选型与命令模板（seedance-video-pipeline 参考）

> 本表为决策速查 + 命令骨架。各通道的**最新档位、字段、脚本路径以专项 skill 的 SKILL.md 为准**，因为它们随平台漂移。

## 0 · 通用前置

- 钥匙串取密钥（绝不入库）：
  - 紫域：`security find-generic-password -a $USER -s seedance-workflow-ziyu -w`
  - MaxForAI sd25：`... -s seedance-workflow-maxforai-sd25 -w`（另 `-sd20-zy` / `-sd20-ft`）
  - Ark：`. ~/.zshrc.ark`（source，不能 cat 整行）
- 计费换算：紫域 **100 点 = 1 元**。

## 1 · 紫域 AI（ziyuai.vip）

- 提交：`POST /api/v1/jobs`，modelId 从 `GET /api/v1/models` 实拉。
- 本地图先 `POST /api/v1/uploads`（复数）拿公网 URL，再放进 `assets.image`。
- 音频：`assets.audio` 收公网 mp3 URL（不要 .m4a）。
- 常用档（2026-08-26 快照，⚠️会漂移）：
  - 2.5 720p 15s 带音频：`zy_model_beb4bdb66a86f1fc42c7`（600/次）
  - 2.5 720p 按秒带音频：`zy_model_2bf90606d3250d5026ce`（60/秒，4–30s）
  - 2.5 720p 挂表演视频：`zy_model_85b5f6490c0952cc3f68`（1000/次，仅 20–30s）
- 委派：`ziyu-video-submit` 的 `scripts/submit.py`（或项目内提交脚本）。

## 2 · 火山 Ark（ark.cn-beijing.volces.com）

- 提交：`POST /api/v3/contents/generations/tasks`
- `role` 必须用 `reference_image` / `reference_video` / `reference_audio`（非 image/video）。
- `duration` 取整数（13.3 → 13）。
- 模型：`doubao-seedance-2-0-260128` / `2-5-260628`。
- 委派：`seedance-ark-submit` / `seedance-2-0-ark`。

## 3 · MaxForAI（maxforai.top）

- 3 把 Key 分模型组（不是站点通用 pass）：
  - `seedance-workflow-maxforai-sd25` → `wf-sd2-5-720p`（2.5，≈¥0.30/秒）
  - `...-sd20-zy` → `zy-SD满血933` / `zy-特价豆包900`
  - `...-sd20-ft` → `特价ft-sd2.0fast` / `特价ft-sd2.0满血`
- 提交：`POST /v1/videos`；轮询 `GET /v1/videos/{id}`；下载 `GET /v1/videos/{id}/content`。
- 素材：紫域/TOS 公网 URL 一律先 `--transfer` 转存（`/v1/assets/url`）；本地文件 `POST /v1/assets`；**不需要 TOS**。
- 委派：`maxforai-video-submit` 的 `scripts/submit.py --tier sd25 --transfer`。

## 决策口诀

> 要 2.5 带音频默认紫域；要便宜 2.0 看紫域2.0/Ark/MaxForAI sd20；要按秒 2.5 可走 MaxForAI 但转存；要 Ark 专属能力走 Ark。
> 提交前报账、留 task_id、断线先查后台再重提。
