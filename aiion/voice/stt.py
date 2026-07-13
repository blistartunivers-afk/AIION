"""aiion/voice/stt.py — Voz a texto vía termux-speech-to-text."""
import subprocess
from aiion.cli.ui import c, PK, GR, YL, RE

def listen(prompt="🎤 Escuchando..."):
    print(c(PK,f"\n  {prompt}"),flush=True)
    try:
        r=subprocess.run(["termux-speech-to-text"],capture_output=True,text=True,timeout=30)
        text=r.stdout.strip()
        if text:
            print(c(GR,f"  🗣  {text}"))
            return text
        return ""
    except subprocess.TimeoutExpired:
        print(c(YL,"  Timeout STT")); return ""
    except Exception as e:
        print(c(RE,f"  STT: {e}")); return ""

