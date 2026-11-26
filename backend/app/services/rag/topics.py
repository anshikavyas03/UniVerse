"""Shared topic detection for English, Hindi and Hinglish questions."""

import re

_HINDI_TERMS = {
    "शुल्क": "fee", "फीस": "fee", "फ़ीस": "fee", "हॉस्टल": "hostel", "होस्टल": "hostel", "छात्रावास": "hostel",
    "प्रवेश": "admission", "दाखिला": "admission", "दाख़िला": "admission", "एडमिशन": "admission", "पात्रता": "eligibility",
    "कमरा": "room", "कमरे": "room", "पाठ्यक्रम": "course", "वर्ष": "year",
}
COST_WORDS = {"fee", "fees", "charge", "charges", "tuition", "cost", "price", "security", "deposit"}
HOSTEL_WORDS = {"hostel", "hostels", "room", "rooms", "accommodation", "seater"}
ADMISSION_WORDS = {"admission", "admissions", "apply", "application", "eligibility"}
TOPIC_WORDS = COST_WORDS | HOSTEL_WORDS | ADMISSION_WORDS | {"ordinance", "course", "courses", "programme", "program", "library", "exam", "exams", "scholarship"}
_NON_COST_HOSTEL = {"rule", "rules", "timing", "timings", "curfew", "menu", "mess", "visitor", "visitors", "leave"}


def search_text(message: str) -> str:
    """Add English search terms for Hindi words so retrieval can match English documents."""
    extra = [english for hindi, english in _HINDI_TERMS.items() if hindi in message]
    return f"{message} {' '.join(dict.fromkeys(extra))}" if extra else message


def words_of(message: str) -> set[str]:
    return set(re.findall(r"[a-z]+", search_text(message).lower()))


def needs_fee_document(message: str) -> bool:
    """Fee and hostel-cost questions are answered from the Fee Structure document."""
    words = words_of(message)
    return bool(words & COST_WORDS) or (bool(words & HOSTEL_WORDS) and not words & _NON_COST_HOSTEL)


def topic_of(message: str) -> str:
    words = words_of(message)
    if words & ADMISSION_WORDS:
        return "admissions"
    if words & HOSTEL_WORDS:
        return "hostel"
    if words & COST_WORDS:
        return "fees"
    return "general"
