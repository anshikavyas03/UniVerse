"use client";

import { useState } from "react";
import { AvatarStage } from "./AvatarStage";
import { ChatPanel } from "./ChatPanel";
import type { AvatarState, Language } from "./types";

const actions = ["Academics", "Admissions", "Campus", "Events"];

export function DigitalHuman() {
  const [language, setLanguage] = useState<Language>("en");
  const [avatarState, setAvatarState] = useState<AvatarState>("welcome");

  return (
    <main className="experience-shell">
      <header>
        <a className="brand" href="#top" aria-label="University Digital Human home"><span className="brand-mark">U</span><span>UNIVERSITY<br /><b>DIGITAL HUMAN</b></span></a>
        <div className="language-toggle" aria-label="Choose language">
          <button className={language === "en" ? "active" : ""} onClick={() => setLanguage("en")}>EN</button>
          <button className={language === "hi" ? "active" : ""} onClick={() => setLanguage("hi")}>हिन्दी</button>
        </div>
      </header>
      <div className="stage-layout" id="top">
        <AvatarStage state={avatarState} />
        <ChatPanel language={language} onStateChange={setAvatarState} />
      </div>
      <nav className="quick-actions" aria-label="Quick topics">
        {actions.map((action) => <button key={action} onClick={() => setAvatarState("thinking")}><span>→</span>{action}</button>)}
      </nav>
      <footer>AI UNIVERSITY ASSISTANT <span>•</span> VERIFIED INFORMATION COMING IN PHASE 3</footer>
    </main>
  );
}

