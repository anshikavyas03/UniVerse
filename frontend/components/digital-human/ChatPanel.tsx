"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { Markdown } from "./Markdown";
import type { ChatMessage, Language } from "./types";

const copy = {
  en: { title: "Let’s talk", newChat: "New chat", try: "You could ask", next: "Ask next", retry: "Retry", listen: "Listen", verified: "Verified", placeholder: "Ask your university guide…", listening: "I’m listening… tap the mic to finish", transcribing: "Writing down what you said…", thinking: "Checking the university documents…", slow: "Still working. A local model can take a little while…", note: "University facts come only from your uploaded documents." },
  hi: { title: "बात करते हैं", newChat: "नई बातचीत", try: "आप पूछ सकते हैं", next: "आगे पूछें", retry: "फिर कोशिश करें", listen: "सुनें", verified: "सत्यापित", placeholder: "विश्वविद्यालय के बारे में पूछें…", listening: "मैं सुन रही हूँ… रोकने के लिए माइक दबाएँ", transcribing: "आपकी बात लिखी जा रही है…", thinking: "विश्वविद्यालय के दस्तावेज़ देख रही हूँ…", slow: "अभी काम जारी है। लोकल मॉडल को थोड़ा समय लग सकता है…", note: "विश्वविद्यालय की जानकारी केवल अपलोड किए गए दस्तावेज़ों से आती है।" },
};

export const starterQuestions: Record<Language, string[]> = {
  en: ["What are the hostel charges?", "What is the B.Tech CSE fee?", "Tell me about admissions"],
  hi: ["हॉस्टल शुल्क क्या है?", "B.Tech CSE की फीस क्या है?", "प्रवेश के बारे में बताइए"],
};

function Thinking({ language }: { language: Language }) {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    const timer = window.setTimeout(() => setSlow(true), 8000);
    return () => window.clearTimeout(timer);
  }, []);
  return <div className="message assistant thinking-bubble" role="status">
    <span className="dots" aria-hidden="true"><i /><i /><i /></span>{slow ? copy[language].slow : copy[language].thinking}
  </div>;
}

type Props = {
  language: Language;
  greeting: string;
  messages: ChatMessage[];
  sending: boolean;
  draft: string;
  recording: "off" | "starting" | "recording" | "transcribing";
  notice: string | null;
  onDraft: (value: string) => void;
  onSend: (query: string, retryOf?: string) => void;
  onMic: () => void;
  onReplay: (message: ChatMessage) => void;
  onNewChat: () => void;
};

export function ChatPanel({ language, greeting, messages, sending, draft, recording, notice, onDraft, onSend, onMic, onReplay, onNewChat }: Props) {
  const words = copy[language];
  const history = useRef<HTMLDivElement>(null);
  const last = messages.at(-1);

  // Show the start of a new answer (not its end), so long answers read from the top.
  useEffect(() => {
    const box = history.current;
    if (!box) return;
    const latest = box.querySelector<HTMLElement>("[data-latest]");
    const top = !latest ? 0 : last?.role === "assistant" && !sending ? latest.offsetTop - 12 : box.scrollHeight;
    const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    box.scrollTo({ top, behavior: calm ? "auto" : "smooth" });
  }, [last?.id, last?.role, sending]);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!sending && draft.trim()) onSend(draft);
  }

  const chips = !messages.length ? starterQuestions[language] : last?.role === "assistant" ? last.suggestions ?? [] : [];

  return (
    <section className="chat-panel" aria-label="Conversation">
      <div className="chat-panel-header">
        <div><span className="eyebrow">YOUR CONVERSATION</span><h2>{words.title}</h2></div>
        <button type="button" className="new-chat" onClick={onNewChat} disabled={!messages.length}>{words.newChat}</button>
      </div>
      <div className="chat-history" ref={history} role="log" aria-live="polite" tabIndex={0}>
        <article className="message assistant"><p>{greeting}</p></article>
        {messages.map((message) => <article className={`message ${message.role} ${message.failed ? "failed" : ""}`} key={message.id} lang={message.language} data-latest={message === last ? true : undefined}>
          {message.role === "assistant" ? <Markdown content={message.content} /> : message.content}
          {message.followUp ? <p className="follow-up">{message.followUp}</p> : null}
          {message.verified && message.sources?.length ? <div className="source-row">
            <span className="verified-badge">✓ {words.verified}</span>
            {message.sources.map((source) => <span className="source-chip" key={`${source.title}-${source.page}`}>{source.title}{source.page ? ` · p.${source.page}` : ""}</span>)}
          </div> : null}
          {message.role === "assistant" ? <div className="message-actions">
            {message.retryQuery && message === last ? <button type="button" onClick={() => onSend(message.retryQuery!, message.id)} disabled={sending}>↻ {words.retry}</button> : null}
            {!message.failed ? <button type="button" onClick={() => onReplay(message)}>▶ {words.listen}</button> : null}
          </div> : null}
        </article>)}
        {sending ? <Thinking language={language} /> : null}
        {!sending && chips.length ? <div className="suggestion-area">
          <p>{messages.length ? words.next : words.try}</p>
          <div>{chips.map((chip) => <button type="button" key={chip} onClick={() => onSend(chip)}>{chip}<span aria-hidden="true">↗</span></button>)}</div>
        </div> : null}
      </div>
      {notice ? <p className="composer-error" role="alert">{notice}</p> : null}
      <form className="composer" onSubmit={submit}>
        <button type="button" className={`mic ${recording === "recording" ? "recording" : ""}`} onClick={onMic} disabled={sending || recording === "starting" || recording === "transcribing"} aria-label={recording === "recording" ? "Stop voice input" : "Start voice input"} aria-pressed={recording === "recording"}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21" /></svg>
        </button>
        <input value={draft} maxLength={1000} onChange={(event) => onDraft(event.target.value)} placeholder={recording === "recording" ? words.listening : recording === "transcribing" ? words.transcribing : words.placeholder} aria-label="Your question" />
        <button className="send" disabled={sending || !draft.trim()} aria-label="Send question">↑</button>
      </form>
      <p className="composer-note">{words.note}</p>
    </section>
  );
}
