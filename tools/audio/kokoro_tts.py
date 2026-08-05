"""Kokoro-82M local text-to-speech provider tool.

Kokoro is an open-weight TTS model (82M params) with Apache license.
Supports Chinese, English, Japanese, Korean, and many more languages.
Runs locally — no API key required.

Requires Python 3.10-3.12 (uses uv-managed Python 3.12 venv at .kokoro-venv/).

Install:
  uv venv --python 3.12 .kokoro-venv
  uv pip install --python .kokoro-venv/bin/python kokoro soundfile "misaki[zh]"
  # Download model: run kokoro once (auto-downloads from HuggingFace)
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)

# Path to the uv-managed Python 3.12 venv
_KOKORO_VENV = Path(__file__).resolve().parent.parent.parent / ".kokoro-venv"
_KOKORO_PYTHON = _KOKORO_VENV / "bin" / "python"

# Voice lists by language for user guidance
CHINESE_VOICES = [
    "zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zf_xiaoyi",
    "zm_yunjian", "zm_yunxi", "zm_yunxia", "zm_yunyang",
]
ENGLISH_VOICES = [
    "af_alloy", "af_aoede", "af_bella", "af_heart", "af_jessica",
    "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
    "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam", "am_michael",
    "am_onyx", "am_puck", "am_santa",
    "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
    "bm_daniel", "bm_fable", "bm_george", "bm_lewis",
]
JAPANESE_VOICES = ["jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro", "jm_kumo"]
KOREAN_VOICES = ["hf_alpha", "hf_beta", "hm_omega", "hm_psi"]


class KokoroTTS(BaseTool):
    name = "kokoro_tts"
    version = "0.1.0"
    tier = ToolTier.VOICE
    capability = "tts"
    provider = "kokoro"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.LOCAL

    dependencies = ["cmd:.kokoro-venv/bin/python"]
    install_instructions = (
        "Install Kokoro TTS:\n"
        "  uv venv --python 3.12 .kokoro-venv\n"
        "  uv pip install --python .kokoro-venv/bin/python kokoro soundfile 'misaki[zh]'\n"
        "  # Model auto-downloads on first run (~327MB)\n"
        "  # For Chinese: ensure misaki[zh] is installed"
    )
    agent_skills = ["text-to-speech"]

    capabilities = [
        "text_to_speech",
        "offline_generation",
        "multilingual",
    ]
    supports = {
        "voice_cloning": False,
        "multilingual": True,
        "offline": True,
        "native_audio": True,
        "speed_control": True,
        "pitch_control": False,
    }
    best_for = [
        "free offline narration with no API key",
        "high-quality Chinese TTS (offline)",
        "privacy-sensitive local-only workflows",
    ]
    not_good_for = [
        "voice clone matching",
        "extremely long-form narration (>30 min)",
    ]

    input_schema = {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {"type": "string"},
            "voice": {
                "type": "string",
                "description": "Kokoro voice name. Chinese: zf_xiaobei, zm_yunxi, etc.",
                "default": "zf_xiaobei",
            },
            "speed": {
                "type": "number",
                "description": "Speaking speed. 1.0 = normal, 0.5 = slow, 1.5 = fast.",
                "default": 1.0,
                "minimum": 0.25,
                "maximum": 2.0,
            },
            "lang_code": {
                "type": "string",
                "description": "Language code: 'z'=Chinese, 'a'=American English, 'b'=British English, 'j'=Japanese, 'h'=Korean",
                "default": "z",
            },
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=4, ram_mb=1024, vram_mb=512, disk_mb=400, network_required=False
    )
    retry_policy = RetryPolicy(max_retries=1, retryable_errors=["Timeout"])
    idempotency_key_fields = ["text", "voice", "speed"]
    side_effects = ["writes audio file to output_path"]
    user_visible_verification = ["Listen to generated audio for intelligibility"]

    def get_status(self) -> ToolStatus:
        if not _KOKORO_PYTHON.exists():
            return ToolStatus.UNAVAILABLE
        try:
            result = subprocess.run(
                [_KOKORO_PYTHON, "-c", "from kokoro import KPipeline; print('ok')"],
                capture_output=True, text=True, timeout=30,
            )
            return ToolStatus.AVAILABLE if result.returncode == 0 else ToolStatus.UNAVAILABLE
        except Exception:
            return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def _detect_lang_code(self, text: str) -> str:
        """Auto-detect language code from text."""
        for ch in text:
            if "\u4e00" <= ch <= "\u9fff":
                return "z"
            if "\u3040" <= ch <= "\u30ff":
                return "j"
            if "\uac00" <= ch <= "\ud7af":
                return "h"
        return "a"

    def _detect_voice(self, voice: str | None, lang_code: str) -> str:
        """Pick a sensible default voice if none provided."""
        if voice:
            return voice
        defaults = {
            "z": "zf_xiaobei",
            "a": "af_heart",
            "b": "bf_emma",
            "j": "jf_alpha",
            "h": "hf_alpha",
        }
        return defaults.get(lang_code, "af_heart")

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        if self.get_status() != ToolStatus.AVAILABLE:
            return ToolResult(
                success=False,
                error="Kokoro TTS not available. Install: uv venv --python 3.12 .kokoro-venv && uv pip install --python .kokoro-venv/bin/python kokoro soundfile 'misaki[zh]'",
            )

        start = time.time()
        try:
            result = self._generate(inputs)
        except Exception as exc:
            return ToolResult(success=False, error=f"Kokoro TTS generation failed: {exc}")

        result.duration_seconds = round(time.time() - start, 2)
        return result

    def _generate(self, inputs: dict[str, Any]) -> ToolResult:
        text = inputs["text"]
        output_path = Path(inputs.get("output_path", "tts_output.wav"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lang_code = inputs.get("lang_code") or self._detect_lang_code(text)
        voice = self._detect_voice(inputs.get("voice"), lang_code)
        speed = float(inputs.get("speed", 1.0))
        env = os.environ.copy()
        env["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

        wrapper_script = f"""
import sys, soundfile as sf
from kokoro import KPipeline
pipeline = KPipeline(lang_code='{lang_code}')
text = {repr(text)}
generator = pipeline(text, voice='{voice}', speed={speed})
all_audio = []
for gs, ps, audio in generator:
    all_audio.append(audio)
if len(all_audio) == 0:
    print('ERROR: No audio generated', file=sys.stderr)
    sys.exit(1)
import numpy as np
combined = np.concatenate(all_audio)
sf.write('''{output_path}''', combined, 24000)
print('OK:' + str(len(combined)))
"""

        proc = subprocess.run(
            [_KOKORO_PYTHON, "-c", wrapper_script],
            capture_output=True, text=True, timeout=300, env=env,
        )

        if proc.returncode != 0:
            return ToolResult(
                success=False,
                error=f"Kokoro failed (exit {proc.returncode}): {proc.stderr[:500]}",
            )
        if not output_path.exists():
            return ToolResult(
                success=False,
                error=f"Kokoro output file missing: {output_path}",
            )
        if "ERROR:" in proc.stdout:
            return ToolResult(
                success=False,
                error=f"Kokoro error: {proc.stdout}",
            )

        return ToolResult(
            success=True,
            data={
                "provider": self.provider,
                "voice": voice,
                "speed": speed,
                "lang_code": lang_code,
                "text_length": len(text),
                "output": str(output_path),
                "format": "wav",
                "samples": proc.stdout.strip(),
            },
            artifacts=[str(output_path)],
            model=voice,
        )
