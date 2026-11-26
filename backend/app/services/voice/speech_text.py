"""Turn Markdown answers into plain, natural text before they reach text-to-speech.

The chat model writes Markdown (headings, bullets, **bold**, links). A speech
engine would read those symbols aloud ("asterisk asterisk"), so every spoken
reply passes through ``to_spoken_text`` first.
"""

import re

_SENTENCE_END = (".", "!", "?", ":", ";", "…", "।")
_EMOJI_AND_SYMBOLS = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\uFE0F\u200D•●▪►◆]")
_RULE_LINE = re.compile(r"^[\s|:\-_*=]{3,}$")
_LIST_MARKER = re.compile(r"^(?:[-*+•–—]|\d{1,3}[.)])\s+")
_UNESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!|>~])")


def _strip_inline_markup(line: str) -> str:
    line = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", line)  # image -> alt text
    line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)  # link -> label only
    line = re.sub(r"(?:https?://|www\.)\S+", "", line)  # bare web addresses
    line = re.sub(r"`([^`]*)`", r"\1", line)  # inline code
    line = re.sub(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1", r"\2", line)  # bold
    line = re.sub(r"~~(.+?)~~", r"\1", line)  # strikethrough
    line = re.sub(r"(?<![\w*])\*(?=\S)([^*]+?)(?<=\S)\*(?![\w*])", r"\1", line)  # *italic*
    line = re.sub(r"(?<!\w)_(?=\S)([^_]+?)(?<=\S)_(?!\w)", r"\1", line)  # _italic_
    return line


def to_spoken_text(text: str, language: str = "en") -> str:
    """Return plain speech text: no Markdown symbols, one clear sentence per line item."""
    stop = "।" if language == "hi" else "."
    text = _UNESCAPE.sub(r"\1", text.replace("\r\n", "\n"))
    spoken: list[str] = []
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line or _RULE_LINE.match(line):
            continue
        line = re.sub(r"^```\w*", "", line).strip()
        line = re.sub(r"^#{1,6}\s*", "", line)  # headings
        line = re.sub(r"^>+\s*", "", line)  # block quotes
        line = _LIST_MARKER.sub("", line)  # bullets and numbered items
        if "|" in line:  # table row -> comma-separated phrase
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            line = ", ".join(cell for cell in cells if cell)
        line = _strip_inline_markup(line)
        line = _EMOJI_AND_SYMBOLS.sub(" ", line)
        line = re.sub(r"(?<!\w)#+|[*`~|]", "", line)  # any leftover symbols
        line = re.sub(r"(?<!\w)_+|_+(?!\w)", "", line)
        line = re.sub(r"\s+", " ", line).strip(" -–—")
        if not line:
            continue
        if not line.endswith(_SENTENCE_END):
            line += stop  # gives the voice a natural pause between items
        spoken.append(line)
    return " ".join(spoken)
