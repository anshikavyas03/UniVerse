"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "./api";
import { toSpokenText } from "./speechText";
import type { Language, MouthShape } from "./types";

type Phase = "off" | "preparing" | "speaking";

/** Keep within the server's request limit and end on a full sentence. */
function shorten(text: string, limit = 1800) {
  if (text.length <= limit) return text;
  const cut = text.slice(0, limit);
  const end = Math.max(cut.lastIndexOf(". "), cut.lastIndexOf("। "), cut.lastIndexOf("? "));
  return end > 0 ? cut.slice(0, end + 1) : cut;
}

/**
 * Speaks answers and reports the mouth shape while doing so.
 * Server audio drives the mouth from its real loudness; the browser voice is the
 * fallback and uses an approximate rhythm, because browsers expose no audio for it.
 */
export function useVoice() {
  const [phase, setPhase] = useState<Phase>("off");
  const [mouth, setMouth] = useState<MouthShape>(0);
  const [muted, setMuted] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const turn = useRef(0);
  const context = useRef<AudioContext | null>(null);
  const source = useRef<AudioBufferSourceNode | null>(null);
  const request = useRef<AbortController | null>(null);
  const frame = useRef(0);
  const timers = useRef<number[]>([]);
  const mutedRef = useRef(false);

  const halt = useCallback(() => {
    turn.current += 1;
    request.current?.abort();
    cancelAnimationFrame(frame.current);
    timers.current.forEach((timer) => window.clearTimeout(timer));
    timers.current = [];
    if (source.current) {
      source.current.onended = null;
      try { source.current.stop(); } catch { /* not started */ }
      source.current = null;
    }
    window.speechSynthesis?.cancel();
  }, []);

  const stop = useCallback(() => {
    halt();
    setMouth(0);
    setPhase("off");
  }, [halt]);

  /** Browsers only allow sound after a click, so call this from click and submit handlers. */
  const unlock = useCallback(() => {
    if (typeof AudioContext === "undefined") return;
    context.current ??= new AudioContext();
    if (context.current.state === "suspended") void context.current.resume();
  }, []);

  const speakWithBrowser = useCallback((text: string, language: Language, id: number) => {
    const synth = window.speechSynthesis;
    const voices = synth?.getVoices() ?? [];
    const wanted = language === "hi" ? "hi" : "en";
    const voice = voices.find((item) => item.lang.replace("_", "-").toLowerCase() === `${wanted}-in`)
      ?? voices.find((item) => item.lang.toLowerCase().startsWith(wanted));
    const finish = (message: string | null) => {
      if (id !== turn.current) return;
      halt();
      setMouth(0);
      setPhase("off");
      setProblem(message);
    };
    if (!synth || (language === "hi" && !voice)) return finish("Voice isn’t available right now, so please read the answer in the chat.");

    // Sentence-sized pieces avoid Chrome cutting off long utterances.
    const pieces = text.match(/[^.!?।]+[.!?।]*\s*/g) ?? [text];
    const rhythm: MouthShape[] = [1, 2, 3, 2, 0, 2, 1, 3, 1, 0];
    let tick = 0;
    const flap = () => {
      if (id !== turn.current) return;
      setMouth(synth.speaking ? rhythm[tick++ % rhythm.length] : 0);
      timers.current.push(window.setTimeout(flap, 110));
    };
    pieces.forEach((piece, index) => {
      const utterance = new SpeechSynthesisUtterance(piece);
      utterance.lang = language === "hi" ? "hi-IN" : "en-IN";
      if (voice) utterance.voice = voice;
      utterance.rate = 0.95;
      utterance.onstart = () => { if (id === turn.current) setPhase("speaking"); };
      if (index === pieces.length - 1) utterance.onend = () => finish(null);
      utterance.onerror = () => finish("Voice playback failed, so please read the answer in the chat.");
      synth.speak(utterance);
    });
    flap();
    // Some browsers never fire "end"; never leave the avatar stuck speaking.
    timers.current.push(window.setTimeout(() => finish(null), 4000 + text.length * 110));
  }, [halt]);

  const speak = useCallback(async (answer: string, language: Language) => {
    halt();
    setMouth(0);
    setProblem(null);
    const text = shorten(toSpokenText(answer, language));
    if (mutedRef.current || !text) return setPhase("off");
    const id = turn.current;
    setPhase("preparing");
    try {
      const audio = context.current;
      if (!audio || audio.state !== "running") throw new Error("Audio is locked");
      request.current = new AbortController();
      const response = await apiFetch("/api/voice/speech", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, language }), signal: request.current.signal }, 30_000);
      if (!response.ok) throw new Error("Speech request failed");
      const buffer = await audio.decodeAudioData(await response.arrayBuffer());
      if (id !== turn.current) return;
      const node = audio.createBufferSource();
      const analyser = audio.createAnalyser();
      analyser.fftSize = 1024;
      node.buffer = buffer;
      node.connect(analyser).connect(audio.destination);
      const samples = new Float32Array(analyser.fftSize);
      let peak = 0.08;
      let changedAt = 0;
      const follow = (time: number) => {
        if (id !== turn.current) return;
        if (time - changedAt > 70) {
          analyser.getFloatTimeDomainData(samples);
          const loudness = Math.sqrt(samples.reduce((sum, value) => sum + value * value, 0) / samples.length);
          peak = Math.max(loudness, peak * 0.995);
          const level = loudness / peak;
          setMouth(loudness < 0.012 ? 0 : level < 0.35 ? 1 : level < 0.65 ? 2 : 3);
          changedAt = time;
        }
        frame.current = requestAnimationFrame(follow);
      };
      node.onended = () => { if (id === turn.current) stop(); };
      source.current = node;
      node.start();
      setPhase("speaking");
      frame.current = requestAnimationFrame(follow);
    } catch {
      if (id === turn.current) speakWithBrowser(text, language, id);
    }
  }, [halt, speakWithBrowser, stop]);

  const toggleMuted = useCallback(() => {
    mutedRef.current = !mutedRef.current;
    setMuted(mutedRef.current);
    if (mutedRef.current) stop();
  }, [stop]);

  useEffect(() => {
    window.speechSynthesis?.getVoices(); // start loading the voice list early
    return () => { halt(); void context.current?.close(); context.current = null; };
  }, [halt]);

  return { phase, mouth, muted, problem, speak, stop, unlock, toggleMuted };
}
