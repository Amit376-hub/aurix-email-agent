import re
import html

# Patterns commonly used in prompt injection attacks
INJECTION_PATTERNS = [
    r"ignore\s+(all|previous|above)?\s*instructions?",
    r"disregard\s+(all|previous|above)?\s*instructions?",
    r"reveal\s+(your|the)?\s*system\s*prompt",
    r"show\s+(your|the)?\s*hidden\s*instructions?",
    r"act\s+as",
    r"pretend\s+to\s+be",
    r"you\s+are\s+now",
    r"developer\s*mode",
    r"system\s*override",
    r"send\s+all\s+emails?",
    r"exfiltrate\s+data",
    r"leak\s+data",
    r"bypass\s+security",
]

def normalize_text(text: str) -> str:
    """
    Normalize text to make detection harder to bypass.
    """
    text = html.unescape(text)  # decode HTML entities
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)  # normalize whitespace
    return text


def detect_prompt_injection(text: str) -> bool:
    """
    Detect prompt injection patterns.
    """
    normalized = normalize_text(text)

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, normalized):
            return True

    return False


def sanitize_email_content(text: str) -> str:
    """
    Replace malicious instructions in email content.
    """
    cleaned = text

    for pattern in INJECTION_PATTERNS:
        cleaned = re.sub(
            pattern,
            "[REMOVED_POTENTIAL_PROMPT_INJECTION]",
            cleaned,
            flags=re.IGNORECASE
        )

    return cleaned


def secure_email_input(email_text: str):
    """
    Main guard function before sending content to the LLM.
    """

    injection_detected = detect_prompt_injection(email_text)

    if injection_detected:
        sanitized = sanitize_email_content(email_text)

        return {
            "safe": False,
            "sanitized_text": sanitized,
            "reason": "prompt_injection_detected"
        }

    return {
        "safe": True,
        "sanitized_text": email_text,
        "reason": None
    }