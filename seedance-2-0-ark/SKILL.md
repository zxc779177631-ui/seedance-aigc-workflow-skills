---
name: seedance-2-0-ark
version: "1.0.0"
description: "用火山方舟官方 SDK 提交、轮询、下载 Seedance 2.0 视频任务。覆盖文生视频、图生（首帧/首尾帧）、全模态参考、视频编辑、视频延长。用户说 Seedance 2.0、sd20、官方 2.0 出片、方舟生成视频、编辑视频、延长视频、首尾帧、ARK API 时使用。只负责调用 API 出片；2.0 提示词写法交给 Seedance2.0提示词工程，2.5 审查交给 seedance-2-5-prompt-reviewer。"
agent_created: true
---

# Seedance 2.0 官方出片

用火山方舟官方 `volcenginesdkarkruntime` 提交 Seedance 2.0 任务，不走 inference.sh / 紫域。封装自官方 `ark_seedance2.0_quickstart_package`。

> 版本：1.0.0 ｜ 更新记录见 [CHANGELOG.md](CHANGELOG.md)

## 边界

- **本 Skill**：把已写好的 2.0 提示词 + 素材提交到方舟，拿回视频。
- **写/改 2.0 提示词**：读知识库 `concepts/Seedance2.0提示词工程`；需要八要素/特殊字符细节再读 `references/prompt-rules.md`。
- **2.5 提示词把关**：`seedance-2-5-prompt-reviewer`。2.5 不要用本 Skill（时长/素材上限不同）。
- **口播切分、资产提示词、成片管线 UI**：分别交给 `digital-human-script-segmenter` / `ai-video-asset-director` / `seedance-workflow`。

用户没给提示词就先问，不要替他写完整成片提示词后再偷偷提交。

## 开工前

1. 把本 Skill 内 `scripts/seedance20.py` 解析为绝对路径，记为 `$SD20`。
2. **必须用官方接入包的解释器**（已装 SDK）：

```text
$PY="$HOME/Developer/ark-seedance2.0-quickstart/.venv/bin/python"
```

该文件不存在时，先让用户装官方 zip（或告知路径），不要用系统 Python 硬跑。

3. 先跑体检，缺 Key / 缺 SDK 立刻停：

```bash
"$PY" "$SD20" doctor
```

API Key 读取顺序：环境变量 `ARK_API_KEY` → macOS 钥匙串 `seedance-workflow-ark`（与现有 `seedance-workflow` 共用）。没有 Key 就停，不要问用户把密钥贴进对话。

## 工作流

### 1. 锁任务类型

按用户原话选一类，句式写错会被模型当成另一类任务：

| 类型 | 何时用 | 提示词句式 | 素材 |
|---|---|---|---|
| 文生 | 无图无视频 | 直接描述画面 | 无 |
| 图生-首帧 | 从一张图动起来 | 描述后续动作 | `--image first_frame=路径` |
| 图生-首尾帧 | 从 A 过渡到 B | 描述中间运动 | `first_frame` + `last_frame` 各 1 |
| 全模态参考 | 提取素材元素造新片 | `参考<图片N/视频N>的[维度]，生成…` | 图 0–9、视频 0–3、音频 0–3 |
| 编辑 | 改原片局部 | `严格编辑<视频1>，将X改为Y`（**禁止**加「参考」） | 待编辑视频 + 可选参考图/音频 |
| 延长 | 时间续写 | `向前/向后延长<视频1>…` | 原视频 |

官方不支持「纯音频」和「文本+音频」。音频必须搭配图或视频。

### 2. 默认参数（可被用户覆盖）

| 参数 | 默认 | 2.0 合法值 |
|---|---|---|
| model | `doubao-seedance-2-0-260128` | 也可 `…-fast-260128` / `…-mini-260615` |
| duration | 5 | **4–15 秒** |
| ratio | `16:9` | 21:9 / 16:9 / 4:3 / 1:1 / 3:4 / 9:16 |
| resolution | `720p` | 480p / 720p；正片 2.0 可用 1080p / 4k（贵、更慢） |
| generate_audio | 开 | `--no-audio` 关 |
| watermark | 关 | `--watermark` 开 |
| draft | 关 | 调提示词先开 `--draft`，确认后再关 |
| wait | 开 | 只交任务用 `--no-wait` |

用户要「先看效果」→ 加 `--draft`，分辨率不要上 1080p。正式交付再关 draft。

**提交前口头复述**：任务类型、时长、画幅、分辨率、是否有声、素材清单。用户没反对再跑。计费按秒，不要默默开 1080p/4k。

### 3. 提交

本地路径会自动上传为 `asset://文件ID`；`https://` 与已有 `asset://` 原样使用。

```bash
"$PY" "$SD20" generate \
  --prompt "严格编辑视频1，将礼盒中的香水替换成图片1中的面霜，运镜不变" \
  --image /path/to/cream.jpg \
  --video /path/to/box.mp4 \
  --ratio 16:9 \
  --duration 5 \
  --resolution 720p \
  --download \
  --out /path/to/out.mp4
```

首尾帧：

```bash
"$PY" "$SD20" generate \
  --prompt "镜头缓慢前推，人物转身挥手" \
  --image first_frame=/path/to/start.jpg \
  --image last_frame=/path/to/end.jpg \
  --duration 5
```

只看请求不花钱：`--dry-run`。只要任务 ID：`--no-wait`。

其他子命令：

```bash
"$PY" "$SD20" status <task_id> --download --out /path/to/out.mp4
"$PY" "$SD20" cancel <task_id>
"$PY" "$SD20" upload /path/to/file.jpg
```

### 4. 交付

成功后给用户：**本地路径**（若下了）、`video_url`（会过期，尽快转存）、任务 ID、实际 duration/ratio/resolution。失败给 `error.code` + `error.message`，常见原因：

- `ModelNotOpen`：控制台未开通该模型
- API Key 无效 / 余额不足 / 未买资源包
- 素材 URL 拉不到、role 和 type 不匹配
- 图片>9 / 视频>3 / 音频>3 / 纯音频

不要重试超过 1 次同一失败请求（避免重复扣费）。换提示词或换素材后再提。

## 铁律

1. **先 dry-run 或复述参数，再花钱。**
2. **密钥不进对话、不写进仓库。**
3. **编辑/延长提示词禁止加「参考」，否则任务类型被改写。**
4. **2.0 时长上限 15 秒。** 用户要 30 秒，改走 2.5，不要硬提交。
5. **视频 URL 会过期**，交付时尽量 `--download` 落到用户指定目录。
6. 批量出片、口播分段成片，优先建议用现成 `seedance-workflow`，不要在本 Skill 里重造排队系统。
