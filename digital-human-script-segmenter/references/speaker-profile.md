# 人物语速档案

人物档案由 `speech_timing.py calibrate` 生成，保存人物长期稳定的语速和表演偏好。章节情绪、特定机位、资产编号等一次性要求放入项目覆盖配置，不写死在 Skill 中。

```json
{
  "schema_version": 1,
  "speaker": "人物名",
  "language": "zh",
  "sample": {
    "text": "确认听感自然的逐字稿",
    "duration_seconds": 15.0,
    "reading_map": {"AI": "A I"}
  },
  "rates": {
    "zh_chars_per_second": 3.8,
    "en_syllables_per_second": null
  },
  "tolerance_percent": 8,
  "performance_preferences": {
    "body_language": "少量",
    "pose_lock": "参考图片坐姿"
  },
  "notes": "数字、缩写、专名和停顿说明"
}
```

## 使用规则

- `null` 表示尚未标定，不能用行业平均值补齐。
- 同一人物有明显的中文、英文两种口播模式时，优先分别采样后合并速度值。混合样本必须有两种语言各自的实际时长，不能用总时长分别相除。
- 语速或声音模型发生变化时重新标定，不直接覆盖旧档案；用日期或版本号区分。
- 单样本默认容差为 8%。若有三段以上样本，建议取各段速度的中位数，并把异常样本保留在备注中。
- 样本应是最终成片或确认自然的原始音频对应逐字稿，不使用目标时长倒推的文案。
- `performance_preferences.body_language` 使用 `少量`、`适中` 或 `较多`。章节情绪和一次性资产要求属于项目覆盖配置，不写入人物长期档案。

## 配置优先级

按以下顺序合并配置，越靠前优先级越高：

1. 当前片段的明确要求；
2. 项目或章节覆盖配置；
3. 人物长期档案；
4. Skill 通用默认值。

项目覆盖配置至少区分：章节情绪、肢体语言密度、姿态锁定、人物参考、表情参考、景别参考、音频参考、场景标签和需换机位的指定句子。素材用途不明时先确认，不根据 asset id 猜测角色。

项目覆盖配置可使用以下结构，保存在客户项目中：

```json
{
  "project": "项目名",
  "speaker_profile": "人物档案路径",
  "default_assets": {
    "person": null,
    "expression": null,
    "framing": null,
    "audio": null,
    "scene_labels": []
  },
  "chapter_overrides": {},
  "shot_change_lines": []
}
```
