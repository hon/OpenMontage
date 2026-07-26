# Script Director — Trading Explainer Pipeline

## Customizations from base `animated-explainer/script-director.md`

This file is forked and completely rewritten for the `trading-animated-explainer` pipeline:
- **User provides copy** — no AI script generation. The user supplies the narration text.
- **Format only** — the AI splits user copy into sections, assigns visual concepts (画面构思) and timing, and presents the structured plan for confirmation.
- **No research, no proposal** — the user's copy IS the script. No fact-checking, no enhancement cues, no voice performance directions.
- **Output is a structured table** — 段落/时间/画面构思/文案 — rendered for user approval, then converted to a machine-readable script artifact.

## When to Use

The user has provided their own narration copy. Your job is to:
1. Parse the copy into logical sections (段落)
2. Assign a timing budget to each section
3. Suggest a visual concept (画面构思) for each section, following the simple template mode
4. Format everything into the table below
5. Present to the user for confirmation
6. After confirmation, produce a structured script artifact for downstream stages

## Process

### Step 1: Parse User Copy into Sections

Given the user's narration text, split it into logical sections. Each section should be:
- One coherent thought or narrative beat
- 8-20 seconds of spoken time (adjustable based on content density)
- Suitable for one background image scene

Use natural breaks in the user's copy (paragraph breaks, topic shifts, or punctuation) to determine section boundaries. Aim for 4-8 sections for a typical 60-90s video.

### Step 2: Assign Timing and Visual Concepts

For each section, determine:
- **Timing (approximate only)**: Calculate a rough spoken duration. Chinese narration at ~2.5-3 characters/second. A 40-character sentence takes ~13-16 seconds. **This is just an estimate** — the real timing will be determined later from the actual narration audio.
- **画面构思**: A one-line visual description following the pipeline's simple template (background image + text overlay). Describe the scenery mood and what text appears.

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
| **1. 开场 — 概率的本质** | 0:00-0:15 | Misty mountain lake at sunrise, calm reflective mood. 文字：市场是概率的游戏... | 市场是概率的游戏，充满了不确定性。很多时候你做了所有正确的事情，但市场依然给你一张亏损的单子。 |
| **2. 挫折与门槛** | 0:15-0:30 | A person walking through wind and sand, blurred. 文字浮出："允许失败" | 很多人因为挫败感而离开。除非你允许自己失败，否则你很难生存下去。 |
...
```

**Rules for 画面构思:**
- Always natural scenery or simple visual metaphor — no complex animations, no diagrams, no charts
- Specify what text appears on screen
- Match scenery mood to the section's emotional tone
- Keep descriptions to 1-2 sentences max

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
      "text": "市场是概率的游戏，充满了不确定性。很多时候你做了所有正确的事情，但市场依然给你一张亏损的单子。",
      "start_seconds": 0,
      "end_seconds": 15,
      "visual_concept": "Misty mountain lake at sunrise, calm reflective mood. Text overlay shows the narration sentence-by-sentence.",
      "background_mood": "calm"
    },
    {
      "id": "s2",
      "label": "挫折与门槛",
      "text": "很多人因为挫败感而离开。除非你允许自己失败，否则你很难生存下去。",
      "start_seconds": 15,
      "end_seconds": 30,
      "visual_concept": "Sparse desert landscape with wind-blown sand, solitary figure silhouette. Text overlay emphasizes '允许失败'.",
      "background_mood": "serious"
    }
  ],
  "total_duration_seconds": 40,
  "source": "user_provided",
  "confirmation_status": "confirmed"
}
```

### Step 6: Self-Evaluate

| Criterion | Question |
|-----------|----------|
| **Section boundaries** | Do sections follow natural pauses in the narration? |
| **Timing** | Is each section's duration proportional to its text length? |
| **Visual relevance** | Does each 画面构思 match the section's content and mood? |
| **Completeness** | Is all user-provided copy covered? No omissions? |

If any dimension fails, revise the table before presenting to the user.

### Step 7: Submit

Call `handle_explainer_script(state, {"script": script_json})` to validate and persist.

## Common Pitfalls

- **Adding to the copy**: Do NOT rewrite, summarize, or add to the user's copy. The text in the table must be exactly what the user provided.
- **Skipping confirmation**: The table MUST be presented to the user and confirmed before proceeding. This is a hard gate.
- **Overly complex visual concepts**: Keep 画面构思 simple — natural scenery + text overlay. No animations, diagrams, or charts.
- **Uneven timing**: Don't assign 5s to a long paragraph and 20s to a short one. Proportion timing to text length.
- **Multiple paragraphs in one section**: If the user provides a long block of text, split it into multiple scenes for visual variety.
- **Ignoring mood shifts**: If the copy shifts from serious to hopeful, the background scenery should shift too.
