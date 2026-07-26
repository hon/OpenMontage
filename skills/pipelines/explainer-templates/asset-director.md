# Asset Director — Explainer Templates Pipeline

## When to Use

You are the Asset Director for an explainer video. You have a `scene_plan` with per-scene background requirements and a `script` with narration text. Your job is to generate or source all required assets: narration audio, background images/videos, and background music.

## Zero-Cost Asset Strategy

This pipeline operates at **$0 budget**. All assets must be free:
- **Images**: Stock photo APIs (Pexels, Unsplash, Pixabay)
- **Narration**: Edge TTS (free, via `edge-tts` CLI with `--write-subtitles`)
- **Music**: Free stock music (Pixabay Music) or skip
- **Video backgrounds**: Stock video APIs (Pexels Videos, Pixabay Videos)

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/asset_manifest.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["scene_plan"]["scene_plan"]` | Per-scene background requirements |
| Template config | `template.yaml` of selected template | Asset source constraints |

## Process

### Step 1: Generate Narration

Generate per-section narration files using Edge TTS:

```bash
edge-tts --voice zh-CN-XiaoxiaoNeural --text "市场是概率的游戏..." \
  --write-media projects/<project>/assets/narration/s1.mp3 \
  --write-subtitles projects/<project>/assets/narration/s1.srt
```

- **One file per script section** — named `s1.mp3`, `s2.mp3`, etc.
- **Always use `--write-subtitles`** — produces SRT files with per-word timestamps. These are essential for correct subtitle timing.
- **Concatenate** after all sections are generated:
  ```bash
  python scripts/concat_audio.py projects/<project>/assets/narration/s*.mp3 \
    --output projects/<project>/assets/audio/narration.mp3
  ```

### Step 2: Source Background Images

For each scene with `type: background_image`, search stock photo APIs:

```python
from tools.graphics.image_selector import ImageSelector

result = ImageSelector().execute({
    'query': scene.search_query,
    'min_width': 1080,
    'min_height': 1920,
    'orientation': 'portrait',
    'count': 3,
    'budget_usd': 0.00,
})
```

- **Portrait orientation required** (1080×1920)
- **Budget locked to $0** — only free stock APIs
- Download selected image and save as `projects/<project>/assets/images/scene-<id>-bg.jpg`

### Step 3: Source Background Video (Optional)

If any scene uses `type: background_video` and a single full-length video works:
- Search Pexels/Pixabay for loopable stock video
- Download, ensure landscape → portrait crop or center crop
- Save as `projects/<project>/assets/video/background.mp4`

### Step 4: Source Background Music

Find royalty-free background music that matches the video's tone:
```python
music_gen.search(mood=playbook.audio.music_mood, duration=60, budget_usd=0.00)
```
- Download and save as `projects/<project>/assets/music/background_music.mp3`
- If no free music fits, skip music (video will have narration only)

### Step 5: Build Asset Manifest

```json
{
  "assets": {
    "narration": {
      "path": "assets/audio/narration.mp3",
      "type": "audio",
      "format": "mp3",
      "cost_usd": 0.00
    },
    "background_images": [
      {
        "scene_id": "s1",
        "path": "assets/images/scene-s1-bg.jpg",
        "type": "image",
        "source": "pexels",
        "cost_usd": 0.00
      }
    ],
    "background_music": {
      "path": "assets/music/background_music.mp3",
      "type": "audio",
      "format": "mp3",
      "cost_usd": 0.00
    }
  },
  "total_cost_usd": 0.00
}
```

### Step 6: Self-Review

- [ ] All narration files exist on disk
- [ ] SRT subtitle files exist alongside each narration file
- [ ] All background images are portrait 1080×1920
- [ ] Total cost is $0.00
- [ ] Background music file exists (or explicitly skipped)
- [ ] Narration covers the full script (concatenated duration ≥ total_duration)

### Step 7: Submit

Validate the asset_manifest against the schema and persist via checkpoint.

## Common Pitfalls

- **Missing `--write-subtitles`**: Always generate SRT files. They are critical for subtitle sync.
- **Using paid APIs**: Budget is $0. Only use free stock photo/video APIs.
- **Landscape images**: Always search with `orientation: portrait` and `min_width: 1080, min_height: 1920`.
- **Skipping narration verification**: ffprobe each narration file to ensure it has content (duration > 0).
