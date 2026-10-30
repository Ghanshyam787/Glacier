"""
Glacier Voice
=============
BOLNA (TTS): Microsoft Edge neural voice (edge-tts, free) - ChatGPT/Gemini voice jaisi smooth awaaz.
   * Playback Windows ke built-in MCI se (ctypes) - pygame/pyaudio ki ZAROORAT NAHI (jo Python 3.14 par build fail hote the)
   * Lambe jawab sentence-by-sentence: agla sentence tayyar hota rehta hai jab pichhla bol raha hota hai
   * Internet na ho ya edge-tts fail ho to Windows ki apni awaaz (offline fallback)
SUNNA (STT): sounddevice (mic) + faster-whisper (offline, free). Fallback: Google Web Speech (SpeechRecognition).
   * Wake word ("Glacier, ...") optional: WAKE_WORD_ENABLED=true
"""

import asyncio
import ctypes
import difflib
import itertools
import os
import queue
import re
import tempfile
import threading
import time

import config
import registry

TTS_DIR = os.path.join(config.DATA_DIR, "tts")
os.makedirs(TTS_DIR, exist_ok=True)

_speak_q = queue.Queue()
_stop_flag = threading.Event()
_speaking = threading.Event()
_alias_counter = itertools.count(1)
_current_alias = None
_worker_started = False
_worker_lock = threading.Lock()
_edge_failures = 0


# ============================================================ text cleanup for speech
_MD = [(re.compile(r"```.*?```", re.S), " code block. "), (re.compile(r"`([^`]*)`"), r"\1"),
       (re.compile(r"\*\*|__|~~"), ""), (re.compile(r"^#+\s*", re.M), ""), (re.compile(r"^\s*[-*•]\s+", re.M), ""),
       (re.compile(r"\[([^\]]+)\]\([^)]+\)"), r"\1"), (re.compile(r"https?://\S+"), " link "),
       (re.compile(r"\b[A-Za-z]:\\(?:[^\\\s]+\\)*([^\\\s]+)"), r"\1"),
       (re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⬆️]"), "")]


def clean_for_speech(text: str, max_chars: int = 650) -> str:
    t = config.fix_address(text or "")
    for rx, rep in _MD:
        t = rx.sub(rep, t)
    t = re.sub(r"\s*\n+\s*", ". ", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" .")
    if len(t) > max_chars:
        cut = t[:max_chars]
        end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
        t = (cut[: end + 1] if end > 200 else cut) + " Baaki jawab screen par hai."
    return t


def _split_sentences(text: str, limit: int = 230) -> list:
    """Pehla tukda alag aur chhota (jaldi bolna shuru), baaki limit tak jod-jod ke."""
    parts = [p for p in re.split(r"(?<=[.!?।])\s+", text) if p.strip()]
    if not parts:
        return []
    first = parts[0]
    if len(first) > 160:                       # bahut lamba vaakya: comma par todo
        cut = first.rfind(",", 40, 160)
        cut = cut if cut > 0 else first.rfind(" ", 40, 160)
        if cut > 0:
            parts[0:1] = [first[:cut + 1].strip(), first[cut + 1:].strip()]
    out, cur = [parts[0]], ""
    for p in parts[1:]:
        if len(cur) + len(p) + 1 <= limit:
            cur = f"{cur} {p}".strip()
        else:
            if cur:
                out.append(cur)
            cur = p
    if cur:
        out.append(cur)
    return [x for x in out if x.strip()]


# ============================================================ Windows MCI playback
def _short_path(path: str) -> str:
    try:
        buf = ctypes.create_unicode_buffer(520)
        if ctypes.windll.kernel32.GetShortPathNameW(path, buf, 520):  # type: ignore[attr-defined]
            return buf.value
    except Exception:
        pass
    return path


def _mci(cmd: str):
    buf = ctypes.create_unicode_buffer(256)
    err = ctypes.windll.winmm.mciSendStringW(cmd, buf, 255, 0)  # type: ignore[attr-defined]
    return err, buf.value


def _play_mp3(path: str):
    global _current_alias
    alias = f"glc{next(_alias_counter)}"
    err, _ = _mci(f'open "{_short_path(path)}" type mpegvideo alias {alias}')
    if err:
        raise RuntimeError(f"MCI open error {err}")
    _current_alias = alias
    try:
        _mci(f"play {alias} wait")
    finally:
        _mci(f"close {alias}")
        _current_alias = None


def _sapi_speak(text: str):
    """Offline fallback - Windows ki apni awaaz."""
    from winutil import ps_quote, run_ps
    rate = 0
    run_ps("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
           f"$s.Rate = {rate}; $s.Speak({ps_quote(text)})", timeout=90)


# ============================================================ edge-tts
def _pick_voice(text: str) -> str:
    if re.search(r"[ऀ-ॿ]", text):
        return "hi-IN-SwaraNeural"
    return config.TTS_VOICE


async def _synthesize(text: str, path: str):
    import edge_tts
    comm = edge_tts.Communicate(text, _pick_voice(text), rate=config.TTS_RATE, pitch=config.TTS_PITCH)
    await asyncio.wait_for(comm.save(path), 25)


def _synth_to_file(text: str):
    """Returns mp3 path ya None (edge-tts fail)."""
    global _edge_failures
    if _edge_failures >= 3:
        return None
    fd, path = tempfile.mkstemp(suffix=".mp3", dir=TTS_DIR)
    os.close(fd)
    try:
        asyncio.run(_synthesize(text, path))
        if os.path.getsize(path) < 500:
            raise RuntimeError("khaali audio")
        _edge_failures = 0
        return path
    except Exception as e:
        _edge_failures += 1
        registry.log_error("edge-tts", e)
        try:
            os.remove(path)
        except OSError:
            pass
        return None


def _speak_worker():
    from concurrent.futures import ThreadPoolExecutor
    pool = ThreadPoolExecutor(max_workers=1)
    while True:
        text = _speak_q.get()
        if text is None:
            break
        _stop_flag.clear()
        _speaking.set()
        try:
            sentences = _split_sentences(text)
            futs = [pool.submit(_synth_to_file, sentences[0])] if sentences else []
            for i, s in enumerate(sentences):
                if _stop_flag.is_set():
                    break
                path = futs[i].result()
                if i + 1 < len(sentences):
                    futs.append(pool.submit(_synth_to_file, sentences[i + 1]))
                if _stop_flag.is_set():
                    break
                if path is None:
                    if config.IS_WINDOWS:
                        _sapi_speak(" ".join(sentences[i:]))
                    break
                try:
                    if config.IS_WINDOWS:
                        _play_mp3(path)
                except Exception as e:
                    registry.log_error("voice playback", e)
                finally:
                    try:
                        os.remove(path)
                    except OSError:
                        pass
        except Exception as e:
            registry.log_error("speak worker", e)
        finally:
            if _speak_q.empty():
                _speaking.clear()


def _ensure_worker():
    global _worker_started
    with _worker_lock:
        if not _worker_started:
            threading.Thread(target=_speak_worker, daemon=True, name="glacier-tts").start()
            _worker_started = True


def speak(text: str, wait: bool = False):
    """Text ko bolo (background mein). wait=True = bolne tak ruko. Console par bhi print karta hai."""
    spoken = clean_for_speech(text)
    try:
        print(f"{config.ASSISTANT_NAME}: {text}")
    except Exception:
        pass
    if not spoken:
        return
    _ensure_worker()
    _speak_q.put(spoken)
    if wait:
        time.sleep(0.2)
        while _speaking.is_set() or not _speak_q.empty():
            time.sleep(0.1)


def speak_if_enabled(text: str):
    if config.VOICE_ENABLED:
        speak(text)


def stop_speaking():
    """Abhi ki awaaz turant band + queue saaf."""
    _stop_flag.set()
    while not _speak_q.empty():
        try:
            _speak_q.get_nowait()
        except queue.Empty:
            break
    alias = _current_alias
    if alias and config.IS_WINDOWS:
        try:
            _mci(f"stop {alias}")
        except Exception:
            pass


def is_speaking() -> bool:
    return _speaking.is_set() or not _speak_q.empty()


# ============================================================ speech-to-text
SAMPLE_RATE = 16000
_whisper = None
_whisper_lock = threading.Lock()
_HALLUCINATIONS = {"thank you", "thanks for watching", "you", "bye", "thank you.", ".", "thanks", "subtitles by",
                   "okay", "ok"}


def _device():
    d = config.MIC_DEVICE
    if not d:
        return None
    return int(d) if d.isdigit() else d


def mic_available() -> bool:
    try:
        import sounddevice as sd
        sd.query_devices(kind="input")
        return True
    except Exception:
        return False


def list_microphones() -> list:
    try:
        import sounddevice as sd
        return [f"{i}: {d['name']}" for i, d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0]
    except Exception:
        return []


def record_utterance(wait_seconds: float = 8.0, max_seconds: float = 15.0, silence_seconds: float = 0.7):
    """
    Mic se ek vaakya record karo (energy-based voice detection). Returns float32 numpy array (16 kHz) ya None
    agar wait_seconds mein koi bola hi nahi. Raises RuntimeError agar mic/sounddevice nahi hai.
    """
    try:
        import numpy as np
        import sounddevice as sd
    except ImportError:
        raise RuntimeError("Voice input ke liye 'sounddevice' aur 'numpy' chahiye (pip install sounddevice numpy).")
    block = int(SAMPLE_RATE * 0.05)
    frames, started, silent_blocks = [], False, 0
    need_silent = int(silence_seconds / 0.05)
    t0 = time.time()
    noise = []
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=block, device=_device()) as stream:
            while True:
                data, _ = stream.read(block)
                chunk = data[:, 0]
                rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
                if len(noise) < 8:  # pehle 0.4 sec = background noise
                    noise.append(rms)
                    continue
                threshold = max(350.0, (sum(noise) / len(noise)) * 3.0)
                if not started:
                    if rms > threshold:
                        started = True
                        frames.append(chunk.copy())
                    elif time.time() - t0 > wait_seconds:
                        return None
                else:
                    frames.append(chunk.copy())
                    silent_blocks = silent_blocks + 1 if rms < threshold * 0.7 else 0
                    if silent_blocks >= need_silent or (time.time() - t0) > max_seconds + wait_seconds:
                        break
    except Exception as e:
        raise RuntimeError(f"Mic open nahi hua: {e}")
    audio = np.concatenate(frames).astype(np.float32) / 32768.0
    return audio if len(audio) > SAMPLE_RATE * 0.3 else None


def _get_whisper():
    global _whisper
    with _whisper_lock:
        if _whisper is None:
            from faster_whisper import WhisperModel
            print(f"[Voice] Whisper '{config.WHISPER_MODEL}' model load ho raha hai (pehli baar download hoga)...")
            _whisper = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
        return _whisper


def _transcribe_whisper(audio) -> str:
    model = _get_whisper()
    lang = config.STT_LANGUAGE or None
    segments, _info = model.transcribe(
        audio, language=lang, beam_size=1, vad_filter=True, condition_on_previous_text=False,
        initial_prompt="Glacier assistant. Shyam sir. Hinglish commands: kholo, band karo, chalao, batao, bhejo, dhundo, reminder.")
    return " ".join(s.text.strip() for s in segments).strip()


def _transcribe_google(audio) -> str:
    import numpy as np
    import speech_recognition as sr
    pcm = (audio * 32768.0).astype(np.int16).tobytes()
    r = sr.Recognizer()
    try:
        return r.recognize_google(sr.AudioData(pcm, SAMPLE_RATE, 2), language="en-IN")
    except sr.UnknownValueError:
        return ""


def transcribe(audio) -> str:
    text = ""
    if config.STT_ENGINE == "whisper":
        try:
            text = _transcribe_whisper(audio)
        except ImportError:
            print("[Voice] faster-whisper install nahi hai, Google speech use kar raha hoon.")
            text = _transcribe_google(audio)
        except Exception as e:
            registry.log_error("whisper", e)
            try:
                text = _transcribe_google(audio)
            except Exception as e2:
                registry.log_error("google-stt", e2)
    else:
        try:
            text = _transcribe_google(audio)
        except Exception as e:
            registry.log_error("google-stt", e)
    t = text.strip()
    if t.lower().strip(" .!") in _HALLUCINATIONS or len(t) < 2:
        return ""
    return t


def transcribe_file(path: str) -> str:
    """Audio file (Telegram .ogg etc.) -> text. faster-whisper file seedha padh leta hai."""
    try:
        model = _get_whisper()
        segments, _ = model.transcribe(path, language=config.STT_LANGUAGE or None, beam_size=1, vad_filter=True)
        return " ".join(s.text.strip() for s in segments).strip()
    except Exception as e:
        registry.log_error("transcribe_file", e)
        return ""


def listen(timeout: int = 8, phrase_time_limit: int = 15) -> str:
    """Ek command sunke text do (khaali string = kuchh sunai nahi diya). Bolte waqt mic band rehta hai."""
    while is_speaking():
        time.sleep(0.1)
    audio = record_utterance(wait_seconds=timeout, max_seconds=phrase_time_limit)
    if audio is None:
        return ""
    text = transcribe(audio)
    if text:
        print(f"You: {text}")
    return text


# ============================================================ wake word
def _beep(freq=880, ms=120):
    try:
        import winsound
        winsound.Beep(freq, ms)
    except Exception:
        pass


def split_wake_word(text: str):
    """(found, remainder). 'Glacier open chrome' -> (True, 'open chrome')."""
    t = (text or "").strip()
    words = re.findall(r"\S+", t)
    for i, w in enumerate(words[:3]):  # wake word shuru ke 3 shabdon mein
        wl = re.sub(r"[^\w]", "", w.lower())
        if not wl:
            continue
        if wl in config.WAKE_WORDS or any(difflib.SequenceMatcher(None, wl, ww).ratio() >= 0.78 for ww in config.WAKE_WORDS):
            rest = " ".join(words[i + 1:]).lstrip(" ,.:;-")
            return True, rest
    return False, t


def preload_whisper():
    """Background mein model load (pehli baar download) taaki pehli command late na ho."""
    try:
        _get_whisper()
        return True
    except Exception as e:
        registry.log_error("whisper preload", e)
        return False


class WakeListener(threading.Thread):
    """
    Hamesha sunne wala mic (ek hi stream, koi gap nahi).
      * "Glacier, <command>" bolo -> command chalta hai
      * Jawab ke baad FOLLOWUP_SECONDS tak bina "Glacier" bole bhi agli command sunta hai (baat-cheet jaisa)
      * Glacier jab khud bol raha ho to apni awaaz nahi sunta
    States: listening | hearing | thinking | speaking | muted  (on_state callback -> dashboard)
    """

    PRE_ROLL = 8          # 0.4 sec pehle ka audio bhi rakho (shabd ka shuru na kate)

    def __init__(self, on_command, on_state=None):
        super().__init__(daemon=True, name="glacier-wake")
        self.on_command = on_command
        self.on_state = on_state or (lambda s: None)
        self._stop_evt = threading.Event()
        self.paused = threading.Event()          # user ne mute kiya
        self._q = queue.Queue()
        self._state = ""
        self._last_activity = 0.0

    # ---- control
    def stop(self):
        self._stop_evt.set()

    def set_muted(self, muted: bool):
        (self.paused.set if muted else self.paused.clear)()
        self._set("muted" if muted else "listening")

    def _set(self, st: str):
        if st != self._state:
            self._state = st
            try:
                self.on_state(st)
            except Exception:
                pass

    @property
    def state(self) -> str:
        return self._state

    # ---- worker: transcribe + dispatch (capture loop ko kabhi nahi rokta)
    def _worker(self):
        preload_whisper()
        while not self._stop_evt.is_set():
            try:
                audio, ts = self._q.get(timeout=0.5)
            except queue.Empty:
                continue
            if time.time() - ts > 25:            # purani baat, ignore
                continue
            try:
                self._handle(audio)
            except Exception as e:
                registry.log_error("wake handle", e)
                self._set("listening")

    def _handle(self, audio):
        self._set("thinking")
        text = transcribe(audio)
        if not text:
            self._set("listening")
            return
        found, rest = split_wake_word(text)
        in_followup = (time.time() - self._last_activity) < config.FOLLOWUP_SECONDS
        if not found and not in_followup:
            self._set("listening")
            return
        command = rest if found else text
        if found and len(command) < 3:           # sirf "Glacier" bola: agli baat ka intezaar
            _beep()
            self._last_activity = time.time()
            self._set("listening")
            return
        print(f"You (voice): {command}")
        self._set("thinking")
        self.on_command(command)
        self._last_activity = time.time()
        self._set("speaking" if is_speaking() else "listening")

    # ---- capture loop
    def run(self):
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError:
            print("[Voice] sounddevice/numpy nahi hai - hamesha sunna band.")
            return
        threading.Thread(target=self._worker, daemon=True, name="glacier-stt").start()
        from collections import deque
        block = int(SAMPLE_RATE * 0.05)
        errors = 0
        while not self._stop_evt.is_set():
            try:
                with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=block, device=_device()) as stream:
                    errors = 0
                    pre = deque(maxlen=self.PRE_ROLL)
                    frames, started, silent, noise, hearing_since = [], False, 0, 250.0, 0.0
                    need_silent = int(0.7 / 0.05)
                    self._set("muted" if self.paused.is_set() else "listening")
                    while not self._stop_evt.is_set():
                        data, _ = stream.read(block)
                        chunk = data[:, 0]
                        if self.paused.is_set() or is_speaking():
                            if is_speaking():
                                self._last_activity = time.time()   # followup window bolne ke baad shuru
                                self._set("speaking")
                            else:
                                self._set("muted")
                            started, frames, silent = False, [], 0
                            pre.clear()
                            continue
                        if self._state in ("speaking", "muted"):
                            self._set("listening")
                        rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
                        thr = max(300.0, noise * 3.0)
                        if not started:
                            if rms > thr:
                                started, silent, hearing_since = True, 0, time.time()
                                frames = list(pre) + [chunk.copy()]
                                self._set("hearing")
                            else:
                                noise = noise * 0.97 + rms * 0.03
                                pre.append(chunk.copy())
                        else:
                            frames.append(chunk.copy())
                            silent = silent + 1 if rms < thr * 0.7 else 0
                            if silent >= need_silent or time.time() - hearing_since > 15:
                                audio = np.concatenate(frames).astype(np.float32) / 32768.0
                                started, frames, silent = False, [], 0
                                pre.clear()
                                if len(audio) > SAMPLE_RATE * 0.5:
                                    self._q.put((audio, time.time()))
                                    self._set("thinking")
                                else:
                                    self._set("listening")
            except Exception as e:
                errors += 1
                registry.log_error("wake listener", e)
                self._set("muted")
                if errors >= 5:
                    print(f"[Voice] Mic ki dikkat, hamesha sunna band: {e}")
                    return
                time.sleep(3)
