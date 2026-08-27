# Seedance 数字人视频工作流 Skills

把「提示词 → 选通道 → 提交到紫域 AI / 火山方舟 Ark / MaxForAI 生成 Seedance 视频 → 轮询下载」的全流程拆成可复用 skill。
鉴权走 macOS 钥匙串，脚本运行时读取，**仓库不含任何 API Key / Token**。
**许可证：MIT**（见 `LICENSE`）。仓库现为 **public**。

## 工作流总览

```
口播/脚本
   │
   ▼ [1] 分段          digital-human-script-segmenter
   ▼ [2] 提示词工程     seedance（每镜两套：2.0 + 2.5，不互套）
   ▼ [3] 2.5 提示词审查  seedance-2-5-prompt-reviewer
   ▼ [4] 选通道+提交+下载  ► seedance-video-pipeline（总控编排）
              ┌────────────────────────┼────────────────────────┐
           紫域 AI (ziyu)          火山 Ark (ark)          MaxForAI (maxforai)
```

| 环节 | Skill | 职责 |
|---|---|---|
| **总控编排** | `seedance-video-pipeline` | 串起四阶段、按决策树选通道、卡报账/防叠单等铁律 |
| 提示词工程（2.0/2.5 分流、垫图规则） | `seedance` | 写 Seedance 图生视频提示词、控景别、定参考图角色 |
| 2.5 提示词审查 | `seedance-2-5-prompt-reviewer` | 审 2.5 提示词短板（表演/口型/景别/时长） |
| 口播/脚本分段 | `digital-human-script-segmenter` | 把中文口播按镜头、秒轴、参考图切分 |
| **提交紫域 AI** | `ziyu-video-submit` | `POST /api/v1/jobs`，上传参考图、轮询、下载成片 |
| **提交火山 Ark** | `seedance-ark-submit` + `seedance-2-0-ark` | `POST /api/v3/contents/generations/tasks`，轮询下载 |
| **提交 MaxForAI** | `maxforai-video-submit` | `POST /v1/videos`，3 把 Key 分模型组 |

## 三条提交通道（2026-08-26 实拉）

| 通道 | 鉴权（钥匙串） | 关键模型 | 提交端点 |
|---|---|---|---|
| 紫域 AI `ziyuai.vip` | `seedance-workflow-ziyu` | h3 `zy_model_2134621044047793db22`；2.5 720p 15s `zy_model_beb4bdb66a86f1fc42c7`(600/次)；2.5 720p 按秒 `zy_model_2bf90606d3250d5026ce`(60/秒) | `POST /api/v1/jobs` |
| 火山 Ark `ark.cn-beijing.volces.com` | `ARK_API_KEY`（source `~/.zshrc.ark`） | `doubao-seedance-2-0-260128` / `2-5-260628` | `POST /api/v3/contents/generations/tasks` |
| MaxForAI `maxforai.top` | `seedance-workflow-maxforai-sd25` / `-sd20-zy` / `-sd20-ft`（**3 把 Key 分模型组**） | `wf-sd2-5-720p`(≈¥0.30/秒) | `POST /v1/videos` |

## 通用铁律

- **付费提交前必须报账等用户 OK**：成本 = 模型单价 × 任务数（最便宜档也要算任务数）。
- **2.0 与 2.5 提示词不互套**：同一镜头两套提示词分别存档。
- **时长格式**：紫域用中文串 `"5秒"`，Ark 用整数 `5`。
- **紫域音频**：用 `.mp3` / `.wav`，**不要 `.m4a`**（容器被拒）。
- **MaxForAI**：紫域 / TOS bucket 的 URL 一律先 `--transfer` 转存，直传会被上游拒；**不需要 TOS**。
- **钥匙串名是本地标签，不是密钥**；紫域 `zy_model_*` 与 MaxForAI `zy-SD*` 仅是名字撞 `zy`，两家平台、两套 Key，禁止混用。

## 安全

- 所有 API Key 存 macOS 钥匙串，由各 skill 的 `scripts/*.py` 运行时读取。
- 本仓库**只含钥匙串条目名（如 `seedance-workflow-ziyu`），不含任何真实密钥**。
- 紫域文档明令：API Key 只能放服务器/本机脚本，绝不能写前端。

## 安装

把需要的子目录整体复制到 WorkBuddy 技能目录即可：

```bash
cp -R ziyu-video-submit ~/.workbuddy/skills/
cp -R seedance-ark-submit ~/.workbuddy/skills/
# ...
```

钥匙串需本机提前配好（参考各 skill 的 SKILL.md 鉴权小节）。
