"""
generator.py — MultimodalGenerator
Handles: image generation (Stable Diffusion), speech synthesis (pyttsx3), text generation (LLaMA 3)
"""

import os
import uuid
import logging
import time
import requests

import config

logger = logging.getLogger(__name__)


def _unique_filename(ext: str) -> str:
    ts   = int(time.time())
    uid  = uuid.uuid4().hex[:8]
    return f"{ts}_{uid}.{ext}"


def _ollama_generate(model: str, prompt: str) -> str:
    payload = {"model": model, "prompt": prompt, "stream": False}
    try:
        resp = requests.post(
            f"{config.OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=config.OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Cannot connect to Ollama. Make sure it is running: ollama serve")
    except requests.exceptions.Timeout:
        raise RuntimeError("Ollama request timed out.")
    except Exception as exc:
        raise RuntimeError(f"Ollama error: {exc}") from exc


# ──────────────────────────────────────────────────────────────────────────────
class MultimodalGenerator:

    def __init__(self):
        self._sd_pipe     = None   # lazy-loaded
        self._tts_engine  = None   # lazy-loaded

    # ── Stable Diffusion (lazy) ───────────────────────────────────────────────
    def _get_sd_pipe(self):
        if self._sd_pipe is None:
            try:
                import torch
                from diffusers import StableDiffusionPipeline

                device = config.SD_DEVICE
                if device == "cuda" and not torch.cuda.is_available():
                    logger.warning("CUDA not available — falling back to CPU.")
                    device = "cpu"

                dtype = torch.float16 if device == "cuda" else torch.float32
                logger.info("Loading Stable Diffusion '%s' on %s …", config.SD_MODEL_ID, device)

                self._sd_pipe = StableDiffusionPipeline.from_pretrained(
                    config.SD_MODEL_ID,
                    torch_dtype=dtype,
                    safety_checker=None,
                )
                self._sd_pipe = self._sd_pipe.to(device)
                logger.info("Stable Diffusion loaded.")
            except ImportError as exc:
                raise RuntimeError(
                    f"diffusers/torch missing: {exc}. "
                    "Run: pip install torch diffusers transformers"
                ) from exc
        return self._sd_pipe

    # ── pyttsx3 (lazy) ───────────────────────────────────────────────────────
    def _get_tts(self):
        if self._tts_engine is None:
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty("rate",   config.TTS_RATE)
                engine.setProperty("volume", config.TTS_VOLUME)
                self._tts_engine = engine
                logger.info("pyttsx3 TTS engine initialised.")
            except ImportError as exc:
                raise RuntimeError(
                    f"pyttsx3 missing: {exc}. Run: pip install pyttsx3"
                ) from exc
        return self._tts_engine

    # ── Image Generation ──────────────────────────────────────────────────────
    def generate_image(self, prompt: str, negative_prompt: str = "") -> dict:
        if not prompt.strip():
            return {"error": "Image prompt cannot be empty."}
        try:
            pipe = self._get_sd_pipe()
            logger.info("Generating image for prompt: %s …", prompt[:80])

            kwargs: dict = {
                "prompt":            prompt,
                "height":            config.SD_IMAGE_SIZE[1],
                "width":             config.SD_IMAGE_SIZE[0],
                "num_inference_steps": config.SD_INFERENCE_STEPS,
            }
            if negative_prompt.strip():
                kwargs["negative_prompt"] = negative_prompt

            result     = pipe(**kwargs)
            image      = result.images[0]
            filename   = _unique_filename("png")
            out_path   = os.path.join(config.OUTPUT_FOLDER, filename)
            image.save(out_path)
            logger.info("Image saved: %s", out_path)

            return {
                "type":     "image_generation",
                "filename": filename,
                "url":      f"/generated_outputs/{filename}",
                "prompt":   prompt,
                "size":     f"{config.SD_IMAGE_SIZE[0]}×{config.SD_IMAGE_SIZE[1]}",
            }
        except Exception as exc:
            logger.error("Image generation failed: %s", exc)
            return {"error": str(exc)}

    # ── Speech Generation ─────────────────────────────────────────────────────
    def generate_speech(self, text: str) -> dict:
        if not text.strip():
            return {"error": "Text for speech cannot be empty."}
        try:
            engine   = self._get_tts()
            filename = _unique_filename("wav")
            out_path = os.path.join(config.OUTPUT_FOLDER, filename)

            engine.save_to_file(text, out_path)
            engine.runAndWait()
            logger.info("Speech saved: %s", out_path)

            return {
                "type":     "speech_generation",
                "filename": filename,
                "url":      f"/generated_outputs/{filename}",
                "text":     text[:200],
            }
        except Exception as exc:
            logger.error("Speech generation failed: %s", exc)
            return {"error": str(exc)}

    # ── Text Generation ───────────────────────────────────────────────────────
    def generate_text(self, prompt: str, style: str = "") -> dict:
        if not prompt.strip():
            return {"error": "Prompt cannot be empty."}
        try:
            full_prompt = prompt
            if style.strip():
                full_prompt = f"Write in the style of {style}:\n\n{prompt}"

            logger.info("Generating text for: %s …", prompt[:80])
            response = _ollama_generate(
                model=config.OLLAMA_TEXT_MODEL,
                prompt=full_prompt,
            )
            return {
                "type":     "text_generation",
                "model":    config.OLLAMA_TEXT_MODEL,
                "response": response,
            }
        except Exception as exc:
            logger.error("Text generation failed: %s", exc)
            return {"error": str(exc)}

    # ── Unified dispatch ──────────────────────────────────────────────────────
    def generate(self, generation_type: str, prompt: str, **kwargs) -> dict:
        """
        generation_type: 'image' | 'speech' | 'text'
        """
        if generation_type == "image":
            return self.generate_image(prompt, kwargs.get("negative_prompt", ""))
        elif generation_type == "speech":
            return self.generate_speech(prompt)
        elif generation_type == "text":
            return self.generate_text(prompt, kwargs.get("style", ""))
        else:
            return {"error": f"Unknown generation type: {generation_type}"}
