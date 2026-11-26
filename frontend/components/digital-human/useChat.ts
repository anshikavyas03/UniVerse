"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "./api";
import type { ChatMessage, Language, Source } from "./types";

type ChatApiResponse = {
  conversation_id: string;
  message: string;
  language: Language;
  verified: boolean;
  sources: Source[];
  follow_up: string | null;
  suggestions: string[];
  error: "database_unavailable" | "model_unavailable" | null;
  session_reset: boolean;
};

const text = {
  en: {
    offline: "I can’t reach the university assistant. Please check that the backend is running on port 8000, then retry.",
    slow: "That took too long to answer. Please retry in a moment.",
    server: "Something went wrong on the assistant’s side. Please retry.",
    reset: "The assistant restarted, so I no longer remember our earlier messages.",
  },
  hi: {
    offline: "विश्वविद्यालय सहायक से संपर्क नहीं हो पा रहा। कृपया जाँचें कि बैकएंड पोर्ट 8000 पर चल रहा है, फिर कोशिश करें।",
    slow: "उत्तर आने में बहुत समय लग गया। कृपया थोड़ी देर बाद फिर कोशिश करें।",
    server: "सहायक की तरफ़ कुछ गड़बड़ हुई। कृपया फिर कोशिश करें।",
    reset: "सहायक दोबारा शुरू हुआ है, इसलिए पिछली बातचीत मुझे याद नहीं है।",
  },
};

type Options = {
  language: Language;
  onAnswer: (spoken: string, language: Language) => void;
};

export function useChat({ language, onAnswer }: Options) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [failed, setFailed] = useState(false);
  const conversationId = useRef<string | undefined>(undefined);
  const inFlight = useRef<AbortController | null>(null);

  useEffect(() => () => inFlight.current?.abort(), []);

  // The avatar's worried look fades back to idle on its own.
  useEffect(() => {
    if (!failed) return;
    const timer = window.setTimeout(() => setFailed(false), 6000);
    return () => window.clearTimeout(timer);
  }, [failed]);

  const send = useCallback(async (raw: string, retryOf?: string) => {
    const query = raw.trim();
    // A ref, not state, so a double click in the same instant is also blocked.
    if (!query || inFlight.current) return false;
    const controller = new AbortController();
    inFlight.current = controller;
    setSending(true);
    setFailed(false);
    setMessages((current) => retryOf
      ? current.filter((item) => item.id !== retryOf)
      : [...current, { id: crypto.randomUUID(), role: "user", content: query, language }]);

    const add = (message: Omit<ChatMessage, "id">) => setMessages((current) => [...current, { ...message, id: crypto.randomUUID() }]);
    const fail = (content: string) => {
      add({ role: "assistant", content, language, failed: true, retryQuery: query });
      setFailed(true);
    };

    void (async () => {
      try {
        const response = await apiFetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: query, language, conversation_id: conversationId.current }), signal: controller.signal });
        if (!response.ok) return fail(text[language].server);
        const reply: ChatApiResponse = await response.json();
        if (controller.signal.aborted) return;
        conversationId.current = reply.conversation_id;
        if (reply.session_reset) add({ role: "notice", content: text[language].reset, language });
        add({ role: "assistant", content: reply.message, language: reply.language, verified: reply.verified, sources: reply.sources, followUp: reply.follow_up, suggestions: reply.suggestions, failed: Boolean(reply.error), retryQuery: reply.error ? query : undefined });
        if (reply.error) setFailed(true);
        onAnswer(reply.follow_up ? `${reply.message}\n${reply.follow_up}` : reply.message, reply.language);
      } catch (error) {
        if (inFlight.current !== controller) return; // a new chat cancelled this one
        fail(text[language][error instanceof DOMException && error.name === "AbortError" ? "slow" : "offline"]);
      } finally {
        if (inFlight.current === controller) {
          inFlight.current = null;
          setSending(false);
        }
      }
    })();
    return true;
  }, [language, onAnswer]);

  const reset = useCallback(() => {
    const controller = inFlight.current;
    inFlight.current = null;
    controller?.abort();
    conversationId.current = undefined;
    setMessages([]);
    setSending(false);
    setFailed(false);
  }, []);

  return { messages, sending, failed, send, reset };
}
