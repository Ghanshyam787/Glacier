"""
Glacier - Bhasha (language) support
===================================
* detect(text)      -> ISO code ("hi", "ja", "es" ...) ya None (English / Hinglish / pata nahi)
* voice_for(code)   -> edge-tts awaaz ka naam (gentle male pehle, nahi to female) ya None
* STT: Whisper ~99 bhashayein; TTS: edge-tts ~70 bhashayein; likhna/samajhna/translate: Gemini 100+ bhashayein.
Script se detect (non-Latin) + 'langdetect' library (Latin bhashayein). Library na ho to bhi script wali sab chalti hain.
"""

import re

# ---- script ranges -> language
_SCRIPTS = [
    ("hi", r"[ऀ-ॿ]"), ("bn", r"[ঀ-৿]"), ("pa", r"[਀-੿]"), ("gu", r"[઀-૿]"),
    ("or", r"[଀-୿]"), ("ta", r"[஀-௿]"), ("te", r"[ఀ-౿]"), ("kn", r"[ಀ-೿]"),
    ("ml", r"[ഀ-ൿ]"), ("si", r"[඀-෿]"), ("th", r"[฀-๿]"), ("lo", r"[຀-໿]"),
    ("my", r"[က-႟]"), ("km", r"[ក-៿]"), ("ka", r"[Ⴀ-ჿ]"), ("hy", r"[԰-֏]"),
    ("he", r"[֐-׿]"), ("el", r"[Ͱ-Ͽ]"), ("ko", r"[가-힯ᄀ-ᇿ]"), ("am", r"[ሀ-፿]"),
    ("bo", r"[ༀ-࿿]"), ("ja_kana", r"[぀-ヿ]"), ("zh_han", r"[一-鿿]"),
    ("ar", r"[؀-ۿݐ-ݿ]"), ("ru", r"[Ѐ-ӿ]"),
]
_SCRIPTS = [(c, re.compile(p)) for c, p in _SCRIPTS]

_HINGLISH = set("hai hain kya ho nahi nahin aap tum main mein kar karo karna kaise kyun kab abhi ka ki ke ko se par bhi toh "
                "yeh ye woh wo acha accha theek thik batao bolo chalo mujhe tumhe hum kuch kaam bhai sir".split())
_LATIN_OK = {"es", "fr", "de", "it", "pt", "nl", "pl", "tr", "id", "vi", "sv", "da", "no", "fi", "cs", "ro", "hu",
             "ms", "sw", "ca", "hr", "sk", "sl", "et", "lv", "lt", "af", "sq", "is", "cy", "tl"}
_REFINE = {"hi": {"hi", "mr", "ne"}, "ar": {"ar", "fa", "ur", "ps"}, "ru": {"ru", "uk", "bg", "sr", "mk", "kk", "mn", "be"}}


def _ld():
    try:
        from langdetect import DetectorFactory, detect_langs
        DetectorFactory.seed = 0
        return detect_langs
    except Exception:
        return None


LATIN_LANGS = _LATIN_OK | {"en", "pt", "es"}


def is_latin(text: str) -> bool:
    """Kya text mostly Latin akshar (a-z + accents) mein hai?"""
    letters = re.findall(r"[^\W\d_]", text or "")
    if not letters:
        return True
    latin = sum(1 for c in letters if c.isascii() or "\u00c0" <= c <= "\u024f" or "\u1e00" <= c <= "\u1eff")
    return latin / len(letters) >= 0.8


# Test ke liye chhote vaakya ("Hello, I am Glacier. How can I help you?")
SAMPLES = {
    "hi": "नमस्ते, मैं ग्लेशियर हूँ। मैं आपकी क्या मदद कर सकता हूँ?",
    "bn": "নমস্কার, আমি গ্লেশিয়ার। আমি আপনাকে কীভাবে সাহায্য করতে পারি?",
    "ta": "வணக்கம், நான் கிளேசியர். நான் உங்களுக்கு எப்படி உதவ முடியும்?",
    "te": "నమస్కారం, నేను గ్లేసియర్. నేను మీకు ఎలా సహాయం చేయగలను?",
    "kn": "ನಮಸ್ಕಾರ, ನಾನು ಗ್ಲೇಸಿಯರ್. ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?",
    "ml": "നമസ്കാരം, ഞാൻ ഗ്ലേസിയർ ആണ്. ഞാൻ നിങ്ങളെ എങ്ങനെ സഹായിക്കണം?",
    "gu": "નમસ્તે, હું ગ્લેશિયર છું. હું તમારી શું મદદ કરી શકું?",
    "mr": "नमस्कार, मी ग्लेशियर आहे. मी तुम्हाला कशी मदत करू?",
    "pa": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ, ਮੈਂ ਗਲੇਸ਼ੀਅਰ ਹਾਂ। ਮੈਂ ਤੁਹਾਡੀ ਕੀ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ?",
    "ur": "السلام علیکم، میں گلیشیئر ہوں۔ میں آپ کی کیا مدد کر سکتا ہوں؟",
    "ne": "नमस्ते, म ग्लेशियर हुँ। म तपाईंलाई कसरी मद्दत गर्न सक्छु?",
    "ja": "こんにちは、グレイシャーです。何をお手伝いしましょうか？",
    "ko": "안녕하세요, 저는 글레이셔입니다. 무엇을 도와드릴까요?",
    "zh": "你好，我是冰川。有什么可以帮您的吗？",
    "ar": "مرحبا، أنا غلاسير. كيف يمكنني مساعدتك؟",
    "he": "שלום, אני גלייסיר. איך אוכל לעזור לך?",
    "fa": "سلام، من گلاسیر هستم. چطور می‌توانم کمکتان کنم؟",
    "ru": "Здравствуйте, я Глейшер. Чем могу вам помочь?",
    "uk": "Вітаю, я Глейшер. Чим можу вам допомогти?",
    "el": "Γεια σας, είμαι ο Glacier. Πώς μπορώ να σας βοηθήσω;",
    "th": "สวัสดีครับ ผมคือเกลเซียร์ ให้ผมช่วยอะไรดีครับ",
    "vi": "Xin chào, tôi là Glacier. Tôi có thể giúp gì cho bạn?",
    "id": "Halo, saya Glacier. Ada yang bisa saya bantu?",
    "es": "Hola, soy Glacier. ¿En qué puedo ayudarte?",
    "fr": "Bonjour, je suis Glacier. Comment puis-je vous aider ?",
    "de": "Hallo, ich bin Glacier. Wie kann ich Ihnen helfen?",
    "it": "Ciao, sono Glacier. Come posso aiutarti?",
    "pt": "Olá, eu sou o Glacier. Como posso ajudar?",
    "tr": "Merhaba, ben Glacier. Size nasıl yardımcı olabilirim?",
    "nl": "Hallo, ik ben Glacier. Waar kan ik u mee helpen?",
    "pl": "Dzień dobry, jestem Glacier. W czym mogę pomóc?",
    "sv": "Hej, jag är Glacier. Hur kan jag hjälpa dig?",
    "sw": "Habari, mimi ni Glacier. Nikusaidie vipi?",
    "en": "Hello, I am Glacier. How can I help you?",
}


def _refine_cyrillic(t: str) -> str:
    low = t.lower()
    if re.search(r"[іїєґ]", low):
        return "uk"
    if re.search(r"[ђћџљњ]", low):
        return "sr"
    if re.search(r"[ѓќѕ]", low):
        return "mk"
    if re.search(r"[әғқңұһ]", low):
        return "kk"
    if re.search(r"[өү]", low):
        return "mn"
    return "ru"


def _refine_arabic(t: str) -> str:
    if re.search(r"[ټډړږښځڅڼ]", t):
        return "ps"
    if re.search(r"[ٹڈڑںےھۓ]", t):
        return "ur"
    if re.search(r"[يك]", t):
        return "ar"
    if re.search(r"[پچژگکی]", t):
        return "fa"
    return "ar"


_DEV = {
    "hi": set("है हैं मैं आप क्या नहीं और कर रहा रही हूँ हूं था थी में को से पर यह वह".split()),
    "mr": set("आहे आहेत मी तुम्ही काय नाही आणि करू करा होते आम्ही तुला मला".split()),
    "ne": set("छ छन् हुन्छ तपाईं तपाईंलाई गर्नु गर्न भएको म हो छैन के".split()),
}


def _refine_devanagari(t: str) -> str:
    if "ळ" in t:
        return "mr"
    words = set(re.findall(r"[ऀ-ॿ]+", t))
    scores = {k: len(words & v) for k, v in _DEV.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 and scores[best] > scores["hi"] else "hi"


def detect(text: str):
    t = re.sub(r"https?://\S+|[`*_#>\[\]()0-9]", " ", text or "")
    t = t.strip()
    if len(t) < 3:
        return None
    # 1) script
    counts = {}
    for code, rx in _SCRIPTS:
        n = len(rx.findall(t))
        if n:
            counts[code] = n
    letters = len(re.findall(r"[^\W\d_]", t)) or 1
    if counts:
        code, n = max(counts.items(), key=lambda kv: kv[1])
        if n / letters >= 0.3:
            if code in ("ja_kana", "zh_han"):
                return "ja" if counts.get("ja_kana") else "zh"
            if code == "hi":
                code = _refine_devanagari(t)
            elif code == "ar":
                code = _refine_arabic(t)
            elif code == "ru":
                code = _refine_cyrillic(t)
            if code in _REFINE:
                det = _ld()
                if det and len(t) >= 12:
                    try:
                        for cand in det(t):
                            if cand.lang in _REFINE[code] and cand.prob > 0.6:
                                return cand.lang
                    except Exception:
                        pass
                return code
            return code
    # 2) Latin: sirf bharose layak bhashayein; Hinglish ko English hi maano
    words = re.findall(r"[a-zA-Z]+", t.lower())
    if len(words) < 4:
        return None
    if sum(1 for w in words if w in _HINGLISH) >= 2:
        return None
    det = _ld()
    if not det:
        return None
    try:
        best = det(t)[0]
    except Exception:
        return None
    if best.lang in _LATIN_OK and best.prob >= 0.95:
        return best.lang
    return None


# (male, female) - edge-tts neural voices
VOICES = {
    "hi": ("hi-IN-MadhurNeural", "hi-IN-SwaraNeural"), "bn": ("bn-IN-BashkarNeural", "bn-IN-TanishaaNeural"),
    "ta": ("ta-IN-ValluvarNeural", "ta-IN-PallaviNeural"), "te": ("te-IN-MohanNeural", "te-IN-ShrutiNeural"),
    "kn": ("kn-IN-GaganNeural", "kn-IN-SapnaNeural"), "ml": ("ml-IN-MidhunNeural", "ml-IN-SobhanaNeural"),
    "gu": ("gu-IN-NiranjanNeural", "gu-IN-DhwaniNeural"), "mr": ("mr-IN-ManoharNeural", "mr-IN-AarohiNeural"),
    "pa": ("pa-IN-OjasNeural", "pa-IN-VaaniNeural"), "ur": ("ur-IN-SalmanNeural", "ur-IN-GulNeural"),
    "ne": ("ne-NP-SagarNeural", "ne-NP-HemkalaNeural"), "si": ("si-LK-SameeraNeural", "si-LK-ThiliniNeural"),
    "es": ("es-ES-AlvaroNeural", "es-ES-ElviraNeural"), "fr": ("fr-FR-HenriNeural", "fr-FR-DeniseNeural"),
    "de": ("de-DE-ConradNeural", "de-DE-KatjaNeural"), "it": ("it-IT-DiegoNeural", "it-IT-ElsaNeural"),
    "pt": ("pt-BR-AntonioNeural", "pt-BR-FranciscaNeural"), "ru": ("ru-RU-DmitryNeural", "ru-RU-SvetlanaNeural"),
    "ja": ("ja-JP-KeitaNeural", "ja-JP-NanamiNeural"), "ko": ("ko-KR-InJoonNeural", "ko-KR-SunHiNeural"),
    "zh": ("zh-CN-YunxiNeural", "zh-CN-XiaoxiaoNeural"), "ar": ("ar-SA-HamedNeural", "ar-SA-ZariyahNeural"),
    "fa": ("fa-IR-FaridNeural", "fa-IR-DilaraNeural"), "tr": ("tr-TR-AhmetNeural", "tr-TR-EmelNeural"),
    "nl": ("nl-NL-MaartenNeural", "nl-NL-ColetteNeural"), "pl": ("pl-PL-MarekNeural", "pl-PL-ZofiaNeural"),
    "sv": ("sv-SE-MattiasNeural", "sv-SE-SofieNeural"), "da": ("da-DK-JeppeNeural", "da-DK-ChristelNeural"),
    "no": ("nb-NO-FinnNeural", "nb-NO-PernilleNeural"), "fi": ("fi-FI-HarriNeural", "fi-FI-NooraNeural"),
    "el": ("el-GR-NestorasNeural", "el-GR-AthinaNeural"), "he": ("he-IL-AvriNeural", "he-IL-HilaNeural"),
    "th": ("th-TH-NiwatNeural", "th-TH-PremwadeeNeural"), "vi": ("vi-VN-NamMinhNeural", "vi-VN-HoaiMyNeural"),
    "id": ("id-ID-ArdiNeural", "id-ID-GadisNeural"), "ms": ("ms-MY-OsmanNeural", "ms-MY-YasminNeural"),
    "uk": ("uk-UA-OstapNeural", "uk-UA-PolinaNeural"), "cs": ("cs-CZ-AntoninNeural", "cs-CZ-VlastaNeural"),
    "hu": ("hu-HU-TamasNeural", "hu-HU-NoemiNeural"), "ro": ("ro-RO-EmilNeural", "ro-RO-AlinaNeural"),
    "bg": ("bg-BG-BorislavNeural", "bg-BG-KalinaNeural"), "hr": ("hr-HR-SreckoNeural", "hr-HR-GabrijelaNeural"),
    "sk": ("sk-SK-LukasNeural", "sk-SK-ViktoriaNeural"), "sl": ("sl-SI-RokNeural", "sl-SI-PetraNeural"),
    "sr": ("sr-RS-NicholasNeural", "sr-RS-SophieNeural"), "sw": ("sw-KE-RafikiNeural", "sw-KE-ZuriNeural"),
    "af": ("af-ZA-WillemNeural", "af-ZA-AdriNeural"), "am": ("am-ET-AmehaNeural", "am-ET-MekdesNeural"),
    "km": ("km-KH-PisethNeural", "km-KH-SreymomNeural"), "lo": ("lo-LA-ChanthavongNeural", "lo-LA-KeomanyNeural"),
    "my": ("my-MM-ThihaNeural", "my-MM-NilarNeural"), "ka": ("ka-GE-GiorgiNeural", "ka-GE-EkaNeural"),
    "kk": ("kk-KZ-DauletNeural", "kk-KZ-AigulNeural"), "mn": ("mn-MN-BataaNeural", "mn-MN-YesuiNeural"),
    "et": ("et-EE-KertNeural", "et-EE-AnuNeural"), "lv": ("lv-LV-NilsNeural", "lv-LV-EveritaNeural"),
    "lt": ("lt-LT-LeonasNeural", "lt-LT-OnaNeural"), "is": ("is-IS-GunnarNeural", "is-IS-GudrunNeural"),
    "cy": ("cy-GB-AledNeural", "cy-GB-NiaNeural"), "ca": ("ca-ES-EnricNeural", "ca-ES-JoanaNeural"),
    "mk": ("mk-MK-AleksandarNeural", "mk-MK-MarijaNeural"), "sq": ("sq-AL-IlirNeural", "sq-AL-AnilaNeural"),
    "hy": ("hy-AM-HaykNeural", "hy-AM-AnahitNeural"), "tl": ("fil-PH-AngeloNeural", "fil-PH-BlessicaNeural"),
    "ps": ("ps-AF-GulNawazNeural", "ps-AF-LatifaNeural"),
}

_live = {"voices": None, "tried": False}


def _live_voices():
    """edge-tts ki poori live list (ek baar, internet se)."""
    if _live["tried"]:
        return _live["voices"] or []
    _live["tried"] = True
    try:
        import asyncio
        import edge_tts
        _live["voices"] = asyncio.run(asyncio.wait_for(edge_tts.list_voices(), 10))
    except Exception:
        _live["voices"] = None
    return _live["voices"] or []


def voice_for(code: str, prefer_male: bool = True, avoid: str = ""):
    """Static list se; 'avoid' (jo pehle fail hui) ke badle live list se koi aur."""
    pair = VOICES.get(code)
    if pair and not avoid:
        return pair[0] if prefer_male else pair[1]
    live = [v for v in _live_voices() if v.get("Locale", "").lower().startswith(code.lower() + "-") and v["ShortName"] != avoid]
    if live:
        male = [v for v in live if v.get("Gender") == "Male"]
        return (male or live)[0]["ShortName"] if prefer_male else live[0]["ShortName"]
    if pair:
        return pair[1] if pair[0] == avoid else pair[0]
    return None


def supported_voice_languages() -> int:
    return len(VOICES)
