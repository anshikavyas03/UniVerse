export type AvatarState = "welcome" | "idle" | "listening" | "thinking" | "speaking" | "error";
export type Language = "en" | "hi";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

