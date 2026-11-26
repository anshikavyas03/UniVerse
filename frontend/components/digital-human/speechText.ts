// Turns a Markdown answer into plain speech text. Keep this in step with
// backend/app/services/voice/speech_text.py (the server applies it to every TTS request).

const SENTENCE_END = [".", "!", "?", ":", ";", "…", "।"];
const WORD = "\\p{L}\\p{N}_";

export function toSpokenText(text: string, language: "en" | "hi" = "en"): string {
  const stop = language === "hi" ? "।" : ".";
  const unescaped = text.replace(/\r\n/g, "\n").replace(/\\([\\`*_{}[\]()#+\-.!|>~])/g, "$1");
  const spoken: string[] = [];

  for (const rawLine of unescaped.split("\n")) {
    let line = rawLine.trim();
    if (!line || /^[\s|:\-_*=]{3,}$/.test(line)) continue;

    line = line
      .replace(/^```\w*/, "").trim()
      .replace(/^#{1,6}\s*/, "")
      .replace(/^>+\s*/, "")
      .replace(/^(?:[-*+•–—]|\d{1,3}[.)])\s+/, "");

    if (line.includes("|")) {
      line = line.replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim()).filter(Boolean).join(", ");
    }

    line = line
      .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
      .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
      .replace(/(?:https?:\/\/|www\.)\S+/g, "")
      .replace(/`([^`]*)`/g, "$1")
      .replace(/(\*\*|__)(?=\S)(.+?)(?<=\S)\1/g, "$2")
      .replace(/~~(.+?)~~/g, "$1")
      .replace(new RegExp(`(?<![${WORD}*])\\*(?=\\S)([^*]+?)(?<=\\S)\\*(?![${WORD}*])`, "gu"), "$1")
      .replace(new RegExp(`(?<![${WORD}])_(?=\\S)([^_]+?)(?<=\\S)_(?![${WORD}])`, "gu"), "$1")
      .replace(/[\u{1F300}-\u{1FAFF}\u2600-\u27BF\u2B50\uFE0F\u200D•●▪►◆]/gu, " ")
      .replace(new RegExp(`(?<![${WORD}])#+|[*\`~|]`, "gu"), "")
      .replace(new RegExp(`(?<![${WORD}])_+|_+(?![${WORD}])`, "gu"), "")
      .replace(/\s+/g, " ")
      .replace(/^[\s\-–—]+|[\s\-–—]+$/g, "");

    if (!line) continue;
    if (!SENTENCE_END.some((mark) => line.endsWith(mark))) line += stop;
    spoken.push(line);
  }
  return spoken.join(" ");
}
