"use client";

import { useState, useSyncExternalStore } from "react";
import { AvatarStage } from "./AvatarStage";
import { ChatPanel } from "./ChatPanel";
import type { AvatarState, Language } from "./types";
import { useChat } from "./useChat";
import { useRecorder } from "./useRecorder";
import { useServiceStatus } from "./useServiceStatus";
import { useVoice } from "./useVoice";

function greetingFor(language: Language, hour: number | null) {
  const part = hour === null ? 0 : hour < 12 ? 1 : hour < 17 ? 2 : 3;
  if (language === "hi") return `${["नमस्ते", "सुप्रभात", "नमस्ते", "शुभ संध्या"][part]}! मैं आन्या हूँ, आपकी विश्वविद्यालय गाइड। आपसे मिलकर अच्छा लगा। आज मैं आपकी क्या मदद करूँ?`;
  return `${["Hello", "Good morning", "Good afternoon", "Good evening"][part]}! I’m Aanya, your university guide. It’s nice to meet you. What can I help you with today?`;
}

const noSubscription = () => () => {};

export function DigitalHuman() {
  const [language, setLanguage] = useState<Language>("en");
  const [draft, setDraft] = useState("");
  const [greeted, setGreeted] = useState(false);
  // The server does not know the visitor's local time, so it renders a neutral greeting.
  const hour = useSyncExternalStore(noSubscription, () => new Date().getHours(), () => null);
  const greeting = greetingFor(language, hour);

  const voice = useVoice();
  const chat = useChat({ language, onAnswer: voice.speak });
  const recorder = useRecorder(language, (spoken) => setDraft((current) => `${current} ${spoken}`.trim()));
  const warning = useServiceStatus();

  // Derived from what is really happening, so the avatar can never get stuck in a state.
  const state: AvatarState = recorder.status === "recording" ? "listening"
    : chat.sending || recorder.status === "transcribing" || voice.phase === "preparing" ? "thinking"
    : voice.phase === "speaking" || voice.phase === "paused" ? "speaking"
    : chat.failed || recorder.problem ? "error"
    : greeted || chat.messages.length ? "idle" : "welcome";

  function send(query: string, retryOf?: string) {
    voice.unlock();
    voice.stop();
    recorder.cancel();
    setGreeted(true);
    void chat.send(query, retryOf);
    setDraft((current) => (current.trim() === query.trim() ? "" : current));
  }

  function say(text: string, textLanguage: Language) {
    voice.unlock();
    recorder.cancel();
    setGreeted(true);
    void voice.speak(text, textLanguage);
  }

  function newChat() {
    voice.stop();
    recorder.cancel();
    chat.reset();
    setDraft("");
    setGreeted(false);
  }

  function changeLanguage(next: Language) {
    voice.stop();
    recorder.cancel();
    setLanguage(next);
  }

  return (
    <main className="experience-shell">
      <header className="session-header">
        <a className="brand" href="#top" aria-label="University Digital Human home"><span className="brand-mark">U</span><span>UNIVERSITY<br /><b>DIGITAL HUMAN</b></span></a>
        <h1 id="top">Talk to your guide.</h1>
        <div className="language-toggle" role="group" aria-label="Choose language">
          <button type="button" className={language === "en" ? "active" : ""} aria-pressed={language === "en"} onClick={() => changeLanguage("en")}>EN</button>
          <button type="button" className={language === "hi" ? "active" : ""} aria-pressed={language === "hi"} onClick={() => changeLanguage("hi")}>हिन्दी</button>
        </div>
      </header>
      {warning ? <p className="service-warning" role="alert">{warning}</p> : null}
      <div className="stage-layout">
        <AvatarStage
          state={state} language={language} mouth={voice.mouth} caption={voice.caption} micLevel={recorder.level} muted={voice.muted}
          showGreet={!greeted && !chat.messages.length}
          onGreet={() => say(greeting, language)} paused={voice.phase === "paused"}
          onPause={voice.pause} onResume={voice.resume} onToggleMute={() => { voice.unlock(); voice.toggleMuted(); }}
        />
        <ChatPanel
          language={language} greeting={greeting} messages={chat.messages} sending={chat.sending} draft={draft}
          recording={recorder.status} notice={recorder.problem ?? voice.problem}
          onDraft={setDraft} onSend={send} onNewChat={newChat}
          onMic={() => { voice.stop(); void recorder.toggle(); }}
          onReplay={(message) => say(message.content, message.language)}
        />
      </div>
      <footer>AI UNIVERSITY ASSISTANT <span>•</span> VERIFIED & MULTILINGUAL</footer>
    </main>
  );
}
