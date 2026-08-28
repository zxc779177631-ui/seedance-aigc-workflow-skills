---
name: maxforai-video-submit
description: 把 Seedance 视频任务提交到 MaxForAI（maxforai.top）——3 把分模型组 Key、素材上传/转存、POST /v1/videos 创建、轮询、下载成片。当用户说"提交到 MaxForAI / maxforai / 晚风 2.5 / wf-sd2-5 / 特价 ft-sd2.0 / zy-SD满血933"时使用。
version: 1.0.4
agent_created: true
---

# MaxForAI 视频提交技能

## 一句话定位

MaxForAI（`https://maxforai.top`）是**第三条 Seedance 提交通道**，与火山方舟 Ark、紫域 AI（`ziyuai.vip`）并存。协议偏 OpenAI 风格：`POST /v1/videos` 创建、`GET /v1/videos/{id}` 轮询、`GET /v1/videos/{id}/content` 下载。**3 把 Key 不是通用的**，每把只能打自己那一组模型。

⚠️ **`zy` 撞名，不是一家**：本通道有一组模型叫 `zy-SD满血933` / `zy-特价豆包900`，钥匙串也叫 `-sd20-zy`——**只是模型名碰巧带 zy**。紫域是另一个平台（`ziyuai.vip`，钥匙串 `seedance-workflow-ziyu`，模型 `zy_model_*`）。**禁止**把 MaxForAI 的 zy-SD 叫「紫域档」，也**禁止**拿紫域 key / `/api/v1/jobs` 去打这些模型。

官方文档：https://maxforai.top/docs（SPA）。机器可读全文：https://maxforai.top/llms.txt

## 何时用

- 用户说"走 MaxForAI / maxforai / 晚风 2.5 / wf-sd2-5 / 特价 ft / 满血933"
- Ark 欠费或紫域档位不稳，想换通道试同一条 Seedance
- ⚠️ 与 Ark / 紫域的模型 ID、字段名、时长类型都不同，**不要混用请求体**

## 鉴权（铁律）

3 把 Key 在 **macOS 钥匙串**，禁止写进前端、仓库、对话回显明文。

| 用途 | 钥匙串 service | 该 Key 能打的模型（2026-08-28 实拉） |
|---|---|---|
| SD 2.5 | `seedance-workflow-maxforai-sd25` | **`sd25-30s`**（固定 30s / 720p / ¥5.8/条 / 视频≤3 / **无音频参考**）；另有 sd2-933-720p / seedance2.0-720p / seedance2.0-fast-480p / seedance2.0-fast-720p / wan3.0th |
| SD 2.0 zy-SD 组（**不是紫域**） | `seedance-workflow-maxforai-sd20-zy` | `zy-SD满血933`、`zy-特价豆包900`、`zy-image-2`、`zy-image-2-4K` |
| SD 2.0 特价档 | `seedance-workflow-maxforai-sd20-ft` | `特价ft-sd2.0fast`、`特价ft-sd2.0满血` |
| **auto 总控（全量）** | 不存钥匙串（用户口头给，2026-08-28）：`sk-c48gVC3Fqu2n1OwPzpXb9pG4pFG7cEsjRh4lnZB7HEMh1j4A` | **全量 39 模型**：`mg-seedance-2.5` / `wan3.0th` / `dq-sd933-pro-face` / `特价sd2.5 满血720p` / `sd25-30s` 等，自动切接口分组 |

```bash
security find-generic-password -a $USER -s seedance-workflow-maxforai-sd25 -w
security find-generic-password -a $USER -s seedance-workflow-maxforai-sd20-zy -w
security find-generic-password -a $USER -s seedance-workflow-maxforai-sd20-ft -w
```

- 提交前必须 `GET /v1/models`（带对应 Key）核对：**Key 对不上模型会直接 401/无权限/`insufficient user quota`（分组权限问题，不是余额），不是"清单里没这个模型"**。分 Key 报 quota 错误 → 先换 auto key 试。
- 同一套文档里还有 `mg-seedance-2.5`、官方 `sd-*` 等，**3 把分组 Key 打不到**，只有 **auto key 能打**（2026-08-28 验证：auto key 拉清单 39 个模型、wan3.0th / mg-seedance-2.5 提交均成功）。

## 标准提交流程

> ⛔ **【成本确认铁律】任何付费提交前，必须先把成本清单报给用户并等明确 OK。**
> 格式：`通道 MaxForAI + 模型 + 单价 × 秒数或条数 = 预估总花费（人民币）`

0. **选 Key**：2.5 → sd25；MaxForAI 自家 `zy-SD*` / 特价豆包 / 生图 → sd20-zy（仍是 MaxForAI，不是紫域）；ft-sd2.0 → sd20-ft。
1. **实拉拉清单**：`GET https://maxforai.top/v1/models`，确认该 Key 当前还能打目标模型。
2. **报账等确认**。文档价只是快照，以模型广场/订单为准。
3. **素材**：本地文件 `POST /v1/assets`（multipart `file`）；已有公网 HTTPS 一律 `POST /v1/assets/url` 转存（脚本加 `--transfer`）。不接受本地路径、`file://`、内网 URL。⚠️ **紫域 `ziyuai.vip/uploads/...` 不要直传**：G01 镜头二首测 raw 紫域 URL 上游 `generation failed`；`--transfer` 到 `tempfile.redpandaai.co` 后同参数成功。TOS 不需要。
4. **提交** `POST /v1/videos`。
5. **轮询** `GET /v1/videos/{task_id}`：`queued` → `in_progress`/`processing` → `completed` / `failed`。
6. **下载** `GET /v1/videos/{task_id}/content`（带 Bearer）。多数模型也可读 `metadata.url`；官方 `sd-*` 读 `result_url`。

配套脚本：`scripts/submit.py`（本技能目录）。

## 接口速查

Base URL：`https://maxforai.top/v1`  
Auth：`Authorization: Bearer <KEY>`

| 动作 | 方法 + 路径 |
|---|---|
| 列模型 | `GET /v1/models` |
| 本地上传 | `POST /v1/assets` multipart `file`（图/视频/音频） |
| 公网转存 | `POST /v1/assets/url` `{"url","file_name"}` |
| 创建视频 | `POST /v1/videos` |
| 查任务 | `GET /v1/videos/{task_id}` |
| 下载成片 | `GET /v1/videos/{task_id}/content` |

上传成功从顶层读 `url`：

```json
{"object":"asset","url":"https://cdn.example.com/temporary-file.png","file_name":"reference.png","media_type":"image","temporary":true}
```

## 本机三档请求体（已核对 Key 权限）

### 2.5 · `sd25-30s`（Key: sd25，2026-08-28 实拉，替代已下架的 `wf-sd2-5-720p`）

- 计费：**¥5.8/条**，固定 **30 秒** / 720p；比例含 `9:16`
- 参考：images 1–30 张、videos ≤3、**不支持参考音频 / 首尾帧**（有对白要 005 音色的条走 Ark 或紫域）
- 字段：`model` + `aspect_ratio` + `prompt` + `images`/`videos`（无 audios）

```json
{
  "model": "sd25-30s",
  "aspect_ratio": "9:16",
  "prompt": "...",
  "images": ["https://...png"],
  "videos": ["https://...mp4"]
}
```

- 一条 30s 无对白（如 Scene2 GU-03/06）≈ **¥5.8**。比紫域 2.5 挂视频档（¥10，且已下架）更便宜。
- ⚠️ 紫域 `ziyuai.vip/uploads/...` URL 不要直传，先 `POST /v1/assets/url` 转存。

### 2.5 全能力 · `mg-seedance-2.5`（auto key 专属，2026-08-28 实拉）

> 唯一"真 2.5 + 不卡真人 + 视频/音频全支持 + 时长 4–30s 任意"的档；auto key 才打得到。

- upstream: `seedance-2-5`（官方同源）；分辨率 480p / 720p；images ≤30 / videos ≤10 / audios ≤10
- 定价（按秒 × duration）：
  - **480p**：无视频 ¥0.39/s（30s=¥11.7）；含视频 ¥0.54/s（30s=¥16.2）
  - **720p**：无视频 ¥0.75/s（30s=¥22.5）；含视频 ¥1.2/s（30s=¥36）
- **vs 火山方舟官方**（官方 2026-08 标价：480p ¥0.67/s、720p ¥1.51/s，均 5s 16:9 无视频口径；含视频另按 42 元/百万 Token 计且输入越长越贵）：
  - 无视频 ≈ **官方 5–6 折**（480p ¥0.39/0.67≈58%；720p ¥0.75/1.51≈50%）
  - 含视频固定秒价，官方同场景会随输入视频时长暴涨（官方 720p 含视频 5s 输出即 ¥8.16~31.75）→ **折扣更大，量越长越划算**
- 结论：**MaxForAI 的 2.5 不是官方原价，是无视频 5~6 折、含视频低至 2 折起的渠道价**；`sd25-30s`（¥5.8/30s≈¥0.19/s）与 `特价sd2.5 满血720p`（¥4.5/30s≈¥0.15/s）更便宜但分别卡真人/不支持真人，只适合非真人条。

### 2.0 zy-SD 组 · `zy-SD满血933` / `zy-特价豆包900`（Key: sd20-zy）

> 名称带 zy ≠ 紫域。走 `maxforai.top/v1/videos` + 本把 Key，不要碰 `ziyuai.vip`。

- `zy-SD满血933`：**¥4.2/条**，固定 15 秒 720p，9 图 / 3 视频 / 3 音频
- `zy-特价豆包900`：**¥1/次**，仅图生视频（必须 1–9 图），`duration` 是 **string**，无视频/音频

```json
{
  "model": "zy-SD满血933",
  "aspect_ratio": "9:16",
  "duration": 15,
  "prompt": "...",
  "resolution": "720p",
  "images": ["https://...png"],
  "videos": ["https://...mp4"],
  "audios": ["https://...mp3"]
}
```

### 2.0 特价档 · `特价ft-sd2.0fast` / `特价ft-sd2.0满血`（Key: sd20-ft）

- 比例字段是 **`ratio`（不是 aspect_ratio）**
- prompt 用 `@imageN` / `@videoN` / `@audioN` 引用数组序
- 默认文档：`ratio=9:16`，`duration=15`，`resolution=480p`
- 文档价（按秒；含视频参考更贵）：

| 模型 | 480p 无/有视频 | 720p 无/有视频 |
|---|---|---|
| `特价ft-sd2.0fast` | ¥0.11 / ¥0.13 | ¥0.15 / ¥0.22 |
| `特价ft-sd2.0满血` | ¥0.14 / ¥0.18 | ¥0.18 / ¥0.28 |

```json
{
  "model": "特价ft-sd2.0fast",
  "prompt": "@image1 保持人物特征，参考 @audio1 声线",
  "duration": 10,
  "ratio": "9:16",
  "resolution": "720p",
  "images": ["https://...png"],
  "audios": ["https://...mp3"]
}
```

## 渠道字段差异（必看）

| 渠道 | 时长 | 比例 | 素材 | 结果 |
|---|---|---|---|---|
| `wf-sd2-5-720p` / zy-SD933 | `duration` int | `aspect_ratio` | `images/videos/audios` | `metadata.url` 或 `/content` |
| `zy-特价豆包900` | `duration` **string** | `aspect_ratio` | 仅 `images` | `result_url`/`video_url`/`url` |
| `特价ft-sd2.0*` | `duration` int | **`ratio`** | 同上 + prompt `@imageN` | `metadata.url` |
| 文档里的官方 `sd-*`（本机 Key 暂无） | **`seconds` string** | **`ratio`** | + `generate_audio` | `result_url` |

## 坑

- **Key ≠ 全站通行证**。2.5 Key 只能打 `wf-sd2-5-720p`；拿它去打 `特价ft-sd2.0fast` 必失败。
- 参考音频优先 **mp3**（紫域已验证 m4a 容器会被拒；MaxForAI 上游同类模型建议直接 mp3）。
- 素材必须公网 HTTPS；**紫域 / TOS 一律先 `--transfer`**，不要赌上游能拉第三方。TOS 本通道不需要。
- 参考音频优先按镜头切到 ≤ 输出时长的 mp3（G01 镜头二 5.3s 配 5s 输出）。失败原因不是“超过 10 秒硬拒”——首测用的是 10.01s 镜头一声，不是超限拦截。
- 2.0 / 2.5 提示词不能互相套用。
- 提交前参数校验失败不扣费；提交上游后的退款以订单为准。
- 文档价会变，**调用前实拉 `/v1/models` + 问用户确认**。广场实扣可能高于文档（G01 镜头二两单合计用户看到约 ¥5，文档 2×¥1.50=¥3）。
- **没有任务列表/账单 API**（`GET /v1/videos`、`/orders`、`/billing` 均 404）。提交成功必须立刻记下 `task_id` + `created_at`，否则无法对账、也无法找回叠交的那单。
- 会话中断后**禁止再起一条 submit**：G01 镜头二 14:32 成功单之外，用户后台还有 14:34 一单，本地无 ID，极像断线续跑叠交。先查已有 task / 问用户后台，确认没有进行中的同参数任务再提。
