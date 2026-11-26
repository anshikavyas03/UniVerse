"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "./api";
import { toSpokenText } from "./speechText";
import type { Language, MouthShape } from "./types";

type Phase = "off" | "preparing" | "speaking" | "paused";

function shorten(text: string, limit = 1800) {
  if (text.length <= limit) return text;
  const cut = text.slice(0, limit);
  const end = Math.max(cut.lastIndexOf(". "), cut.lastIndexOf("। "), cut.lastIndexOf("? "));
  return end > 0 ? cut.slice(0, end + 1) : cut;
}

/** Plays one answer at a time. Server audio retains its currentTime when paused. */
export function useVoice() {
  const [phase, setPhaseState] = useState<Phase>("off");
  const [mouth, setMouth] = useState<MouthShape>(0);
  const [muted, setMuted] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [caption, setCaption] = useState("");
  const phaseRef = useRef<Phase>("off");
  const turn = useRef(0);
  const request = useRef<AbortController | null>(null);
  const player = useRef<HTMLAudioElement | null>(null);
  const objectUrl = useRef<string | null>(null);
  const usingBrowser = useRef(false);
  const frame = useRef(0);
  const timers = useRef<number[]>([]);
  const mutedRef = useRef(false);
  const spokenText = useRef("");

  const showCaption = useCallback((text: string, wordCount: number) => {
    const words = text.trim().split(/\s+/).filter(Boolean);
    const end = Math.min(words.length, Math.max(1, wordCount));
    setCaption(words.slice(Math.max(0, end - 10), end).join(" "));
  }, []);

  const setPhase = useCallback((next: Phase) => {
    phaseRef.current = next;
    setPhaseState(next);
  }, []);
  const clearMotion = useCallback(() => {
    cancelAnimationFrame(frame.current);
    timers.current.forEach((timer) => window.clearTimeout(timer));
    timers.current = [];
    setMouth(0);
  }, []);
  const releasePlayer = useCallback(() => {
    const audio = player.current;
    if (audio) {
      audio.onended = null;
      audio.onerror = null;
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
      player.current = null;
    }
    if (objectUrl.current) {
      URL.revokeObjectURL(objectUrl.current);
      objectUrl.current = null;
    }
  }, []);
  const halt = useCallback(() => {
    turn.current += 1;
    request.current?.abort();
    request.current = null;
    clearMotion();
    const synth = window.speechSynthesis;
    if (synth?.paused) synth.resume();
    synth?.cancel();
    usingBrowser.current = false;
    releasePlayer();
    spokenText.current = "";
    setCaption("");
  }, [clearMotion, releasePlayer]);
  const stop = useCallback(() => {
    halt();
    setPhase("off");
  }, [halt, setPhase]);

  const unlock = useCallback(() => {
    // Calling speak from the user action is sufficient for an HTMLAudioElement.
  }, []);

  const animateBrowserMouth = useCallback((id: number, text: string) => {
    const rhythm: MouthShape[] = [1, 2, 3, 2, 0, 2, 1, 3, 1, 0];
    let tick = 0;
    const startedAt = performance.now();
    const flap = () => {
      if (id !== turn.current || phaseRef.current === "paused") return;
      setMouth(window.speechSynthesis?.speaking ? rhythm[tick++ % rhythm.length] : 0);
      showCaption(text, Math.floor((performance.now() - startedAt) / 1000 * 2.4) + 1);
      timers.current.push(window.setTimeout(flap, 110));
    };
    flap();
  }, [showCaption]);

  const speakWithBrowser = useCallback((text: string, language: Language, id: number) => {
    const synth = window.speechSynthesis;
    const voices = synth?.getVoices() ?? [];
    const wanted = language === "hi" ? "hi" : "en";
    const voice = voices.find((item) => item.lang.replace("_", "-").toLowerCase() === `${wanted}-in`) ?? voices.find((item) => item.lang.toLowerCase().startsWith(wanted));
    const finish = (message: string | null) => {
      if (id !== turn.current) return;
      clearMotion();
      usingBrowser.current = false;
      releasePlayer();
      spokenText.current = "";
      setCaption("");
      setPhase("off");
      setProblem(message);
    };
    if (!synth || (language === "hi" && !voice)) return finish("Voice isn’t available right now, so please read the answer in the chat.");
    usingBrowser.current = true;
    const pieces = text.match(/[^.!?।]+[.!?।]*\s*/g) ?? [text];
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
    setPhase("speaking");
    animateBrowserMouth(id, text);
    timers.current.push(window.setTimeout(() => finish(null), 4000 + text.length * 110));
  }, [animateBrowserMouth, clearMotion, releasePlayer, setPhase]);

  const speak = useCallback(async (answer: string, language: Language) => {
    halt();
    setProblem(null);
    setCaption("");
    const text = shorten(toSpokenText(answer, language));
    if (mutedRef.current || !text) return setPhase("off");
    spokenText.current = text;
    const id = turn.current;
    setPhase("preparing");
    try {
      request.current = new AbortController();
      const response = await apiFetch("/api/voice/speech", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, language }), signal: request.current.signal }, 30_000);
      if (!response.ok) throw new Error("Speech request failed");
      const url = URL.createObjectURL(await response.blob());
      if (id !== turn.current) { URL.revokeObjectURL(url); return; }
      objectUrl.current = url;
      const audio = new Audio(url);
      player.current = audio;
      audio.onended = () => { if (id === turn.current) stop(); };
      audio.onerror = () => { if (id === turn.current) speakWithBrowser(text, language, id); };
      await audio.play();
      if (id !== turn.current) return;
      setPhase("speaking");
      const words = text.trim().split(/\s+/).filter(Boolean);
      let captionIndex = -1;
      const follow = () => {
        if (id !== turn.current || phaseRef.current === "paused") return;
        setMouth(([1, 2, 3, 2, 1, 0] as MouthShape[])[Math.floor(audio.currentTime * 9) % 6]);
        const nextIndex = audio.duration > 0 ? Math.floor(audio.currentTime / audio.duration * words.length) + 1 : Math.floor(audio.currentTime * 2.4) + 1;
        if (nextIndex !== captionIndex) {
          captionIndex = nextIndex;
          showCaption(text, nextIndex);
        }
        frame.current = requestAnimationFrame(follow);
      };
      frame.current = requestAnimationFrame(follow);
    } catch {
      if (id === turn.current) speakWithBrowser(text, language, id);
    }
  }, [halt, setPhase, showCaption, speakWithBrowser, stop]);

  const pause = useCallback(() => {
    if (phaseRef.current !== "speaking") return;
    if (usingBrowser.current) window.speechSynthesis?.pause(); else player.current?.pause();
    clearMotion();
    setPhase("paused");
  }, [clearMotion, setPhase]);
  const resume = useCallback(() => {
    if (phaseRef.current !== "paused") return;
    if (usingBrowser.current) {
      window.speechSynthesis?.resume();
      animateBrowserMouth(turn.current, spokenText.current);
    } else if (player.current) {
      void player.current.play().catch(() => setProblem("Voice playback could not resume. Please use Listen to try again."));
      const id = turn.current;
      const follow = () => {
        if (id !== turn.current || phaseRef.current === "paused") return;
        setMouth(([1, 2, 3, 2, 1, 0] as MouthShape[])[Math.floor((player.current?.currentTime ?? 0) * 9) % 6]);
        frame.current = requestAnimationFrame(follow);
      };
      frame.current = requestAnimationFrame(follow);
    }
    setPhase("speaking");
  }, [animateBrowserMouth, setPhase]);
  const toggleMuted = useCallback(() => {
    mutedRef.current = !mutedRef.current;
    setMuted(mutedRef.current);
    if (mutedRef.current) stop();
  }, [stop]);

  useEffect(() => {
    window.speechSynthesis?.getVoices();
    return () => halt();
  }, [halt]);
  return { phase, mouth, muted, problem, caption, speak, stop, pause, resume, unlock, toggleMuted };
}
