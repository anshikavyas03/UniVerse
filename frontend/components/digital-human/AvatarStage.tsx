import type { AvatarState } from "./types";

const copy: Record<AvatarState, string> = {
  welcome: "How can I help you today?",
  idle: "Ask me anything about your university.",
  listening: "I’m listening…",
  thinking: "Let me find that for you…",
  speaking: "Here’s what I found.",
  error: "Something needs another try."
};

export function AvatarStage({ state }: { state: AvatarState }) {
  return (
    <section className={`avatar-stage avatar-${state}`} aria-live="polite">
      <div className="orbit orbit-one" />
      <div className="orbit orbit-two" />
      <div className="avatar-halo" />
      <div className="avatar" aria-label={`Avatar is ${state}`}>
        <div className="avatar-hair" />
        <div className="avatar-head">
          <i className="eye left" /><i className="eye right" />
          <i className="nose" /><i className="mouth" />
        </div>
        <div className="avatar-neck" />
        <div className="avatar-shoulders" />
      </div>
      <p className="avatar-status"><span className="status-dot" />{copy[state]}</p>
    </section>
  );
}

