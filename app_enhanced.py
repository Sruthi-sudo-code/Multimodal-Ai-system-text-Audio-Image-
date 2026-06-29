"""
app_enhanced.py — Flask server + inline single-page UI for the Multimodal AI System
Run:  python app_enhanced.py
Open: http://localhost:5000
"""

import os
import logging
import json
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, send_from_directory, Response
from typing import Optional

import config
from main      import MultimodalAI
from generator import MultimodalGenerator

# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level   = getattr(logging, config.LOG_LEVEL),
    format  = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt = "%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key              = config.SECRET_KEY
app.config["UPLOAD_FOLDER"] = config.UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_MB * 1024 * 1024

analyser  = MultimodalAI()
generator = MultimodalGenerator()


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in config.ALLOWED_EXTENSIONS


def detect_media_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext in {"png", "jpg", "jpeg", "gif", "bmp", "webp"}:
        return "image"
    if ext in {"mp3", "wav", "ogg", "flac", "m4a"}:
        return "audio"
    if ext in {"mp4", "avi", "mov", "mkv", "webm"}:
        return "video"
    return "text"


# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(config.UPLOAD_FOLDER, filename)


@app.route("/generated_outputs/<path:filename>")
def serve_output(filename):
    return send_from_directory(config.OUTPUT_FOLDER, filename)


@app.route("/process", methods=["POST"])
def process():
    try:
        mode             = request.form.get("mode", "analysis")
        prompt           = request.form.get("prompt", "").strip()
        generation_type  = request.form.get("generation_type", "text")
        negative_prompt  = request.form.get("negative_prompt", "")
        style            = request.form.get("style", "")

        file_path: Optional[str] = None

        # ── Save uploaded file ────────────────────────────────────────────────
        if "file" in request.files:
            f = request.files["file"]
            if f and f.filename and allowed_file(f.filename):
                safe_name = secure_filename(f.filename)
                file_path = os.path.join(config.UPLOAD_FOLDER, safe_name)
                f.save(file_path)
                logger.info("File saved: %s", file_path)
            elif f and f.filename:
                return jsonify({"error": f"File type not allowed: {f.filename}"}), 400

        # ── Dispatch ──────────────────────────────────────────────────────────
        if mode == "analysis":
            if not prompt and not file_path:
                return jsonify({"error": "Please provide a prompt or upload a file."}), 400

            media_type = detect_media_type(Path(file_path).name) if file_path else "text"
            result     = analyser.analyze(file_path, prompt, media_type)

        elif mode == "generation":
            if not prompt:
                return jsonify({"error": "Please enter a generation prompt."}), 400

            result = generator.generate(
                generation_type,
                prompt,
                negative_prompt=negative_prompt,
                style=style,
            )
        else:
            return jsonify({"error": f"Unknown mode: {mode}"}), 400

        if "error" in result:
            return jsonify(result), 500
        return jsonify(result)

    except Exception as exc:
        logger.exception("Unhandled error in /process")
        return jsonify({"error": str(exc)}), 500


# ──────────────────────────────────────────────────────────────────────────────
# Main page (single-page app, served inline)
# ──────────────────────────────────────────────────────────────────────────────

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"/>
<meta http-equiv="Pragma" content="no-cache"/>
<meta http-equiv="Expires" content="0"/>
<title>Multimodal AI System</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<style>
/* ─── Reset & Base ─────────────────────────────────────────────────────── */
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

:root{
  --bg:         #07090f;
  --surface:    #0e1117;
  --surface2:   #141720;
  --border:     #1e2330;
  --accent:     #00e5ff;
  --accent2:    #00ff9d;
  --accent3:    #7b5ea7;
  --text:       #e2e8f0;
  --muted:      #6b7280;
  --danger:     #ff4d6d;
  --warn:       #fbbf24;
  --radius:     12px;
  --font-ui:    'Syne', sans-serif;
  --font-mono:  'JetBrains Mono', monospace;
  --glow:       0 0 20px rgba(0,229,255,0.15);
  --glow2:      0 0 20px rgba(0,255,157,0.15);
}

html{scroll-behavior:smooth}
body{
  background:var(--bg);
  color:var(--text);
  font-family:var(--font-ui);
  min-height:100vh;
  overflow-x:hidden;
}

/* ─── Noise overlay ────────────────────────────────────────────────────── */
body::before{
  content:'';
  position:fixed;inset:0;
  background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
  pointer-events:none;z-index:0;opacity:.4;
}

/* ─── Layout ───────────────────────────────────────────────────────────── */
.wrapper{
  position:relative;z-index:1;
  max-width:1100px;
  margin:0 auto;
  padding:2rem 1.5rem 4rem;
}

/* ─── Header ───────────────────────────────────────────────────────────── */
header{
  display:flex;align-items:center;justify-content:space-between;
  padding:1.25rem 0 2rem;
  border-bottom:1px solid var(--border);
  margin-bottom:2.5rem;
}
.logo{
  display:flex;align-items:center;gap:.75rem;
  font-size:1.35rem;font-weight:800;letter-spacing:-.02em;
}
.logo-icon{
  width:36px;height:36px;border-radius:10px;
  background:linear-gradient(135deg,var(--accent),var(--accent2));
  display:grid;place-items:center;font-size:1rem;
}
.logo-sub{font-size:.7rem;font-weight:400;color:var(--muted);letter-spacing:.08em;text-transform:uppercase;}
.status-dot{
  display:flex;align-items:center;gap:.5rem;
  font-size:.75rem;color:var(--muted);font-family:var(--font-mono);
}
.dot{
  width:8px;height:8px;border-radius:50%;
  background:var(--accent2);
  box-shadow:0 0 8px var(--accent2);
  animation:pulse 2s ease-in-out infinite;
}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}

/* ─── Mode Tabs ────────────────────────────────────────────────────────── */
.tabs{
  display:flex;gap:.5rem;
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:var(--radius);
  padding:.35rem;
  margin-bottom:2rem;
  width:fit-content;
}
.tab{
  padding:.55rem 1.4rem;
  border:none;outline:none;cursor:pointer;
  border-radius:9px;
  font-family:var(--font-ui);font-size:.85rem;font-weight:600;
  color:var(--muted);background:transparent;
  transition:all .25s ease;letter-spacing:.02em;
}
.tab.active{
  color:var(--bg);
  background:linear-gradient(135deg,var(--accent),var(--accent2));
  box-shadow:var(--glow);
}
.tab:not(.active):hover{color:var(--text);background:var(--surface2);}

/* ─── Panels ───────────────────────────────────────────────────────────── */
.panel{display:none;animation:fadeIn .3s ease}
.panel.active{display:block}
@keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}

/* ─── Cards ────────────────────────────────────────────────────────────── */
.card{
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:var(--radius);
  padding:1.5rem;
  margin-bottom:1.25rem;
}
.card-title{
  font-size:.7rem;font-weight:700;
  text-transform:uppercase;letter-spacing:.1em;
  color:var(--muted);margin-bottom:1rem;
}

/* ─── Upload Zone ──────────────────────────────────────────────────────── */
.upload-zone{
  border:2px dashed var(--border);
  border-radius:var(--radius);
  padding:2rem;
  text-align:center;cursor:pointer;
  transition:all .25s ease;
  position:relative;
}
.upload-zone:hover,.upload-zone.drag-over{
  border-color:var(--accent);
  background:rgba(0,229,255,.04);
  box-shadow:var(--glow);
}
.upload-icon{font-size:2rem;margin-bottom:.75rem;opacity:.5}
.upload-text{font-size:.85rem;color:var(--muted)}
.upload-text strong{color:var(--accent);cursor:pointer}
.upload-input{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%;}
.file-info{
  display:none;
  margin-top:.75rem;padding:.75rem 1rem;
  background:var(--surface2);border-radius:8px;
  font-family:var(--font-mono);font-size:.75rem;color:var(--accent2);
  text-align:left;
}
.file-info.show{display:flex;align-items:center;gap:.5rem}
.file-badge{
  background:rgba(0,255,157,.1);
  color:var(--accent2);
  padding:.2rem .6rem;border-radius:4px;
  font-size:.65rem;font-weight:600;text-transform:uppercase;
}

/* ─── Textarea & Inputs ────────────────────────────────────────────────── */
textarea,input[type=text]{
  width:100%;
  background:var(--surface2);
  border:1px solid var(--border);
  border-radius:9px;
  color:var(--text);
  font-family:var(--font-ui);font-size:.9rem;
  padding:.75rem 1rem;
  outline:none;
  transition:border-color .2s,box-shadow .2s;
  resize:vertical;
}
textarea:focus,input[type=text]:focus{
  border-color:var(--accent);
  box-shadow:var(--glow);
}
textarea::placeholder,input::placeholder{color:var(--muted)}
textarea{min-height:90px}

/* ─── Select ───────────────────────────────────────────────────────────── */
select{
  background:var(--surface2);
  border:1px solid var(--border);
  border-radius:9px;
  color:var(--text);
  font-family:var(--font-ui);font-size:.85rem;
  padding:.65rem 1rem;
  outline:none;
  cursor:pointer;
  width:100%;
  transition:border-color .2s;
}
select:focus{border-color:var(--accent)}

/* ─── Buttons ──────────────────────────────────────────────────────────── */
.btn{
  display:inline-flex;align-items:center;justify-content:center;gap:.5rem;
  padding:.7rem 1.6rem;
  border:none;outline:none;cursor:pointer;
  border-radius:9px;
  font-family:var(--font-ui);font-size:.9rem;font-weight:700;
  letter-spacing:.02em;
  transition:all .2s ease;
}
.btn-primary{
  background:linear-gradient(135deg,var(--accent),var(--accent2));
  color:var(--bg);
  box-shadow:var(--glow);
}
.btn-primary:hover{transform:translateY(-1px);box-shadow:0 0 30px rgba(0,229,255,.3)}
.btn-primary:active{transform:translateY(0)}
.btn-secondary{
  background:var(--surface2);
  color:var(--text);
  border:1px solid var(--border);
}
.btn-secondary:hover{border-color:var(--accent);color:var(--accent)}
.btn:disabled{opacity:.4;cursor:not-allowed;transform:none!important}

/* ─── Grid helpers ─────────────────────────────────────────────────────── */
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.grid-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem}
@media(max-width:640px){.grid-2,.grid-3{grid-template-columns:1fr}}

/* ─── Labels ───────────────────────────────────────────────────────────── */
label{
  display:block;
  font-size:.75rem;font-weight:600;
  color:var(--muted);
  text-transform:uppercase;letter-spacing:.07em;
  margin-bottom:.4rem;
}

/* ─── Loading spinner ──────────────────────────────────────────────────── */
.spinner-wrap{
  display:none;flex-direction:column;align-items:center;
  justify-content:center;gap:1rem;
  padding:2.5rem;
}
.spinner-wrap.show{display:flex}
.spinner{
  width:40px;height:40px;border-radius:50%;
  border:3px solid var(--border);
  border-top-color:var(--accent);
  animation:spin .8s linear infinite;
}
@keyframes spin{to{transform:rotate(360deg)}}
.spinner-text{font-size:.8rem;color:var(--muted);font-family:var(--font-mono)}

/* ─── Result area ──────────────────────────────────────────────────────── */
#result-area{display:none}
#result-area.show{display:block;animation:fadeIn .3s ease}

.result-card{
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:var(--radius);
  overflow:hidden;
}
.result-header{
  display:flex;align-items:center;justify-content:space-between;
  padding:1rem 1.25rem;
  border-bottom:1px solid var(--border);
  background:var(--surface2);
}
.result-type{
  display:flex;align-items:center;gap:.5rem;
  font-size:.75rem;font-weight:700;
  text-transform:uppercase;letter-spacing:.08em;
  color:var(--accent);
}
.result-model{
  font-family:var(--font-mono);font-size:.7rem;color:var(--muted);
}
.result-body{padding:1.25rem}

.result-text{
  font-size:.9rem;line-height:1.7;color:var(--text);
  white-space:pre-wrap;word-break:break-word;
}

/* image / audio / video previews */
.preview-image{
  max-width:100%;border-radius:9px;
  border:1px solid var(--border);
  margin-bottom:1rem;
}
.preview-audio{width:100%;margin-bottom:1rem}
.preview-video{width:100%;border-radius:9px;border:1px solid var(--border);margin-bottom:1rem}

.download-link{
  display:inline-flex;align-items:center;gap:.4rem;
  font-size:.8rem;font-family:var(--font-mono);
  color:var(--accent2);text-decoration:none;
  padding:.4rem .9rem;border-radius:6px;
  border:1px solid rgba(0,255,157,.2);
  background:rgba(0,255,157,.05);
  transition:all .2s;
}
.download-link:hover{background:rgba(0,255,157,.1);border-color:var(--accent2);}

/* frame grid for video analysis */
.frame-grid{
  display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));
  gap:1rem;margin-top:1rem;
}
.frame-item{
  background:var(--surface2);border-radius:9px;padding:.75rem;
  border:1px solid var(--border);
}
.frame-ts{
  font-family:var(--font-mono);font-size:.7rem;color:var(--accent);
  margin-bottom:.4rem;
}
.frame-desc{font-size:.8rem;color:var(--muted);line-height:1.5}

/* ─── Error box ────────────────────────────────────────────────────────── */
.error-box{
  background:rgba(255,77,109,.07);
  border:1px solid rgba(255,77,109,.3);
  border-radius:var(--radius);
  padding:1rem 1.25rem;
  color:var(--danger);
  font-size:.85rem;
  display:flex;gap:.75rem;align-items:flex-start;
}
.error-icon{font-size:1.1rem;flex-shrink:0;margin-top:.1rem}

/* ─── Section heading ──────────────────────────────────────────────────── */
.section-label{
  font-size:.7rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.1em;color:var(--muted);
  margin-bottom:.6rem;display:block;
}

/* ─── Generation type pills ────────────────────────────────────────────── */
.gen-types{display:flex;gap:.5rem;flex-wrap:wrap}
.gen-pill{
  padding:.45rem 1rem;
  border:1px solid var(--border);border-radius:999px;
  font-size:.8rem;font-weight:600;color:var(--muted);
  background:transparent;cursor:pointer;
  transition:all .2s;
}
.gen-pill.active{
  color:var(--bg);
  background:linear-gradient(135deg,var(--accent3),var(--accent));
  border-color:transparent;
}
.gen-pill:not(.active):hover{color:var(--text);border-color:var(--accent3)}

/* extra generation options */
.extra-opts{display:none;margin-top:.75rem;animation:fadeIn .2s ease}
.extra-opts.show{display:block}

/* ─── Scrollbar ────────────────────────────────────────────────────────── */
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:var(--surface)}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:999px}

/* ─── Footer ───────────────────────────────────────────────────────────── */
footer{
  margin-top:4rem;padding-top:1.5rem;
  border-top:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;
  flex-wrap:wrap;gap:1rem;
}
.footer-text{font-size:.72rem;color:var(--muted);font-family:var(--font-mono)}
.footer-links{display:flex;gap:1.25rem}
.footer-links a{
  font-size:.72rem;color:var(--muted);text-decoration:none;
  font-family:var(--font-mono);transition:color .2s;
}
.footer-links a:hover{color:var(--accent)}
</style>
</head>
<body>
<div class="wrapper">

  <!-- ─── Header ─────────────────────────────────────────────────────── -->
  <header>
    <div class="logo">
      <div class="logo-icon">✦</div>
      <div>
        Multimodal AI
        <div class="logo-sub">Powered by Ollama · LLaVA · LLaMA 3</div>
      </div>
    </div>
    <div class="status-dot">
      <div class="dot"></div>
      Local &amp; Private
    </div>
  </header>

  <!-- ─── Mode Tabs ───────────────────────────────────────────────────── -->
  <div class="tabs" role="tablist">
    <button class="tab active" id="tab-analysis"
            onclick="switchMode('analysis', event)" role="tab">
      ◈ Analysis
    </button>
    <button class="tab" id="tab-generation"
            onclick="switchMode('generation', event)" role="tab">
      ◇ Generation
    </button>
  </div>

  <!-- ════════════════════ ANALYSIS PANEL ════════════════════════════ -->
  <div class="panel active" id="panel-analysis">

    <!-- Upload -->
    <div class="card">
      <div class="card-title">Upload Media (optional)</div>
      <div class="upload-zone" id="upload-zone"
           ondragover="handleDragOver(event)"
           ondragleave="handleDragLeave(event)"
           ondrop="handleDrop(event)">
        <div class="upload-icon">⬆</div>
        <div class="upload-text">
          Drag &amp; drop or <strong onclick="document.getElementById('file-input').click()">browse</strong>
        </div>
        <div class="upload-text" style="font-size:.72rem;margin-top:.35rem;color:var(--muted)">
          Images · Audio · Video &nbsp;|&nbsp; Max 100 MB
        </div>
        <input type="file" id="file-input" class="upload-input"
               accept="image/*,audio/*,video/*"
               onchange="handleFileSelect(event)"/>
        <div class="file-info" id="file-info">
          <span class="file-badge" id="file-badge">IMG</span>
          <span id="file-name">filename.png</span>
          <span style="color:var(--muted)" id="file-size">0 KB</span>
        </div>
      </div>
    </div>

    <!-- Question -->
    <div class="card">
      <div class="card-title">Your Question / Prompt</div>
      <textarea id="analysis-prompt"
                placeholder="Ask anything about the uploaded media, or enter a text prompt for a direct conversation…"></textarea>
    </div>

    <!-- Submit -->
    <div style="display:flex;gap:.75rem;flex-wrap:wrap">
      <button class="btn btn-primary" onclick="analyze()">
        ◈ Analyze Content
      </button>
      <button class="btn btn-secondary" onclick="clearAnalysis()">
        ✕ Clear
      </button>
    </div>

  </div><!-- /panel-analysis -->

  <!-- ════════════════════ GENERATION PANEL ═══════════════════════════ -->
  <div class="panel" id="panel-generation">

    <!-- Generation type -->
    <div class="card">
      <div class="card-title">Generation Type</div>
      <div class="gen-types" id="gen-types">
        <button class="gen-pill active" data-type="image"
                onclick="setGenType('image', event)">🖼 Image</button>
        <button class="gen-pill" data-type="speech"
                onclick="setGenType('speech', event)">🔊 Speech</button>
        <button class="gen-pill" data-type="text"
                onclick="setGenType('text', event)">✦ Text</button>
      </div>
    </div>

    <!-- Prompt -->
    <div class="card">
      <div class="card-title">Generation Prompt</div>
      <textarea id="generation-prompt"
                placeholder="Describe what you want to generate…"></textarea>

      <!-- Extra: image negative prompt -->
      <div class="extra-opts show" id="extra-image">
        <label>Negative Prompt (optional)</label>
        <input type="text" id="negative-prompt"
               placeholder="blurry, low quality, deformed…"/>
      </div>

      <!-- Extra: text style -->
      <div class="extra-opts" id="extra-text">
        <label>Writing Style (optional)</label>
        <input type="text" id="text-style"
               placeholder="e.g. Ernest Hemingway, technical documentation, haiku…"/>
      </div>
    </div>

    <!-- Submit -->
    <div style="display:flex;gap:.75rem;flex-wrap:wrap">
      <button class="btn btn-primary" onclick="generate()">
        ◇ Generate
      </button>
      <button class="btn btn-secondary" onclick="clearGeneration()">
        ✕ Clear
      </button>
    </div>

  </div><!-- /panel-generation -->

  <!-- ─── Spinner ─────────────────────────────────────────────────────── -->
  <div class="spinner-wrap" id="spinner">
    <div class="spinner"></div>
    <div class="spinner-text" id="spinner-text">Processing…</div>
  </div>

  <!-- ─── Result ──────────────────────────────────────────────────────── -->
  <div id="result-area"></div>

  <!-- ─── Footer ─────────────────────────────────────────────────────── -->
  <footer>
    <span class="footer-text">multimodal-ai · flask 3 · ollama · whisper · stable-diffusion</span>
    <div class="footer-links">
      <a href="https://ollama.ai" target="_blank">Ollama</a>
      <a href="https://github.com/openai/whisper" target="_blank">Whisper</a>
      <a href="https://huggingface.co/runwayml/stable-diffusion-v1-5" target="_blank">SD v1.5</a>
    </div>
  </footer>

</div><!-- /wrapper -->

<script>
/* ─── State ──────────────────────────────────────────────────────────────── */
let selectedFile  = null;
let currentMode   = 'analysis';
let currentGenType = 'image';

/* ─── Mode switching ─────────────────────────────────────────────────────── */
window.switchMode = function(mode, event) {
  if (event) event.preventDefault();
  currentMode = mode;

  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));

  const tabEl   = document.getElementById('tab-' + mode);
  const panelEl = document.getElementById('panel-' + mode);
  if (tabEl)   tabEl.classList.add('active');
  if (panelEl) panelEl.classList.add('active');

  clearResult();
  console.log('[mode]', mode);
};

/* ─── Generation type ────────────────────────────────────────────────────── */
window.setGenType = function(type, event) {
  if (event) event.preventDefault();
  currentGenType = type;

  document.querySelectorAll('.gen-pill').forEach(p => p.classList.remove('active'));
  const pill = document.querySelector(`.gen-pill[data-type="${type}"]`);
  if (pill) pill.classList.add('active');

  // Show/hide extra options
  const extraImage = document.getElementById('extra-image');
  const extraText  = document.getElementById('extra-text');
  if (extraImage) extraImage.classList.toggle('show', type === 'image');
  if (extraText)  extraText.classList.toggle('show',  type === 'text');

  // Update placeholder
  const ta = document.getElementById('generation-prompt');
  if (ta) {
    const placeholders = {
      image:  'A futuristic cyberpunk cityscape at night, neon reflections on rain-soaked streets…',
      speech: 'Enter the text you want to convert to speech…',
      text:   'Write a short story about a robot who learns to paint…',
    };
    ta.placeholder = placeholders[type] || 'Describe what you want to generate…';
  }
  console.log('[gen-type]', type);
};

/* ─── File handling ──────────────────────────────────────────────────────── */
window.handleFileSelect = function(event) {
  const file = event.target.files && event.target.files[0];
  if (file) setSelectedFile(file);
};

window.handleDragOver = function(event) {
  event.preventDefault();
  const zone = document.getElementById('upload-zone');
  if (zone) zone.classList.add('drag-over');
};

window.handleDragLeave = function(event) {
  const zone = document.getElementById('upload-zone');
  if (zone) zone.classList.remove('drag-over');
};

window.handleDrop = function(event) {
  event.preventDefault();
  const zone = document.getElementById('upload-zone');
  if (zone) zone.classList.remove('drag-over');
  const file = event.dataTransfer.files && event.dataTransfer.files[0];
  if (file) setSelectedFile(file);
};

function setSelectedFile(file) {
  selectedFile = file;
  const info   = document.getElementById('file-info');
  const badge  = document.getElementById('file-badge');
  const name   = document.getElementById('file-name');
  const size   = document.getElementById('file-size');

  if (!info) return;
  info.classList.add('show');

  const ext = file.name.split('.').pop().toUpperCase();
  if (badge) badge.textContent = ext;
  if (name)  name.textContent  = file.name;
  if (size) {
    const kb = (file.size / 1024).toFixed(1);
    size.textContent = kb > 1024 ? (kb / 1024).toFixed(1) + ' MB' : kb + ' KB';
  }
  console.log('[file]', file.name, file.size);
}

/* ─── Analysis ───────────────────────────────────────────────────────────── */
window.analyze = async function() {
  const promptEl = document.getElementById('analysis-prompt');
  const prompt   = promptEl ? promptEl.value.trim() : '';

  if (!prompt && !selectedFile) {
    showError('Please upload a file or enter a prompt before analyzing.');
    return;
  }

  const formData = new FormData();
  formData.append('mode', 'analysis');
  formData.append('prompt', prompt);
  if (selectedFile) formData.append('file', selectedFile);

  showSpinner('Analyzing with AI…');
  try {
    const resp = await fetch('/process', { method: 'POST', body: formData });
    const data = await resp.json();
    hideSpinner();
    if (data.error) { showError(data.error); return; }
    renderAnalysisResult(data);
  } catch (err) {
    hideSpinner();
    showError('Network error: ' + err.message);
    console.error('[analyze]', err);
  }
};

window.clearAnalysis = function() {
  selectedFile = null;
  const promptEl = document.getElementById('analysis-prompt');
  const fileInfo = document.getElementById('file-info');
  const fileInput = document.getElementById('file-input');
  if (promptEl)  promptEl.value = '';
  if (fileInfo)  fileInfo.classList.remove('show');
  if (fileInput) fileInput.value = '';
  clearResult();
};

/* ─── Generation ─────────────────────────────────────────────────────────── */
window.generate = async function() {
  const promptEl = document.getElementById('generation-prompt');
  const prompt   = promptEl ? promptEl.value.trim() : '';

  if (!prompt) {
    showError('Please enter a generation prompt.');
    return;
  }

  const negEl   = document.getElementById('negative-prompt');
  const styleEl = document.getElementById('text-style');

  const formData = new FormData();
  formData.append('mode', 'generation');
  formData.append('generation_type', currentGenType);
  formData.append('prompt', prompt);
  if (negEl)   formData.append('negative_prompt', negEl.value);
  if (styleEl) formData.append('style', styleEl.value);

  const labels = { image: 'Generating image…', speech: 'Synthesising speech…', text: 'Writing…' };
  showSpinner(labels[currentGenType] || 'Generating…');

  try {
    const resp = await fetch('/process', { method: 'POST', body: formData });
    const data = await resp.json();
    hideSpinner();
    if (data.error) { showError(data.error); return; }
    renderGenerationResult(data);
  } catch (err) {
    hideSpinner();
    showError('Network error: ' + err.message);
    console.error('[generate]', err);
  }
};

window.clearGeneration = function() {
  const p = document.getElementById('generation-prompt');
  const n = document.getElementById('negative-prompt');
  const s = document.getElementById('text-style');
  if (p) p.value = '';
  if (n) n.value = '';
  if (s) s.value = '';
  clearResult();
};

/* ─── Render helpers ─────────────────────────────────────────────────────── */
function renderAnalysisResult(data) {
  const area = document.getElementById('result-area');
  if (!area) return;

  let html = `
    <div class="result-card" style="margin-top:1.5rem">
      <div class="result-header">
        <div class="result-type">◈ Analysis Result &nbsp;·&nbsp; ${escHtml(data.type || '')}</div>
        <div class="result-model">${escHtml(data.model || '')}</div>
      </div>
      <div class="result-body">`;

  if (data.type === 'image_analysis') {
    if (data.metadata && Object.keys(data.metadata).length) {
      html += `<div style="display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:1rem">`;
      for (const [k, v] of Object.entries(data.metadata)) {
        html += `<span style="font-family:var(--font-mono);font-size:.7rem;padding:.2rem .6rem;
                  background:var(--surface2);border:1px solid var(--border);border-radius:4px;
                  color:var(--muted)">${escHtml(k)}: <strong style="color:var(--text)">${escHtml(String(v))}</strong></span>`;
      }
      html += `</div>`;
    }
    html += `<div class="result-text">${escHtml(data.response || '')}</div>`;
  }
  else if (data.type === 'audio_analysis') {
    html += `<div style="margin-bottom:1rem">
      <span class="section-label">Transcript (${escHtml(data.language || 'unknown')})</span>
      <div class="result-text" style="background:var(--surface2);padding:.85rem;border-radius:8px;
           border:1px solid var(--border)">${escHtml(data.transcript || '(no speech detected)')}</div>
    </div>`;
    if (data.llm_response) {
      html += `<span class="section-label">AI Answer</span>
               <div class="result-text">${escHtml(data.llm_response)}</div>`;
    }
  }
  else if (data.type === 'video_analysis') {
    html += `<div style="display:flex;gap:.75rem;flex-wrap:wrap;margin-bottom:1rem">
      <span style="font-family:var(--font-mono);font-size:.72rem;color:var(--muted)">
        Duration: <strong style="color:var(--accent)">${data.duration_seconds}s</strong>
      </span>
      <span style="font-family:var(--font-mono);font-size:.72rem;color:var(--muted)">
        Frames: <strong style="color:var(--accent)">${data.total_frames}</strong>
      </span>
      <span style="font-family:var(--font-mono);font-size:.72rem;color:var(--muted)">
        FPS: <strong style="color:var(--accent)">${data.fps}</strong>
      </span>
    </div>`;
    if (data.summary) {
      html += `<span class="section-label">Summary</span>
               <div class="result-text" style="margin-bottom:1rem">${escHtml(data.summary)}</div>`;
    }
    if (data.frame_descriptions && data.frame_descriptions.length) {
      html += `<span class="section-label">Frame Analysis</span><div class="frame-grid">`;
      for (const fd of data.frame_descriptions) {
        html += `<div class="frame-item">
          <div class="frame-ts">⏱ ${fd.timestamp}s</div>
          <div class="frame-desc">${escHtml(fd.description || '')}</div>
        </div>`;
      }
      html += `</div>`;
    }
  }
  else {
    // text_analysis fallback
    html += `<div class="result-text">${escHtml(data.response || JSON.stringify(data, null, 2))}</div>`;
  }

  html += `</div></div>`;
  area.innerHTML = html;
  area.classList.add('show');
  area.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function renderGenerationResult(data) {
  const area = document.getElementById('result-area');
  if (!area) return;

  let html = `
    <div class="result-card" style="margin-top:1.5rem">
      <div class="result-header">
        <div class="result-type">◇ Generation Result &nbsp;·&nbsp; ${escHtml(data.type || '')}</div>
        <div class="result-model">${escHtml(data.model || '')}</div>
      </div>
      <div class="result-body">`;

  if (data.type === 'image_generation') {
    html += `<img src="${escHtml(data.url || '')}" alt="Generated image" class="preview-image"/>
             <br/>
             <a href="${escHtml(data.url || '')}" download class="download-link">
               ↓ Download Image &nbsp;(${escHtml(data.size || '')})
             </a>`;
  }
  else if (data.type === 'speech_generation') {
    html += `<audio controls class="preview-audio" src="${escHtml(data.url || '')}"></audio>
             <br/>
             <a href="${escHtml(data.url || '')}" download class="download-link">↓ Download Audio</a>
             <div style="margin-top:1rem;font-size:.8rem;color:var(--muted)">
               <em>${escHtml((data.text || '').substring(0,200))}…</em>
             </div>`;
  }
  else if (data.type === 'text_generation') {
    html += `<div class="result-text">${escHtml(data.response || '')}</div>`;
  }
  else {
    html += `<pre class="result-text">${escHtml(JSON.stringify(data, null, 2))}</pre>`;
  }

  html += `</div></div>`;
  area.innerHTML = html;
  area.classList.add('show');
  area.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/* ─── UI utilities ───────────────────────────────────────────────────────── */
function showSpinner(msg) {
  const spinner = document.getElementById('spinner');
  const text    = document.getElementById('spinner-text');
  clearResult();
  if (text)    text.textContent = msg || 'Processing…';
  if (spinner) spinner.classList.add('show');
}

function hideSpinner() {
  const spinner = document.getElementById('spinner');
  if (spinner) spinner.classList.remove('show');
}

function clearResult() {
  const area = document.getElementById('result-area');
  if (area) { area.innerHTML = ''; area.classList.remove('show'); }
  hideSpinner();
}

function showError(msg) {
  const area = document.getElementById('result-area');
  if (!area) return;
  area.innerHTML = `
    <div class="error-box" style="margin-top:1.25rem">
      <span class="error-icon">⚠</span>
      <div><strong>Error</strong><br/>${escHtml(msg)}</div>
    </div>`;
  area.classList.add('show');
}

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}

/* ─── Init ───────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  console.log('[init] Multimodal AI System ready.');
  setGenType('image', null);
});
</script>
</body>
</html>"""


@app.route("/")
def index():
    resp = Response(HTML_PAGE, content_type="text/html; charset=utf-8")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"]        = "no-cache"
    resp.headers["Expires"]       = "0"
    return resp


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("╔══════════════════════════════════════╗")
    logger.info("║   Multimodal AI System  —  Flask 3   ║")
    logger.info("╚══════════════════════════════════════╝")
    logger.info("Upload dir   : %s", config.UPLOAD_FOLDER)
    logger.info("Output dir   : %s", config.OUTPUT_FOLDER)
    logger.info("Ollama URL   : %s", config.OLLAMA_BASE_URL)
    logger.info("Listening on : http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
