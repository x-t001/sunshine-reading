import { apiRequest } from "@/lib/api/request";
import type { AiChatRequest, AiChatResponse } from "@/types/ai";

export function sendAiChatMessage(payload: AiChatRequest): Promise<AiChatResponse> {
  return apiRequest<AiChatResponse>("/ai/chat/", {
    method: "POST",
    auth: false,
    body: JSON.stringify(payload),
  });
}
