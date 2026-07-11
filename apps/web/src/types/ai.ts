export type AiChatRole = "user" | "assistant";

export type AiChatMessage = {
  role: AiChatRole;
  content: string;
};

export type AiChatContext = {
  novel_title?: string;
  novel_description?: string;
  author_name?: string;
  category_name?: string;
  chapter_title?: string;
  chapter_excerpt?: string;
};

export type AiChatRequest = {
  api_key: string;
  api_url?: string;
  model?: string;
  messages: AiChatMessage[];
  context?: AiChatContext;
};

export type AiChatResponse = {
  answer: string;
  model: string;
  usage: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  } | null;
};
