# 紫域提交常见坑（已实测）

## 1. 模型维护 / 没货
- 现象：提交即失败，HTTP 400，message="当前模型正在维护，请稍后再试" 或 "该模型没货，请等待补货"
- 不扣费、自动退款
- 处理：换可用模型，或设定时稍后重试（维护通常短时）

## 2. 时长格式
- 紫域 `duration` 收**中文串**：`"4秒"` / `"13秒"`
- ⚠️ 与火山方舟 Ark 不同（Ark 收整数 `4` / `13`）。混用会报参数错
- 最短秒数以该档 `allowedDurations` 为准（H3 约 4 秒；2.5 挂视频档最短 20 秒）

## 3. 不支持 asset://
- 紫域读不到 Ark 的 `asset://` 内部 URI
- 必须传公网可访问 URL：TOS（`drhon` bucket `新书房和海/` 前缀）或紫域 `uploads` 体系
- 同一张图：TOS URL 既能当 Ark `reference_image`，也能当紫域 `assets.image`

## 4. 下载要鉴权
- `previewUrl` 必须带 `Authorization: Bearer {KEY}` 下载，否则 403
- 链接有时效，completed 后尽快下

## 5. 2.0 / 2.5 提示词不通用
- 同一镜头两套提示词，分别存档（如 `00xx/G0x-prompt.txt`）
- 别拿 2.5 提交包 prompt 喂 2.0（反之亦然）——既浪费钱、效果也不对

## 6. key 取不到
- `security find-generic-password` 在后台/无桌面时可能弹 Touch ID 卡住
- 脚本里设 `timeout=20` 兜底，超时回退 `env ZIYUAI_API_KEY`
- 钥匙串条目：`-a $USER -s seedance-workflow-ziyu`

## 7. 多图顺序
- `assets.image[]` 顺序 = 提示词里 `<Picture 1>`..`<Picture N>` 的对应
- h3 支持最多 9 图；逐镜生成时每镜 1 图即可

## 8. 轮询状态字段
- jobId 字段名可能为 `jobId` 或 `id`，取数时两者都试
- `status` 取值：`queued` / `processing` / `completed` / `failed`

## 9. modes 字段 ≠ 素材类型（极易误判）
- 模型详情里的 `modes: ["i2v","t2v"]` 只是**生成模式**（图生视频 / 文生视频），**不代表能不能传参考音频**！
- 判断能否传音频要看 `allowedAssetTypes` 字段：含 `"audio"` 即支持，`assetLimits.audio` 是上限条数。
- ✅ 判据不变：看 `allowedAssetTypes` 含 `"audio"`。2026-08-26 现网 2.5 720p 15秒档 `beb4bdb66a86f1fc42c7`、按秒档 `2bf90606d3250d5026ce`、默认档 `85b5f6490c0952cc3f68` 均含 audio。job 结构 `assets:{image:[],video:[],audio:[]}` 按数组序匹配 @图片N/@视频N/@音频N；给 audio asset 即用该声线生成对白，**不是无声版**。
- ⚠️ 多数新 2.5 档 `assetLimits.video=0`（15秒 600、按秒 60/s）：能挂音频，**不能挂表演视频**。要同时挂 004，只剩 `85b5f649`（1000/次、20–30s）。旧 60/s `5c90cf20` / 70/s `eb7c51f2` 已下架。
- 紫域不认 Ark 的 `generate_audio` 参数，改用 `assets.audio` 公网 URL 即可。

## 10. 音频参考不认 .m4a 容器（2026-08-17 实测）
- 即使 m4a 内部是**标准 AAC-LC 128kbps mono 44100**，紫域（2.5 720p 档）也会报 `音频文件处理失败，请检查音频格式和大小` 并失败退款。
- ✅ 解决：ffmpeg 转成 **`.mp3`**（128kbps mono 44100）或 `.wav` 再上传紫域；实测 mp3 上传后 mime 被识别为 `audio/mp3`、可被正常处理。
- 诊断顺序：先 `ffprobe` 确认编码正常（排除极低码率怪档，如 12.8kbps ALAC/AAC 混合标识会被拒）→ 若编码正常仍失败，基本是**容器格式**问题，换 mp3/wav 即可。
- 提交前可先用 `POST /api/v1/uploads` 传音频拿 URL，确认返回 `mime` 是 `audio/mp3` 或 `audio/wav` 再进 job。
