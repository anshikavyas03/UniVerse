"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "./api";
import type { Language } from "./types";

type Status = "off" | "starting" | "recording" | "transcribing";

const errors = {
  en: {
    denied: "Microphone permission is blocked. Allow it from the address bar, or type your question.",
    missing: "I couldn’t find a working microphone. You can type your question instead.",
    unsupported: "This browser can’t record audio. You can type your question instead.",
    unclear: "I couldn’t catch that. Please try again, or type your question.",
    unavailable: "Voice typing isn’t available right now (speech recognition isn’t ready). Please type your question.",
  },
  hi: {
    denied: "माइक्रोफ़ोन की अनुमति बंद है। एड्रेस बार से अनुमति दें, या अपना प्रश्न लिखें।",
    missing: "कोई चालू माइक्रोफ़ोन नहीं मिला। आप अपना प्रश्न लिख सकते हैं।",
    unsupported: "यह ब्राउज़र ऑडियो रिकॉर्ड नहीं कर सकता। आप अपना प्रश्न लिख सकते हैं।",
    unclear: "मैं ठीक से सुन नहीं पाई। कृपया फिर बोलें, या प्रश्न लिखें।",
    unavailable: "बोलकर लिखने की सुविधा अभी उपलब्ध नहीं है। कृपया अपना प्रश्न लिखें।",
  },
};

export function useRecorder(language: Language, onText: (text: string) => void) {
  const [status, setStatus] = useState<Status>("off");
  const [problem, setProblem] = useState<string | null>(null);
  const [level, setLevel] = useState(0);
  const recorder = useRef<MediaRecorder | null>(null);
  const cleanup = useRef<() => void>(() => {});
  const session = useRef(0);
  const busy = useRef(false);

  const cancel = useCallback(() => {
    session.current += 1;
    busy.current = false;
    if (recorder.current) recorder.current.onstop = null;
    cleanup.current();
    recorder.current = null;
    setStatus("off");
    setProblem(null);
  }, []);

  useEffect(() => () => { session.current += 1; cleanup.current(); }, []);

  async function transcribe(blob: Blob, id: number) {
    setStatus("transcribing");
    let reason: "unclear" | "unavailable" = "unclear";
    try {
      if (!blob.size) throw new Error("Empty recording");
      const form = new FormData();
      form.append("file", blob, "question.webm");
      form.append("language", language);
      reason = "unavailable";
      const response = await apiFetch("/api/voice/transcriptions", { method: "POST", body: form });
      if (!response.ok) {
        const body: { detail?: string } = await response.json().catch(() => ({}));
        if (/no speech|empty/i.test(body.detail ?? "")) reason = "unclear";
        throw new Error("Transcription failed");
      }
      const result: { text: string } = await response.json();
      if (id === session.current) onText(result.text);
    } catch {
      if (id === session.current) setProblem(errors[language][reason]);
    } finally {
      if (id === session.current) { busy.current = false; setStatus("off"); }
    }
  }

  async function toggle() {
    if (recorder.current?.state === "recording") return recorder.current.stop();
    if (busy.current) return;
    setProblem(null);
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") return setProblem(errors[language].unsupported);
    busy.current = true;
    const id = ++session.current;
    setStatus("starting");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (id !== session.current) return stream.getTracks().forEach((track) => track.stop());
      const chunks: Blob[] = [];
      const media = new MediaRecorder(stream);
      const meter = new AudioContext();
      const analyser = meter.createAnalyser();
      meter.createMediaStreamSource(stream).connect(analyser);
      const samples = new Uint8Array(analyser.fftSize);
      const meterTimer = window.setInterval(() => {
        analyser.getByteTimeDomainData(samples);
        const peak = samples.reduce((max, value) => Math.max(max, Math.abs(value - 128)), 0);
        setLevel(Math.min(1, peak / 60));
      }, 100);
      const limit = window.setTimeout(() => { if (media.state === "recording") media.stop(); }, 60_000);
      cleanup.current = () => {
        cleanup.current = () => {};
        window.clearInterval(meterTimer);
        window.clearTimeout(limit);
        stream.getTracks().forEach((track) => track.stop());
        void meter.close();
        setLevel(0);
      };
      media.ondataavailable = (event) => chunks.push(event.data);
      media.onstop = () => {
        cleanup.current();
        recorder.current = null;
        void transcribe(new Blob(chunks, { type: media.mimeType || "audio/webm" }), id);
      };
      recorder.current = media;
      media.start();
      setStatus("recording");
    } catch (error) {
      if (id !== session.current) return;
      busy.current = false;
      cleanup.current();
      setStatus("off");
      const name = error instanceof DOMException ? error.name : "";
      setProblem(errors[language][name === "NotAllowedError" || name === "SecurityError" ? "denied" : "missing"]);
    }
  }

  return { status, problem, level, toggle, cancel };
}
