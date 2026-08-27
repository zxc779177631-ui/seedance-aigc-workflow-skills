# CHANGELOG · maxforai-video-submit

## [1.0.4] 2026-08-17 · zy-SD ≠ 紫域

- 纠正「2.0 紫域档」叫法：`zy-SD满血933` / `zy-特价豆包900` 是 MaxForAI 模型名碰巧带 zy，与 `ziyuai.vip` 紫域无关。
- 钥匙串 `-sd20-zy` 只是本地标签；禁止与紫域钥匙串 `seedance-workflow-ziyu`、模型 `zy_model_*` 混用。

## [1.0.3] 2026-08-17 · 对账：无列表接口、禁叠交

- 确认 `GET /v1/videos` / `/orders` / `/billing` 均 404，只能凭本地记下的 `task_id` 查询。
- 会话中断后续跑可能叠交（G01 镜头二用户后台 14:32 + 14:34 两单）；禁止未核对就再起 submit。

## [1.0.2] 2026-08-17 · 紫域 URL 必须先转存

- G01 镜头二：直传 ziyuai.vip 素材 → `generation failed`；`--transfer` 后再提成功（task `task_yhQkx99clHbhXZ1oKXsvb2VL63ueoZ1l`）。
- 修正技能：公网素材默认转存，不再“先直传再失败重试”。TOS 不需要。

## [1.0.1] 2026-08-17 · 轮询网络抖动重试

- `scripts/submit.py` 的 `req()` 对 URLError / ConnectionReset 做 3 次退避重试。G01 镜头二首测时本地轮询被 `Connection reset by peer` 打断，但任务其实已在服务端 failed。

## [1.0.0] 2026-08-17 · 首发

- 接入 MaxForAI（`https://maxforai.top/v1`）作为第三条 Seedance 通道。
- 3 把 Key 分模型组写入钥匙串：`sd25` / `sd20-zy` / `sd20-ft`。
- 配套 `scripts/submit.py`：选对钥匙串、上传/转存素材、创建任务、轮询、下载。
- 写明成本确认铁律、渠道字段差异（`aspect_ratio` vs `ratio`、`duration` vs `seconds`）、本机 Key 实际能打的模型清单。
