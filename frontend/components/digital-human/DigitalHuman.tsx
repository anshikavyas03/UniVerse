"use client";

import { useState } from "react";
import { AvatarStage } from "./AvatarStage";
import { ChatPanel } from "./ChatPanel";
import type { AvatarState, Language } from "./types";

export function DigitalHuman() {
  const [language, setLanguage] = useState<Language>("en");
  const [avatarState, setAvatarState] = useState<AvatarState>("welcome");

  return (
    <main className="experience-shell live-experience">
      <header className="session-header">
        <a className="brand" href="#top" aria-label="University Digital Human home"><span className="brand-mark">U</span><span>UNIVERSITY<br /><b>DIGITAL HUMAN</b></span></a>
        <div className="session-label"><span className="live-dot" /> PRIVATE STUDENT SESSION</div>
        <div className="language-toggle" aria-label="Choose language">
          <button className={language === "en" ? "active" : ""} onClick={() => setLanguage("en")}>EN</button>
          <button className={language === "hi" ? "active" : ""} onClick={() => setLanguage("hi")}>हिन्दी</button>
        </div>
      </header>
      <div className="session-heading" id="top"><div><p className="eyebrow">UNIVERSITY DIGITAL HUMAN</p><h1>Talk to your guide.</h1></div><p>Ask naturally. I will answer from verified university documents and ask when I need more detail.</p></div>
      <div className="stage-layout live-layout">
        <AvatarStage state={avatarState} />
        <ChatPanel language={language} onStateChange={setAvatarState} />
      </div>
      <footer>AI UNIVERSITY ASSISTANT <span>•</span> VERIFIED, PRIVATE & MULTILINGUAL</footer>
    </main>
  );
}
