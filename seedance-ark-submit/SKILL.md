---
name: seedance-ark-submit
description: "通过火山方舟（Volcengine Ark）API 提交 Seedance 2.0 数字人口播视频生成任务并轮询下载成片。覆盖：密钥加载（~/.zshrc.ark 是 export 语句，必须 source）、请求体 schema（content 数组 + reference_image/video/audio 角色）、提交端点、轮询与下载、账号/模型开通坑。当用户要『提交并轮询』数字人视频、用火山 Ark 跑 Seedance、或说『另一窗口写好提示词，你这边只提交轮训』时触发。"
---

# 火山方舟 Seedance 提交 + 轮询

用于把数字人口播视频任务提交到 Volcengine Ark 的 `doubao-seedance-2-0-260128`（或兼容模型），并轮询直到成片可下载。

## 0. 密钥加载（必看，坑过两次）
密钥在 `~/.zshrc.ark`，内容是整条语句：`export ARK_API_KEY=ark-xxxxxxxx`（不是裸 key）。
- ❌ 错误：`export ARK_API_KEY="$(cat ~/.zshrc.ark)"` → 会把 `export ARK_API_KEY=ark-...` 整行当值，导致 401。
- ✅ 正确：`source ~/.zshrc.ark`（同 shell 内 ARK_API_KEY 即生效）；或在 Python 里 `KEY = open('~/.zshrc.ark').read().split('=',1)[1].strip()`。
- 注意 `~/.zshrc` 第 8 行有 `unset ARK_API_KEY`，所以每次新 shell 都要重新 source。

## 1. 提交端点
```
POST https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks
Header: Authorization: Bearer $ARK_API_KEY, Content-Type: application/json
```

## 2. 请求体 schema（已用 7 月 payload 与今日 v09 验证）
```json
{
  "model": "doubao-seedance-2-0-260128",
  "content": [
    {"type": "text", "text": "提示词原文（不要再写分辨率/720P）"},
    {"type": "image_url", "image_url": {"url": "asset://asset-xxxx 或 公网URL"}, "role": "reference_image"},
    {"type": "video_url", "video_url": {"url": "asset://..."}, "role": "reference_video"},
    {"type": "audio_url", "audio_url": {"url": "asset://..."}, "role": "reference_audio"}
  ],
  "generate_audio": true,
  "ratio": "9:16",
  "resolution": "480p",
  "duration": 15,
  "watermark": false
}
```
- `content` 顺序：text 在前，参考按「图片1→N、视频1、音频1」顺序，编号须与提示词一致。
- 参考材质：本账号资产用 `asset://asset-<id>`；公网图可用 `https://...tos-cn-beijing.volces.com/...` 形式（提交前 `curl -I` 验 200/206 + image/png）。
- 白描/深度景别图（控景别用）按需求可删，只挂角色/场景/道具/表演/声线类。

## 3. 轮询 + 下载
```
GET https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/{task_id}
```
- 提交返回 `{"id":"cgt-2026xxxx-xxxx"}` 即 task_id。
- 状态：`queued`/`running` → `succeeded`/`failed`。Seedance 2.0 ≈ 1.83s/秒视频，15s 约 6 分钟。
- 成功响应结构：`{"status":"succeeded","content":{"video_url":"https://ark-acg-cn-beijing.tos-cn-beijing.volces.com/...mp4?签名"}}`（注意：部分返回包在 `data` 下，字段路径不定）。**下载取 URL 必须用 JSON 字段提取，不要正则**：递归遍历响应 dict 找第一个 `http*.mp4` 字符串值（如 `content.video_url.url` / `content.video_url` / `data.content.video_url` 等），再用该 URL GET 下载并带 `Authorization: Bearer $ARK_API_KEY`（TOS 签名链接有时限，约 24h）。⚠️ 踩坑记录：曾用 `re.search(r'https?://[^\s"\\]+\.mp4', json_str)` 提取 mp4 URL，在 Ark 返回下抛 `unterminated character set` 异常，导致轮询脚本全程 0 下载。一律改用递归字段提取。
- 成片校验：`ffprobe` 看 width/height（9:16 应为 ~496×864）、duration≈提交值、codec=h264。

## 4. 账号 / 模型开通坑（重要）
- `GET /api/v3/models` 返回的是**平台全量模型目录（含已下架）**，**不等于你的账号已开通**。判断开通只能看提交返回。
- `ModelNotOpen` 错误 = Key 所属账号未开通该模型。常见根因：**Key 的账号 ≠ 你在控制台开通模型的账号**（本机曾因 2104063304 vs 2105663059 不匹配连续失败）。
- 模型用 `doubao-seedance-2-0-260128`（模型服务，非 ep- 接入点）。换"更便宜模型"前先确认该账号已开通，否则直接 ModelNotOpen。
- `asset://` 引用需 Key 所属账号能访问对应资产；公网 TOS 图需可 200/206。

## 5. 本机已有资产（韩世浩/Johnny 项目，G01）
- 图片1（人物）`asset-20260811170446-cb4wq`
- 书房正/书房30/画：`https://drhon.tos-cn-beijing.volces.com/.../part1 书房正.png` 等（200 可读取）
- 视频1（表演）`asset-20260810153251-89g96`
- 音频1（声线）`asset-20260709101714-8xpwz`
- 项目目录：`~/Movies/seedance-workflow/0015-韩世浩-Part1-G01-火山480p-v02/`（含 submit_*.py / poll_*.py / *-payload.json 留底）

## 6. 提交前 5 项自检
1. 密钥 source 注入、Ark models 返回 200
2. 参考顺序与提示词编号一致
3. 无多余白描/深度景别图（**2.0 默认绝对禁止**；2.5 精修轨可按需）
4. 分辨率只在 API 参数，不在提示词
5. 公网 TOS 图 curl -I 验 200/206 + MIME

## 7. 2.0 / 2.5 垫图与工作流分流（Part1 实测，必读）

体感铁律（用户 2026-08-12 确认）：

| | Seedance **2.0** | Seedance **2.5** |
|---|---|---|
| 参考行为 | **上传即强吸收**。写「只参考构图」也常把比例、线稿、**左上角序号**、标注吸进成片 | 更能只取构图意图，脏层污染明显弱于 2.0 |
| 默认分辨率 | **480p 通结构** | **720p 精修**（结构过后再跑） |
| 白描 / 深度 / 分镜板 | **默认不挂**；控景别用文字 | 可按 QA 短板垫，提示词写清「只借…」 |
| 净参考（身份/场景/道具/画/表演/声线） | 可挂 | 可挂 |

生产流：
1. `doubao-seedance-2-0-260128` + 480p → 验连戏/切镜/身份/口型/道具
2. 结构 OK 后 → `doubao-seedance-2-5-260628`（以开通为准）+ 720p → 按需垫构图图

提示词通用（两轨）：
- 不写分辨率字样；少否定少重复；秒轴可保留；口播写肢体与「保持姿势」
- 每张图一句功能角色；旁白条不上传 VO
- 2.0 payload 宁可少图，不可脏图
