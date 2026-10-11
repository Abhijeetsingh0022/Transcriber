"""
Hugging Face Space Entry Point for TMUX Transcriber.
Runs the FastAPI Backend, Next.js Static Studio UI, and mounts Gradio at /gradio.
"""
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure writable data directory in HF environment
os.environ.setdefault("DATA_DIR", str(BACKEND_DIR / "data"))

import gradio as gr
from backend.main import app as fastapi_app

# Minimal Gradio demo for Spaces compliance & status check
with gr.Blocks(title="TMUX Transcriber") as demo:
    gr.HTML("""
        <div style="background:#090d16; border:1px solid #1e293b; border-radius:12px; padding:32px; text-align:center; font-family:ui-sans-serif, system-ui, sans-serif; max-width:600px; margin:40px auto; color:#f8fafc;">
            <div style="display:inline-flex; align-items:center; gap:8px; padding:4px 12px; border-radius:9999px; background:rgba(6,182,212,0.1); border:1px solid rgba(6,182,212,0.25); color:#22d3ee; font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:16px;">
                ● Studio Online
            </div>
            <h1 style="font-size:24px; font-weight:800; color:#ffffff; margin:0 0 8px 0; letter-spacing:-0.025em;">TMUX Transcriber Workstation</h1>
            <p style="font-size:14px; color:#94a3b8; margin:0 0 24px 0; line-height:1.5;">Next.js Studio, Faster-Whisper Large-v3 Engine, and Audio Muxer are running live.</p>
            <a href="/" target="_top" style="display:inline-block; background:#06b6d4; color:#020617; font-weight:700; font-size:14px; padding:12px 28px; border-radius:8px; text-decoration:none; box-shadow:0 0 20px rgba(6,182,212,0.35);">
                Open Full TMUX Studio ➔
            </a>
        </div>
    """)

# Mount Gradio interface onto FastAPI at /gradio so root / serves the Next.js Studio UI directly
app = gr.mount_gradio_app(fastapi_app, demo, path="/gradio")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
