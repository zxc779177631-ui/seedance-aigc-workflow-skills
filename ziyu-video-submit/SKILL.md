---
name: ziyu-video-submit
description: 把 Seedance 文/图/视频生视频任务提交到紫域 AI（ziyuai.vip）——上传参考图、提交 i2v/t2v/t2i 任务、轮询并下载成片。覆盖 macOS 钥匙串鉴权、模型清单、最便宜档 h3、常见坑（模型维护/时长中文格式/不支持 asset://）。当用户说"提交到紫域/ziyu""用 h3 跑""紫域最便宜档""换紫域通道"时使用。
version: 1.2.1
---

# 紫域 AI 视频提交技能

## 一句话定位

紫域 AI（`https://ziyuai.vip`）是**独立的 Seedance 视频提交通道**（不是图床）。本技能负责把文/图/视频生视频任务提交上去、轮询状态、下载成片。与火山方舟 Ark 是**两条并存通道**，互不通用。

## 何时用本技能

- 用户说"提交到紫域 / ziyu / 用 h3 / 紫域最便宜档 / 换紫域通道"
- 需要跑 Seedance 但不走火山方舟 Ark（例如 Ark 没货、或想用紫域不排队档）
- ⚠️ 紫域与 Ark 的提示词、模型 ID、时长格式都不同，**不要混用**（`duration` 紫域用中文串如 `"4秒"`，Ark 用整数）

## 鉴权（铁律）

API Key 在 **macOS 钥匙串**，本地脚本取：

```bash
security find-generic-password -a $USER -s seedance-workflow-ziyu -w
```

- ⚠️ 紫域文档明令：**API Key 只能放服务器/本机脚本，绝不能写前端**。
- 不读 `~/.zshrc.ziyuai`（本机无此文件）；Obsidian 库 `seedance-workflow/run.sh` 起的本地 Web App（127.0.0.1:8765，双通道 ark+ziyu）也是自动读钥匙串。
- 提交脚本统一用子进程调 `security` 取 key（见 `scripts/submit.py`）。

## 标准提交流程

> ⛔ **【成本确认铁律，2026-08-15 立】执行任何付费提交前，必须先把成本清单报给用户并等明确 OK，才动手。**
> 清单格式固定：`模型名 + 单价 × 任务数 = 预估总花费`。
> 例：`zy_model_beb4bdb66a86f1fc42c7`（2.5 720p 15秒）600/次 × 1 镜 = **600 点**。
> - 哪怕选的是"最便宜档"也要讲清**任务数=乘数**（最便宜≠总价最低）。
> - 提交包写"N 个任务 / N 镜 / 分镜"时，必须 × 单价报总价，绝不自作主张连发。
> - 含重提 / 重试 / 补跑——只要产生新扣费，一律先确认。
> - 计价分三类，报账前先看该档：H3 = 基础+按秒；2.5 按秒档 = `costPerSecond × 秒`（无基础费）；flat = `cost`/次。**不要再用已下架的 70/秒 `eb7c51f2` / 60/秒 `5c90cf20`。**

0. **成本确认（必须先做）**：`GET /api/v1/models` 拿到目标模型单价 → 数清本次要提交几个任务 → 在回复里打印 `模型 + 单价 × 任务数 = 总价` → **等待用户确认** → 收到 OK 才进下一步。

1. **素材准备**：本地图 → 先传紫域拿公网 URL（见下"上传参考图"）；已有公网 URL（TOS `drhon` bucket / `ziyuai.vip/uploads/...`）直接复用。
   - ⚠️ 紫域**不支持** Ark 的 `asset://` 内部 URI，必须给公网可访问 URL。
2. **选模型**：默认最便宜档 `zy_model_2134621044047793db22`（h3）；或用户指定（见 `references/models.md`）。
3. **提交**：`POST /api/v1/jobs`，body 见下。
4. **轮询**：`GET /api/v1/jobs/{id}`，`status` 从 `queued`→`processing`→`completed`（或 `failed`）。
5. **下载**：`completed` 后取 `previewUrl`，带 `Authorization: Bearer {key}` 下载成片。

## 接口速查（完整字段见 references/api.md）

| 动作 | 方法 + 路径 | 关键字段 |
|---|---|---|
| 列模型 | `GET /api/v1/models` | 返回 `models[]`：`id` / `name` / `cost` / `status` |
| 传图 | `POST /api/v1/uploads` | `files:[{type:"image",name,data:"data:image/png;base64,..."}]` → `assets[].url` |
| 提交任务 | `POST /api/v1/jobs` | `modelId, mode, prompt, ratio, duration, assets{image:[{url}],video:[],audio:[]}` |
| 查任务 | `GET /api/v1/jobs/{id}` | `status`；`completed` 时 `previewUrl` |
| 下载成片 | `GET {previewUrl}`（带 Bearer） | 二进制 mp4 |

### 提交 body 示例

```json
{
  "modelId": "zy_model_2134621044047793db22",
  "mode": "i2v",
  "prompt": "（提示词文本）",
  "ratio": "16:9",
  "duration": "4秒",
  "assets": {
    "image": [{"url": "https://ziyuai.vip/uploads/asset_upload_xxx.png"}],
    "video": [],
    "audio": []
  }
}
```

- `mode`：`i2v`（图生视频，最常用）/ `t2v`（文生视频）/ `t2i`（文生图）
- `ratio`：`"16:9"` 或 `"9:16"`
- `duration`：**中文串** `"5秒"` / `"12秒"`（非 Ark 整数）。最短秒数看该档 `allowedDurations`：H3 约 4 秒；2.5 15秒档 4–15；2.5 要挂视频的 `85b5f649` **最短 20 秒**；按秒 30秒档 4–30。
- `assets.image`：每项 `{"url": "..."}`；h3 支持最多 9 图

## 已知模型 ID（references/models.md 有完整成本表，**2026-08-26 实拉**）

- **h3 最便宜档** `zy_model_2134621044047793db22`（H3 速度快 720p，基础 50 + 10/s）→ 默认试跑走这条
- **2.5 720p 15秒** `zy_model_beb4bdb66a86f1fc42c7`（**600/次**，4–15s，30图+音频，**无参考视频**）→ 数字人对白 15s 首选
- **2.5 720p 按秒** `zy_model_2bf90606d3250d5026ce`（**60/秒**，4–30s，无参考视频）→ 替换已下架的 60/s `5c90cf20`
- **2.5 720p 要挂表演视频** 只剩 `zy_model_85b5f6490c0952cc3f68`（**1000/次，仅 20–30s**，图9/视频3/音频3）
- ⚠️ **已下架勿打**：`eb7c51f23a5143170ba2`（旧 70/s）、`5c90cf20cebcfdbef433`（旧 60/s，G01 镜头一曾用）、`e12f07f8eb343aae90a1`、`f4f1d999d1dfd3b5905b`。提交前一律 `GET /api/v1/models` 实时核对。

## 常见坑（references/gotchas.md）

- **模型维护**：返回 HTTP 400 + "当前模型正在维护"，**不扣费自动退款**，换模型或稍后重试。
- **时长格式**：紫域用 `"4秒"` 中文串（Ark 用整数），写错会被拒。
- **asset:// 不支持**：Ark 内部图 URI 紫域读不到，必须公网 URL。
- **下载要鉴权**：`previewUrl` 必须带 `Authorization: Bearer {key}` 才能下。
- **2.0/2.5 提示词不通用**：同一镜头两套提示词分别存档，别拿 2.5 提交包 prompt 喂 2.0（反之亦然）。
- **key 取不到**：`security` 可能弹 Touch ID，后台跑时确保已解锁；脚本里设超时兜底。
- **音频参考不认 m4a 容器**：即便 m4a 内部是标准 AAC-LC 也会被拒（`音频文件处理失败`）；必须 ffmpeg 转 `.mp3`/`.wav` 再传（详见 gotchas §10）。

## 通用提交脚本

`scripts/submit.py` —— 参数化提交器，支持：本地图自动上传 + 公网 URL 直传、i2v/t2v、自动轮询下载、失败/超时退出。用法见文件头。
