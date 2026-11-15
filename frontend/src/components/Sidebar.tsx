"use client";

import { useMemo, useState } from "react";
import type { Strings } from "@/lib/i18n";
import type { Chat, ServerStatus, Theme } from "@/lib/types";
import { ChatBubble, Globe, Leaf, Moon, Plus, Search, Trash } from "./Icons";

interface Props {
  s: Strings;
  chats: Chat[];
  currentId: string | null;
  status: ServerStatus;
  theme: Theme;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onNew: () => void;
  onClearAll: () => void;
  onCycleTheme: () => void;
  onToggleLang: () => void;
}

const DAY = 864e5;

export default function Sidebar({ s, chats, currentId, status, theme, onSelect, onDelete, onNew, onClearAll, onCycleTheme, onToggleLang }: Props) {
  const [query, setQuery] = useState("");

  const groups = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = chats.filter((c) => !q || c.title.toLowerCase().includes(q)).sort((a, b) => b.updated - a.updated);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const defs: [string, (t: number) => boolean][] = [
      [s.today, (t) => t >= today],
      [s.yesterday, (t) => t >= today - DAY],
      [s.week, (t) => t >= today - 7 * DAY],
      [s.older, () => true],
    ];
    const used = new Set<string>();
    return defs
      .map(([label, fn]) => {
        const items = list.filter((c) => !used.has(c.id) && fn(c.updated));
        items.forEach((c) => used.add(c.id));
        return { label, items };
      })
      .filter((g) => g.items.length);
  }, [chats, query, s]);

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="logo"><Leaf size={20} /></div>
        <div>
          <div className="brand-name">Smarter <span>Crops</span></div>
          <div className="brand-sub">{s.brandSub}</div>
        </div>
      </div>

      <button className="new-chat" onClick={onNew}><Plus />{s.newChat}</button>

      <div className="search">
        <Search opacity={0.6} />
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={s.search} aria-label={s.search} />
      </div>

      <nav className="history">
        {groups.length === 0 && <div className="group-label plain">{s.noChats}</div>}
        {groups.map((g) => (
          <div key={g.label}>
            <div className="group-label">{g.label}</div>
            {g.items.map((c) => (
              <div
                key={c.id}
                role="button"
                tabIndex={0}
                className={`chat-item ${c.id === currentId ? "active" : ""}`}
                onClick={() => onSelect(c.id)}
                onKeyDown={(e) => e.key === "Enter" && onSelect(c.id)}
              >
                <ChatBubble opacity={0.7} />
                <span className="t">{c.title}</span>
                <button className="del" title="Delete" aria-label={`Delete ${c.title}`} onClick={(e) => { e.stopPropagation(); onDelete(c.id); }}>
                  <Trash />
                </button>
              </div>
            ))}
          </div>
        ))}
      </nav>

      <div className="side-foot">
        <div className="status">
          <span className={`dot ${status.state === "ok" ? "ok" : status.state === "err" ? "err" : ""}`} />
          <div>
            <span>{status.text}</span>
            <small>{status.sub}</small>
          </div>
        </div>
        <button className="side-btn lang-btn" onClick={onToggleLang}><Globe />{s.language}</button>
        <button className="side-btn" onClick={onCycleTheme}><Moon />{s.theme}: {s.themeNames[theme]}</button>
        <button className="side-btn" onClick={onClearAll}><Trash size={16} />{s.clearAll}</button>
      </div>
    </aside>
  );
}
