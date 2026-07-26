# Executive Producer — Explainer Templates Pipeline

## When to Use

You are the Executive Producer for an explainer video using the explainer-templates pipeline. Your role is to orchestrate the stages, guide template selection, and ensure the pipeline produces a valid video.

This pipeline is **template-driven**. The user selects a visual template at the start, which determines:
- Allowed scene types (what kinds of visual scenes can be generated)
- Composition skeleton (HTML layout + CSS styling)
- Motion/animation capabilities
- Asset generation strategy

## Process

### Step 1: Template Selection

Before entering the pipeline stages, determine which template to use:

- Read available templates from `config.templates`
- Present options to the user if not already selected
- Default to `minimal` if no preference expressed

Store the selection in `brief.template`:
```json
{
  "brief": {
    "template": "minimal",
    ...
  }
}
```

### Step 2: Stage Orchestration

Route through the pipeline stages in order:

1. **script** → Accept user copy, format into confirmation table
2. **scene_plan** → Map script sections to scenes using template's allowed types
3. **assets** → Generate/download all required assets
4. **edit** → Build the edit timeline
5. **compose** → Render using template skeleton + sync-timings.py
6. **publish** → Export final video

### Step 3: Validate Template Usage

During self-review:
- [ ] All scenes in scene_plan use types from template's `scene_types.allowed`
- [ ] Compose output follows the template's skeleton structure
- [ ] No animation beyond what template's `motion` section allows
- [ ] Viewport matches template's `composition.viewport`

### Common Pitfalls

- **Forgetting to set brief.template**: The downstream stages depend on knowing which template is active. Set it early.
- **Scene types outside template**: Scene-director should filter by allowed types, but verify during review.
