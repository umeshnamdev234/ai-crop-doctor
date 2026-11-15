// Client for the Smarter Crops FastAPI backend (../backend).
import type { ChatMessage, DirectoryMeta, Lang, RecFilters, Recommendation } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8100";

export interface Health {
  status: "ok" | "degraded";
  model: string;
  model_server: string;
  model_server_reachable: boolean;
  model_available: boolean;
  database_reachable: boolean;
}

export type StreamEvent =
  | { type: "meta"; model: string; emergency: boolean; emergency_notice: string | null }
  | { type: "delta"; text: string }
  | { type: "done"; elapsed_s: number; tokens_per_s: number | null }
  | { type: "error"; message: string };

async function errorDetail(res: Response): Promise<string> {
  try {
    const j = await res.json();
    return typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
  } catch {
    return `HTTP ${res.status}`;
  }
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(await errorDetail(res));
  return res.json();
}

export const getHealth = () => getJSON<Health>("/api/health");
export const getModels = () => getJSON<{ default: string; models: string[] }>("/api/models");
export const getDirectoryMeta = () => getJSON<DirectoryMeta>("/api/directory/meta");

/** Converts UI messages into the backend's request format. */
export function toApiMessages(messages: ChatMessage[]) {
  return messages
    .filter((m) => !m.error && (m.content || m.images?.length))
    .map((m) => ({
      role: m.role,
      content: m.content || "",
      images: (m.images ?? []).map((im) => ({ mime_type: im.type, data: im.data })),
    }));
}

/** Streams a reply from POST /api/chat/stream (Server-Sent Events). */
export async function* streamChat(
  body: { messages: ReturnType<typeof toApiMessages>; model?: string; reply_language: "auto" | Lang },
  signal: AbortSignal,
): AsyncGenerator<StreamEvent> {
  const res = await fetch(`${API_URL}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) throw new Error(await errorDetail(res));
  if (!res.body) throw new Error("Empty response from server");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) >= 0) {
      const raw = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const data = raw.split("\n").filter((l) => l.startsWith("data:")).map((l) => l.slice(5).trim()).join("");
      if (data) yield JSON.parse(data) as StreamEvent;
    }
  }
}

/** Experts, treatments and centres for a conversation. Pass `previous` to re-rank without calling the model. */
export async function recommend(messages: ChatMessage[], filters: RecFilters, lang: Lang, previous?: Recommendation): Promise<Recommendation> {
  const res = await fetch(`${API_URL}/api/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages: toApiMessages(messages), ...filters, reply_language: lang === "hi" ? "hi" : "auto", previous: previous?.triage }),
  });
  if (!res.ok) throw new Error(await errorDetail(res));
  return res.json();
}
