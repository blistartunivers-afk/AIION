"""aiion/voice/tts.py — Texto a voz: Groq PlayAI con fallback a termux-tts-speak."""
import re, os, json, subprocess, tempfile, threading, urllib.request
from aiion.config import GROQ_TTS_URL, GROQ_TTS_MODEL, GROQ_API_KEY, TTS_CHUNK

VOICE_STATE = {
    "enabled": False, "voice": "Celeste-PlayAI",
    "volume": 100, "speed": 1.0, "last_error": "",
}

def _clean_for_tts(text):
    text=re.sub(r'\*{1,2}([^*]+)\*{1,2}',r'\1',text)
    text=re.sub(r'`[^`]+`','',text)
    text=re.sub(r'#{1,6}\s+','',text)
    text=re.sub(r'\033\[[0-9;]*m','',text)
    text=re.sub(r'\n{2,}','. ',text)
    return re.sub(r'\n',' ',text).strip()

def _split_tts(text, max_len=TTS_CHUNK):
    if len(text)<=max_len: return [text]
    chunks=[]; sentences=re.split(r'(?<=[.!?])\s+',text); cur=""
    for s in sentences:
        if len(cur)+len(s)+1<=max_len: cur=(cur+" "+s).strip()
        else:
            if cur: chunks.append(cur)
            cur=s if len(s)<=max_len else s[:max_len]
    if cur: chunks.append(cur)
    return chunks or [text[:max_len]]

def _tts_chunk_api(text, voice):
    if not GROQ_API_KEY: return None
    payload=json.dumps({"model":GROQ_TTS_MODEL,"input":text,"voice":voice,"response_format":"mp3"}).encode()
    req=urllib.request.Request(GROQ_TTS_URL,data=payload,
        headers={"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=30) as r: return r.read()

def speak(text, blocking=True):
    if not VOICE_STATE["enabled"] or not text.strip(): return False
    clean=_clean_for_tts(text)
    if not clean: return False
    voice=VOICE_STATE["voice"]

    def _play():
        # Intentar Groq primero, fallback a termux-tts-speak
        if GROQ_API_KEY:
            for chunk in _split_tts(clean):
                try:
                    audio=_tts_chunk_api(chunk,voice)
                    if not audio: raise Exception("empty")
                    with tempfile.NamedTemporaryFile(suffix=".mp3",delete=False) as f:
                        f.write(audio); tmp=f.name
                    subprocess.run(["mpv","--no-video","--really-quiet",
                                   f"--volume={VOICE_STATE['volume']}",
                                   f"--speed={VOICE_STATE['speed']}",tmp],timeout=60)
                    os.unlink(tmp)
                except Exception as e:
                    VOICE_STATE["last_error"]=str(e)
                    _tts_fallback(clean); break
        else:
            _tts_fallback(clean)

    def _tts_fallback(text):
        try:
            subprocess.run(["termux-tts-speak","-r","1.0","-l","es",text[:400]],timeout=8)
        except: pass

    if blocking: _play()
    else: threading.Thread(target=_play,daemon=True).start()
    return True
