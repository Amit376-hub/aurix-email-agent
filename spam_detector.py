from groq import Groq
from dotenv import load_dotenv
import os
import re
import json
import hashlib

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ---------- CONFIG ----------

FEEDBACK_FILE = "spam_feedback.txt"
LEARNED_KEYWORDS_FILE = "learned_spam_keywords.json"
CACHE = {}

# ---------- STATIC BASE RULES ----------
# FIX: Tightened to only obvious, unambiguous spam phrases

SPAM_KEYWORDS = [
    "lottery winner", "free money", "claim prize",
    "crypto investment", "earn money fast",
    "urgent payment", "verify your account", "bank alert",
    "you have been selected", "send your bank details",
    "wire transfer required", "unclaimed funds"
]

SUSPICIOUS_DOMAINS = [
    ".xyz", ".top", ".ru", ".click", ".loan"
]

# ---------- DYNAMIC KEYWORD LEARNING ----------

def load_learned_keywords() -> list:
    if not os.path.exists(LEARNED_KEYWORDS_FILE):
        return []
    try:
        with open(LEARNED_KEYWORDS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_learned_keyword(keyword: str):
    """Only learn multi-word phrases to avoid over-flagging."""
    keywords = load_learned_keywords()
    keyword = keyword.lower().strip()
    # FIX: Require at least 2 words and 8 chars to avoid learning generic single words
    if keyword and keyword not in keywords and len(keyword) >= 8 and " " in keyword:
        keywords.append(keyword)
        with open(LEARNED_KEYWORDS_FILE, "w") as f:
            json.dump(keywords, f, indent=2)
        print(f"[LEARNED NEW SPAM KEYWORD]: '{keyword}'")

def get_all_keywords() -> list:
    return SPAM_KEYWORDS + load_learned_keywords()

# ---------- HELPERS ----------

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())

def text_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()

# ---------- FEEDBACK LEARNING ----------

def load_feedback():
    spam_samples, safe_samples = [], []
    if not os.path.exists(FEEDBACK_FILE):
        return spam_samples, safe_samples
    with open(FEEDBACK_FILE, "r") as f:
        for line in f:
            if "::" in line:
                label, content = line.strip().split("::", 1)
                if label == "SPAM":
                    spam_samples.append(content.lower())
                elif label == "NOT_SPAM":
                    safe_samples.append(content.lower())
    return spam_samples, safe_samples

def feedback_match_score(text, spam_samples, safe_samples) -> tuple[int, list]:
    text = text.lower()
    reasons = []
    score = 0
    for s in spam_samples:
        if s[:50] in text:
            score += 2
            reasons.append("Matched a previously confirmed spam pattern from feedback history")
            break
    for s in safe_samples:
        if s[:50] in text:
            score -= 3  # FIX: stronger safe signal to counter false positives
            break
    return score, reasons

# ---------- RULE CHECKS ----------

def keyword_score(text: str) -> tuple[int, list]:
    """
    FIX: Score by NUMBER OF UNIQUE PHRASES matched, not individual word count.
    Each matched phrase = 1 point. Need multiple to matter.
    """
    score = 0
    reasons = []
    text_lower = text.lower()
    all_keywords = get_all_keywords()
    matched = [word for word in all_keywords if word in text_lower]

    # FIX: Cap score at 3 from keywords alone, and only score if 2+ phrases match
    if len(matched) >= 2:
        score = min(len(matched), 3)
        reasons.append(f"Contains spam keywords: {', '.join(f'\"{w}\"' for w in matched)}")
    elif len(matched) == 1:
        score = 1  # Not enough alone to trigger spam
        reasons.append(f"Contains possible spam keyword: \"{matched[0]}\"")

    return score, reasons

def link_score(text: str) -> tuple[int, list]:
    score = 0
    reasons = []
    urls = re.findall(r'https?://\S+', text)
    flagged_urls = []
    for url in urls:
        for domain in SUSPICIOUS_DOMAINS:
            if domain in url:
                score += 2
                flagged_urls.append(url)
    if flagged_urls:
        reasons.append(f"Contains links with suspicious domains: {', '.join(flagged_urls[:3])}")
    return score, reasons

# ---------- AI CHECK ----------

def ai_check(text: str) -> tuple[int, list]:
    """
    FIX: AI returns score of 1 (not 2) — it alone cannot trigger spam.
    Requires corroboration from at least one rule-based signal.
    Also use a stricter prompt to reduce false positives.
    """
    prompt = f"""You are a strict email spam classifier. Your job is to identify ONLY clear, 
obvious spam — phishing attempts, scams, fake prizes, unsolicited promotions.

Do NOT flag:
- Normal work emails
- Newsletters the user signed up for
- Automated notifications (order confirmations, OTPs, alerts)
- Emails from colleagues or contacts
- Any email that could be legitimate business communication

Respond ONLY in this exact JSON format (no extra text):
{{
  "verdict": "SPAM" or "NOT_SPAM",
  "reason": "One sentence explaining your decision.",
  "new_spam_indicators": ["phrase1", "phrase2"]
}}

Only populate new_spam_indicators for obvious scam/phishing phrases. Leave empty for NOT_SPAM.

Email to analyze:
{text}
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("```").strip()

        data = json.loads(raw)
        verdict = data.get("verdict", "").upper()
        reason = data.get("reason", "")
        new_indicators = data.get("new_spam_indicators", [])

        if verdict == "SPAM":
            for phrase in new_indicators:
                if isinstance(phrase, str):
                    save_learned_keyword(phrase)
            reasons = [f"AI analysis: {reason}"] if reason else ["AI classified this as spam"]
            return 1, reasons  # FIX: was 2, now 1 — AI alone can't trigger spam
        else:
            return 0, []

    except json.JSONDecodeError:
        try:
            result = raw.upper()
            if "NOT_SPAM" in result:
                return 0, []
            if "SPAM" in result:
                return 1, ["AI classified this email as spam"]
        except Exception:
            pass
        return 0, []
    except Exception as e:
        print("AI error:", e)
        return 0, []

# ---------- MAIN FUNCTION ----------

def is_spam(email_text: str) -> tuple[bool, str]:
    """
    Returns:
        (True, reason_string)  if spam
        (False, "")            if safe

    FIX: Raised threshold from 3 → 4.
    This means AI alone (1pt) or a single keyword (1pt) is never enough.
    Need strong rule signals OR AI + keyword combination.
    """
    if not email_text:
        return False, ""

    email_text = normalize(email_text[:1500])
    key = text_hash(email_text)

    if key in CACHE:
        cached = CACHE[key]
        return cached["is_spam"], cached["reason"]

    spam_samples, safe_samples = load_feedback()

    total_score = 0
    all_reasons = []

    kw_score, kw_reasons = keyword_score(email_text)
    total_score += kw_score
    all_reasons.extend(kw_reasons)

    lk_score, lk_reasons = link_score(email_text)
    total_score += lk_score
    all_reasons.extend(lk_reasons)

    fb_score, fb_reasons = feedback_match_score(email_text, spam_samples, safe_samples)
    total_score += fb_score
    all_reasons.extend(fb_reasons)

    # FIX: Raised early-exit threshold from 3 → 5 (only very obvious rule-based spam)
    if total_score >= 5:
        reason_text = " | ".join(all_reasons) if all_reasons else "Multiple spam signals detected"
        CACHE[key] = {"is_spam": True, "reason": reason_text}
        print(f"[SPAM SCORE]: {total_score} → SPAM (rule-based)")
        return True, reason_text

    # AI layer (only called when rules are inconclusive)
    ai_score, ai_reasons = ai_check(email_text)
    total_score += ai_score
    all_reasons.extend(ai_reasons)

    # FIX: Final threshold raised from 3 → 4
    is_spam_result = total_score >= 4
    reason_text = " | ".join(all_reasons) if all_reasons else ""

    print(f"[SPAM SCORE]: {total_score} → {'SPAM' if is_spam_result else 'SAFE'}")
    if is_spam_result:
        print(f"[REASON]: {reason_text}")

    CACHE[key] = {"is_spam": is_spam_result, "reason": reason_text}
    return is_spam_result, reason_text