import os

# ─── Base Paths ────────────────────────────────────────────────────────────────
BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER     = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER     = os.path.join(BASE_DIR, "generated_outputs")

# ─── Ensure directories exist ──────────────────────────────────────────────────
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ─── Flask ─────────────────────────────────────────────────────────────────────
SECRET_KEY        = os.getenv("FLASK_SECRET", "multimodal-ai-secret-2024")
MAX_CONTENT_MB    = 100                          # max upload size in MB
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "webp",
                       "mp3", "wav", "ogg", "flac", "m4a",
                       "mp4", "avi", "mov", "mkv", "webm"}

# ─── Ollama ────────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL   = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_VISION_MODEL = "llava"
OLLAMA_TEXT_MODEL   = "llama3"
OLLAMA_TIMEOUT    = 120   # seconds

# ─── Whisper ───────────────────────────────────────────────────────────────────
WHISPER_MODEL     = "base"        # tiny | base | small | medium | large

# ─── Stable Diffusion ──────────────────────────────────────────────────────────
SD_MODEL_ID       = "runwayml/stable-diffusion-v1-5"
SD_DEVICE         = "cuda"        # fall back to "cpu" automatically
SD_IMAGE_SIZE     = (512, 512)
SD_INFERENCE_STEPS = 20

# ─── TTS ───────────────────────────────────────────────────────────────────────
TTS_RATE          = 175           # words per minute
TTS_VOLUME        = 0.9

# ─── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL         = "INFO"
