# Multimodal AI System

A fully local, privacy-first AI system with an Analysis mode and a Generation mode — no external API keys required.

---

## Features

| Mode | Capability | Engine |
|------|-----------|--------|
| Analysis | Image understanding | LLaVA (Ollama) |
| Analysis | Audio transcription + Q&A | Whisper + LLaMA 3 |
| Analysis | Video frame analysis | LLaVA + LLaMA 3 |
| Analysis | Pure text chat | LLaMA 3 (Ollama) |
| Generation | Image synthesis | Stable Diffusion v1-5 |
| Generation | Text-to-speech | pyttsx3 |
| Generation | Creative writing | LLaMA 3 (Ollama) |

---

## Prerequisites

### 1 — Install Ollama

```bash
# macOS / Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows: download installer from https://ollama.ai
```

### 2 — Pull required models

```bash
ollama pull llava      # Vision model (~4 GB)
ollama pull llama3     # Text model (~4 GB)
```

### 3 — Start Ollama server

```bash
ollama serve           # Runs on http://localhost:11434
```

---

## Installation

```bash
# Clone / copy project files into a folder
cd multimodal_ai

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS / Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

> **GPU users**: PyTorch with CUDA will significantly speed up Stable Diffusion.  
> Install the CUDA-enabled build from https://pytorch.org/get-started/locally/ before running `pip install -r requirements.txt`.

---

## Running

```bash
python app_enhanced.py
```

Open **http://localhost:5000** in your browser.

---

## Project Structure

```
multimodal_ai/
├── app_enhanced.py       # Flask server + single-page UI
├── main.py               # MultimodalAI — analysis engine
├── generator.py          # MultimodalGenerator — generation engine
├── config.py             # All configuration constants
├── requirements.txt      # Python dependencies
├── uploads/              # Auto-created: uploaded files
└── generated_outputs/    # Auto-created: generated media
```

---

## Configuration

Edit `config.py` to change:

| Setting | Default | Description |
|---------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `WHISPER_MODEL` | `base` | tiny / base / small / medium / large |
| `SD_MODEL_ID` | `runwayml/stable-diffusion-v1-5` | HuggingFace model ID |
| `SD_DEVICE` | `cuda` | `cuda` or `cpu` |
| `SD_INFERENCE_STEPS` | `20` | More steps = higher quality, slower |
| `MAX_CONTENT_MB` | `100` | Max upload size |

---

## Supported File Types

- **Images**: PNG, JPG, JPEG, GIF, BMP, WEBP  
- **Audio**: MP3, WAV, OGG, FLAC, M4A  
- **Video**: MP4, AVI, MOV, MKV, WEBM  

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `Cannot connect to Ollama` | Run `ollama serve` in a separate terminal |
| `CUDA out of memory` | Set `SD_DEVICE = "cpu"` in `config.py` |
| `whisper not found` | Run `pip install openai-whisper` |
| `pyttsx3 init failed` | On Linux: `sudo apt install espeak` |
| `diffusers missing` | Run `pip install diffusers transformers accelerate` |

---

## License

MIT — use freely for personal or commercial projects.
