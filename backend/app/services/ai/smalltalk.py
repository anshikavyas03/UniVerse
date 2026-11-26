"""Warm, fixed replies for social messages, so a "hello" never triggers document search."""

import re

_PATTERNS: dict[str, str] = {
    "how_are_you": r"(?:(?:hi|hii+|hello|hey|namaste) )?(?:how are you(?: doing)?(?: today)?|how r u|how are u|kaise ho|kaisi ho|aap kaise ho|aap kaisi (?:ho|hain)|आप कैसी हैं|आप कैसे हैं|कैसी हो|कैसे हो)",
    "identity": r"(?:who are you|what is your name|whats your name|what can you do|what can you help(?: me)?(?: with)?|help|aap kaun ho|tum kaun ho|आप कौन हैं|आप कौन हो|तुम कौन हो|आपका नाम क्या है)",
    "greeting": r"(?:hi|hii+|hello|helo|hey|heya|namaste|namaskar|good (?:morning|afternoon|evening)|नमस्ते|नमस्कार|हेलो|हैलो|हाय)(?: there| aanya| maam| ji| आन्या)?",
    "thanks": r"(?:(?:ok|okay|great|cool) )?(?:thanks|thank you|thankyou|thx|dhanyavad|shukriya|धन्यवाद|शुक्रिया)(?: so much| a lot| very much| aanya)?",
    "bye": r"(?:ok |okay )?(?:bye|goodbye|good bye|see you|good night|alvida|अलविदा|बाय)(?: aanya| for now)?",
    "ack": r"(?:ok|okay|cool|great|nice|got it|no|no thanks|nothing else|thats all|ठीक है|अच्छा|नहीं)",
}

_REPLIES: dict[str, dict[str, str]] = {
    "greeting": {
        "en": "Hello! It’s lovely to meet you. I’m Aanya, your university guide. How are you doing, and what can I help you with today?",
        "hi": "नमस्ते! आपसे मिलकर अच्छा लगा। मैं आन्या हूँ, आपकी विश्वविद्यालय गाइड। आप कैसे हैं, और आज मैं आपकी किस तरह मदद करूँ?",
    },
    "how_are_you": {
        "en": "I’m doing well, thank you for asking! How about you? Tell me what’s on your mind about the university.",
        "hi": "मैं बिल्कुल ठीक हूँ, पूछने के लिए धन्यवाद! आप कैसे हैं? बताइए, विश्वविद्यालय के बारे में क्या जानना चाहेंगे?",
    },
    "identity": {
        "en": "I’m Aanya, your digital university guide. I can help with fees, hostel and admissions using the documents the university has uploaded. Where shall we start?",
        "hi": "मैं आन्या हूँ, आपकी डिजिटल विश्वविद्यालय गाइड। अपलोड किए गए दस्तावेज़ों के आधार पर मैं फीस, हॉस्टल और प्रवेश में मदद कर सकती हूँ। कहाँ से शुरू करें?",
    },
    "thanks": {
        "en": "You’re most welcome! Is there anything else you’d like to know?",
        "hi": "आपका स्वागत है! क्या आप कुछ और जानना चाहेंगे?",
    },
    "bye": {
        "en": "Goodbye, and all the best! Come back any time you have a question.",
        "hi": "अलविदा, और शुभकामनाएँ! कोई भी सवाल हो तो फिर आइए।",
    },
    "ack": {
        "en": "Sure. I’m right here if you have another question.",
        "hi": "ठीक है। कोई और सवाल हो तो मैं यहीं हूँ।",
    },
}


def small_talk_reply(message: str, language: str) -> str | None:
    """Return a friendly reply only when the whole message is social, else None."""
    cleaned = re.sub(r"[^\wऀ-ॿ ]+", "", message.lower().replace("-", " "))
    cleaned = " ".join(cleaned.split())
    for kind, pattern in _PATTERNS.items():
        if re.fullmatch(pattern, cleaned):
            return _REPLIES[kind]["hi" if language == "hi" else "en"]
    return None
