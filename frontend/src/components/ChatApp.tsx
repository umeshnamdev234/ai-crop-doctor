"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getDirectoryMeta, getHealth, getModels, recommend, streamChat, toApiMessages } from "@/lib/api";
import { t } from "@/lib/i18n";
import { load, save, saveChats } from "@/lib/storage";
import type { Chat, ChatMessage, DirectoryMeta, ImageAttachment, Lang, RecFilters, ServerStatus, Theme } from "@/lib/types";
import Composer from "./Composer";
import EmptyState, { type Suggestion } from "./EmptyState";
import { Lock, Menu } from "./Icons";
import MessageItem from "./MessageItem";
import Sidebar from "./Sidebar";

const THEMES: Theme[] = ["auto", "light", "dark"];
const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 7);

// Rendered client-only (see ClientRoot), so reading localStorage in initialisers is safe.
export default function ChatApp() {
  const [chats, setChats] = useState<Chat[]>(() =>
    load<Chat[]>("sc.chats", []).map((c) => ({ ...c, messages: c.messages.map((m) => (m.recLoading ? { ...m, recLoading: false } : m)) })),
  );
  const [currentId, setCurrentId] = useState<string | null>(() => {
    const id = load<string | null>("sc.current", null);
    return id && load<Chat[]>("sc.chats", []).some((c) => c.id === id) ? id : null;
  });
  const [lang, setLang] = useState<Lang>(() => load<Lang>("sc.lang", "en"));
  const s = t(lang);
  const [input, setInput] = useState("");
  const [images, setImages] = useState<ImageAttachment[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [theme, setTheme] = useState<Theme>(() => load<Theme>("sc.theme", "auto"));
  const [models, setModels] = useState<string[]>([]);
  const [model, setModel] = useState<string>(() => load<string>("sc.model", ""));
  const [meta, setMeta] = useState<DirectoryMeta | null>(null);
  const [status, setStatus] = useState<ServerStatus>({ state: "loading", text: s.connecting, sub: "API :8100" });

  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const forceScroll = useRef(true);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const current = chats.find((c) => c.id === currentId) ?? null;
  const chatsRef = useRef(chats);
  useEffect(() => { chatsRef.current = chats; }, [chats]);

  /* ---------- persistence ---------- */
  useEffect(() => {
    if (streaming) return;
    saveChats(chats);
    save("sc.current", currentId);
  }, [chats, currentId, streaming]);

  useEffect(() => {
    const el = document.documentElement;
    if (theme === "auto") el.removeAttribute("data-theme");
    else el.setAttribute("data-theme", theme);
    save("sc.theme", theme);
  }, [theme]);

  useEffect(() => {
    document.documentElement.lang = lang;
    save("sc.lang", lang);
  }, [lang]);

  /* ---------- backend status ---------- */
  const refreshStatus = useCallback(async () => {
    const str = t(load<Lang>("sc.lang", "en"));
    try {
      const h = await getHealth();
      if (!h.model_server_reachable) {
        setStatus({ state: "err", text: str.modelOffline, sub: "Start Ollama" });
        return;
      }
      const m = await getModels();
      setModels(m.models);
      setModel((prev) => (m.models.includes(prev) ? prev : m.models.find((n) => n.startsWith(m.default)) ?? m.models[0] ?? ""));
      getDirectoryMeta().then(setMeta).catch(() => {});
      setStatus(
        h.model_available
          ? { state: "ok", text: str.online, sub: `${h.model} · API :8100` }
          : { state: "warn", text: `Model "${h.model}" not found`, sub: `ollama pull ${h.model}` },
      );
    } catch {
      setStatus({ state: "err", text: str.offline, sub: "docker compose up -d" });
    }
  }, []);

  useEffect(() => {
    const first = setTimeout(refreshStatus, 0);
    const id = setInterval(() => { if (!abortRef.current) refreshStatus(); }, 15000);
    return () => { clearTimeout(first); clearInterval(id); };
  }, [refreshStatus, lang]);

  /* ---------- auto-scroll ---------- */
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    if (forceScroll.current || el.scrollHeight - el.scrollTop - el.clientHeight < 160) {
      el.scrollTop = el.scrollHeight;
      forceScroll.current = false;
    }
  }, [chats, currentId]);

  /* ---------- streaming ---------- */
  const runStream = useCallback(
    async (chatId: string, history: ChatMessage[]) => {
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      setStreaming(true);
      forceScroll.current = true;
      setChats((cs) => cs.map((c) => (c.id === chatId ? { ...c, messages: [...history, { role: "assistant", content: "" }], updated: Date.now() } : c)));
      const patch = (p: Partial<ChatMessage>) =>
        setChats((cs) => cs.map((c) => {
          if (c.id !== chatId) return c;
          const msgs = c.messages.slice();
          msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], ...p };
          return { ...c, messages: msgs };
        }));

      let content = "";
      let failed = false;
      let raf = 0;
      const flush = () => { raf = 0; patch({ content }); };
      try {
        const body = { messages: toApiMessages(history), model: model || undefined, reply_language: lang === "hi" ? ("hi" as const) : ("auto" as const) };
        for await (const ev of streamChat(body, ctrl.signal)) {
          if (ev.type === "meta" && ev.emergency) patch({ emergency: ev.emergency_notice });
          else if (ev.type === "delta") { content += ev.text; if (!raf) raf = requestAnimationFrame(flush); }
          else if (ev.type === "done") patch({ stats: ev.tokens_per_s ? `${ev.tokens_per_s} tok/s` : `${ev.elapsed_s}s` });
          else if (ev.type === "error") throw new Error(ev.message);
        }
      } catch (err) {
        const e = err as Error;
        if (e.name !== "AbortError") {
          failed = true;
          patch({ error: /fetch|network|load failed/i.test(e.message) ? t(lang).apiOffline : `Error: ${e.message}` });
        }
      } finally {
        cancelAnimationFrame(raf);
        patch({ content: content || (failed ? "" : t(lang).stopped) });
        setChats((cs) => cs.map((c) => (c.id === chatId ? { ...c, updated: Date.now() } : c)));
        abortRef.current = null;
        setStreaming(false);
        refreshStatus();
      }
    },
    [model, lang, refreshStatus],
  );

  const send = useCallback(
    (text?: string) => {
      const txt = (text ?? input).trim();
      if ((!txt && !images.length) || streaming) return;
      const userMsg: ChatMessage = { role: "user", content: txt, images: images.length ? images : undefined };
      let chat = current;
      if (!chat) {
        chat = { id: uid(), title: (txt || "Crop photo").slice(0, 48), messages: [], updated: Date.now() };
        const created = chat;
        setChats((cs) => [...cs, created]);
        setCurrentId(created.id);
      }
      setInput("");
      setImages([]);
      runStream(chat.id, [...chat.messages, userMsg]);
    },
    [input, images, streaming, current, runStream],
  );

  const stop = () => abortRef.current?.abort();

  const regenerate = useCallback(() => {
    if (!current || streaming) return;
    const msgs = current.messages.slice();
    if (msgs.at(-1)?.role === "assistant") msgs.pop();
    runStream(current.id, msgs);
  }, [current, streaming, runStream]);

  /* ---------- recommendations ---------- */
  const getRecommendations = useCallback(
    async (index: number, filters: RecFilters) => {
      const chat = chatsRef.current.find((c) => c.id === currentId);
      if (!chat) return;
      const chatId = chat.id;
      const previous = chat.messages[index]?.recommendation; // re-rank only when filters change
      const patchMsg = (p: Partial<ChatMessage>) =>
        setChats((cs) => cs.map((c) => (c.id !== chatId ? c : { ...c, messages: c.messages.map((m, i) => (i === index ? { ...m, ...p } : m)) })));
      patchMsg({ recLoading: true, recError: undefined });
      try {
        const rec = await recommend(chat.messages.slice(0, index + 1), filters, lang, previous);
        patchMsg({ recommendation: rec, recLoading: false });
      } catch (err) {
        const msg = (err as Error).message;
        patchMsg({ recLoading: false, recError: /fetch|network|load failed/i.test(msg) ? t(lang).apiOffline : msg });
      }
    },
    [currentId, lang],
  );

  /* ---------- sidebar actions ---------- */
  const selectChat = (id: string) => { stop(); forceScroll.current = true; setCurrentId(id); setSidebarOpen(false); };
  const newChat = () => { stop(); setCurrentId(null); setSidebarOpen(false); textareaRef.current?.focus(); };
  const deleteChat = (id: string) => {
    if (id === currentId) { stop(); setCurrentId(null); }
    setChats((cs) => cs.filter((c) => c.id !== id));
  };
  const clearAll = () => {
    if (!confirm(s.clearConfirm)) return;
    stop(); setChats([]); setCurrentId(null);
  };

  const pickSuggestion = (sg: Suggestion) => {
    if ("image" in sg && sg.image) {
      setInput(s.imagePrompt);
      fileInputRef.current?.click();
    } else send(sg.prompt);
  };

  const lastIndex = (current?.messages.length ?? 0) - 1;

  return (
    <div className={`app ${sidebarOpen ? "open" : ""}`}>
      <Sidebar
        s={s}
        chats={chats}
        currentId={currentId}
        status={status}
        theme={theme}
        onSelect={selectChat}
        onDelete={deleteChat}
        onNew={newChat}
        onClearAll={clearAll}
        onCycleTheme={() => setTheme((th) => THEMES[(THEMES.indexOf(th) + 1) % THEMES.length])}
        onToggleLang={() => setLang((l) => (l === "en" ? "hi" : "en"))}
      />
      <div className="scrim" onClick={() => setSidebarOpen(false)} />

      <main className="main">
        <header className="topbar">
          <button className="icon-btn menu-btn" aria-label="Open menu" onClick={() => setSidebarOpen(true)}><Menu /></button>
          <div className="model-pill">
            <select aria-label="Model" value={model} onChange={(e) => { setModel(e.target.value); save("sc.model", e.target.value); }}>
              {models.length === 0 && <option value="">gemma3:4b</option>}
              {models.map((m) => <option key={m} value={m}>{m.replace(":latest", "")}</option>)}
            </select>
            <span className="badge agri">AGRI</span>
          </div>
          <div className="spacer" />
          <div className="privacy" title={s.privacy}>
            <Lock stroke="var(--accent)" /><span>{s.privacy}</span>
          </div>
        </header>

        <div className="scroll" ref={scrollRef}>
          {!current || current.messages.length === 0 ? (
            <EmptyState s={s} onPick={pickSuggestion} />
          ) : (
            <div className="thread">
              {current.messages.map((m, i) => (
                <MessageItem
                  key={i}
                  s={s}
                  message={m}
                  index={i}
                  meta={meta}
                  onRecommend={getRecommendations}
                  isLast={i === lastIndex}
                  streaming={streaming && i === lastIndex && m.role === "assistant"}
                  canRegenerate={!streaming}
                  onRegenerate={regenerate}
                />
              ))}
            </div>
          )}
        </div>

        <Composer
          s={s}
          value={input}
          onChange={setInput}
          images={images}
          onImagesChange={setImages}
          streaming={streaming}
          onSend={() => send()}
          onStop={stop}
          fileInputRef={fileInputRef}
          textareaRef={textareaRef}
        />
      </main>
    </div>
  );
}
