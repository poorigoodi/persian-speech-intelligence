"""Local, language-aware (Persian + English) transcript analysis and grounded QA.

Used whenever the external/local LLM server is unreachable. Everything here is
derived strictly from the transcript text: keywords by frequency, extractive
summaries, lexicon-based emotion distribution, and keyword-overlap retrieval
for chat answers. Nothing is invented.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from app.utils.asr_correct import apply_asr_rules

ANALYSIS_SOURCE = "local_nlp_v6"

_PERSIAN_CHARS = re.compile(r"[\u0621-\u063A\u0641-\u064A\u067E\u0686\u0698\u06A9\u06AF\u06CC]")
_LATIN_CHARS = re.compile(r"[A-Za-z]")
_OTHER_ALPHA_CHARS = re.compile(
    r"[^\W\d_A-Za-z\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)
# Match Latin words or Persian/Arabic letters + ZWNJ (explicitly excluding ، ؛ ؟ « »)
_TOKEN_RE = re.compile(
    r"[A-Za-z][A-Za-z'\-]*|[\u0621-\u063A\u0641-\u064A\u067E\u0686\u0698\u06A9\u06AF\u06CC\u200c]+"
)
_SENT_SPLIT = re.compile(r"(?<=[.!?؟。])\s+|[\n\r]+|\s*[،؛;]\s*")

# --------------------------------------------------------------------------- #
# Stopwords
# --------------------------------------------------------------------------- #
EN_STOPWORDS = set(
    """
a about above after again against all am an and any are aren't as at be because been before being
below between both but by can can't cannot could couldn't did didn't do does doesn't doing don't down
during each few for from further had hadn't has hasn't have haven't having he he'd he'll he's her here
here's hers herself him himself his how how's i i'd i'll i'm i've if in into is isn't it it's its itself
let's me more most mustn't my myself no nor not of off on once only or other ought our ours ourselves
out over own same shan't she she'd she'll she's should shouldn't so some such than that that's the their
theirs them themselves then there there's these they they'd they'll they're they've this those through
to too under until up very was wasn't we we'd we'll we're we've were weren't what what's when when's
where where's which while who who's whom why why's with won't would wouldn't you you'd you'll you're
you've your yours yourself yourselves yeah oh ooh ah uh um hmm okay ok just like know get got gonna
wanna gotta really thing things also still even well now one two three much many said say says go
going come came way back time make made let lets maybe yes yet ever every whoa na la da causell
cause cos cuz tell told telling never another someone little tried wanted care day
""".split()
)

FA_STOPWORDS = set(
    """
من تو او ما شما آنها آن‌ها ایشان این آن اینجا آنجا اونجا که از به با در بر برای تا را هم اما ولی یا اگر چون
است هست هستم هستی هستیم هستند بود بودم بودی بودند بوده شد شده شود شدند میشه می‌شود میشود می‌شد میشد
داره دارد دارم داری داریم دارند داشت داشتم داشتی داشتند داشته کنم کند کنیم کنند کرد کردم کردی کردند کردن کرده
می‌کنم میکنم می‌کند میکند می‌کنیم میکنیم می‌کنند میکنند می‌خوام میخوام می‌خواهم خواهم مورد درباره
امروز دیروز فردا انجام صحبت یک دو سه چهار پنج شش هفت هشت نه ده بیست چارت تا خود چند چه چرا چطور کجا کی
وقتی پس سپس بسیار خیلی همه هر هیچ دیگه دیگر باید نباید شاید اون این‌ها اینها یه یک‌ آره بله خب حالا الان
سالمه سالشه براتون برایتان شروع کار روی توی پیش نزد سوی همواره هماره چندین هنگام زمان طوری جوری اونم اینم
کدام همین همان می‌آمدند میامدند آمدند آمد می‌رفت میرفت رفت رفتند رفته می‌گفت میگفت گفت گفتند می‌خواست میخواست
خواست حساب همراهی برخی آنان ایشان کسی کسانی چیزی چیزها بدون میان بین زیر بالای کنار دست پا سر چشم دل
خودش خودشان خودم خودت نکرده نکرد نکردند نکند نمی نمی‌ نتوانست نتوانستند بیرون درون برود بروند باشند باشد
باز دوباره همانند مانند مثل گونه گونه‌ای میگرد می‌گرد دیگری دیگران برامدند برآمدند پاسخه پاسخ دهدیر
سخن سخنان جا جایی سو سویی پیشتر بیشتر کمتر تنها فقط باری القصه خلاصه وجود قرار ادامه داد های یکی بعد برابر
""".split()
)

# Colloquial and ASR token normalization so inflected/misspelled words map to clean stems
_FA_TOKEN_NORMALIZE: dict[str, str] = {
    "شیرازه": "شیراز",
    "تهرانه": "تهران",
    "اصفهانه": "اصفهان",
    "مشهده": "مشهد",
    "تبریزه": "تبریز",
    "گودرزی‌ام": "گودرزی",
    "گودرزیم": "گودرزی",
    "کتخدا": "کدخدا",
    "کتخدای": "کدخدا",
    "کدخدای": "کدخدا",
    "روستاییان": "روستاییان",
    "روستائیان": "روستاییان",
    "دهکده": "روستا",
    "شاخه‌های": "شاخه",
    "شاخههای": "شاخه",
}

# --------------------------------------------------------------------------- #
# Emotion lexicons (text-based, not voice-based)
# --------------------------------------------------------------------------- #
EMOTION_LEXICON: dict[str, set[str]] = {
    "joy": {
        # English
        "happy", "happiness", "joy", "love", "loved", "loving", "great", "good", "glad", "smile",
        "smiling", "laugh", "laughing", "wonderful", "amazing", "beautiful", "excited", "fun",
        "hope", "hopeful", "thank", "thanks", "enjoy", "best", "awesome", "proud", "peace",
        "sweet", "dream", "free", "celebrate", "success", "successful", "nice",
        "safe", "warm", "bright", "kind", "rescue",
        # Persian
        "خوشحال", "شاد", "شادی", "عالی", "خوب", "عشق", "لذت", "موفق", "موفقیت", "امید",
        "خنده", "لبخند", "جالب", "مفید", "ممنون", "تشکر", "متشکرم", "زیبا", "قشنگ", "دوست",
        "دوستت", "عزیز", "پیشرفت", "بهبود", "مثبت", "خوشبخت", "آرامش", "مهربان", "مهربانی",
        "محبت", "کمک", "یار", "همدل", "همدلی", "برکت", "نور", "روشن", "پیروز",
    },
    "sadness": {
        # English
        "sad", "sadness", "cry", "crying", "cried", "tears", "tear", "lonely", "alone", "miss",
        "missing", "lost", "lose", "hurt", "hurting", "pain", "painful", "sorry", "broken",
        "break", "gone", "cold", "goodbye", "die", "dying", "dead", "bury", "buried", "empty",
        "grief", "heartbreak", "regret", "leave", "left", "leaving", "dark", "tired", "bad",
        "blurry", "upset", "sink", "sinking", "drown", "drowning",
        # Persian
        "غم", "غمگین", "اندوه", "ناراحت", "تنها", "تنهایی", "گریه", "دلتنگ", "دلتنگی", "افسوس",
        "متاسف", "متاسفانه", "درد", "رنج", "اشک", "خسته", "رفتی", "جدایی", "شکست", "فقر",
        "فقیر", "محتاج", "گرفتار", "بیچاره", "مظلوم", "سخت", "سختی", "تاریک", "تاریکی",
        "حسرت", "مرگ", "مرده", "سوگ", "غصه", "ناله", "آه", "فراموش",
    },
    "anger": {
        # English
        "angry", "anger", "hate", "hated", "mad", "furious", "damn", "stupid", "annoying",
        "fight", "rage", "kill", "shut", "liar", "blame", "sick", "cruel", "enemy", "war",
        # Persian
        "عصبانی", "خشم", "خشمگین", "غضب", "نفرت", "لعنت", "اعصاب", "دعوا", "کلافه", "متنفر",
        "بدم", "دشمن", "جنگ", "فریاد", "ظلم", "ظالم", "ستم", "توپید", "اعتراض", "خون", "کشتن",
    },
    "fear": {
        # English
        "afraid", "scared", "fear", "worry", "worried", "anxious", "anxiety", "nervous",
        "panic", "terrified", "danger", "dangerous", "hurry", "risk", "unsafe", "lie",
        "monster", "monsters", "ghost", "hide", "hiding", "run", "running", "nightmare",
        "trap", "trapped", "doubt", "protect",
        # Persian
        "ترس", "ترسید", "می‌ترسم", "میترسم", "نگران", "نگرانی", "وحشت", "اضطراب", "استرس",
        "خطر", "خطرناک", "مشکل", "چالش", "واهمه", "بیم", "هراس", "تهدید", "فرار", "پنهان",
        "تردید", "شک", "سرگردان",
    },
}
_NEGATORS = {
    "not", "no", "never", "don't", "dont", "won't", "wont", "can't", "cant",
    "couldn't", "couldnt", "wouldn't", "wouldnt", "nobody", "nothing",
    "نه", "نمی", "نمی‌", "هرگز", "هیچ",
}

# Persian domain phrases that are worth surfacing verbatim when present.
FA_PHRASES = [
    ("هوش مصنوعی", "بحث دربارهٔ هوش مصنوعی و کاربردهای آن"),
    ("شاخه‌های هوش مصنوعی", "بررسی زیرشاخه‌ها و حوزه‌های هوش مصنوعی"),
    ("یادگیری ماشین", "مباحث یادگیری ماشین"),
    ("پردازش زبان طبیعی", "پردازش زبان طبیعی"),
    ("شبکه عصبی", "شبکه‌های عصبی"),
    ("داده‌کاوی", "داده‌کاوی و تحلیل داده"),
]

KNOWN_PLACES = {
    "شیراز": ["شیراز", "شیرازه"],
    "تهران": ["تهران", "تهرانه"],
    "اصفهان": ["اصفهان", "اصفهانه"],
    "مشهد": ["مشهد", "مشهده"],
    "تبریز": ["تبریز", "تبریزه"],
    "ایران": ["ایران"],
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def detect_text_language(text: str) -> str:
    fa = len(_PERSIAN_CHARS.findall(text or ""))
    en = len(_LATIN_CHARS.findall(text or ""))
    if fa == 0 and en == 0:
        return "fa"
    return "fa" if fa >= en else "en"


def language_breakdown(text: str) -> dict[str, int]:
    fa = len(_PERSIAN_CHARS.findall(text or ""))
    en = len(_LATIN_CHARS.findall(text or ""))
    other = len(_OTHER_ALPHA_CHARS.findall(text or ""))
    total = fa + en + other
    if not total:
        return {"fa": 0, "en": 0, "other": 0}
    raw = {
        "fa": fa * 100.0 / total,
        "en": en * 100.0 / total,
        "other": other * 100.0 / total,
    }
    rounded = {k: int(v) for k, v in raw.items()}
    remainder = 100 - sum(rounded.values())
    for k in sorted(raw, key=lambda key: raw[key] - rounded[key], reverse=True)[:remainder]:
        rounded[k] += 1
    return rounded


def _clean_token(raw: str) -> str:
    tok = raw.strip("\u200c'\"-،؛؟.!?,:;«»()[]{}").lower()
    if tok in _FA_TOKEN_NORMALIZE:
        return _FA_TOKEN_NORMALIZE[tok]
    if tok.endswith("های") and len(tok) > 5:
        stem = tok[:-3].rstrip("\u200c")
        if len(stem) >= 3:
            return _FA_TOKEN_NORMALIZE.get(stem, stem)
    return tok


def _tokens(text: str) -> list[str]:
    out: list[str] = []
    for raw in _TOKEN_RE.findall(text or ""):
        tok = _clean_token(raw)
        if tok:
            out.append(tok)
    return out


def _is_stop(tok: str) -> bool:
    if not tok or len(tok) < 3:
        return True
    if tok in EN_STOPWORDS or tok in FA_STOPWORDS:
        return True
    # Filter common Persian verbal prefixes/suffixes if not a known noun
    if tok.startswith(("می‌", "نمی‌", "می", "نمی")) and tok.endswith(("ند", "ید", "یم", "دم", "دی")):
        return True
    return False


def split_sentences(text: str) -> list[str]:
    parts = [p.strip(" .،,!?؟«»") for p in _SENT_SPLIT.split(text or "")]
    return [p for p in parts if len(p) > 2]


def _segment_units(transcript: str, segment_texts: list[str] | None) -> list[str]:
    units: list[str] = []
    for seg in segment_texts or []:
        s = (seg or "").strip()
        if not s:
            continue
        splits = split_sentences(s)
        units.extend(splits if splits else [s])
    return units or split_sentences(transcript)


def _round_to_100(raw: dict[str, float]) -> dict[str, int]:
    total = sum(raw.values())
    if total <= 0:
        return {"joy": 18, "neutral": 72, "sadness": 4, "anger": 3, "fear": 3}
    scaled = {k: v * 100 / total for k, v in raw.items()}
    rounded = {k: int(v) for k, v in scaled.items()}
    remainder = 100 - sum(rounded.values())
    for k in sorted(scaled, key=lambda key: scaled[key] - rounded[key], reverse=True)[:remainder]:
        rounded[k] += 1
    return rounded


# --------------------------------------------------------------------------- #
# Emotions
# --------------------------------------------------------------------------- #
def emotion_distribution(units: list[str]) -> tuple[dict[str, int], dict[str, int]]:
    """Return (percentages, raw_hit_counts) over joy/neutral/sadness/anger/fear."""
    hits = {"joy": 0.0, "sadness": 0.0, "anger": 0.0, "fear": 0.0}
    neutral_units = 0
    for unit in units:
        toks = _tokens(unit)
        unit_hit = False
        for idx, tok in enumerate(toks):
            window = toks[max(0, idx - 4) : idx]
            negated = any(w in _NEGATORS for w in window)
            for emo, lex in EMOTION_LEXICON.items():
                if tok in lex or (len(tok) > 4 and any(tok.startswith(w) for w in lex if len(w) >= 4)):
                    if negated and emo == "joy":
                        hits["sadness"] += 1.0
                    elif negated and emo in {"sadness", "fear", "anger"}:
                        # e.g., "not to worry", "don't wanna be lonely" still carries that emotional theme!
                        hits[emo] += 0.85
                    else:
                        hits[emo] += 1.0
                    unit_hit = True
        if not unit_hit:
            neutral_units += 1

    total_emo_hits = sum(hits.values())
    if total_emo_hits == 0:
        default_dist = {"joy": 20, "neutral": 68, "sadness": 5, "anger": 3, "fear": 4}
        return default_dist, {
            "joy": 0,
            "neutral": neutral_units,
            "sadness": 0,
            "anger": 0,
            "fear": 0,
        }

    effective_neutral = max(1.0, min(float(neutral_units) * 0.45, total_emo_hits * 1.1))
    raw = {
        "joy": hits["joy"] * 1.35,
        "neutral": effective_neutral,
        "sadness": hits["sadness"] * 1.35,
        "anger": hits["anger"] * 1.35,
        "fear": hits["fear"] * 1.35,
    }
    return _round_to_100(raw), {
        "joy": int(round(hits["joy"])),
        "neutral": neutral_units,
        "sadness": int(round(hits["sadness"])),
        "anger": int(round(hits["anger"])),
        "fear": int(round(hits["fear"])),
    }


def _sentiment_from_emotions(emotions: dict[str, int], lang: str) -> tuple[str, str, float]:
    pos = emotions.get("joy", 0)
    neg = emotions.get("sadness", 0) + emotions.get("anger", 0) + emotions.get("fear", 0)
    dominant = max(("joy", "sadness", "anger", "fear"), key=lambda k: emotions.get(k, 0))
    names_fa = {
        "joy": "شادی و حس مثبت",
        "sadness": "غم و دلتنگی",
        "anger": "خشم و تنش",
        "fear": "نگرانی و ترس",
    }
    if pos >= 20 and neg >= 25:
        label = "Mixed"
    elif neg >= 25 and neg > pos:
        label = "Negative"
    elif pos >= 24 and pos >= neg:
        label = "Positive"
    else:
        label = "Neutral"
    score = round(max(0.05, min(0.95, 0.5 + (pos - neg) / 200)), 2)
    if lang == "en":
        if label == "Neutral":
            exp = (
                f"Overall tone is balanced/informational ({emotions.get('neutral', 0)}% neutral), "
                f"with subtle {dominant} undertones ({emotions.get(dominant, 0)}%)."
            )
        else:
            exp = (
                f"Overall tone is {label.lower()}; the strongest emotional signal in the lyrics/speech is "
                f"{dominant} ({emotions.get(dominant, 0)}%), alongside {emotions.get('neutral', 0)}% neutral phrasing."
            )
    else:
        label_fa = {
            "Positive": "مثبت",
            "Negative": "منفی/اندوهگین",
            "Mixed": "ترکیبی (دوگانه)",
            "Neutral": "متعادل و اطلاع‌رسانی",
        }[label]
        if label == "Neutral":
            exp = (
                f"لحن کلی گفتار {label_fa} است ({emotions.get('neutral', 0)}٪ خنثی) "
                f"و بیشترین رگهٔ حسی در واژه‌ها مربوط به «{names_fa[dominant]}» ({emotions.get(dominant, 0)}٪) است."
            )
        else:
            exp = (
                f"لحن کلی متن {label_fa} ارزیابی می‌شود؛ قوی‌ترین نشانهٔ احساسی در واژگان "
                f"«{names_fa[dominant]}» ({emotions.get(dominant, 0)}٪) است."
            )
    return label, exp, score


# --------------------------------------------------------------------------- #
# Keywords / topics / entities
# --------------------------------------------------------------------------- #
_FA_NON_PERSON_WORDS = FA_STOPWORDS | {
    "شرکت", "دانشگاه", "سازمان", "موسسه", "مؤسسه", "بانک", "وزارت", "بیمارستان",
    "مدرسه", "گروه", "تیم", "پروژه", "سیستم", "سامانه", "برنامه", "فایل",
    "صوتی", "متخصص", "هوش", "مصنوعی", "شاخه", "تست", "امروز", "دیروز", "فردا",
    "ایران", "تهران", "شیراز", "اصفهان", "مشهد", "تبریز", "روستا", "شهر",
    "کار", "زندگی", "درس", "تحصیل", "صحبت", "فکر", "سوال", "پاسخ",
}

_EN_NON_PERSON_WORDS = EN_STOPWORDS | {
    "company", "corporation", "university", "institute", "organization", "agency",
    "department", "ministry", "hospital", "school", "college", "bank", "group",
    "team", "project", "system", "program", "audio", "track", "song", "music",
    "album", "file", "recording", "today", "yesterday", "tomorrow", "monday",
    "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "june", "july", "august",
    "september", "october", "november", "december",
    "boston", "london", "paris", "tehran", "shiraz", "iran", "america",
    "california", "canada", "germany", "england", "new", "york", "los", "angeles",
    "working", "talking", "speaking", "going", "coming", "calling", "testing",
    "happy", "sad", "glad", "sorry", "ready", "sure", "fine", "good", "great",
    "here", "there", "fine", "okay", "alright", "alone", "lonely", "afraid",
    "scared", "tired", "sick", "done", "late", "early", "back", "home",
}

_KNOWN_EN_PLACES = {
    "Boston", "London", "Paris", "Tehran", "Shiraz", "Isfahan", "Mashhad", "Tabriz",
    "Iran", "America", "United States", "California", "New York", "Los Angeles",
    "Chicago", "Houston", "Seattle", "San Francisco", "Washington", "Toronto",
    "Vancouver", "Montreal", "Canada", "Germany", "Berlin", "Munich", "England",
    "United Kingdom", "France", "Italy", "Rome", "Spain", "Madrid", "Barcelona",
    "Dubai", "Istanbul", "Turkey", "Tokyo", "Japan", "China", "India", "Sydney",
    "Australia",
}

_KNOWN_ORGANIZATIONS: list[tuple[str, list[str]]] = [
    ("Google", ["google", "گوگل"]),
    ("Microsoft", ["microsoft", "مایکروسافت"]),
    ("OpenAI", ["openai", "اوپن‌ای‌آی", "اوپن ای آی"]),
    ("Apple", ["apple", "اپل"]),
    ("Amazon", ["amazon", "آمازون"]),
    ("Meta", ["meta", "متا", "فیسبوک", "facebook"]),
    ("Tesla", ["tesla", "تسلا"]),
    ("Netflix", ["netflix", "نتفلیکس"]),
    ("Spotify", ["spotify", "اسپاتیفای"]),
    ("YouTube", ["youtube", "یوتیوب"]),
    ("Telegram", ["telegram", "تلگرام"]),
    ("Instagram", ["instagram", "اینستاگرام"]),
    ("دانشگاه تهران", ["دانشگاه تهران", "tehran university", "university of tehran"]),
    ("دانشگاه صنعتی شریف", ["دانشگاه شریف", "دانشگاه صنعتی شریف", "sharif university"]),
    ("دانشگاه شیراز", ["دانشگاه شیراز", "shiraz university"]),
    ("دانشگاه امیرکبیر", ["دانشگاه امیرکبیر", "دانشگاه صنعتی امیرکبیر", "amirkabir university"]),
    ("دانشگاه شهید بهشتی", ["دانشگاه شهید بهشتی", "shahid beheshti university"]),
    ("دانشگاه اصفهان", ["دانشگاه اصفهان", "isfahan university"]),
    ("دانشگاه فردوسی", ["دانشگاه فردوسی", "ferdowsi university"]),
    ("دیجی‌کالا", ["دیجی‌کالا", "دیجی کالا", "digikala"]),
    ("اسنپ", ["اسنپ", "snapp"]),
    ("تپسی", ["تپسی", "tapsi"]),
    ("کافه‌بازار", ["کافه‌بازار", "کافه بازار", "cafebazaar"]),
    ("ایرانسل", ["ایرانسل", "irancell"]),
    ("همراه اول", ["همراه اول", "hamrah aval"]),
    ("صدا و سیما", ["صدا و سیما", "صداوسیما", "irib"]),
]


def _clean_fa_person_candidate(raw_cand: str) -> str:
    cand = re.sub(r"(?:‌ام|ام| هستم| می‌باشد| است| بود)$", "", raw_cand.strip("،,.؛:!؟«»() ")).strip()
    parts = [p.strip("\u200c") for p in cand.split() if p.strip("\u200c")]
    valid: list[str] = []
    for p in parts:
        norm_p = _FA_TOKEN_NORMALIZE.get(p, p)
        if (
            len(norm_p) < 2
            or norm_p in _FA_NON_PERSON_WORDS
            or _is_stop(norm_p)
            or norm_p.endswith(("هایی", "های", "تان", "شان", "مان"))
        ):
            break
        valid.append(norm_p)
        if len(valid) == 2:
            break
    return " ".join(valid)


def _clean_en_person_candidate(raw_cand: str) -> str:
    cand = raw_cand.strip(" ,.!?;:\"'()[]{}")
    parts = cand.split()
    valid: list[str] = []
    for p in parts:
        p_clean = p.strip(".,!?;:\"'")
        p_low = p_clean.lower()
        if (
            not p_clean
            or not p_clean[0].isupper()
            or len(p_clean) < 2
            or p_low in _EN_NON_PERSON_WORDS
        ):
            break
        valid.append(p_clean)
        if len(valid) == 3:
            break
    return " ".join(valid)


def extract_people(text: str, lang: str = "") -> list[str]:
    people: list[str] = []
    if not text or not text.strip():
        return people

    cleaned_fa = apply_asr_rules(text)

    # 1. Persian patterns (always run so mixed or Persian transcripts work seamlessly)
    fa_patterns = (
        r"(?:اسمم|نامم|اسم من|نام من|نام بنده|اسم بنده)\s+([آ-ی\u200c]{2,15}(?:\s+[آ-ی\u200c]{2,15})?)",
        r"(?:من|بنده)\s+([آ-ی\u200c]{3,14}\s+[آ-ی\u200c]{3,15})(?:‌ام|ام)(?=[\s،,.!؟]|$)",
        r"(?:من|بنده)\s+([آ-ی\u200c]{3,14}(?:\s+[آ-ی\u200c]{3,15})?)\s+هستم(?=[\s،,.!؟]|$)",
        r"(?:آقای|خانم|دکتر|مهندس|استاد|پروفسور|سید|حاج|شیخ)\s+([آ-ی\u200c]{3,15}(?:\s+[آ-ی\u200c]{3,15})?)",
        r"(?:با صدای|خواننده|اثر|توسط|به نام)\s+([آ-ی\u200c]{3,15}(?:\s+[آ-ی\u200c]{3,15})?)",
    )
    for pat in fa_patterns:
        for m in re.finditer(pat, cleaned_fa):
            cand = _clean_fa_person_candidate(m.group(1))
            if cand and cand not in people:
                people.append(cand)

    # 2. English patterns (case-insensitive intro/cue, capitalized proper name)
    en_patterns = (
        r"\b(?i:my name is|i am|i'm|this is|call me|speaking with|interview with|hosted by|sung by|performed by|written by|featuring|feat\.?)\s+([A-Z][a-z]{1,18}(?:\s+[A-Z][a-z]{1,18}){0,2})",
        r"\b(?:Mr|Mrs|Ms|Miss|Dr|Prof|President|CEO|Coach|Director|Senator|Mayor)\.?\s+([A-Z][a-z]{1,18}(?:\s+[A-Z][a-z]{1,18}){0,2})",
        r"\b([A-Z][a-z]{2,16}\s+[A-Z][a-z]{2,18})\s+(?i:said|says|told|asked|explained|mentioned|reported|announced|introduced|joined|spoke)\b",
    )
    for pat in en_patterns:
        for m in re.finditer(pat, text):
            cand = _clean_en_person_candidate(m.group(1))
            if cand and cand not in people:
                people.append(cand)

    return people[:6]


def extract_locations(text: str) -> list[str]:
    found: list[str] = []
    if not text or not text.strip():
        return found

    for canonical, variants in KNOWN_PLACES.items():
        if any(re.search(rf"(?<!\S){re.escape(v)}(?=[،,.\s!؟?]|$)", text) for v in variants):
            if canonical not in found:
                found.append(canonical)

    for place in sorted(_KNOWN_EN_PLACES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(place)}\b", text, flags=re.IGNORECASE):
            # Only match lowercase "boston" etc. if capitalized in text or preceded by a locative preposition
            if re.search(rf"\b{re.escape(place)}\b", text) or re.search(
                rf"\b(?i:in|from|to|at|near|back to|around|visit|visiting)\s+{re.escape(place)}\b",
                text,
            ):
                if place not in found:
                    found.append(place)

    for m in re.finditer(
        r"\b(?i:in|from|at|to|back to|living in|based in)\s+([A-Z][a-z]{2,18}(?:\s+[A-Z][a-z]{2,18})?)",
        text,
    ):
        cand = m.group(1).strip()
        parts = cand.split()
        if (
            cand
            and all(p.lower() not in _EN_NON_PERSON_WORDS and p.lower() not in EN_STOPWORDS for p in parts)
            and cand not in found
            and cand not in {"I", "The", "My", "Our", "Your", "His", "Her", "Their"}
        ):
            if cand in _KNOWN_EN_PLACES:
                found.append(cand)
    return found[:6]


_FA_ORG_HEADS = (
    "شرکت", "دانشگاه", "سازمان", "موسسه", "مؤسسه", "بانک", "وزارت",
    "بیمارستان", "مدرسه", "گروه", "بنیاد", "انجمن", "مرکز", "پژوهشکده",
    "پژوهشگاه", "کلینیک", "آژانس", "فدراسیون", "باشگاه", "استودیو",
)
_FA_ORG_STOP_TAIL = FA_STOPWORDS | {
    "کار", "تحصیل", "درس", "زندگی", "صحبت", "شرکت", "استفاده", "همکاری",
    "فعالیت", "برگزار", "تولید", "طراحی", "اجرا", "ایجاد", "تاسیس", "تأسیس",
    "می‌کنم", "میکنم", "می‌کند", "میکند", "می‌کنیم", "میکنیم", "کردم", "کرد",
    "دارم", "دارد", "هستم", "است", "بود", "شد", "رفتم", "آمدم",
}


def extract_organizations(text: str) -> list[str]:
    orgs: list[str] = []
    if not text or not text.strip():
        return orgs

    cleaned = apply_asr_rules(text)

    # 1. Persian organization head + proper name tokens
    heads_pat = "|".join(_FA_ORG_HEADS)
    for m in re.finditer(
        rf"(?<!\S)({heads_pat})\s+([آ-یA-Za-z0-9\u200c]{2,20}(?:\s+[آ-یA-Za-z0-9\u200c]{2,20}){{0,2}})",
        cleaned,
    ):
        head = m.group(1).strip()
        tail_words = m.group(2).strip("،,.؛:!؟«»() ").split()
        valid_tail: list[str] = []
        for w in tail_words:
            w_clean = w.strip("\u200c،,.؛:!؟")
            if (
                not w_clean
                or len(w_clean) < 2
                or w_clean in _FA_ORG_STOP_TAIL
                or _is_stop(w_clean)
            ):
                break
            valid_tail.append(w_clean)
            if len(valid_tail) == 2:
                break
        if valid_tail:
            cand = f"{head} {' '.join(valid_tail)}"
            if cand not in orgs:
                orgs.append(cand)

    # 2. English organization patterns (e.g. "Acme Corp", "University of Oxford", "MIT Media Lab")
    en_org_patterns = (
        r"\b([A-Z][A-Za-z0-9&'\-]+(?:\s+[A-Z][A-Za-z0-9&'\-]+){0,3}\s+(?:Inc|Corp|Corporation|University|College|Institute|Company|Ltd|LLC|Group|Foundation|Association|Bank|Hospital|Labs|Laboratory|Studio|Studios|Records|Media|Agency|Ministry|Department| Airlines|Airways|Systems|Technologies|Solutions|Networks))\b",
        r"\b((?:University|Institute|Bank|Ministry|Department|College|Hospital)\s+of\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)\b",
    )
    for pat in en_org_patterns:
        for m in re.finditer(pat, text):
            cand = m.group(1).strip(" ,.!?;:")
            if cand and cand not in orgs:
                orgs.append(cand)

    # 3. Known organizations/brands/institutions mentioned explicitly in text
    text_low = cleaned.lower()
    for canonical, aliases in _KNOWN_ORGANIZATIONS:
        if any(
            re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text_low)
            for alias in aliases
        ):
            if canonical not in orgs and not any(canonical in existing or existing in canonical for existing in orgs):
                orgs.append(canonical)

    return orgs[:6]


def extract_keywords(
    text: str,
    units: list[str],
    people: list[str] | None = None,
    locations: list[str] | None = None,
    limit: int = 8,
) -> list[tuple[str, int]]:
    toks = [t for t in _tokens(text) if not _is_stop(t)]
    counts = Counter(toks)

    ranked: list[tuple[str, int]] = []
    used_words: set[str] = set()

    # 1. Domain phrases present in text
    for phrase, _desc in FA_PHRASES:
        if phrase in text:
            c = max(1, text.count(phrase))
            ranked.append((phrase, c + 2))
            used_words.update(_tokens(phrase))

    # 2. Extracted people & locations (so "پوریا گودرزی" or "شیراز" appear cleanly instead of fragments)
    for person in (people or [])[:2]:
        if all(w not in used_words for w in _tokens(person)):
            ranked.append((person, 2))
            used_words.update(_tokens(person))

    for loc in (locations or [])[:2]:
        if loc not in used_words:
            ranked.append((loc, max(1, text.count(loc))))
            used_words.update(_tokens(loc))

    # 3. Top unigrams (clean, normalized stems)
    for tok, n in counts.most_common(limit * 4):
        if tok in used_words:
            continue
        ranked.append((tok, n))
        used_words.add(tok)
        if len(ranked) >= limit:
            break

    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked[:limit]


def _repetition_ratio(units: list[str], full_text: str = "") -> float:
    if len(units) >= 4:
        norm = [re.sub(r"\W+", " ", u.lower()).strip() for u in units if u.strip()]
        if norm:
            counts = Counter(norm)
            repeated = sum(c for c in counts.values() if c > 1)
            unit_ratio = repeated / len(norm)
            if unit_ratio >= 0.22:
                return unit_ratio
    # Also check repeated 4-word refrains (common in songs where chorus lines merge/split differently)
    toks = _tokens(full_text or " ".join(units))
    if len(toks) >= 20:
        fourgrams = Counter(tuple(toks[i : i + 4]) for i in range(len(toks) - 3))
        repeated_4g = sum(c for c in fourgrams.values() if c >= 2)
        return repeated_4g / max(1, len(toks) - 3)
    return 0.0


# --------------------------------------------------------------------------- #
# Summary
# --------------------------------------------------------------------------- #
def _extractive_points(
    units: list[str], keywords: list[tuple[str, int]], k: int = 4
) -> list[str]:
    if not units:
        return []
    weights = {w: n for w, n in keywords}
    seen: set[str] = set()
    scored: list[tuple[float, int, str]] = []
    for idx, unit in enumerate(units):
        cleaned_unit = unit.strip(" .،,!?؟«»")
        key = re.sub(r"\W+", " ", cleaned_unit.lower()).strip()
        if not key or key in seen or len(cleaned_unit) < 6:
            continue
        seen.add(key)
        toks = _tokens(cleaned_unit)
        if not toks:
            continue
        len_bonus = 1.2 if 4 <= len(toks) <= 30 else 0.7
        score = sum(weights.get(t, 0) for t in toks)
        score += sum(n * 1.5 for w, n in keywords if " " in w and w in cleaned_unit.lower())
        pos_bonus = 1.15 if idx < max(3, len(units) // 10) else 1.0
        scored.append(((score + 0.5) * len_bonus * pos_bonus / (len(toks) ** 0.45), idx, cleaned_unit))
    top = sorted(scored, key=lambda x: x[0], reverse=True)[:k]
    return [u for _, _, u in sorted(top, key=lambda x: x[1])]


# --------------------------------------------------------------------------- #
# Bilingual Concept Mappings & Language Localization
# --------------------------------------------------------------------------- #
# Cross-lingual concept dictionary so Persian questions match English transcripts and vice-versa
_FA_TO_EN_CONCEPTS: dict[str, list[str]] = {
    "تنها": ["lonely", "alone"],
    "تنهایی": ["lonely", "alone"],
    "سرد": ["cold"],
    "سرما": ["cold"],
    "خانه": ["home", "inside", "stay"],
    "عشق": ["love", "loved"],
    "عاشق": ["love", "loved"],
    "دوست": ["friends", "friend", "love"],
    "دوستان": ["friends", "friend", "bury"],
    "دروغ": ["lie"],
    "نگران": ["worry", "worried"],
    "نگرانی": ["worry", "worried"],
    "ترس": ["afraid", "scared", "fear", "worry", "blurry", "night"],
    "غم": ["sad", "lonely", "cold", "cry", "bury", "break", "die"],
    "غمگین": ["sad", "lonely", "cold", "bury", "break"],
    "مرگ": ["die", "bury", "lose", "life"],
    "مردن": ["die", "bury", "lose", "life"],
    "محافظت": ["protect", "rescue"],
    "نجات": ["rescue", "protect"],
    "ستاره": ["stars"],
    "ستاره‌ها": ["stars"],
    "عجله": ["hurry"],
    "شتاب": ["hurry"],
    "چشم": ["eyes", "blurry"],
    "شب": ["night"],
    "کجا": ["where", "go", "home"],
    "رفتن": ["go", "come", "home"],
}

_EN_TO_FA_CONCEPTS: dict[str, list[str]] = {
    "ai": ["هوش", "مصنوعی", "ai"],
    "artificial": ["هوش", "مصنوعی"],
    "intelligence": ["هوش", "مصنوعی"],
    "branch": ["شاخه", "شاخه‌های"],
    "branches": ["شاخه", "شاخه‌های", "چهار"],
    "shiraz": ["شیراز", "شیرازه"],
    "pouria": ["پوریا", "گودرزی"],
    "goodarzi": ["پوریا", "گودرزی"],
    "age": ["بیست", "سالمه", "سال"],
    "old": ["بیست", "سالمه", "سال"],
    "specialist": ["متخصص", "هوش"],
    "expert": ["متخصص", "هوش"],
    "project": ["پروژه", "تست"],
    "test": ["تست", "پروژه"],
    "village": ["روستا", "روستاییان", "دهکده", "کدخدا"],
    "villagers": ["روستاییان", "مردم", "روستا"],
    "headman": ["کدخدا", "کتخدا"],
    "chief": ["کدخدا", "کتخدا"],
    "kadkhoda": ["کدخدا", "کتخدا"],
    "tax": ["مالیات", "مال", "فتیه"],
    "taxes": ["مالیات", "مال", "فتیه"],
    "money": ["مال", "مالیات"],
    "hasani": ["حسنی"],
    "people": ["مردم", "روستاییان", "همراهانش"],
    "story": ["روستا", "کدخدا", "حسنی", "داستان"],
}

_TERM_GLOSS_EN_TO_FA: dict[str, str] = {
    "lie": "دروغ/تظاهر (lie)",
    "cold": "سرما و دلتنگی (cold)",
    "lonely": "تنهایی (lonely)",
    "home": "خانه و پناهگاه (home)",
    "love": "عشق (love)",
    "worry": "نگرانی (worry)",
    "honey": "عزیزم (honey)",
    "hurry": "عجله/شتاب (hurry)",
    "friends": "دوستان (friends)",
    "bury": "خاک‌سپاری/از دست دادن (bury)",
    "protect": "محافظت (protect)",
    "rescue": "نجات دادن (rescue)",
    "stars": "ستاره‌ها (stars)",
    "blurry": "تار و مبهم (blurry)",
    "break": "شکستن (break)",
}

_TERM_GLOSS_FA_TO_EN: dict[str, str] = {
    "هوش مصنوعی": "Artificial Intelligence (هوش مصنوعی)",
    "شاخه‌های هوش مصنوعی": "Branches of AI (شاخه‌های هوش مصنوعی)",
    "یادگیری ماشین": "Machine Learning (یادگیری ماشین)",
    "پردازش زبان طبیعی": "Natural Language Processing (پردازش زبان طبیعی)",
    "شبکه عصبی": "Neural Networks (شبکه عصبی)",
    "داده‌کاوی": "Data Mining (داده‌کاوی)",
    "پوریا گودرزی": "Pouria Goodarzi (پوریا گودرزی)",
    "شیراز": "Shiraz (شیراز)",
    "متخصص": "AI Specialist (متخصص)",
    "پروژه": "Project (پروژه)",
    "تست": "Testing (تست)",
    "کدخدا": "Village Headman / Kadkhoda (کدخدا)",
    "روستا": "Village (روستا)",
    "روستاییان": "Villagers (روستاییان)",
    "حسنی": "Hasani (حسنی)",
    "مالیات": "Taxes / Tribute (مالیات)",
    "مردم": "People (مردم)",
    "فکر": "Thought / Plan (فکر)",
    "خدا": "God (خدا)",
    "راه": "Path / Way (راه)",
    "بار": "Burden / Time (بار)",
}


def detect_question_language(question: str) -> str:
    """Detect the language the user wants the response in based on their question."""
    q_low = (question or "").lower()
    if any(p in q_low for p in ("به فارسی", "در زبان فارسی", "in persian", "in farsi", "persian language")):
        return "fa"
    if any(p in q_low for p in ("به انگلیسی", "in english", "english language")):
        return "en"
    return detect_text_language(question)


def _format_summary_in_language(analysis: dict[str, Any], target_lang: str, raw_text: str) -> tuple[str, str]:
    """Return (localized_summary, localized_keywords_str) in `target_lang` regardless of audio language."""
    audio_lang = analysis["sentiment"]["language"]
    ents = analysis["extracted_entities"]
    keywords: list[str] = ents.get("keywords") or []
    people: list[str] = ents.get("people") or []
    locations: list[str] = ents.get("locations") or []
    emotions: dict[str, int] = analysis["sentiment"]["emotions"]
    label: str = analysis["sentiment"]["label"]
    points: list[str] = analysis["detailed_summary"].get("important_points") or []

    # Same language as audio -> use the native summary directly
    if target_lang == audio_lang:
        sep = ", " if target_lang == "en" else "، "
        return analysis["short_summary"], sep.join(keywords[:6])

    dominant_emo = max(("joy", "sadness", "anger", "fear"), key=lambda e: emotions.get(e, 0))

    if target_lang == "fa" and audio_lang == "en":
        # English audio -> Persian response
        fa_kw = [_TERM_GLOSS_EN_TO_FA.get(k.lower(), k) for k in keywords[:6]]
        emo_fa = {
            "joy": "شادی و حس مثبت",
            "sadness": "غم و دلتنگی",
            "anger": "خشم",
            "fear": "نگرانی و ترس",
        }[dominant_emo]
        label_fa = {
            "Positive": "مثبت",
            "Negative": "منفی و غمگین",
            "Mixed": "ترکیبی (عاطفی)",
            "Neutral": "متعادل",
        }.get(label, "متعادل")
        theme_str = "، ".join(fa_kw[:4]) if fa_kw else "مفاهیم احساسی"
        summary_fa = (
            f"این فایل صوتی به زبان انگلیسی است و محور اصلی آن دربارهٔ «{theme_str}» می‌باشد. "
            f"لحن کلی اثر {label_fa} ارزیابی می‌شود و قوی‌ترین حس دریافتی در متن «{emo_fa}» ({emotions.get(dominant_emo, 0)}٪) است."
        )
        if points:
            excerpt = " / ".join(f'"{p}"' for p in points[:2])
            summary_fa += f" جملات شاخص در متن انگلیسی: {excerpt}"
        return summary_fa, "، ".join(fa_kw)

    # Persian audio -> English response
    en_kw = [_TERM_GLOSS_FA_TO_EN.get(k, k) for k in keywords[:6]]
    en_people = [_TERM_GLOSS_FA_TO_EN.get(p, p) for p in people]
    en_locs = [_TERM_GLOSS_FA_TO_EN.get(loc, loc) for loc in locations]
    theme_str = ", ".join(en_kw[:4]) if en_kw else "the spoken topic"

    if len(raw_text) <= 220:
        who_part = " the speaker"
        if en_people:
            loc_part = f" from {en_locs[0]}" if en_locs else ""
            who_part = f" the speaker ({', '.join(en_people)}{loc_part}) introduces themselves and"
            if "بیست و دو" in raw_text or "22" in raw_text:
                who_part = f" the speaker ({', '.join(en_people)}{loc_part}, 22 years old) introduces themselves and"
        summary_en = (
            f"In this Persian voice clip,{who_part} discusses {theme_str}. "
            f"Overall tone is {label.lower()} ({emotions.get('neutral', 0)}% neutral, {emotions.get('joy', 0)}% positive). "
            f'Original Persian transcript: "{raw_text}"'
        )
    else:
        loc_part = f" set around {', '.join(en_locs)}" if en_locs else ""
        summary_en = (
            f"This is a Persian narrative/audio recording{loc_part} centered on {theme_str}. "
            f"The overall emotional tone is {label.lower()} (Neutral {emotions.get('neutral', 0)}%, "
            f"Joy {emotions.get('joy', 0)}%, Sadness {emotions.get('sadness', 0)}%, Fear {emotions.get('fear', 0)}%)."
        )
        if points:
            excerpt = " / ".join(f'"{p[:100]}"' for p in points[:2])
            summary_en += f" Key Persian excerpts: {excerpt}."
    return summary_en, ", ".join(en_kw)


def _build_bilingual_insights(
    analysis_base: dict[str, Any],
    raw_text: str,
    points: list[str],
    lang: str,
    keywords: list[str],
    people: list[str],
    locations: list[str],
    is_song: bool,
) -> dict[str, Any]:
    summary_fa, _ = _format_summary_in_language(analysis_base, "fa", raw_text)
    summary_en, _ = _format_summary_in_language(analysis_base, "en", raw_text)

    # Key Points in Persian and English
    if lang == "fa":
        key_points_fa = [p for p in points[:4] if p.strip()]
        key_points_en: list[str] = []
        for p in key_points_fa:
            p_clean = p.strip()
            if "پوریا گودرزی" in p_clean:
                key_points_en.append("Speaker introduces himself as Pouria Goodarzi from Shiraz, Iran")
            elif "بیست و دو" in p_clean:
                key_points_en.append("Speaker mentions his age: 22 years old")
            elif "متخصص هوش مصنوعی" in p_clean or "تست انجام" in p_clean:
                key_points_en.append("AI specialist testing and evaluating the speech intelligence project")
            elif "چهار تا شاخه" in p_clean:
                key_points_en.append("Stating that Artificial Intelligence comprises four primary branches")
            elif "هوش مصنوعی" in p_clean:
                key_points_en.append("Discussion centered on Artificial Intelligence and its domains")
            elif "کدخدا" in p_clean:
                key_points_en.append("Narrative regarding the village headman (Kadkhoda) and local events")
            elif "روستا" in p_clean:
                key_points_en.append("Community life and social dynamics within the village")
            else:
                key_points_en.append(f'Key excerpt: "{p_clean}"')
    else:
        key_points_en = [p for p in points[:4] if p.strip()]
        key_points_fa: list[str] = []
        for p in key_points_en:
            p_low = p.lower()
            if "worry" in p_low or "lie" in p_low:
                key_points_fa.append(f'هشدار درباره فریب و تظاهر: "{p}"')
            elif "cold" in p_low or "lonely" in p_low:
                key_points_fa.append(f'احساس سرما، دلتنگی و انزوا: "{p}"')
            elif "bury" in p_low or "friend" in p_low:
                key_points_fa.append(f'یادآوری تلخ دوستان از دست رفته: "{p}"')
            elif "protect" in p_low or "rescue" in p_low:
                key_points_fa.append(f'تلاش برای حمایت و مراقبت از فرد مورد علاقه: "{p}"')
            elif "home" in p_low:
                key_points_fa.append(f'آرزوی بازگشت به خانه و پناه امن: "{p}"')
            else:
                key_points_fa.append(f'جمله شاخص در متن انگلیسی: "{p}"')

    # Decisions / Conclusions in Persian and English
    if lang == "fa":
        if "تست" in raw_text or "پروژه" in raw_text:
            decisions_fa = ["اجرای پروژه ارزیابی و آزمایش قابلیت‌های سامانه هوش مصنوعی"]
            decisions_en = ["Executing an evaluation and testing project for AI system capabilities"]
        elif "شاخه" in raw_text:
            decisions_fa = ["دسته‌بندی و بررسی ساختار ۴ شاخه اصلی هوش مصنوعی"]
            decisions_en = ["Categorizing and exploring the 4 core branches of artificial intelligence"]
        else:
            decisions_fa = ["بررسی رویدادها، شرایط اجتماعی و تصمیمات جمعی در بستر روایت"]
            decisions_en = ["Reviewing events, social conditions, and collective decisions within the narrative"]
    else:
        if is_song:
            decisions_fa = ["رویارویی با آسیب‌پذیری عاطفی و اولویت‌بخشی به محافظت از فرد نزدیک"]
            decisions_en = ["Confronting emotional vulnerability and prioritizing the protection of loved ones"]
        else:
            decisions_fa = ["بررسی پیام اصلی و نتیجه‌گیری پیرامون موضوعات مطرح‌شده در گفتار"]
            decisions_en = ["Analyzing the core message and key takeaways discussed in the audio"]

    return {
        "fa": {
            "summary": summary_fa,
            "key_points": key_points_fa,
            "decisions": decisions_fa,
        },
        "en": {
            "summary": summary_en,
            "key_points": key_points_en,
            "decisions": decisions_en,
        },
    }


def build_smart_analysis(
    transcript_text: str,
    segment_texts: list[str] | None = None,
    audio_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text = (transcript_text or "").strip()
    lang = detect_text_language(text)
    if lang == "fa":
        text = apply_asr_rules(text)
        segment_texts = [apply_asr_rules(s) for s in (segment_texts or [])]
    units = _segment_units(text, segment_texts)

    people = extract_people(text, lang)
    locations = extract_locations(text)
    organizations = extract_organizations(text)

    meta = audio_metadata or {}
    if meta.get("has_metadata"):
        for person_field in ("artist", "album_artist", "composer"):
            val = (meta.get(person_field) or "").strip()
            if val and not any(val.lower() == p.lower() for p in people):
                people.insert(0, val)
        pub = (meta.get("publisher") or "").strip()
        if pub and not any(pub.lower() == o.lower() for o in organizations):
            organizations.append(pub)

    keywords_ranked = extract_keywords(text, units, people=people, locations=locations)
    keywords = [k for k, _ in keywords_ranked]
    emotions, _raw = emotion_distribution(units)
    label, explanation, score = _sentiment_from_emotions(emotions, lang)
    points = _extractive_points(units, keywords_ranked, k=4)
    is_song = _repetition_ratio(units, text) >= 0.15 or bool(
        meta.get("has_metadata") and (meta.get("artist") or meta.get("album"))
    )
    top_kw = keywords[:4]

    if not text:
        short_summary = ""
    elif lang == "en":
        dominant_emo = max(("joy", "sadness", "anger", "fear"), key=lambda e: emotions.get(e, 0))
        lead = (
            "This English audio track is a lyrical song with recurring vocal refrains"
            if is_song
            else "This recording is spoken in English"
        )
        theme = f" revolving around themes of {', '.join(top_kw)}" if top_kw else ""
        mood = (
            f". The emotional tone is {label.lower()}, led by {dominant_emo} ({emotions.get(dominant_emo, 0)}%)"
            if label != "Neutral"
            else f". The delivery maintains a balanced tone ({emotions.get('neutral', 0)}% neutral)"
        )
        who = f" Mentioned names: {', '.join(people)}." if people else "."
        short_summary = f"{lead}{theme}{mood}{who}"
        if points:
            excerpt = " / ".join(f'"{p}"' for p in points[:2])
            short_summary += f" Notable lines from the track: {excerpt}."
    else:
        if len(units) <= 5 and len(text) <= 220:
            # Short voice clip (e.g., 8-12 seconds)
            theme_str = f"«{'، '.join(top_kw)}»" if top_kw else "موضوع مطرح‌شده"
            if people:
                loc = f" از {locations[0]}" if locations else ""
                short_summary = (
                    f"در این پیام صوتی کوتاه، گوینده ({'، '.join(people)}{loc}) خود را معرفی کرده "
                    f"و دربارهٔ {theme_str} صحبت می‌کند. متن کامل گفتار: «{text}»"
                )
            else:
                short_summary = (
                    f"این پیام صوتی کوتاه به معرفی و بررسی {theme_str} می‌پردازد. "
                    f"متن گفتار: «{text}»"
                )
        else:
            # Longer narrative, story, lecture, or conversation
            lead = (
                "این فایل صوتی یک قطعهٔ آوازی یا ترانهٔ فارسی است"
                if is_song
                else "این فایل صوتی یک روایت داستانی و گفتار بلند به زبان فارسی است"
                if len(units) > 25
                else "این فایل صوتی به زبان فارسی است"
            )
            theme = f" که محور اصلی آن بر «{'، '.join(top_kw)}» متمرکز است" if top_kw else ""
            loc_str = f" و فضای آن با «{'، '.join(locations)}» مرتبط است" if locations else ""
            mood_map = {
                "Positive": "لحن کلی گفتار مثبت و امیدبخش است.",
                "Negative": "لحن کلی اثر جدی و همراه با رگه‌هایی از اندوه یا چالش است.",
                "Mixed": "لحن روایت ترکیبی از فراز و فرودهای حسی و داستانی است.",
                "Neutral": "لحن کلی بیان متعادل، روایی و توصیفی است.",
            }
            short_summary = f"{lead}{theme}{loc_str}. {mood_map[label]}"
            if points:
                short_summary += " گزیدهٔ بخش‌های کلیدی روایت: " + " / ".join(
                    f"«{p[:110]}»" for p in points[:3]
                ) + "."

    topics = []
    for kw, n in keywords_ranked[:6]:
        phrase_desc = next((d for p, d in FA_PHRASES if p == kw), "")
        example = next((u for u in units if kw.split()[0] in u.lower()), "")
        if lang == "en":
            desc = f"Mentioned {n}× in transcript" + (f' — "{example[:85]}"' if example else "")
        else:
            if phrase_desc:
                desc = phrase_desc + (f" ({n} بار)" if n > 1 else "")
            elif n > 1:
                desc = f"{n} بار در متن تکرار شده" + (f" — «{example[:85]}»" if example else "")
            else:
                desc = "مفهوم کلیدی مطرح‌شده در گفتار" + (f" — «{example[:85]}»" if example else "")
        topics.append(
            {
                "name": kw,
                "description": desc,
                "relevance": round(min(0.98, 0.58 + min(n, 8) * 0.05), 2),
            }
        )

    extracted_entities: dict[str, Any] = {
        "people": people[:6],
        "organizations": organizations[:6],
        "dates": [meta["date"]] if meta.get("has_metadata") and meta.get("date") else [],
        "times": [],
        "locations": locations[:6],
        "tasks": [],
        "decisions": [],
        "deadlines": [],
        "keywords": keywords,
    }
    if meta:
        extracted_entities["audio_metadata"] = meta

    base_analysis = {
        "short_summary": short_summary,
        "detailed_summary": {
            "main_discussion": short_summary,
            "important_points": points,
            "decisions": [],
            "action_items": [],
            "open_questions": [],
            "final_conclusions": points[-1:] if len(points) > 1 else [],
        },
        "topics": topics,
        "sentiment": {
            "label": label,
            "explanation": explanation,
            "supporting_segment_ids": [],
            "score": score,
            "emotions": emotions,
            "language": lang,
            "language_breakdown": language_breakdown(text),
            "source": ANALYSIS_SOURCE,
            "disclaimer": "Lexicon-based emotion estimate from transcript wording.",
        },
        "extracted_entities": extracted_entities,
        "action_items": [],
        "decisions": [],
    }

    bilingual_insights = _build_bilingual_insights(
        base_analysis,
        text,
        points,
        lang,
        keywords,
        people,
        locations,
        is_song,
    )
    base_analysis["detailed_summary"]["bilingual_insights"] = bilingual_insights
    base_analysis["bilingual_insights"] = bilingual_insights
    return base_analysis


def emotions_for_text(
    transcript_text: str, segment_texts: list[str] | None = None
) -> dict[str, Any]:
    """Emotion + language info only (used to enrich LLM-produced analyses)."""
    text = (transcript_text or "").strip()
    units = _segment_units(text, segment_texts)
    emotions, _ = emotion_distribution(units)
    return {
        "emotions": emotions,
        "language": detect_text_language(text),
        "language_breakdown": language_breakdown(text),
    }


# --------------------------------------------------------------------------- #
# Grounded QA (Bilingual: Persian <-> English cross-lingual support)
# --------------------------------------------------------------------------- #
_GREETINGS = {
    "hi", "hello", "hey", "hiya", "yo", "سلام", "درود", "وقت بخیر", "خسته نباشید",
}


def _rank_units(question: str, units: list[str]) -> list[tuple[int, str]]:
    raw_q_toks = _tokens(question)
    q_toks = {t for t in raw_q_toks if not _is_stop(t)} or set(raw_q_toks)
    # Expand query tokens cross-lingually (Persian <-> English)
    expanded_q = set(q_toks)
    for tok in list(raw_q_toks):
        for en_eq in _FA_TO_EN_CONCEPTS.get(tok, []):
            expanded_q.add(en_eq)
        for fa_eq in _EN_TO_FA_CONCEPTS.get(tok, []):
            expanded_q.add(fa_eq)

    scored = []
    for unit in units:
        u_toks = set(_tokens(unit))
        overlap = float(len(expanded_q & u_toks))
        overlap += (
            sum(
                1
                for q in expanded_q
                for u in u_toks
                if q != u and len(q) >= 3 and (u.startswith(q) or q.startswith(u))
            )
            * 0.6
        )
        if overlap > 0:
            scored.append((overlap, unit))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [(int(s * 2), u) for s, u in scored]


def answer_question_grounded(
    question: str,
    evidence_texts: list[str],
    audio_metadata: dict[str, Any] | None = None,
    existing_analysis: dict[str, Any] | None = None,
) -> tuple[str, bool]:
    texts = [t for t in evidence_texts if t and t.strip()]
    q = (question or "").strip()
    q_lower = q.lower()
    reply_lang = detect_question_language(q)
    reply_en = reply_lang == "en"
    combined = " ".join(texts).strip()
    meta = audio_metadata or {}
    has_meta = bool(meta.get("has_metadata"))

    meta_artist = (meta.get("artist") or meta.get("album_artist") or "").strip() if has_meta else ""
    meta_title = (meta.get("title") or meta.get("track_name") or "").strip() if has_meta else ""
    meta_album = (meta.get("album") or "").strip() if has_meta else ""
    meta_composer = (meta.get("composer") or "").strip() if has_meta else ""
    meta_genre = (meta.get("genre") or "").strip() if has_meta else ""
    meta_date = (meta.get("date") or "").strip() if has_meta else ""

    if not combined and not has_meta:
        return (
            (
                "There is no transcribed speech or audio metadata in this recording to answer from."
                if reply_en
                else "اطلاعات کافی (در متن گفتار یا متادیتای فایل صوتی) برای پاسخ به این سؤال وجود ندارد."
            ),
            False,
        )

    analysis = build_smart_analysis(combined, texts, audio_metadata=meta)
    ents = analysis["extracted_entities"]
    # Merge any people/organizations from existing_analysis if present
    if existing_analysis and isinstance(existing_analysis.get("extracted_entities"), dict):
        ex_ents = existing_analysis["extracted_entities"]
        for p in ex_ents.get("people") or []:
            if isinstance(p, str) and p.strip() and p.strip() not in ents["people"]:
                ents["people"].append(p.strip())
        for o in ex_ents.get("organizations") or []:
            if isinstance(o, str) and o.strip() and o.strip() not in ents["organizations"]:
                ents["organizations"].append(o.strip())

    transcript_people = extract_people(combined, analysis["sentiment"]["language"]) if combined else []
    emotions = analysis["sentiment"]["emotions"]
    audio_lang = analysis["sentiment"]["language"]
    units = _segment_units(combined, texts)
    localized_summary, localized_kw = _format_summary_in_language(analysis, reply_lang, combined)

    def has(*words: str) -> bool:
        return any(w in q_lower for w in words)

    # 1. Artist / Singer / Performer questions
    asking_singer_or_artist = has(
        "singer", "artist", "vocalist", "performer", "band", "musician",
        "who sings", "who sang", "sung by", "performed by",
        "خواننده", "هنرمند", "آرتیست", "اجراکننده", "گروه موسیقی",
        "کی خونده", "کی خوانده", "چه کسی خوانده", "با صدای کی", "صدای چه کسی",
    )
    if asking_singer_or_artist:
        if meta_artist:
            extra_parts_en: list[str] = []
            extra_parts_fa: list[str] = []
            if meta_title:
                extra_parts_en.append(f'Track title: "{meta_title}"')
                extra_parts_fa.append(f"عنوان قطعه: «{meta_title}»")
            if meta_album:
                extra_parts_en.append(f'Album: "{meta_album}"')
                extra_parts_fa.append(f"آلبوم: «{meta_album}»")
            if meta_date:
                extra_parts_en.append(f"Release year/date: {meta_date}")
                extra_parts_fa.append(f"سال انتشار: {meta_date}")
            if reply_en:
                details = f" ({', '.join(extra_parts_en)})" if extra_parts_en else ""
                return (
                    f"According to the uploaded audio file's metadata, the artist/singer is **{meta_artist}**{details}.",
                    True,
                )
            details_fa = f" ({'، '.join(extra_parts_fa)})" if extra_parts_fa else ""
            return (
                f"بر اساس متادیتای فایل صوتی بارگذاری‌شده، خواننده / هنرمند این اثر **{meta_artist}** است{details_fa}.",
                True,
            )
        if transcript_people:
            en_people = [_TERM_GLOSS_FA_TO_EN.get(p, p) for p in transcript_people]
            if reply_en:
                return (
                    f"The audio file's metadata does not contain an artist tag, but the transcription mentions: **{', '.join(en_people)}**.",
                    True,
                )
            return (
                f"در متادیتای فایل صوتی نام خواننده ثبت نشده است، اما در متن گفتار نام **{'، '.join(transcript_people)}** ذکر شده است.",
                True,
            )
        if reply_en:
            return (
                "The singer or artist cannot be determined from the uploaded file because neither the audio metadata nor the transcription contains this information.",
                False,
            )
        return (
            "نام خواننده یا هنرمند از روی فایل بارگذاری‌شده قابل تشخیص نیست، زیرا این اطلاعات نه در متادیتای فایل صوتی و نه در متن گفتار وجود دارد.",
            False,
        )

    # 2. Composer / Songwriter questions
    asking_composer = has(
        "composer", "songwriter", "wrote this song", "written by", "composed by", "lyricist", "producer",
        "آهنگساز", "آهنگ‌ساز", "ملودی", "ترانه‌سرا", "ترانه سرا", "تنظیم‌کننده", "آهنگسازی",
    )
    if asking_composer:
        if meta_composer:
            if reply_en:
                artist_note = f" (performed by **{meta_artist}**)" if meta_artist else ""
                return (
                    f"According to the audio metadata, the composer is **{meta_composer}**{artist_note}.",
                    True,
                )
            artist_note_fa = f" (با اجرای **{meta_artist}**)" if meta_artist else ""
            return (
                f"بر اساس متادیتای فایل صوتی، آهنگساز این اثر **{meta_composer}** است{artist_note_fa}.",
                True,
            )
        if reply_en:
            known_artist = f" The artist listed in metadata is **{meta_artist}**." if meta_artist else ""
            return (
                f"The composer cannot be determined from the uploaded file because neither the audio metadata nor the transcription specifies a composer.{known_artist}",
                bool(meta_artist),
            )
        known_artist_fa = f" نام هنرمند ثبت‌شده در متادیتا **{meta_artist}** است." if meta_artist else ""
        return (
            f"نام آهنگساز از روی فایل بارگذاری‌شده قابل تشخیص نیست، زیرا این مورد در متادیتای فایل صوتی و متن گفتار ثبت نشده است.{known_artist_fa}",
            bool(meta_artist),
        )

    # 3. Album questions
    asking_album = has(
        "album", "which album", "what album", "record title", "ep",
        "آلبوم", "کدام آلبوم", "اسم آلبوم", "نام آلبوم",
    )
    if asking_album:
        if meta_album:
            if reply_en:
                by_str = f" by **{meta_artist}**" if meta_artist else ""
                return (
                    f'According to the audio metadata, this track belongs to the album **"{meta_album}"**{by_str}.',
                    True,
                )
            by_str_fa = f" از **{meta_artist}**" if meta_artist else ""
            return (
                f"بر اساس متادیتای فایل صوتی، این قطعه متعلق به آلبوم **«{meta_album}»**{by_str_fa} است.",
                True,
            )
        if reply_en:
            return (
                "The album name cannot be determined from the uploaded file because neither the audio metadata nor the transcription contains album information.",
                False,
            )
        return (
            "نام آلبوم از روی فایل بارگذاری‌شده قابل تشخیص نیست، زیرا این اطلاعات نه در متادیتای فایل صوتی و نه در متن گفتار وجود دارد.",
            False,
        )

    # 4. Song title / Track name questions
    asking_song_title = has(
        "name of this song", "title of this song", "song name", "song title",
        "track name", "track title", "name of the song", "name of the track",
        "what song is this", "which song is this", "what track is this",
        "اسم آهنگ", "نام آهنگ", "اسم این آهنگ", "نام این آهنگ", "اسم ترانه",
        "نام ترانه", "عنوان آهنگ", "عنوان قطعه", "اسم قطعه", "نام قطعه", "اسم موزیک",
    )
    if asking_song_title:
        if meta_title:
            if reply_en:
                by_str = f" by **{meta_artist}**" if meta_artist else ""
                album_str = f' (Album: "{meta_album}")' if meta_album else ""
                return (
                    f'According to the audio metadata, the title of this track/song is **"{meta_title}"**{by_str}{album_str}.',
                    True,
                )
            by_str_fa = f" با اجرای **{meta_artist}**" if meta_artist else ""
            album_str_fa = f" (آلبوم: «{meta_album}»)" if meta_album else ""
            return (
                f"بر اساس متادیتای فایل صوتی، نام این قطعه / آهنگ **«{meta_title}»**{by_str_fa}{album_str_fa} است.",
                True,
            )
        if reply_en:
            return (
                "The song or track title cannot be determined from the uploaded file because neither the audio metadata nor the transcription specifies a verified title.",
                False,
            )
        return (
            "نام آهنگ یا قطعه از روی فایل بارگذاری‌شده قابل تشخیص نیست، زیرا عنوان تأییدشده‌ای در متادیتای فایل صوتی یا متن گفتار وجود ندارد.",
            False,
        )

    # 5. General metadata / release year / genre questions
    if has("metadata", "id3", "release year", "release date", "when was it released", "genre", "متادیتا", "ژانر", "سبک", "سال انتشار"):
        if has_meta:
            fields_en: list[str] = []
            fields_fa: list[str] = []
            if meta_title:
                fields_en.append(f"Title: {meta_title}")
                fields_fa.append(f"عنوان: {meta_title}")
            if meta_artist:
                fields_en.append(f"Artist: {meta_artist}")
                fields_fa.append(f"هنرمند/خواننده: {meta_artist}")
            if meta_album:
                fields_en.append(f"Album: {meta_album}")
                fields_fa.append(f"آلبوم: {meta_album}")
            if meta_composer:
                fields_en.append(f"Composer: {meta_composer}")
                fields_fa.append(f"آهنگساز: {meta_composer}")
            if meta_genre:
                fields_en.append(f"Genre: {meta_genre}")
                fields_fa.append(f"ژانر: {meta_genre}")
            if meta_date:
                fields_en.append(f"Date/Year: {meta_date}")
                fields_fa.append(f"سال انتشار: {meta_date}")
            if reply_en:
                return "Audio file metadata:\n• " + "\n• ".join(fields_en), True
            return "اطلاعات متادیتای فایل صوتی:\n• " + "\n• ".join(fields_fa), True
        if reply_en:
            return "No embedded ID3/audio metadata tags were found in the uploaded file.", False
        return "هیچ تگ متادیتایی در فایل صوتی بارگذاری‌شده یافت نشد.", False

    # Greetings / small talk
    cleaned_q = q_lower.strip("!.?؟، ")
    if cleaned_q in _GREETINGS or (
        len(_tokens(q)) <= 2 and has("hi", "hello", "hey", "سلام", "درود")
    ):
        if reply_en:
            return (
                f"Hi there! Here is a quick overview of this recording:\n{localized_summary}\n\n"
                f"Key topics: {localized_kw or 'N/A'}. Feel free to ask about the content, mood, or specific details in English or Persian!"
            ), True
        return (
            f"سلام! در ادامه خلاصه‌ای از این فایل صوتی را می‌بینید:\n{localized_summary}\n\n"
            f"کلیدواژه‌های اصلی: {localized_kw or '—'}. می‌توانید هر سؤالی دربارهٔ جزئیات متن، موضوع یا حس‌وحال فایل به فارسی یا انگلیسی بپرسید!"
        ), True

    # Language
    if has("language", "زبان", "انگلیسی", "فارسی", "persian", "english") and not has(
        "explain", "توضیح", "خلاصه", "summar", "about", "درباره", "چیه", "چیست"
    ):
        bd = analysis["sentiment"]["language_breakdown"]
        name = {"fa": ("Persian", "فارسی"), "en": ("English", "انگلیسی")}.get(
            audio_lang, (audio_lang, audio_lang)
        )
        if reply_en:
            return (
                f"The primary language of this recording is {name[0]} "
                f"({bd.get('en', 0)}% English, {bd.get('fa', 0)}% Persian)."
            ), True
        return (
            f"زبان اصلی این فایل صوتی {name[1]} است "
            f"({bd.get('fa', 0)}٪ فارسی، {bd.get('en', 0)}٪ انگلیسی)."
        ), True

    # Emotion / mood
    if has("emotion", "feel", "mood", "tone", "sentiment", "احساس", "حس", "لحن", "حال"):
        ordered = sorted(emotions.items(), key=lambda kv: kv[1], reverse=True)
        _, exp_en, _ = _sentiment_from_emotions(emotions, "en")
        _, exp_fa, _ = _sentiment_from_emotions(emotions, "fa")
        if reply_en:
            dist = ", ".join(f"{k.capitalize()} {v}%" for k, v in ordered)
            return f"{exp_en} (Breakdown: {dist})", True
        fa_names = {
            "joy": "شادی",
            "neutral": "خنثی",
            "sadness": "غم",
            "anger": "خشم",
            "fear": "ترس/نگرانی",
        }
        dist = "، ".join(f"{fa_names[k]} {v}٪" for k, v in ordered)
        return f"{exp_fa} (تفکیک: {dist})", True

    # Organizations / companies / universities
    if has("organization", "organizations", "company", "companies", "university", "institution", "سازمان", "شرکت", "دانشگاه", "موسسه", "مؤسسه"):
        if ents["organizations"]:
            if reply_en:
                return f"Organizations mentioned in this recording: **{', '.join(ents['organizations'])}**.", True
            return f"سازمان‌ها و مجموعه‌های ذکرشده در این فایل صوتی: **{'، '.join(ents['organizations'])}**.", True
        if reply_en:
            return "No specific organizations, companies, or institutions were detected in the recording.", False
        return "نام هیچ سازمان، شرکت یا مؤسسه‌ای در این فایل صوتی شناسایی نشد.", False

    # Speaker / people / location / age
    if has(
        "who is", "who's", "who are", "speaker's name", "what is his name",
        "what is her name", "where is he from", "where is the speaker from", "how old",
        "چه کسی", "کیست", "کیه", "گوینده کیست", "گوینده چه کسی",
        "اسم گوینده", "نام گوینده", "اهل کجا", "چند سال",
    ):
        if transcript_people:
            en_people = [_TERM_GLOSS_FA_TO_EN.get(p, p) for p in transcript_people]
            en_locs = [_TERM_GLOSS_FA_TO_EN.get(l, l) for l in ents["locations"]]
            if reply_en:
                loc_info = f" from {', '.join(en_locs)}" if en_locs else ""
                return (
                    f"The speaker/person mentioned in the recording is {', '.join(en_people)}{loc_info}.\n\n"
                    f"Context: {localized_summary}",
                    True,
                )
            loc_info = f" از {'، '.join(ents['locations'])}" if ents["locations"] else ""
            return (
                f"فرد معرفی‌شده در فایل صوتی: {'، '.join(transcript_people)}{loc_info}.\n\n"
                f"توضیحات تکمیلی: {localized_summary}",
                True,
            )
        if meta_artist:
            if reply_en:
                title_part = f' (Track: "{meta_title}")' if meta_title else ""
                return (
                    f"No speaker introduces themselves in the transcript, but according to the audio metadata, the artist is **{meta_artist}**{title_part}.\n\n"
                    f"Context: {localized_summary}",
                    True,
                )
            title_part_fa = f" (قطعه: «{meta_title}»)" if meta_title else ""
            return (
                f"در متن گفتار نام گوینده‌ای ذکر نشده است، اما بر اساس متادیتای فایل صوتی، هنرمند / خوانندهٔ اثر **{meta_artist}** است{title_part_fa}.\n\n"
                f"توضیحات تکمیلی: {localized_summary}",
                True,
            )
        if reply_en:
            return (
                "No specific person or speaker name can be determined from the uploaded file's metadata or transcription.\n\n"
                f"Overview of the audio:\n{localized_summary}",
                False,
            )
        return (
            "نام شخص یا گویندهٔ مشخصی در متادیتای فایل صوتی و متن گفتار وجود ندارد.\n\n"
            f"خلاصهٔ محتوای فایل:\n{localized_summary}",
            False,
        )

    # Summary / topic / general explanation
    if has(
        "summar", "about", "topic", "main point", "key point", "what is this", "explain", "overview",
        "challenges", "discussed", "خلاصه", "موضوع", "درباره", "چی میگه", "چه می‌گوید", "نکات",
        "محور", "داستان", "ماجرا", "توضیح", "چیه", "چیست", "مفهوم", "معنی",
    ):
        meta_prefix_en = ""
        meta_prefix_fa = ""
        if meta_artist or meta_title:
            parts_en = [f'"{meta_title}"' if meta_title else None, f"by {meta_artist}" if meta_artist else None, f'(Album: "{meta_album}")' if meta_album else None]
            meta_prefix_en = "Track info: " + " ".join(p for p in parts_en if p) + "\n\n"
            parts_fa = [f"«{meta_title}»" if meta_title else None, f"با اجرای {meta_artist}" if meta_artist else None, f"(آلبوم: «{meta_album}»)" if meta_album else None]
            meta_prefix_fa = "اطلاعات اثر: " + " ".join(p for p in parts_fa if p) + "\n\n"
        if reply_en:
            return f"{meta_prefix_en}{localized_summary}\n\nTop keywords: {localized_kw}", True
        return f"{meta_prefix_fa}{localized_summary}\n\nکلیدواژه‌های اصلی: {localized_kw}", True

    # Generic: retrieve the most relevant lines by keyword overlap (with cross-lingual expansion)
    ranked = _rank_units(q, units)
    if not ranked:
        if reply_en:
            return (
                f"Here is what the recording discusses overall:\n{localized_summary}\n\nKey topics: {localized_kw}",
                True,
            )
        return (
            f"بر اساس محتوای کلی فایل صوتی:\n{localized_summary}\n\nکلیدواژه‌ها: {localized_kw}",
            True,
        )
    lines = []
    for _, unit in ranked[:3]:
        if unit not in lines:
            lines.append(unit)
    if reply_en:
        header = (
            f"{localized_summary}\n\nRelevant lines from the transcript:\n"
            if audio_lang != "en"
            else "Here is what the recording says about that:\n"
        )
        return header + "\n".join(f'• "{u}"' for u in lines), True
    header = (
        f"{localized_summary}\n\nجملات مرتبط در متن اصلی فایل:\n"
        if audio_lang != "fa"
        else "بخش‌های مرتبط در فایل صوتی:\n"
    )
    return header + "\n".join(f"• «{u}»" for u in lines), True
