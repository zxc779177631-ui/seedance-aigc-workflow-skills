---
name: seedance-video-pipeline
version: 1.1.0
description: 数字人视频总控编排——把「提示词工程 → 选择提交通道 → 提交生成 → 轮询下载」串成一条可复用流水线。覆盖 Seedance 2.0/2.5 提示词分流、紫域AI/火山Ark/MaxForAI 三通道选型与提交、成本报账与常见坑。当用户要把脚本/口播做成数字人视频、从文案到成片、或在多个生成平台间选型时调用。
---

# 数字人视频总控流水线（seedance-video-pipeline）

本 skill 是**编排层（orchestrator）**：不重复各通道的实现细节，而是负责「走哪条通道、按什么顺序、卡哪些点」，并把具体工作**委派**给专项 skill。每个专项 skill 拥有自己的脚本、命令与最新档位，本层只做决策与衔接。

## 流水线四阶段

```
口播/脚本
   │
   ▼ [阶段1] 分段
digital-human-script-segmenter  →  镜头、秒轴、参考图清单
   │
   ▼ [阶段2] 提示词工程
seedance  →  每个镜头两套提示词（2.0 版 + 2.5 版，⚠️不互套）
   │
   ▼ [阶段3] 2.5 提示词审查（可选但推荐）
seedance-2-5-prompt-reviewer
   │
   ▼ [阶段4] 选通道 + 提交 + 轮询下载
本层决策树 → 委派 ziyu-video-submit / seedance-ark-submit / maxforai-video-submit
```

### 阶段 1 · 分段（委派 `digital-human-script-segmenter`）
把口播/文案按镜头、时间轴、所需参考图切块，产出可独立提交的镜头清单。

### 阶段 2 · 提示词工程（委派 `seedance`）
- 每个镜头产出**两套**提示词：2.0 版、2.5 版。
- ⚠️ **2.0 与 2.5 提示词不能互相套用**（用户已明确）：2.0 不挂白描/深度/构图线稿；景别文字写死。
- 参考视频职责：@视频N 只借**神态/眨眼/交流式视线/呼吸/肢体习惯**，**显式排除配饰、衣物细节、随身物件**（手表/戒指等）——点名会把注意力引到局部，且 2.5 会把这些配件继承进成片。

### 阶段 3 · 2.5 提示词审查（委派 `seedance-2-5-prompt-reviewer`）
审表演/口型/景别/时长短板，降低重提率。

### 阶段 4 · 选通道 + 提交（本层决策 → 委派）
见下方「通道选型决策树」。提交前必须过「卡点」章节。

## 通道选型决策树

完整命令模板与档位见 `references/channels.md`。速查表（⚠️ 紫域档位持续漂移，调用前务必 `GET /api/v1/models` 实拉）：

| 你要的 | 首选通道 | 模型/档位 | 鉴权（钥匙串） | 参考成本 |
|---|---|---|---|---|
| 2.5 720p 带音频、按条(15s) | 紫域 | `zy_model_beb4bdb66a86f1fc42c7` (600/次) | `seedance-workflow-ziyu` | 600点=¥6 |
| 2.5 720p 带音频、按秒(4–30s) | 紫域 | `zy_model_2bf90606d3250d5026ce` (60/秒) | `seedance-workflow-ziyu` | 60点/秒 |
| 2.5 720p 挂表演视频(20–30s) | 紫域 | `zy_model_85b5f6490c0952cc3f68` (1000/次) | `seedance-workflow-ziyu` | 1000点 |
| 2.0 口播、低成本 | 紫域2.0 / Ark / MaxForAI sd20 | 见各 skill | 对应钥匙串 | 低 |
| 2.5 走 MaxForAI | MaxForAI | `wf-sd2-5-720p` (sd25 key) | `seedance-workflow-maxforai-sd25` | ≈¥0.30/秒 |
| 需 Ark 专属能力 | 火山 Ark | `doubao-seedance-2-0-260128` / `2-5-260628` | `~/.zshrc.ark` | — |

**选型原则**
- 默认走**紫域**（档位最多、带音频成熟），除非成本或能力更合适。
- 单镜头、预算紧 → 紫域 2.0 或 MaxForAI 特价档。
- 需要 Ark 的 `reference_*` 角色体系 / 特定模型 → 火山 Ark。
- MaxForAI 适合 2.5 按秒、¥0.30/秒档；但紫域 URL 必须 `--transfer` 转存。

## 卡点（每次付费提交前必过）

1. **报账确认**：把「通道 + 模型 + 时长 + 预估成本 × 任务数」报给用户并等 OK 再提交。最便宜档也要算任务数。
2. **断线防叠单**：断线后续跑极易叠交同参数任务。重提前先查后台 task 状态（保留 task_id！），确认没有在跑的重复单。
3. **紫域素材**：本地图先 `POST /api/v1/uploads`（复数，非 /upload）拿公网 URL；音频用 **mp3**（不要 .m4a）；`assets.audio` 只收公网 URL。
4. **MaxForAI**：紫域/TOS 链接一律 `--transfer` 转存，直传会 generation failed；**不需要 TOS**。
5. **Ark**：`role` 必须用 `reference_image`/`reference_video`/`reference_audio`；`duration` 取整数。
6. **钥匙串取密钥**，绝不写进前端/仓库。

## 常见坑（已验证，别再踩）

- 紫域 TOS 403 → 先传紫域 `/uploads` 拿 URL
- 紫域音频 `.m4a` 被拒 → 转 `.mp3`
- 紫域带音频走 60/s 档而非 70/s（70/s 带音频连挂）
- MaxForAI 直传紫域 URL 失败 → 转存 `--transfer`
- 2.0/2.5 提示词互套 → 浪费钱且效果错
- @视频N 配饰会被 2.5 继承 → 职责写死排除
- 紫域 `zy_model_*` 与 MaxForAI `zy-SD*` 只是名字撞 `zy`，两家平台、两套 Key，禁止混用

## 委派关系（专项 skill 拥有命令与最新档位）

| 阶段 | 委派 skill |
|---|---|
| 分段 | `digital-human-script-segmenter` |
| 提示词工程 / 2.0-2.5 分流 | `seedance` |
| 2.5 提示词审查 | `seedance-2-5-prompt-reviewer` |
| 提交紫域 | `ziyu-video-submit` |
| 提交 Ark | `seedance-ark-submit` / `seedance-2-0-ark` |
| 提交 MaxForAI | `maxforai-video-submit` |

## 交互式选型问卷（scripts/channel_quiz.py）

把需求直接翻译成「通道 + 模型 + 预估费用 + 命令骨架」，省去手查决策树。两种用法：

```bash
# 1) 逐项问答（直接回车用默认 = 2.5 带音频 720p）
python3 ~/.workbuddy/skills/seedance-video-pipeline/scripts/channel_quiz.py

# 2) 一行出结果（CI / 快速选型）
python3 ~/.workbuddy/skills/seedance-video-pipeline/scripts/channel_quiz.py \
  --ver 2.5 --audio y --duration 15 --res 720p --perf n --budget normal
```

问卷维度：模型版本（2.0/2.5）、是否带音频/口型、时长（秒）、分辨率（720p/480p）、是否挂表演参考视频、预算倾向（质量优先/最便宜）。
输出含：推荐通道、模型 ID、钥匙串条目、预估费用、命令骨架（占位符，flag 名以专项 skill 为准）、提交前卡点提醒。

⚠️ 紫域/MaxForAI 档位持续漂移，问卷给出的是**决策树推荐值**，最终提交前仍需实拉对应 `/models` 接口确认。

## 交付物约定

- 成片落 `项目目录/original/` 或专项 skill 约定目录。
- 每次提交**必须记录 task_id / job_id + 通道 + 模型 + 时长 + 实际扣费**，便于对账与防叠单。
