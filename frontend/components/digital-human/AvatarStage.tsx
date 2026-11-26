"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import type { AvatarState, Language, MouthShape } from "./types";

const copy: Record<Language, Record<AvatarState, string>> = {
  en: { welcome: "Hi! I’m here when you’re ready.", idle: "Ask me anything about your university.", listening: "I’m listening…", thinking: "Let me check that for you…", speaking: "Speaking…", error: "Sorry, something didn’t work. Let’s try again." },
  hi: { welcome: "नमस्ते! जब आप तैयार हों, मैं यहीं हूँ।", idle: "विश्वविद्यालय के बारे में कुछ भी पूछें।", listening: "मैं सुन रही हूँ…", thinking: "एक पल, मैं देखती हूँ…", speaking: "बोल रही हूँ…", error: "माफ़ कीजिए, कुछ गड़बड़ हुई। फिर कोशिश करें।" },
};

// Overlay boxes inside the 1024x1536 portrait; keep in step with scripts/build_avatar_frames.py.
const place = (x: number, y: number, width: number, height: number) => ({ left: `${x / 10.24}%`, top: `${y / 15.36}%`, width: `${width / 10.24}%`, height: `${height / 15.36}%` });
const mouthBox = place(400, 520, 240, 150);
const blinkBox = place(350, 365, 310, 90);

function useBlink(active: boolean) {
  const [closed, setClosed] = useState(false);
  useEffect(() => {
    if (!active || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let timer: number;
    const schedule = () => {
      timer = window.setTimeout(() => {
        setClosed(true);
        timer = window.setTimeout(() => {
          setClosed(false);
          // A rare double blink keeps the idle portrait from feeling looped.
          if (Math.random() < 0.18) {
            timer = window.setTimeout(() => {
              setClosed(true);
              timer = window.setTimeout(() => { setClosed(false); schedule(); }, 115);
            }, 150);
          } else schedule();
        }, 115 + Math.random() * 55);
      }, 2200 + Math.random() * 3600);
    };
    schedule();
    return () => { window.clearTimeout(timer); setClosed(false); };
  }, [active]);
  return closed;
}

function Clock() {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, []);
  return <span className="session-clock">{String(Math.floor(seconds / 60)).padStart(2, "0")}:{String(seconds % 60).padStart(2, "0")}</span>;
}

type Props = {
  state: AvatarState;
  language: Language;
  mouth: MouthShape;
  caption: string;
  micLevel: number;
  muted: boolean;
  showGreet: boolean;
  onGreet: () => void;
  paused: boolean;
  onPause: () => void;
  onResume: () => void;
  onToggleMute: () => void;
};

export function AvatarStage({ state, language, mouth, caption, micLevel, muted, showGreet, onGreet, paused, onPause, onResume, onToggleMute }: Props) {
  // The listening and thinking portraits are separate poses; the others share the front-facing one.
  const pose = state === "listening" || state === "thinking" ? state : "front";
  const blink = useBlink(pose === "front");
  const portrait = (name: string, visible: boolean, alt = "") =>
    <Image className={`portrait ${visible ? "visible" : ""}`} src={`/avatars/${name}.png`} alt={alt} fill sizes="(max-width: 940px) 100vw, 60vw" loading="eager" />;
  const overlay = (name: string, visible: boolean, box: React.CSSProperties) =>
    // eslint-disable-next-line @next/next/no-img-element -- tiny pre-sized overlays that must swap instantly
    <img key={name} className={`overlay ${visible ? "visible" : ""}`} src={`/avatars/${name}.webp`} alt="" style={box} />;

  return (
    <section className={`avatar-stage avatar-${state} ${paused ? "avatar-paused" : ""}`} aria-label="Aanya, your university guide">
      <div className="portrait-frame">
        <div className="portrait-canvas">
          {portrait("university-guide-v1", pose === "front", "Aanya, an AI university guide")}
          {portrait("university-guide-listening-v1", pose === "listening")}
          {portrait("university-guide-thinking-v1", pose === "thinking")}
          {([1, 2, 3] as const).map((shape) => overlay(`mouth-${shape}`, pose === "front" && mouth === shape, mouthBox))}
          {overlay("blink", blink, blinkBox)}
        </div>
      </div>
      <div className="avatar-shade" />
      <div className="video-topbar"><span><i /> AI guide · live session</span><Clock /></div>
      {showGreet ? <button type="button" className="greet-button" onClick={onGreet}>{language === "hi" ? "आन्या को नमस्ते कहें" : "Say hello to Aanya"}</button> : null}
      <div className="avatar-copy">
        <p className="avatar-name">Aanya <span>· Your university guide</span></p>
        <p className="avatar-status" role="status"><span className="status-dot" />{paused ? (language === "hi" ? "रुका हुआ…" : "Paused…") : copy[language][state]}</p>
        {state === "listening" ? <div className="mic-meter" aria-hidden="true"><i style={{ transform: `scaleX(${Math.max(0.04, micLevel)})` }} /></div> : null}
      </div>
      {caption && (state === "speaking" || paused) ? <p className="live-caption" aria-live="polite">{caption}</p> : null}
      <div className="session-controls">
        {state === "speaking" ? <button type="button" onClick={paused ? onResume : onPause}>{paused ? (language === "hi" ? "फिर चलाएँ" : "Resume") : (language === "hi" ? "रोकें" : "Pause")}</button> : null}
        <button type="button" onClick={onToggleMute} aria-pressed={muted}>{muted ? (language === "hi" ? "आवाज़ बंद" : "Voice off") : (language === "hi" ? "आवाज़ चालू" : "Voice on")}</button>
      </div>
      <div className="speaking-bars" aria-hidden="true">{[0, 1, 2, 3, 4].map((bar) => <i key={bar} />)}</div>
    </section>
  );
}
