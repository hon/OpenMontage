"""Chatterbox local text-to-speech provider tool.

Chatterbox is a zero-shot voice cloning TTS model from ResembleAI (0.5B params).
Supports 23 languages including Chinese, English, Japanese, Korean, and more.
Runs locally on macOS (MPS) — no API key required.

Voice cloning: provide an audio_prompt_path to clone a voice from a reference
audio file. Without it, uses the built-in default voice (conds.pt).
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

_CHATTERBOX_HF_CACHE = (
    Path.home()
    / ".cache"
    / "huggingface"
    / "hub"
    / "models--ResembleAI--chatterbox"
    / "snapshots"
    / "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18"
)

# Language codes supported by the multilingual v3 model
SUPPORTED_LANGUAGES = {
    "ar": "Arabic",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "es": "Spanish",
    "fi": "Finnish",
    "fr": "French",
    "he": "Hebrew",
    "hi": "Hindi",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "ms": "Malay",
    "nl": "Dutch",
    "no": "Norwegian",
    "pl": "Polish",
    "pt": "Portuguese",
    "ru": "Russian",
    "sv": "Swedish",
    "sw": "Swahili",
    "tr": "Turkish",
    "zh": "Chinese",
}

# Default recommended voices for common languages (using the built-in default)
# Chatterbox is zero-shot voice cloning — there are no preset speaker names.
# The default conds.pt provides a generic English female voice.
# To use a different voice, pass an audio_prompt_path to clone from.
LANGUAGE_VOICE_NOTES = {
    "en": "Default conds.pt voice (English female). Provide audio_prompt_path for voice cloning.",
    "zh": "Default conds.pt voice. Provide a Mandarin reference audio for better Chinese prosody.",
    "ja": "Default conds.pt voice. Provide a Japanese reference audio for better prosody.",
    "ko": "Default conds.pt voice. Provide a Korean reference audio for better prosody.",
}


class ChatterboxTTS(BaseTool):
    name = "chatterbox_tts"
    version = "0.1.0"
    tier = ToolTier.VOICE
    capability = "tts"
    provider = "chatterbox"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.LOCAL

    dependencies = ["pkg:chatterbox"]
    install_instructions = (
        "Chatterbox is installed locally. If missing:\n"
        "  cd /path/to/chatterbox && pip install -e .\n"
        "Model files are at ~/.cache/huggingface/hub/models--ResembleAI--chatterbox/\n"
        "If missing, download from https://www.modelscope.cn/ResembleAI/chatterbox"
    )
    agent_skills = ["text-to-speech"]

    capabilities = [
        "text_to_speech",
        "offline_generation",
        "multilingual",
        "voice_cloning",
    ]
    supports = {
        "voice_cloning": True,
        "multilingual": True,
        "offline": True,
        "native_audio": True,
        "speed_control": False,
        "pitch_control": False,
        "emotion_control": True,
    }
    best_for = [
        "zero-shot voice cloning from reference audio",
        "multilingual TTS with Chinese support",
        "emotion-controllable narration",
        "privacy-sensitive local-only workflows",
    ]
    not_good_for = [
        "best-in-class expressive voice quality (ElevenLabs is better)",
        "real-time streaming",
        "extremely long-form narration (>30 min)",
    ]

    input_schema = {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {"type": "string", "description": "Text to synthesize"},
            "language_id": {
                "type": "string",
                "description": "Language code. Supported: " + ", ".join(sorted(SUPPORTED_LANGUAGES)),
                "default": "en",
            },
            "audio_prompt_path": {
                "type": "string",
                "description": "Path to reference audio WAV file for voice cloning. If omitted, uses the built-in default voice (conds.pt).",
            },
            "exaggeration": {
                "type": "number",
                "description": "Emotion exaggeration factor. 0.0 = flat/monotone, 1.0 = very expressive.",
                "default": 0.5,
                "minimum": 0.0,
                "maximum": 1.0,
            },
            "cfg_weight": {
                "type": "number",
                "description": "Classifier-free guidance weight. Higher = more stable but less diverse. 0.0-1.0.",
                "default": 0.5,
                "minimum": 0.0,
                "maximum": 1.0,
            },
            "temperature": {
                "type": "number",
                "description": "Sampling temperature. 0.0 = deterministic, higher = more varied.",
                "default": 0.8,
                "minimum": 0.0,
                "maximum": 2.0,
            },
            "output_path": {"type": "string", "description": "Output audio file path (.wav)"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=4, ram_mb=4096, vram_mb=2048, disk_mb=100, network_required=False
    )
    retry_policy = RetryPolicy(max_retries=1, retryable_errors=["RuntimeError", "Timeout"])
    idempotency_key_fields = ["text", "language_id", "audio_prompt_path", "exaggeration", "cfg_weight", "temperature"]
    side_effects = ["writes audio file to output_path"]
    user_visible_verification = ["Listen to generated audio for intelligibility"]

    def get_status(self) -> ToolStatus:
        if not _CHATTERBOX_HF_CACHE.exists():
            return ToolStatus.UNAVAILABLE
        required_files = [
            "ve.pt",
            "t3_mtl23ls_v3.safetensors",
            "s3gen.pt",
            "grapheme_mtl_merged_expanded_v1.json",
            "conds.pt",
        ]
        for f in required_files:
            if not (_CHATTERBOX_HF_CACHE / f).exists():
                return ToolStatus.UNAVAILABLE
        # Check package installed without importing (avoids triggering pkuseg download)
        for pkg in ("chatterbox-tts", "chatterbox"):
            try:
                result = subprocess.run(
                    ["python3", "-m", "pip", "show", pkg],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if result.returncode == 0:
                    return ToolStatus.AVAILABLE
            except Exception:
                pass
        return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        if self.get_status() != ToolStatus.AVAILABLE:
            return ToolResult(
                success=False,
                error="Chatterbox TTS not available. Ensure model files exist at "
                f"{_CHATTERBOX_HF_CACHE} and chatterbox package is installed.",
            )

        start = time.time()
        try:
            result = self._generate(inputs)
        except Exception as exc:
            return ToolResult(success=False, error=f"Chatterbox TTS generation failed: {exc}")

        result.duration_seconds = round(time.time() - start, 2)
        return result

    def _generate(self, inputs: dict[str, Any]) -> ToolResult:
        text = inputs["text"]
        language_id = inputs.get("language_id", "en")
        audio_prompt_path = inputs.get("audio_prompt_path")
        exaggeration = float(inputs.get("exaggeration", 0.5))
        cfg_weight = float(inputs.get("cfg_weight", 0.5))
        temperature = float(inputs.get("temperature", 0.8))

        output_path = Path(inputs.get("output_path", "tts_output.wav"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Escape paths for the inline script
        ckpt_dir = str(_CHATTERBOX_HF_CACHE)
        output_path_str = str(output_path.resolve())

        # Build the inline Python script that will be exec'd
        audio_prompt_arg = ""
        if audio_prompt_path:
            audio_prompt_arg = f", audio_prompt_path={repr(audio_prompt_path)}"

        wrapper_path = Path(__file__).parent / "_chatterbox_wrapper.py"

        inference_script = (
            "import sys, torch, soundfile as sf\n"
            "from pathlib import Path\n"
            "sys.path.insert(0, '/Users/hon/dad/work/ai-local/chatterbox/src')\n"
            "from chatterbox import ChatterboxMultilingualTTS\n"
            "device = 'mps' if torch.backends.mps.is_available() else 'cpu'\n"
            f"model = ChatterboxMultilingualTTS.from_local('{ckpt_dir}', device, t3_model='t3_mtl23ls_v3')\n"
            f"wav = model.generate(\n"
            f"    text={repr(text)},\n"
            f"    language_id='{language_id}'{audio_prompt_arg},\n"
            f"    exaggeration={exaggeration},\n"
            f"    cfg_weight={cfg_weight},\n"
            f"    temperature={temperature},\n"
            f")\n"
            f"sf.write('{output_path_str}', wav.squeeze(0).numpy(), model.sr)\n"
            "print('OK')\n"
        )

        proc = subprocess.run(
            ["python3", str(wrapper_path), "-c", inference_script],
            capture_output=True,
            text=True,
            timeout=600,
            env={**os.environ, "PYTORCH_ENABLE_MPS_FALLBACK": "1"},
        )

        if proc.returncode != 0:
            stderr = proc.stderr[:1000]
            return ToolResult(
                success=False,
                error=f"Chatterbox failed (exit {proc.returncode}): {stderr}",
            )
        if not output_path.exists():
            return ToolResult(
                success=False,
                error=f"Chatterbox output file missing: {output_path}",
            )
        if "ERROR:" in proc.stdout:
            return ToolResult(
                success=False,
                error=f"Chatterbox error: {proc.stdout}",
            )

        return ToolResult(
            success=True,
            data={
                "provider": self.provider,
                "model": "t3_mtl23ls_v3",
                "language_id": language_id,
                "voice_source": audio_prompt_path or "built-in default (conds.pt)",
                "exaggeration": exaggeration,
                "cfg_weight": cfg_weight,
                "temperature": temperature,
                "text_length": len(text),
                "output": str(output_path),
                "format": "wav",
                "sample_rate": 24000,
            },
            artifacts=[str(output_path)],
            model="t3_mtl23ls_v3",
        )
