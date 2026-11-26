import Image from "next/image";
import type { AvatarState } from "./types";

const copy: Record<AvatarState, string> = {
  welcome: "How can I help you today?",
  idle: "Ask me anything about your university.",
  listening: "I’m listening…",
  thinking: "Let me find that for you…",
  speaking: "Here’s what I found.",
  error: "Something needs another try."
};

const avatarImage: Record<AvatarState, string> = {
  welcome: "/avatars/university-guide-v1.png",
  idle: "/avatars/university-guide-v1.png",
  listening: "/avatars/university-guide-listening-v1.png",
  thinking: "/avatars/university-guide-thinking-v1.png",
  speaking: "/avatars/university-guide-speaking-v1.png",
  error: "/avatars/university-guide-v1.png"
};

export function AvatarStage({ state }: { state: AvatarState }) {
  return (
    <section className={`avatar-stage avatar-${state}`} aria-live="polite" aria-label={`Digital guide is ${state}`}>
      <div className="video-topbar"><span><i /> AI guide · live session</span><span className="session-clock">00:00</span></div>
      <div className="avatar-card">
        <Image className="avatar-photo" src={avatarImage[state]} alt="AI university guide" width={1024} height={1536} priority />
        <div className="avatar-shade" />
        <div className="speaking-bars" aria-hidden="true"><i /><i /><i /><i /><i /></div>
      </div>
      <div className="avatar-copy">
        <p className="avatar-name">Aanya <span>· Your university guide</span></p>
        <p className="avatar-status"><span className="status-dot" />{copy[state]}</p>
      </div>
      <div className="session-controls" aria-label="Session controls"><span aria-hidden="true">◉</span><span aria-hidden="true">◌</span><span aria-hidden="true">⌁</span></div>
    </section>
  );
}
