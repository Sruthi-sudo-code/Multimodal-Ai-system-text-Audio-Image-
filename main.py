"""
main.py — MultimodalAI analysis engine
Handles: image analysis (LLaVA), audio transcription (Whisper), video frames + text (LLaMA 3)
"""

import os
import base64
import logging
import requests
import tempfile
from pathlib import Path
from typing import Union, List, Optional

import config

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ──────────────────────────────────────────────────────────────────────────────

def _image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _ollama_generate(model: str, prompt: str, images: Optional[List[str]] = None) -> str:
    """
    Send a request to the local Ollama /api/generate endpoint.
    `images` is a list of base64-encoded strings (for LLaVA).
    """
    payload: dict = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    if images:
        payload["images"] = images

    try:
        resp = requests.post(
            f"{config.OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=config.OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Cannot connect to Ollama. Make sure it is running: ollama serve"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("Ollama request timed out. Try a shorter prompt or smaller model.")
    except Exception as exc:
        raise RuntimeError(f"Ollama error: {exc}") from exc


# ──────────────────────────────────────────────────────────────────────────────
# Core MultimodalAI class
# ──────────────────────────────────────────────────────────────────────────────

class MultimodalAI:
    """Unified entry-point for analysis tasks."""

    def __init__(self):
        self._whisper_model = None   # lazy-loaded

    # ── Whisper (lazy load) ───────────────────────────────────────────────────
    def _get_whisper(self):
        if self._whisper_model is None:
            try:
                import whisper
                logger.info("Loading Whisper model '%s' …", config.WHISPER_MODEL)
                self._whisper_model = whisper.load_model(config.WHISPER_MODEL)
                logger.info("Whisper loaded.")
            except ImportError:
                raise RuntimeError(
                    "openai-whisper is not installed. Run: pip install openai-whisper"
                )
        return self._whisper_model

    # ── Image Analysis ────────────────────────────────────────────────────────
    def analyze_image(self, image_path: str, question: str = "") -> dict:
        logger.info("Analyzing image: %s", image_path)
        if not os.path.exists(image_path):
            return {"error": f"Image not found: {image_path}"}

        prompt = question.strip() if question.strip() else (
            "Describe this image in detail. "
            "Include objects, colors, composition, mood, and any notable features."
        )

        try:
            b64 = _image_to_base64(image_path)
            response = _ollama_generate(
                model=config.OLLAMA_VISION_MODEL,
                prompt=prompt,
                images=[b64],
            )
            # Basic metadata via Pillow (optional)
            metadata = {}
            try:
                from PIL import Image as PILImage
                with PILImage.open(image_path) as img:
                    metadata = {
                        "dimensions": f"{img.width}×{img.height}",
                        "mode": img.mode,
                        "format": img.format or Path(image_path).suffix.lstrip(".").upper(),
                    }
            except Exception:
                pass

            return {
                "type": "image_analysis",
                "model": config.OLLAMA_VISION_MODEL,
                "response": response,
                "metadata": metadata,
            }
        except Exception as exc:
            logger.error("Image analysis failed: %s", exc)
            return {"error": str(exc)}

    # ── Audio Analysis ────────────────────────────────────────────────────────
    def analyze_audio(self, audio_path: str, question: str = "") -> dict:
        logger.info("Analyzing audio: %s", audio_path)
        if not os.path.exists(audio_path):
            return {"error": f"Audio file not found: {audio_path}"}

        try:
            model = self._get_whisper()
            result = model.transcribe(audio_path)
            transcript = result.get("text", "").strip()
            detected_lang = result.get("language", "unknown")

            # Follow-up with LLaMA 3 if user asked a question
            llm_response = ""
            if question.strip():
                llm_prompt = (
                    f"The following is a transcript of an audio file:\n\n"
                    f'"""\n{transcript}\n"""\n\n'
                    f"Question: {question.strip()}\n"
                    f"Answer concisely and accurately."
                )
                llm_response = _ollama_generate(
                    model=config.OLLAMA_TEXT_MODEL,
                    prompt=llm_prompt,
                )

            return {
                "type": "audio_analysis",
                "transcript": transcript,
                "language": detected_lang,
                "llm_response": llm_response,
                "model": "whisper + " + config.OLLAMA_TEXT_MODEL if llm_response else "whisper",
            }
        except Exception as exc:
            logger.error("Audio analysis failed: %s", exc)
            return {"error": str(exc)}

    # ── Video Analysis ────────────────────────────────────────────────────────
    def analyze_video(self, video_path: str, question: str = "") -> dict:
        logger.info("Analyzing video: %s", video_path)
        if not os.path.exists(video_path):
            return {"error": f"Video file not found: {video_path}"}

        try:
            import cv2
        except ImportError:
            return {"error": "opencv-python is not installed. Run: pip install opencv-python"}

        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {"error": "Could not open video file."}

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps          = cap.get(cv2.CAP_PROP_FPS) or 24
            duration_sec = total_frames / fps if fps else 0

            # Sample up to 4 evenly-spaced frames
            sample_count = min(4, max(1, total_frames))
            indices      = [int(i * total_frames / sample_count) for i in range(sample_count)]
            frame_descriptions = []

            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if not ret:
                    continue

                # Encode frame as JPEG → base64
                ok, buf = cv2.imencode(".jpg", frame)
                if not ok:
                    continue
                b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

                ts = idx / fps
                frame_prompt = (
                    f"This is frame at {ts:.1f}s of a video. "
                    "Briefly describe what you see (1-2 sentences)."
                )
                desc = _ollama_generate(
                    model=config.OLLAMA_VISION_MODEL,
                    prompt=frame_prompt,
                    images=[b64],
                )
                frame_descriptions.append({"timestamp": round(ts, 1), "description": desc})

            cap.release()

            # Synthesize overall summary
            summary_prompt = (
                "Based on these frame descriptions from a video, "
                "write a cohesive summary of the video content:\n\n"
                + "\n".join(
                    f"[{fd['timestamp']}s] {fd['description']}"
                    for fd in frame_descriptions
                )
            )
            if question.strip():
                summary_prompt += f"\n\nAlso answer: {question.strip()}"

            summary = _ollama_generate(
                model=config.OLLAMA_TEXT_MODEL,
                prompt=summary_prompt,
            )

            return {
                "type": "video_analysis",
                "duration_seconds": round(duration_sec, 1),
                "total_frames": total_frames,
                "fps": round(fps, 2),
                "frame_descriptions": frame_descriptions,
                "summary": summary,
                "model": f"{config.OLLAMA_VISION_MODEL} + {config.OLLAMA_TEXT_MODEL}",
            }
        except Exception as exc:
            logger.error("Video analysis failed: %s", exc)
            return {"error": str(exc)}

    # ── Text / General Analysis ───────────────────────────────────────────────
    def analyze_text(self, prompt: str) -> dict:
        logger.info("Text analysis: %s …", prompt[:80])
        if not prompt.strip():
            return {"error": "Prompt cannot be empty."}
        try:
            response = _ollama_generate(
                model=config.OLLAMA_TEXT_MODEL,
                prompt=prompt,
            )
            return {
                "type": "text_analysis",
                "model": config.OLLAMA_TEXT_MODEL,
                "response": response,
            }
        except Exception as exc:
            logger.error("Text analysis failed: %s", exc)
            return {"error": str(exc)}

    # ── Unified dispatch ──────────────────────────────────────────────────────
    def analyze(self, file_path: Optional[str], question: str, media_type: str) -> dict:
        """
        Dispatch to the correct analyser based on `media_type`.
        media_type: 'image' | 'audio' | 'video' | 'text'
        """
        if media_type == "image" and file_path:
            return self.analyze_image(file_path, question)
        elif media_type == "audio" and file_path:
            return self.analyze_audio(file_path, question)
        elif media_type == "video" and file_path:
            return self.analyze_video(file_path, question)
        else:
            return self.analyze_text(question)
