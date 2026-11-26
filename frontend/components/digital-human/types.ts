export type AvatarState = "welcome" | "idle" | "listening" | "thinking" | "speaking" | "error";
export type Language = "en" | "hi";
export type MouthShape = 0 | 1 | 2 | 3;

export type Source = {
  title: string;
  page?: number | null;
  category?: string | null;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "notice";
  content: string;
  language: Language;
  verified?: boolean;
  sources?: Source[];
  followUp?: string | null;
  suggestions?: string[];
  failed?: boolean;
  retryQuery?: string;
};
