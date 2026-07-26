# Script Director — Explainer Templates Pipeline

## When to Use

You are the Script Director for an explainer video. The user provides their own copy text. Your job is to:
1. Parse the user's copy into titled sections
2. Assign approximate timing and a visual concept for each section
3. Present a confirmation table
4. After confirmation, produce a machine-readable script artifact

This pipeline supports multiple visual templates. The template choice affects what kinds of visual concepts make sense — always check `brief.template` and read the template definition before suggesting visual concepts.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/script.schema.json` | Artifact validation |
| Template config | `config.templates[brief.template]` | Scene types, visual constraints |
| Playbook | Active style playbook | Visual language, color palette |

## Process

### Step 1: Accept User Copy

The user provides their narration text. Accept it verbatim — do NOT rewrite, add, or remove content.

Use natural breaks in the user's copy (paragraph breaks, topic shifts, or punctuation) to determine section boundaries. Aim for 4-8 sections for a typical 60-90s video.

### Step 2: Assign Timing and Visual Concepts

For each section, determine:
- **Timing (approximate only)**: Calculate a rough spoken duration. Chinese narration at ~2.5-3 characters/second. A 40-character sentence takes ~13-16 seconds. **This is just an estimate** — the real timing will be determined later from the actual narration audio.
- **Visual concept**: A one-line description following the selected template's scene types. Describe the scenery/visual mood and what text appears on screen.

Read the active template (`config.templates[brief.template]`) to know:
- Which scene types are allowed (e.g., `background_image` only, or also `illustration_card`, `text_card`)
- The composition approach (viewport size, runtime)
- Whether video backgrounds are available

> **Critical — correct subtitle sync order**: The final subtitle timing must be **derived from the narration audio**, NOT guessed in advance. The correct flow is:
> 1. Generate Edge TTS audio with `--write-subtitles` (produces per-word timestamps)
> 2. Merge per-word timestamps into sentence-level timing
> 3. Use those timestamps to set `data-start`/`data-duration` on each sentence
>
> The table's "时间" column is a planning estimate. Actual timing is locked after TTS generation.

### Step 3: Build the Confirmation Table

Format the result as a Markdown table:

```
| **段落** | **时间** | **画面构思** | **文案** |
| --- | --- | --- | --- |
| **1. 开场 — 概率的本质** | 0:00-0:15 | Misty mountain lake at sunrise, calm reflective mood. 文字：市场是概率的游戏... | 市场是概率的游戏... |
| **2. 挫折与门槛** | 0:15-0:30 | A person walking through wind and sand, blurred. 文字浮出："允许失败" | 很多人因为挫败感而离开... |
...
```

**Rules for 画面构思:**
- Keep descriptions to 1-2 sentences max
- Describe the visual mood, scenery, and what text appears
- Concepts must fit within the active template's allowed scene types

### Step 4: Present to User

Present the table and ask for confirmation:

> 已根据您提供的文案，整理出以下视频脚本方案：
>
> [table]
>
> 请确认以上方案，或指出需要调整的段落/时间/画面构思。确认后将进入场景制作阶段。

**Do NOT proceed beyond this point until the user confirms.**

### Step 5: After Confirmation — Build Structured Script Artifact

Once the user confirms (or requests changes), apply any adjustments then produce the machine-readable script:

```json
{
  "script_sections": [
    {
      "id": "s1",
      "label": "开场 — 概率的本质",
      "text": "市场是概率的游戏...",
      "start_seconds": 0,
      "end_seconds": 15,
      "visual_concept": "Misty mountain lake at sunrise, calm reflective mood"
    },
    ...
  ],
  "script_metadata": {
    "total_duration_seconds": 60,
    "template": "minimal",
    "narration_language": "zh-CN",
    "confirmation_status": "confirmed"
  }
}
```

### Step 6: Self-Review

- [ ] All user-provided copy is preserved verbatim (no additions, no deletions, no rewrites)
- [ ] Section labels match the narrative topic of each section
- [ ] Timing feels proportional (longer text = longer section)
- [ ] Visual concepts fit the active template's scene types
- [ ] Table was presented to user and explicitly confirmed

### Step 7: Submit

Validate the script artifact against the schema and persist via checkpoint.

## Common Pitfalls

- **Rewriting user copy**: Do NOT improve, rephrase, or enhance the user's words. Keep them exactly as provided.
- **Over-splitting**: Keep sections to 4-8 for a 60-90s video. Too many sections makes the pace feel rushed.
- **Visual concepts that don't fit the template**: Check template config before suggesting a diagram, chart, or animation — the selected template may not support it.
- **Estimating real timing**: The table's timing column is an estimate. Actual timing comes from narration audio + sync-timings.py.
