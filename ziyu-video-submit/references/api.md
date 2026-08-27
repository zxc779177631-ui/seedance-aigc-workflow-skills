# 紫域 AI 接口详情

Base: `https://ziyuai.vip`
所有写请求 header：`Authorization: Bearer {KEY}` + `Content-Type: application/json`
所有读请求 header：`Authorization: Bearer {KEY}`

## 1. 列模型 GET /api/v1/models

```bash
KEY=$(security find-generic-password -a $USER -s seedance-workflow-ziyu -w)
curl -s -H "Authorization: Bearer $KEY" "https://ziyuai.vip/api/v1/models"
```

返回（结构可能包在 `models` / `data`）：
```json
{ "models": [ { "id": "zy_model_xxx", "name": "H3 速度快 720p ...", "cost": 50, "status": "active" } ] }
```
- `cost`：基础额度（不含按时长加费）
- `status`：`active` 可用；维护中时提交会 HTTP 400

## 2. 上传参考图 POST /api/v1/uploads

本地图必须先传，拿公网 URL（紫域不吃本地路径 / Ark 的 asset://）。

```python
import base64, json, urllib.request
raw = open("/path/to/img.png","rb").read()
b64 = "data:image/png;base64," + base64.b64encode(raw).decode()
payload = {"files":[{"type":"image","name":"img.png","data":b64}]}
req = urllib.request.Request(BASE+"/api/v1/uploads",
    data=json.dumps(payload).encode(),
    headers={"Authorization":"Bearer "+KEY,"Content-Type":"application/json"}, method="POST")
resp = json.loads(urllib.request.urlopen(req, timeout=180).read())
url = resp["assets"][0]["url"]   # => https://ziyuai.vip/uploads/asset_upload_*.png
```
- 支持批量：`files` 数组放多张
- 返回 URL 体系 `ziyuai.vip/uploads/...`，紫域原生可访问，也可当 Ark 的 `reference_image`

## 3. 提交任务 POST /api/v1/jobs

```json
{
  "modelId": "zy_model_2134621044047793db22",
  "mode": "i2v",
  "prompt": "提示词...",
  "ratio": "16:9",
  "duration": "4秒",
  "assets": {
    "image": [{"url": "https://ziyuai.vip/uploads/asset_upload_xxx.png"}],
    "video": [],
    "audio": []
  }
}
```
- 响应取 jobId 字段名可能为 `jobId` 或 `id`：`resp.get("job") or resp` → `.get("jobId") or .get("id")`
- 提交失败（维护/参数错）会直接在响应里带错误，不进队列

## 4. 轮询 GET /api/v1/jobs/{id}

```bash
curl -s -H "Authorization: Bearer $KEY" "https://ziyuai.vip/api/v1/jobs/{id}"
```
- `status`：`queued` → `processing` → `completed` / `failed`
- `completed` 时：`previewUrl` 即成片地址
- `failed` 时：`message` / `failureReason` 说明原因（维护/没货）

## 5. 下载成片 GET {previewUrl}

```python
req = urllib.request.Request(previewUrl, headers={"Authorization":"Bearer "+KEY})
video = urllib.request.urlopen(req, timeout=300).read()
open("out.mp4","wb").write(video)
```
- ⚠️ 必须带 Bearer，否则 403
- 链接有时效，completed 后尽快下
