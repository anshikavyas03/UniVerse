export type AvatarState = "welcome" | "idle" | "listening" | "thinking" | "speaking" | "error";
export type Language = "en" | "hi";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  verified?: boolean;
  sources?: Source[];
};

export type Source = {
  title: string;
  page?: number | null;
  category?: string | null;
};

