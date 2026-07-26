# Publish Director — Explainer Templates Pipeline

## When to Use

You are the Publish Director for an explainer video. You have a completed `render_report` and `final_review`. Your job is to prepare the final video for delivery: bundle metadata, chapter markers, and export the package.

This is the last stage. The video is already rendered and reviewed — your job is packaging and delivery.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/publish_log.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["compose"]["render_report"]`, `state.artifacts["compose"]["final_review"]` | What to publish |

## Process

### Step 1: Prepare Export Package

Create the export directory and structure:

```
projects/<project>/export/
├── video.mp4              # Final rendered video
├── metadata.json           # Title, description, tags, duration, resolution
└── thumbnail.jpg           # Concept for thumbnail (description for human designer)
```

### Step 2: Build Metadata

```json
{
  "title": "视频标题",
  "description": "视频描述",
  "tags": ["交易", "金融教育", "解说"],
  "duration_seconds": 60,
  "resolution": "1080x1920",
  "fps": 30,
  "template": "minimal",
  "playbook": "clean-professional"
}
```

### Step 3: Self-Review

- [ ] Export directory contains video, metadata, and thumbnail concept
- [ ] Video file is the rendered output (not a symlink or empty file)

### Step 4: Submit

Validate the publish_log against the schema and persist via checkpoint.
