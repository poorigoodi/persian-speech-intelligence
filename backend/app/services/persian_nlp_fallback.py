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

ANALYSIS_SOURCE = "local_nlp_v2"

_PERSIAN_CHARS = re.compile(r"[\u0600-\u06FF]")
_LATIN_CHARS = re.compile(r"[A-Za-z]")
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*|[\u0600-\u06FF\u200c]+")
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
going come came way back time make made let lets maybe yes yet ever every whoa na la da
""".split()
)

FA_STOPWORDS = set(
    """
من تو او ما شما آنها ایشان این آن اینجا آنجا که از به با در بر برای تا را هم اما ولی یا اگر چون
است هست هستم هستی هستیم هستند بود بودم بودند شد شده شود میشه می‌شود میشود داره دارد دارم داریم دارند
کنم کند کنیم کنند کرد کردم کردن کرده می‌کنم میکنم می‌کند می‌خوام میخوام می‌خواهم خواهم مورد درباره
امروز دیروز فردا انجام صحبت یک دو سه چهار پنج تا خود چند چه چرا چطور وقتی پس سپس بسیار خیلی
همه هر هیچ دیگه دیگر باید نباید شاید اون این‌ها اینها آن‌ها یه یک‌ نه آره بله خب حالا الان
""".split()
)

# --------------------------------------------------------------------------- #
# Emotion lexicons (text-based, not voice-based)
# --------------------------------------------------------------------------- #
EMOTION_LEXICON: dict[str, set[str]] = {
    "joy": {
        # English
        "happy", "happiness", "joy", "love", "loved", "loving", "great", "good", "glad", "smile",
        "smiling", "laugh", "laughing", "wonderful", "amazing", "beautiful", "excited", "fun",
        "hope", "hopeful", "thank", "thanks", "enjoy", "best", "awesome", "proud", "peace",
        "sweet", "honey", "dream", "free", "celebrate", "success", "successful", "nice",
        # Persian
        "خوشحال", "شاد", "شادی", "عالی", "خوب", "عشق", "لذت", "موفق", "موفقیت", "امید",
        "خنده", "جالب", "مفید", "ممنون", "تشکر", "متشکرم", "زیبا", "قشنگ", "دوستت", "عزیز",
        "پیشرفت", "بهبود", "مثبت", "خوشبخت",
    },
    "sadness": {
        "sad", "sadness", "cry", "crying", "cried", "tears", "tear", "lonely", "alone", "miss",
        "missing", "lost", "lose", "hurt", "hurting", "pain", "painful", "sorry", "broken",
        "gone", "cold", "goodbye", "die", "dying", "dead", "empty", "grief", "heartbreak",
        "regret", "leave", "left", "leaving", "dark", "tired",
        "غم", "غمگین", "ناراحت", "تنها", "تنهایی", "گریه", "دلتنگ", "دلتنگی", "افسوس",
        "متاسف", "متاسفانه", "درد", "اشک", "خسته", "رفتی", "جدایی", "شکست",
    },
    "anger": {
        "angry", "anger", "hate", "hated", "mad", "furious", "damn", "stupid", "annoying",
        "fight", "rage", "kill", "shut", "liar", "blame", "sick",
        "عصبانی", "خشم", "نفرت", "لعنت", "اعصاب", "دعوا", "کلافه", "متنفر", "بدم",
    },
    "fear": {
        "afraid", "scared", "fear", "worry", "worried", "anxious", "anxiety", "nervous",
        "panic", "terrified", "danger", "dangerous", "hurry", "risk", "unsafe", "lie",
        "ترس", "می‌ترسم", "میترسم", "نگران", "نگرانی", "وحشت", "اضطراب", "استرس", "خطر",
        "مشکل", "چالش",
    },
}
_NEGATORS = {"not", "no", "never", "don't", "dont", "won't", "can't", "nobody", "نه", "نمی", "هرگز"}

# Persian domain phrases that are worth surfacing verbatim when present.
FA_PHRASES = [
    ("هوش مصنوعی", "بحث دربارهٔ هوش مصنوعی و کاربردهای آن"),
    ("یادگیری ماشین", "مباحث یادگیری ماشین"),
    ("پردازش زبان طبیعی", "پردازش زبان طبیعی"),
    ("شبکه عصبی", "شبکه‌های عصبی"),
    ("داده‌کاوی", "داده‌کاوی و تحلیل داده"),
]

KNOWN_PLACES = {
    "شیراز": ["شیراز", "شیرازه"], "تهران": ["تهران", "تهرانه"], "اصفهان": ["اصفهان", "اصفهانه"],
    "مشهد": ["مشهد", "مشهده"], "تبریز": ["تبریز", "تبریزه"], "ایران": ["ایران"],
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
    total = fa + en
    if not total:
        return {"fa": 0, "en": 0, "other": 0}
    fa_pct = round(100 * fa / total)
    return {"fa": fa_pct, "en": 100 - fa_pct, "other": 0}


def _tokens(text: str) -> list[str]:
    return [t.strip("\u200c'-").lower() for t in _TOKEN_RE.findall(text or "") if t.strip("\u200c'-")]


def _is_stop(tok: str) -> bool:
    return tok in EN_STOPWORDS or tok in FA_STOPWORDS or len(tok) < 3


def split_sentences(text: str) -> list[str]:
    parts = [p.strip(" .،,!?؟") for p in _SENT_SPLIT.split(text or "")]
    return [p for p in parts if len(p) > 2]


def _segment_units(transcript: str, segment_texts: list[str] | None) -> list[str]:
    units: list[str] = []
    for seg in segment_texts or []:
        units.extend(split_sentences(seg) or ([seg.strip()] if seg.strip() else []))
    return units or split_sentences(transcript)


def _round_to_100(raw: dict[str, float]) -> dict[str, int]:
    total = sum(raw.values())
    if total <= 0:
        return {k: (100 if k == "neutral" else 0) for k in raw}
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
            window = toks[max(0, idx - 2):idx]
            negated = any(w in _NEGATORS for w in window)
            for emo, lex in EMOTION_LEXICON.items():
                if tok in lex:
                    if negated and emo == "joy":
                        hits["sadness"] += 0.5
                    elif not negated:
                        hits[emo] += 1
                    unit_hit = True
        if not unit_hit:
            neutral_units += 1
    raw = {"joy": hits["joy"], "neutral": float(neutral_units), "sadness": hits["sadness"],
           "anger": hits["anger"], "fear": hits["fear"]}
    return _round_to_100(raw), {k: int(round(v)) for k, v in raw.items()}


def _sentiment_from_emotions(emotions: dict[str, int], lang: str) -> tuple[str, str, float]:
    pos = emotions.get("joy", 0)
    neg = emotions.get("sadness", 0) + emotions.get("anger", 0) + emotions.get("fear", 0)
    dominant = max(("joy", "sadness", "anger", "fear"), key=lambda k: emotions.get(k, 0))
    names_fa = {"joy": "شادی", "sadness": "غم", "anger": "خشم", "fear": "نگرانی/ترس"}
    if pos >= 20 and neg >= 20:
        label = "Mixed"
    elif neg >= 15 and neg > pos:
        label = "Negative"
    elif pos >= 15 and pos > neg:
        label = "Positive"
    else:
        label = "Neutral"
    score = round(0.5 + (pos - neg) / 200, 2)
    if lang == "en":
        if label == "Neutral":
            exp = "The language of the transcript is mostly neutral/informational with few emotional words."
        else:
            exp = (f"Overall tone is {label.lower()}; the strongest emotional signal in the wording is "
                   f"{dominant} ({emotions.get(dominant, 0)}%).")
    else:
        if label == "Neutral":
            exp = "لحن متن عمدتاً خنثی و اطلاع‌رسانی است و واژه‌های احساسی کمی در آن به کار رفته است."
        else:
            exp = f"لحن کلی متن {label} است؛ قوی‌ترین نشانهٔ احساسی در واژه‌ها «{names_fa[dominant]}» ({emotions.get(dominant, 0)}٪) است."
    return label, exp, score


# --------------------------------------------------------------------------- #
# Keywords / topics / entities
# --------------------------------------------------------------------------- #
def extract_keywords(text: str, units: list[str], limit: int = 8) -> list[tuple[str, int]]:
    toks = [t for t in _tokens(text) if not _is_stop(t)]
    counts = Counter(toks)
    # Promote frequent bigrams of content words
    bigrams: Counter[str] = Counter()
    for unit in units:
        ut = _tokens(unit)
        for a, b in zip(ut, ut[1:]):
            if not _is_stop(a) and not _is_stop(b):
                bigrams[f"{a} {b}"] += 1
    ranked: list[tuple[str, int]] = []
    for phrase, n in bigrams.most_common(4):
        if n >= 2:
            ranked.append((phrase, n))
    for phrase, _desc in FA_PHRASES:
        if phrase in text and all(phrase != p for p, _ in ranked):
            ranked.append((phrase, text.count(phrase)))
    for tok, n in counts.most_common(limit * 3):
        if any(tok in p.split() for p, _ in ranked):
            continue
        ranked.append((tok, n))
        if len(ranked) >= limit:
            break
    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked[:limit]


def extract_people(text: str, lang: str) -> list[str]:
    people: list[str] = []
    if lang == "fa":
        cleaned = apply_asr_rules(text)
        for pat in (
            r"(?:اسمم|نامم|اسم من|نام من)\s+([آ-ی]{2,15}(?:\s+[آ-ی]{2,15})?)",
            r"(?:من|بنده)\s+([آ-ی]{3,15}\s+[آ-ی]{3,15}?)(?:‌ام|ام)(?=[\s،,.]|$)",
            r"(?:آقای|خانم|دکتر|مهندس)\s+([آ-ی]{3,15}(?:\s+[آ-ی]{3,15})?)",
        ):
            for m in re.finditer(pat, cleaned):
                cand = re.sub(r"(?:‌ام|ام)$", "", m.group(1).strip("،,. ")).strip()
                if cand and not any(p in FA_STOPWORDS for p in cand.split()) and cand not in people:
                    people.append(cand)
    else:
        for pat in (
            r"\b(?:my name is|i am|i'm|this is|call me)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"\b(?:Mr|Mrs|Ms|Dr)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        ):
            for m in re.finditer(pat, text, flags=re.IGNORECASE if "name" in pat else 0):
                cand = m.group(1).strip()
                if cand and cand[0].isupper() and cand.lower() not in EN_STOPWORDS and cand not in people:
                    people.append(cand)
    return people[:5]


def extract_locations(text: str) -> list[str]:
    found: list[str] = []
    for canonical, variants in KNOWN_PLACES.items():
        if any(re.search(rf"(?<!\S){re.escape(v)}(?=[،,.\s]|$)", text) for v in variants):
            found.append(canonical)
    for m in re.finditer(r"\b(?:in|from|at|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text):
        cand = m.group(1)
        if cand.lower() not in EN_STOPWORDS and cand not in found and cand not in {"I"}:
            if cand in {"London", "Paris", "Tehran", "Shiraz", "Iran", "America", "California",
                        "New York", "Los Angeles", "Canada", "Germany", "England"}:
                found.append(cand)
    return found[:5]


def extract_organizations(text: str) -> list[str]:
    orgs: list[str] = []
    for m in re.finditer(
        r"(?:شرکت|دانشگاه|سازمان|موسسه)\s+[آ-یA-Za-z0-9]{2,20}(?:\s+[آ-یA-Za-z0-9]{2,20})?", text
    ):
        if m.group(0) not in orgs:
            orgs.append(m.group(0).strip())
    for m in re.finditer(r"\b([A-Z][A-Za-z]+\s+(?:Inc|Corp|University|Company|Ltd|Group))\b", text):
        if m.group(1) not in orgs:
            orgs.append(m.group(1))
    return orgs[:5]


def _repetition_ratio(units: list[str]) -> float:
    if len(units) < 4:
        return 0.0
    norm = [re.sub(r"\W+", " ", u.lower()).strip() for u in units]
    counts = Counter(norm)
    repeated = sum(c for c in counts.values() if c > 1)
    return repeated / len(norm)


# --------------------------------------------------------------------------- #
# Summary
# --------------------------------------------------------------------------- #
def _extractive_points(units: list[str], keywords: list[tuple[str, int]], k: int = 4) -> list[str]:
    weights = {w: n for w, n in keywords}
    seen: set[str] = set()
    scored: list[tuple[float, int, str]] = []
    for idx, unit in enumerate(units):
        key = re.sub(r"\W+", " ", unit.lower()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        toks = _tokens(unit)
        if not toks:
            continue
        score = sum(weights.get(t, 0) for t in toks)
        score += sum(n for w, n in keywords if " " in w and w in unit.lower())
        scored.append((score / (len(toks) ** 0.5), idx, unit))
    top = sorted(scored, key=lambda x: x[0], reverse=True)[:k]
    return [u for _, _, u in sorted(top, key=lambda x: x[1])]


def build_smart_analysis(transcript_text: str, segment_texts: list[str] | None = None) -> dict[str, Any]:
    text = (transcript_text or "").strip()
    lang = detect_text_language(text)
    if lang == "fa":
        text = apply_asr_rules(text)
        segment_texts = [apply_asr_rules(s) for s in (segment_texts or [])]
    units = _segment_units(text, segment_texts)

    keywords_ranked = extract_keywords(text, units)
    keywords = [k for k, _ in keywords_ranked]
    people = extract_people(text, lang)
    locations = extract_locations(text)
    organizations = extract_organizations(text)
    emotions, _raw = emotion_distribution(units)
    label, explanation, score = _sentiment_from_emotions(emotions, lang)
    points = _extractive_points(units, keywords_ranked)
    is_song = _repetition_ratio(units) >= 0.3
    top_kw = keywords[:4]

    if lang == "en":
        lead = ("This audio appears to be a song or lyrical piece (many repeated lines)"
                if is_song else "This recording is spoken in English")
        theme = f", centred on {', '.join(top_kw)}" if top_kw else ""
        mood = f" The overall tone is {label.lower()}" + (
            f", with {max(('joy', 'sadness', 'anger', 'fear'), key=lambda e: emotions[e])} as the strongest emotion."
            if label != "Neutral" else "."
        )
        who = f" Mentioned people: {', '.join(people)}." if people else ""
        short_summary = f"{lead}{theme}.{mood}{who}"
        if points:
            short_summary += " Key lines: " + " / ".join(f"“{p}”" for p in points[:2]) + "."
    else:
        lead = ("این فایل به نظر یک قطعهٔ موسیقی یا متن ترانه است (خطوط تکراری زیاد)"
                if is_song else "این فایل صوتی به زبان فارسی است")
        theme = f" و محور اصلی آن «{'، '.join(top_kw)}» است" if top_kw else ""
        who = ""
        if people:
            loc = f" از {locations[0]}" if locations else ""
            who = f" گوینده ({'، '.join(people)}{loc}) خود را معرفی می‌کند."
        mood = {"Positive": " لحن کلی مثبت است.", "Negative": " لحن کلی منفی است.",
                "Mixed": " لحن کلی ترکیبی از احساسات مثبت و منفی است.",
                "Neutral": " لحن کلی خنثی و اطلاع‌رسانی است."}[label]
        short_summary = f"{lead}{theme}.{who}{mood}"
        if points:
            short_summary += " نکات کلیدی: " + " / ".join(f"«{p}»" for p in points[:2]) + "."

    if not text:
        short_summary = ""

    topics = []
    for kw, n in keywords_ranked[:5]:
        example = next((u for u in units if kw in u.lower()), "")
        if lang == "en":
            desc = f"Mentioned {n}×" + (f" — “{example[:90]}”" if example else "")
        else:
            desc = f"{n} بار تکرار شده" + (f" — «{example[:90]}»" if example else "")
        topics.append({"name": kw, "description": desc, "relevance": round(min(1.0, 0.5 + n / 10), 2)})

    return {
        "short_summary": short_summary,
        "detailed_summary": {
            "main_discussion": short_summary,
            "important_points": points,
            "decisions": [],
            "action_items": [],
            "open_questions": [],
            "final_conclusions": [],
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
            "disclaimer": "Lexicon-based emotion estimate from transcript wording only (not voice tone).",
        },
        "extracted_entities": {
            "people": people,
            "organizations": organizations,
            "dates": [],
            "times": [],
            "locations": locations,
            "tasks": [],
            "decisions": [],
            "deadlines": [],
            "keywords": keywords,
        },
        "action_items": [],
        "decisions": [],
    }


def emotions_for_text(transcript_text: str, segment_texts: list[str] | None = None) -> dict[str, Any]:
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
# Grounded QA
# --------------------------------------------------------------------------- #
_GREETINGS = {"hi", "hello", "hey", "hiya", "yo", "سلام", "درود", "سلام!", "hi!", "hello!"}


def _rank_units(question: str, units: list[str]) -> list[tuple[int, str]]:
    q_toks = {t for t in _tokens(question) if not _is_stop(t)}
    scored = []
    for unit in units:
        u_toks = set(_tokens(unit))
        overlap = len(q_toks & u_toks)
        # partial (prefix) matching helps Persian suffixes
        overlap += sum(1 for q in q_toks for u in u_toks if q != u and len(q) > 3 and (u.startswith(q) or q.startswith(u))) * 0.5
        if overlap:
            scored.append((overlap, unit))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [(int(s * 2), u) for s, u in scored]


def answer_question_grounded(question: str, evidence_texts: list[str]) -> tuple[str, bool]:
    texts = [t for t in evidence_texts if t and t.strip()]
    q = (question or "").strip()
    q_lower = q.lower()
    reply_en = detect_text_language(q) == "en"
    combined = " ".join(texts).strip()

    if not combined:
        return (
            ("There is no transcribed speech in this recording to answer from."
             if reply_en else "اطلاعات کافی برای پاسخ به این سؤال در فایل صوتی وجود ندارد."),
            False,
        )

    analysis = build_smart_analysis(combined, texts)
    summary = analysis["short_summary"]
    ents = analysis["extracted_entities"]
    emotions = analysis["sentiment"]["emotions"]
    audio_lang = analysis["sentiment"]["language"]
    units = _segment_units(combined, texts)
    kw = ", ".join(ents["keywords"][:6])

    def has(*words: str) -> bool:
        return any(w in q_lower for w in words)

    # Greetings / small talk
    if q_lower.strip("!.? ") in _GREETINGS or (len(_tokens(q)) <= 2 and has("hi", "hello", "hey", "سلام", "درود")):
        if reply_en:
            return (f"Hi! I can answer questions about this recording. Quick overview: {summary} "
                    f"Try asking about its main topic, mood, or a specific word you heard."), True
        return (f"سلام! می‌توانم دربارهٔ این فایل صوتی به سؤالات شما پاسخ بدهم. خلاصه: {summary} "
                f"می‌توانید دربارهٔ موضوع اصلی، لحن یا یک کلمهٔ خاص بپرسید."), True

    # Language
    if has("language", "زبان"):
        name = {"fa": ("Persian", "فارسی"), "en": ("English", "انگلیسی")}.get(audio_lang, (audio_lang, audio_lang))
        return (f"The recording is in {name[0]}." if reply_en else f"زبان این فایل صوتی {name[1]} است."), True

    # Emotion / mood
    if has("emotion", "feel", "mood", "tone", "sentiment", "احساس", "حس", "لحن", "حال"):
        ordered = sorted(emotions.items(), key=lambda kv: kv[1], reverse=True)
        if reply_en:
            dist = ", ".join(f"{k} {v}%" for k, v in ordered)
            return f"Based on the wording of the transcript: {analysis['sentiment']['explanation']} ({dist})", True
        fa_names = {"joy": "شادی", "neutral": "خنثی", "sadness": "غم", "anger": "خشم", "fear": "ترس/نگرانی"}
        dist = "، ".join(f"{fa_names[k]} {v}٪" for k, v in ordered)
        return f"بر اساس واژه‌های متن: {analysis['sentiment']['explanation']} ({dist})", True

    # Summary / topic
    if has("summar", "about", "topic", "main point", "key point", "what is this", "خلاصه", "موضوع",
           "درباره", "چی میگه", "چه می‌گوید", "نکات", "محور"):
        if reply_en:
            return f"{summary}\n\nKey terms: {kw}", True
        return f"{summary}\n\nکلیدواژه‌ها: {kw}", True

    # Speaker / people
    if has("who", "speaker", "singer", "name", "چه کسی", "کیست", "کیه", "گوینده", "اسم", "نام"):
        if ents["people"]:
            return ((f"People mentioned in the audio: {', '.join(ents['people'])}." if reply_en
                     else f"افراد نام‌برده‌شده در فایل: {'، '.join(ents['people'])}."), True)
        return (("No person's name is mentioned in the transcript, so I can't identify the speaker from it."
                 if reply_en else "در متن فایل نام هیچ شخصی ذکر نشده، بنابراین نمی‌توانم گوینده را از روی متن شناسایی کنم."),
                False)

    # Generic: retrieve the most relevant lines by keyword overlap
    ranked = _rank_units(q, units)
    if not ranked:
        return (("I couldn't find anything about that in this recording's transcript."
                 if reply_en else "اطلاعات کافی برای پاسخ به این سؤال در فایل صوتی وجود ندارد."), False)
    lines = []
    for _, unit in ranked[:3]:
        if unit not in lines:
            lines.append(unit)
    if reply_en:
        return "Here is what the recording says about that:\n" + "\n".join(f"• “{u}”" for u in lines), True
    return "بخش‌های مرتبط در فایل صوتی:\n" + "\n".join(f"• «{u}»" for u in lines), True
