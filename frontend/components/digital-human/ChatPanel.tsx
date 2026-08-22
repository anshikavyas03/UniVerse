"use client";

import { FormEvent, useState } from "react";
import type { AvatarState, ChatMessage, Language } from "./types";

const welcome: Record<Language, string> = {
  en: "Welcome. I’m your AI university guide. Ask about academics, admissions, campus life, or events.",
  hi: "नमस्ते। मैं आपका AI विश्वविद्यालय सहायक हूँ। आप अकादमिक, प्रवेश, कैंपस जीवन या कार्यक्रमों के बारे में पूछ सकते हैं।"
};

type Props = { language: Language; onStateChange: (state: AvatarState) => void };

export function ChatPanel({ language, onStateChange }: Props) {
  const [text, setText] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([{ id: "welcome", role: "assistant", content: welcome[language] }]);

  function submit(event: FormEvent) {
    event.preventDefault();
    const query = text.trim();
    if (!query) return;
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: "user", content: query }]);
    setText("");
    onStateChange("thinking");
    window.setTimeout(() => {
      setMessages((current) => [...current, { id: crypto.randomUUID(), role: "assistant", content: language === "hi" ? "Phase 1 में यह एक अनुभव डेमो है। अगला चरण इसे सत्यापित विश्वविद्यालय जानकारी और AI उत्तरों से जोड़ेगा।" : "This is the Phase 1 experience demo. The next phase connects it to verified university information and live AI responses." }]);
      onStateChange("speaking");
      window.setTimeout(() => onStateChange("idle"), 1800);
    }, 700);
  }

  return (
    <section className="chat-panel" aria-label="Conversation">
      <div className="chat-history">
        {messages.map((message) => <p className={`message ${message.role}`} key={message.id}>{message.content}</p>)}
      </div>
      <form className="composer" onSubmit={submit}>
        <button type="button" className="mic" onClick={() => onStateChange("listening")} aria-label="Start voice input">⌁</button>
        <input value={text} onChange={(event) => setText(event.target.value)} placeholder={language === "hi" ? "विश्वविद्यालय के बारे में कुछ भी पूछें…" : "Ask anything about the university…"} aria-label="Your question" />
        <button className="send" aria-label="Send question">↑</button>
      </form>
    </section>
  );
}

