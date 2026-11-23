"""
Glacier voice test - awaaz kyun nahi aa rahi, ye step-by-step batata hai.
Chalao:  .venv\\Scripts\\python voice_test.py
"""
import asyncio
import os
import sys
import tempfile
import time

import config

print("=== Glacier Voice Test ===")
print(f"VOICE_ENABLED = {config.VOICE_ENABLED}   TTS_VOICE = {config.TTS_VOICE}   RATE = {config.TTS_RATE}   PITCH = {config.TTS_PITCH}")
if not config.VOICE_ENABLED:
    print("[FAIL] .env mein VOICE_ENABLED=false hai. true kar do.")

import voice

print("\n1) edge-tts library")
try:
    import edge_tts
    print("   [ OK ]", getattr(edge_tts, "__version__", "installed"))
except Exception as e:
    print("   [FAIL]", e, "\n   -> .venv\\Scripts\\python -m pip install -U edge-tts")
    sys.exit(1)

print("\n2) edge-tts se awaaz banana (internet chahiye)")
mp3 = None
for v in [config.TTS_VOICE, "en-IN-NeerjaNeural"]:
    fd, p = tempfile.mkstemp(suffix=".mp3"); os.close(fd)
    try:
        kw = {"rate": config.TTS_RATE, "pitch": config.TTS_PITCH} if v == config.TTS_VOICE else {}
        asyncio.run(asyncio.wait_for(edge_tts.Communicate("Namaste Shyam sir, main Glacier hoon.", v, **kw).save(p), 25))
        print(f"   [ OK ] {v}: {os.path.getsize(p)} bytes")
        mp3 = mp3 or p
    except Exception as e:
        print(f"   [FAIL] {v}: {type(e).__name__}: {e}")

if mp3:
    print("\n3) MCI se bajana (ab awaaz aani chahiye)")
    try:
        voice._play_mp3_mci(mp3)
        print("   [ OK ] MCI chala. Awaaz suni? Agar nahi: volume / speaker / output device check karo.")
    except Exception as e:
        print(f"   [FAIL] MCI: {e}")
        print("   PowerShell MediaPlayer try kar raha hoon...")
        try:
            voice._play_mp3_wpf(mp3)
            print("   [ OK ] MediaPlayer chala.")
        except Exception as e2:
            print(f"   [FAIL] MediaPlayer: {e2}")
else:
    print("\n3) edge-tts fail hua, internet ya firewall check karo.")

print("\n4) Windows ki apni awaaz (offline backup)")
try:
    voice._sapi_speak("Windows backup voice test.")
    print("   [ OK ]")
except Exception as e:
    print(f"   [FAIL] {e}")

print("\n5) Mic level + speech-to-text.  Abhi 5 second tak NORMAL awaaz mein bolte raho (jaise 'Glacier kitne baje hain')")
try:
    import numpy as np
    import sounddevice as sd
    levels = []
    with sd.InputStream(samplerate=16000, channels=1, dtype="int16", blocksize=800, device=voice._device()) as st:
        print("   Bolo...", flush=True)
        t0 = time.time()
        while time.time() - t0 < 5:
            d, _ = st.read(800)
            levels.append(float(np.sqrt(np.mean(d[:, 0].astype(np.float32) ** 2))))
    lo, hi = min(levels), max(levels)
    print(f"   Mic level: sabse shaant = {lo:.0f}, sabse tez = {hi:.0f}   (Glacier ki threshold = {config.MIC_MIN_LEVEL:.0f} se upar)")
    if hi < 30:
        print("   [FAIL] Mic se lagbhag koi awaaz nahi aa rahi. Mic mute/disabled hai ya galat mic chuna hai.")
        print("          Windows Settings > Privacy > Microphone ON karo. Phir `voice_test.py --mic` chalao (sahi mic dhundhne ke liye).")
    elif hi < config.MIC_MIN_LEVEL * 1.3:
        print(f"   [WARN] Mic bahut halka hai. .env mein MIC_MIN_LEVEL={max(20, int(hi * 0.4))} likho.")
    else:
        print("   [ OK ] Mic theek level par hai. Ab speech-to-text:")
        print("   Phir se bolo (6 second)...", flush=True)
        audio = voice.record_utterance(wait_seconds=6, max_seconds=8)
        if audio is None:
            print("   [FAIL] Awaaz aayi par Glacier ne vaakya detect nahi kiya. MIC_MIN_LEVEL kam karke dekho.")
        else:
            print("   Model load/transcribe ho raha hai (pehli baar thoda time)...")
            print("   [ OK ] Maine suna:", repr(voice.transcribe(audio)))
except Exception as e:
    print(f"   [FAIL] {type(e).__name__}: {e}")

print("\n6) Glacier ka asli speak() path")
voice.speak("Ye Glacier ka final test hai, Shyam sir.", wait=True)
time.sleep(0.5)
print("   Agar upar [Voice] ... fail jaisi line aayi to wahi dikkat hai. Poora output mujhe bhej do.")


if "--mic" in sys.argv:
    print("\n=== Mic dhundo: har input device ko 3 second sunta hoon - TEZ AWAAZ mein bolte raho ===")
    import numpy as np
    import sounddevice as sd
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] < 1:
            continue
        try:
            with sd.InputStream(samplerate=16000, channels=1, dtype="int16", blocksize=800, device=i) as st:
                m = 0.0
                t0 = time.time()
                while time.time() - t0 < 3:
                    x, _ = st.read(800)
                    m = max(m, float(np.sqrt(np.mean(x[:, 0].astype(np.float32) ** 2))))
            print(f"  {i:3d}  level {m:6.0f}  {d['name'][:60]}")
        except Exception as e:
            print(f"  {i:3d}  (nahi khula: {type(e).__name__})  {d['name'][:50]}")
    print("Jis device ka level sabse zyada aaye uska number .env mein likho:  MIC_DEVICE=<number>")

if "--all" in sys.argv:
    import langs
    print("\n=== Har bhasha ki awaaz ka check (jaise Glacier asal mein karta hai: pehle best, phir backup awaaz) ===")
    bad = []
    for code, text in sorted(langs.SAMPLES.items()):
        cands, _risk = voice.voice_candidates(text, code)
        used, err = None, ""
        for v in cands[:5]:
            fd, p = tempfile.mkstemp(suffix=".mp3"); os.close(fd)
            try:
                asyncio.run(voice._synthesize(text, p, v))
                if os.path.getsize(p) > 500:
                    used = v
                    break
            except Exception as e:
                err = type(e).__name__
        print(f"  [{'OK' if used else 'FAIL'}] {code:3s} {used or cands[0]}" + ("" if used else f"  ({err})")
              + (f"   <- pehli awaaz {cands[0]} fail, backup chali" if used and used != cands[0] else ""))
        if not used:
            bad.append(code)
        if used and "--play" in sys.argv:
            try:
                voice._play_mp3(p)
            except Exception as e:
                print("     bajane mein error:", e)
    print("\nBilkul awaaz nahi bani:", ", ".join(bad) if bad else "koi nahi")
    try:
        live = langs._live_voices()
        langs_live = sorted({v["Locale"].split("-")[0] for v in live})
        print(f"\nEdge ki live list mein {len(live)} awaazein, {len(langs_live)} bhashayein: {' '.join(langs_live)}")
        for code in bad:
            print(f"  {code}: ", [v["ShortName"] for v in live if v["Locale"].lower().startswith(code + "-")])
    except Exception as e:
        print("Live list nahi mili:", e)
