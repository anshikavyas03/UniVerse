"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import type { AvatarState, ChatMessage, Language, Source } from "./types";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const welcome: Record<Language, string> = {
  en: "Welcome. I’m your AI university guide. Ask about academics, admissions, campus life, or events.",
  hi: "नमस्ते। मैं आपका AI विश्वविद्यालय सहायक हूँ। आप अकादमिक, प्रवेश, कैंपस जीवन या कार्यक्रमों के बारे में पूछ सकते हैं।"
};
const suggestions: Record<Language, string[]> = {
  en: ["What are the hostel charges?", "Tell me about admissions", "What is the B.Tech CSE fee?"],
  hi: ["हॉस्टल शुल्क क्या है?", "प्रवेश के बारे में बताइए", "B.Tech CSE की फीस क्या है?"]
};

type Props = { language: Language; onStateChange: (state: AvatarState) => void };
type ChatApiResponse = { conversation_id: string; message: string; language: Language; verified: boolean; sources: Source[] };

function inline(text: string) {
  return text.replace(/\\([*_])/g, "$1").split(/(\*\*[^*]+\*\*)/g).map((part, index) => part.startsWith("**") && part.endsWith("**") ? <strong key={index}>{part.slice(2, -2)}</strong> : part);
}

function AnswerContent({ content }: { content: string }) {
  const normalized = content
    .replace(/\\([*_])/g, "$1")
    .replace(/\*{2,}\s*•\s*\*{2,}/g, "•")
    .replace(/\s+([*-])\s+(?=\*\*)/g, "\n$1 ");
  const lines = normalized.split(/\n+/).map((line) => line.trim()).filter(Boolean);
  return <div className="answer-content">
    {lines.map((line, index) => {
      if (/^#{1,3}\s+/.test(line)) return <h3 key={index}>{inline(line.replace(/^#{1,3}\s+/, ""))}</h3>;
      if (/^[*-]\s+/.test(line)) return <div className="answer-bullet" key={index}><i>•</i><span>{inline(line.replace(/^[*-]\s+/, ""))}</span></div>;
      return <p key={index}>{inline(line)}</p>;
    })}
  </div>;
}

function speechText(content: string) {
  return content
    .replace(/\\([*_])/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/__([^_]+)__/g, "$1")
    .replace(/^#{1,3}\s+/gm, "")
    .replace(/^[*-]\s+/gm, "")
    .replace(/\s+[*-]\s+(?=[A-Za-z0-9₹])/g, ". ")
    .replace(/\[(.*?)\]\([^)]*\)/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
}

export function ChatPanel({ language, onStateChange }: Props) {
  const [text, setText] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([{ id: "welcome", role: "assistant", content: welcome[language] }]);
  const [conversationId, setConversationId] = useState<string>();
  const [recording, setRecording] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const chunks = useRef<Blob[]>([]);
  const audio = useRef<HTMLAudioElement | null>(null);

  useEffect(() => () => {
    stream.current?.getTracks().forEach((track) => track.stop());
    audio.current?.pause();
  }, []);

  function speakNativeHindi(answer: string) {
    if (!("speechSynthesis" in window)) return false;
    const voice = window.speechSynthesis.getVoices().find((candidate) => candidate.lang.toLowerCase().startsWith("hi"));
    if (!voice) return false;
    const utterance = new SpeechSynthesisUtterance(answer);
    utterance.lang = "hi-IN";
    utterance.voice = voice;
    utterance.rate = 0.92;
    utterance.onend = () => onStateChange("idle");
    utterance.onerror = () => void playServerSpeech(answer, "hi");
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
    onStateChange("speaking");
    return true;
  }

  async function playServerSpeech(answer: string, answerLanguage: Language) {
    try {
      const response = await fetch(`${apiUrl}/api/voice/speech`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: answer, language: answerLanguage }) });
      if (!response.ok) return onStateChange("idle");
      const url = URL.createObjectURL(await response.blob());
      audio.current = new Audio(url);
      audio.current.onended = () => { URL.revokeObjectURL(url); onStateChange("idle"); };
      audio.current.onerror = () => { URL.revokeObjectURL(url); onStateChange("idle"); };
      onStateChange("speaking");
      await audio.current.play();
    } catch { onStateChange("idle"); }
  }

  async function speak(answer: string, answerLanguage: Language) {
    const plainAnswer = speechText(answer);
    if (answerLanguage === "hi" && speakNativeHindi(plainAnswer)) return;
    await playServerSpeech(plainAnswer, answerLanguage);
  }

  async function send(query: string) {
    if (isSending) return;
    setIsSending(true);
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: "user", content: query }]);
    onStateChange("thinking");
    try {
      const response = await fetch(`${apiUrl}/api/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: query, language, conversation_id: conversationId }) });
      if (!response.ok) throw new Error("Chat request failed");
      const reply: ChatApiResponse = await response.json();
      setConversationId(reply.conversation_id);
      setMessages((current) => [...current, { id: crypto.randomUUID(), role: "assistant", content: reply.message, verified: reply.verified, sources: reply.sources }]);
      void speak(reply.message, reply.language);
    } catch {
      setMessages((current) => [...current, { id: crypto.randomUUID(), role: "assistant", content: language === "hi" ? "अभी उत्तर प्राप्त नहीं हो सका। कृपया फिर कोशिश करें।" : "I couldn’t reach the university assistant just now. Please try again." }]);
      onStateChange("error");
    } finally {
      setIsSending(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const query = text.trim();
    if (!query) return;
    setText("");
    void send(query);
  }

  async function toggleRecording() {
    if (recording) return recorder.current?.stop();
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream.current);
      chunks.current = [];
      mediaRecorder.ondataavailable = (event) => chunks.current.push(event.data);
      mediaRecorder.onstop = () => void transcribe(new Blob(chunks.current, { type: mediaRecorder.mimeType || "audio/webm" }));
      recorder.current = mediaRecorder;
      mediaRecorder.start();
      setRecording(true);
      onStateChange("listening");
    } catch { onStateChange("error"); }
  }

  async function transcribe(recordingBlob: Blob) {
    setRecording(false);
    stream.current?.getTracks().forEach((track) => track.stop());
    onStateChange("thinking");
    const form = new FormData();
    form.append("file", recordingBlob, "question.webm");
    form.append("language", language);
    try {
      const response = await fetch(`${apiUrl}/api/voice/transcriptions`, { method: "POST", body: form });
      if (!response.ok) throw new Error("Transcription request failed");
      const result: { text: string } = await response.json();
      setText(result.text);
      onStateChange("idle");
    } catch { onStateChange("error"); }
  }

  return (
    <section className="chat-panel" aria-label="Conversation">
      <div className="chat-panel-header">
        <div><span className="eyebrow">YOUR CONVERSATION</span><h2>How can I help?</h2></div>
        <span className="availability"><i /> Verified mode</span>
      </div>
      <div className="chat-history" aria-live="polite">
        {messages.map((message) => <article className={`message ${message.role}`} key={message.id}>
          {message.role === "assistant" ? <AnswerContent content={message.content} /> : message.content}
          {message.verified && message.sources?.length ? <div className="source-row"><span className="verified-badge">✓ Verified</span>{message.sources.map((source) => <span className="source-chip" key={`${source.title}-${source.page}`}>{source.title}{source.page ? ` · p.${source.page}` : ""}</span>)}</div> : null}
        </article>)}
        {messages.length === 1 ? <div className="suggestion-area"><p>Try asking</p><div>{suggestions[language].map((suggestion) => <button type="button" key={suggestion} onClick={() => void send(suggestion)}>{suggestion}<span>↗</span></button>)}</div></div> : null}
      </div>
      <form className="composer" onSubmit={submit}>
        <button type="button" className={`mic ${recording ? "recording" : ""}`} onClick={() => void toggleRecording()} aria-label={recording ? "Stop voice input" : "Start voice input"} aria-pressed={recording}>⌁</button>
        <input disabled={isSending} value={text} onChange={(event) => setText(event.target.value)} placeholder={recording ? (language === "hi" ? "मैं सुन रही हूँ…" : "I’m listening…") : language === "hi" ? "विश्वविद्यालय के बारे में पूछें…" : "Ask your university guide…"} aria-label="Your question" />
        <button className="send" disabled={isSending} aria-label="Send question">{isSending ? "…" : "↑"}</button>
      </form>
      <p className="composer-note">Answers are grounded in your uploaded university documents.</p>
    </section>
  );
}
