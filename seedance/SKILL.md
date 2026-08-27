---
name: seedance
description: "Generate videos with ByteDance Seedance 2.0 models via inference.sh CLI. Models: Seedance 2 T2V, Seedance 2 I2V, Seedance 2 R2V. Capabilities: text-to-video, image-to-video, reference-to-video, synchronized audio, quality/fast modes, 480p/720p. Use for: social media videos, music videos, product demos, animated content, AI video with sound. Triggers: seedance, seedance 2, bytedance video, seedance t2v, seedance i2v, seedance r2v, video with audio, seedance 2.0, bytedance seedance"
allowed-tools: Bash(belt *)
---

# Seedance 2.0 Video Generation

Generate videos with synchronized audio using ByteDance's Seedance 2.0 models via [inference.sh](https://inference.sh) CLI.

## TOS upload and presigned URL workflow

Use this workflow when a local asset must be stored in Volcengine TOS, or when a private TOS object needs a temporary HTTPS URL for Seedance or another agent. This workflow does **not** require Volcengine Coding Plan and must not change the user's Codex model configuration.

Use the maintained project helper:

```text
/Users/a1-6/Library/Mobile Documents/iCloud~md~obsidian/Documents/git/seedance-workflow/scripts/tos_upload.py
```

The helper reads credentials only from the local environment:

- required: `TOS_ACCESS_KEY`, `TOS_SECRET_KEY`;
- optional: `TOS_SECURITY_TOKEN`, `TOS_BUCKET`, `TOS_PREFIX`, `TOS_ENDPOINT`, `TOS_REGION`, `TOS_PRESIGN_EXPIRES`.

`ARK_API_KEY` is for Ark/Seedance API calls and cannot replace TOS AK/SK. Never ask the user to paste AK/SK into chat, place credentials in prompts or source code, or print them in command output. If credentials are missing, ask the user to set them locally and stop before the network operation.

Upload a local file and immediately obtain a temporary GET URL:

```bash
cd '/Users/a1-6/Library/Mobile Documents/iCloud~md~obsidian/Documents/git/seedance-workflow'
.venv/bin/python scripts/tos_upload.py upload '/absolute/path/to/file.png' \
  --bucket drhon \
  --prefix 'project-assets' \
  --expires 43200
```

Generate a new URL for an object already in TOS:

```bash
cd '/Users/a1-6/Library/Mobile Documents/iCloud~md~obsidian/Documents/git/seedance-workflow'
.venv/bin/python scripts/tos_upload.py presign \
  --bucket drhon \
  --key 'project-assets/file.png' \
  --expires 43200 \
  --verify
```

Operational rules:

- treat a presigned URL as a temporary bearer credential; record its expiry and never register it as the permanent asset address;
- keep `tos://bucket/object_key` or separate bucket/key fields in the asset ledger as the stable identity;
- before a generation request, verify that the HTTPS URL returns `200` or `206` and the expected MIME type;
- prefer an intentionally public HTTPS object URL for long-lived shared project assets, and a presigned URL for private objects or temporary handoff;
- use short, task-appropriate expiry times and regenerate the URL when it expires.

## Quick Start

> Requires inference.sh CLI (`belt`). [Install instructions](https://raw.githubusercontent.com/inference-sh/skills/refs/heads/main/cli-install.md)

```bash
belt login

belt app run falai/seedance-2-t2v --input '{
  "prompt": "a jazz band performing in a dimly lit club",
  "generate_audio": true
}'
```

## Ark local file upload for reference assets

When a project uses the Volcengine Ark `/api/v3/contents/generations/tasks` endpoint directly and the user provides local reference images, upload them with the Ark Python SDK before constructing the generation payload.

Use this only when:

- the user gives local files such as `.png`, `.jpg`, `.mp4`, or `.mp3`;
- the immediate workflow is Ark Files API storage / Managed Agents / multimodal conversation;
- or you need to test upload connectivity.

Do **not** assume Files API uploads can be used as Seedance video-generation references. In project testing and customer-support feedback, `file-...` IDs returned by `client.files.create(..., purpose="user_data")` were not accepted by `/api/v3/contents/generations/tasks` as `image_url` references.

### Environment

Create a local virtual environment instead of installing into the system Python:

```bash
python3 -m venv /Users/a1-6/Movies/seedance-workflow/.venv-ark-upload
/Users/a1-6/Movies/seedance-workflow/.venv-ark-upload/bin/python -m pip install --upgrade pip
/Users/a1-6/Movies/seedance-workflow/.venv-ark-upload/bin/python -m pip install volcengine-python-sdk httpx typing_extensions pydantic anyio sniffio distro
```

Do **not** install only `volcenginesdkarkruntime` from PyPI. In testing, that package was an empty `0.0.1` shell until `volcengine-python-sdk` was installed.

Requires `ARK_API_KEY` in the environment. Do not print the key.

### Upload one local file

```python
import os
from pathlib import Path
from volcenginesdkarkruntime import Ark

path = Path("/absolute/path/to/reference.png")

client = Ark(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key=os.getenv("ARK_API_KEY"),
)

with path.open("rb") as f:
    file = client.files.create(file=f, purpose="user_data")

print(file.id)
```

The returned ID may look like `file-20260723103957-glx6d`. Register it in the project asset ledger with the original local path, intended reference role, upload date, and a note that it is **not directly usable** as a Seedance reference image unless future platform docs say otherwise.

### Seedance reference-image support

Seedance generation reference images currently support:

1. public HTTP/HTTPS image URLs;
2. official/platform asset IDs in `asset://asset-...` format;
3. TOS URIs such as `tos://{bucket}/{object_key}` when TOS cross-service authorization is configured.

For existing Ark asset IDs, use:

```json
{"url": "asset://asset-..."}
```

Do not use either of these for Seedance references:

```json
{"url": "file-..."}
{"url": "asset://file-..."}
```

Observed errors:

- bare `file-...`: `content[x].image_url` is not valid;
- `asset://file-...`: `The specified asset file-... is not found`.

If the user only has a local image and needs it as a Seedance reference, use one of:

1. upload it to a public HTTPS URL and pass that URL;
2. upload it to TOS and pass `tos://bucket/object_key` after cross-service authorization;
3. create or obtain a true platform `asset-...` ID;
4. for non-critical atmosphere/prop references, fall back to text-only prompts.

Before submitting a generation task with HTTP/HTTPS reference images, verify each URL is actually readable from the current environment:

- acceptable: HTTP `200` or partial-content `206` with an image content type;
- not acceptable: `403`, expired signed URL, HTML error page, or redirects to an unauthenticated page.

Only include the readable URLs in `content`. If some supporting prop/environment references are unreadable, omit those references and describe the prop/atmosphere in text instead. Do not let one unreadable supporting image block a low-cost 480p demo when the primary person asset and at least one usable environment reference are available.

Exception for user- or client-designated references: if the user explicitly provided specific references for the shot, or the shot's purpose depends on those references (for example Book Master for a reading shot, prop/desk references for a tabletop shot, or a window/environment reference for a spatial B-roll), do **not** silently degrade to text-only or fewer references when those URLs expire or return `403`. Stop before submission, report which references expired, and ask the user for refreshed URLs or permission to proceed without them.

If a task was already submitted before discovering this issue, mark the output as temporary or incomplete in the filename and project ledger. Do not treat it as a formal demo for judging the intended reference strategy.

Observed successful pattern for TOS-hosted public image references:

```json
{
  "type": "image_url",
  "image_url": {
    "url": "https://bucket.tos-cn-beijing.volces.com/object.png"
  },
  "role": "reference_image"
}
```

In testing, a TOS public HTTPS URL returning `206 image/png` was accepted by Seedance generation; other TOS HTTPS URLs returning `403` were not included. A raw `tos://bucket/object_key` string was rejected as invalid in the tested Ark payload shape, so do not rely on `tos://` unless cross-service authorization and the exact accepted format have been confirmed for that account.

### Practical rules

- Use person/face assets as high-priority identity references.
- Use environment and prop references as supporting references; explicitly state they must not alter the person’s identity.
- Keep a per-project asset ledger before generation so prompts remain reproducible.
- When a reference is only for atmosphere and exact reproduction is not required, text-only may be cheaper and sufficient for 480P demos.


## Seedance 2.0 Models

| Model | App ID | Best For |
|-------|--------|----------|
| Seedance 2 T2V | `falai/seedance-2-t2v` | Text-to-video with audio |
| Seedance 2 I2V | `falai/seedance-2-i2v` | Animate images with audio |
| Seedance 2 R2V | `falai/seedance-2-r2v` | Reference images/videos/audio to video |

All models support **quality** and **fast** modes, 480p/720p resolution, and synchronized audio generation.

## Examples

### Text-to-Video with Audio

```bash
belt app run falai/seedance-2-t2v --input '{
  "prompt": "ocean waves crashing on rocks during a storm, dramatic cinematic shot",
  "generate_audio": true,
  "duration": 10,
  "aspect_ratio": "16:9"
}'
```

### Fast Mode (Cheaper)

```bash
belt app run falai/seedance-2-t2v --input '{
  "prompt": "a butterfly landing on a flower in slow motion",
  "mode": "fast",
  "generate_audio": true
}'
```

### Image-to-Video

Animate a still image into a video:

```bash
belt app run falai/seedance-2-i2v --input '{
  "image": "https://your-image.jpg",
  "prompt": "gentle camera movement, leaves rustling in the wind",
  "generate_audio": true
}'
```

### Image-to-Video with Start and End Frames

```bash
belt app run falai/seedance-2-i2v --input '{
  "image": "https://start-frame.jpg",
  "end_image": "https://end-frame.jpg",
  "prompt": "smooth transition between scenes",
  "generate_audio": true
}'
```

### Reference-to-Video

Use reference images, videos, or audio in your prompt with `@Image1`, `@Video1`, `@Audio1` placeholders:

```bash
belt app run falai/seedance-2-r2v --input '{
  "prompt": "A person who looks like @Image1 is walking through a garden",
  "images": ["https://portrait.jpg"],
  "generate_audio": true
}'
```

### Multi-Reference

```bash
belt app run falai/seedance-2-r2v --input '{
  "prompt": "@Image1 and @Image2 are having a conversation at a cafe",
  "images": ["https://person1.jpg", "https://person2.jpg"],
  "generate_audio": true
}'
```

### Reference with Audio

```bash
belt app run falai/seedance-2-r2v --input '{
  "prompt": "A musician who looks like @Image1 is performing @Audio1",
  "images": ["https://musician.jpg"],
  "audios": ["https://music.mp3"],
  "generate_audio": true
}'
```

## Pricing

| Mode | 720p | 480p |
|------|------|------|
| Quality | ~$0.30/sec | ~$0.13/sec |
| Fast | ~$0.24/sec | ~$0.11/sec |

## Parameters (T2V)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | string | required | Text description of the video |
| `generate_audio` | boolean | false | Generate synchronized audio |
| `duration` | enum | - | Duration in seconds (4–10) |
| `aspect_ratio` | enum | - | 16:9, 9:16, 1:1, 4:3, 3:4 |
| `resolution` | enum | - | 480p or 720p |
| `mode` | enum | quality | quality or fast |
| `seed` | integer | random | Reproducible generation |

## Parameters (I2V)

Same as T2V plus:

| Parameter | Type | Description |
|-----------|------|-------------|
| `image` | file | Starting frame image (required) |
| `end_image` | file | Optional ending frame |

## Parameters (R2V)

Same as T2V plus:

| Parameter | Type | Description |
|-----------|------|-------------|
| `images` | array | Reference images (@Image1, @Image2, ...) |
| `videos` | array | Reference videos (@Video1, @Video2, ...) |
| `audios` | array | Reference audio (@Audio1, @Audio2, ...) |

## Search Seedance Apps

```bash
belt app list --search "seedance"
```

## Related Skills

```bash
# Full platform skill (all 250+ apps)
npx skills add inference-sh/skills@infsh-cli

# All video generation models
npx skills add inference-sh/skills@ai-video-generation

# Google Veo
npx skills add inference-sh/skills@google-veo

# Image generation (for image-to-video)
npx skills add inference-sh/skills@ai-image-generation

# AI avatars & lipsync
npx skills add inference-sh/skills@ai-avatar-video
```

Browse all video apps: `belt app list --category video`

## Documentation

- [Running Apps](https://inference.sh/docs/apps/running) - How to run apps via CLI
- [Streaming Results](https://inference.sh/docs/api/sdk/streaming) - Real-time progress updates
- [Content Pipeline Example](https://inference.sh/docs/examples/content-pipeline) - Building media workflows
