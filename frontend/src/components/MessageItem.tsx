"use client";

import { memo, useState } from "react";
import type { Strings } from "@/lib/i18n";
import type { ChatMessage, DirectoryMeta, RecFilters } from "@/lib/types";
import { Alert, Check, Copy, Leaf, Regen } from "./Icons";
import Markdown from "./Markdown";
import Recommendations from "./Recommendations";

interface Props {
  s: Strings;
  message: ChatMessage;
  index: number;
  meta: DirectoryMeta | null;
  onRecommend: (index: number, filters: RecFilters) => void;
  isLast: boolean;
  streaming: boolean;
  canRegenerate: boolean;
  onRegenerate: () => void;
}

function MessageItem({ s, message: m, index, meta, onRecommend, isLast, streaming, canRegenerate, onRegenerate }: Props) {
  const [copied, setCopied] = useState(false);

  if (m.role === "user") {
    return (
      <div className="msg user">
        <div className="user-col">
          {!!m.images?.length && (
            <div className="msg-imgs">
              {m.images.map((im, i) => (
                // eslint-disable-next-line @next/next/no-img-element -- local base64 data
                <img key={i} src={`data:${im.type};base64,${im.data}`} alt="Crop photo" />
              ))}
            </div>
          )}
          {m.content && <div className="bubble">{m.content}</div>}
        </div>
      </div>
    );
  }

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(m.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {
      /* clipboard blocked */
    }
  };

  return (
    <div className={`msg ai ${isLast ? "last" : ""}`}>
      <div className="avatar"><Leaf size={17} /></div>
      <div className="bubble">
        <div className="who">{s.assistant} {m.stats && <span className="meta">{m.stats}</span>}</div>

        {m.emergency && (
          <div className="emergency" role="alert"><Alert /><div><b>{s.emergencyTitle}</b>{m.emergency}</div></div>
        )}

        {m.error ? (
          <div className="err-box">{m.error}</div>
        ) : streaming && !m.content ? (
          <div className="thinking">
            <svg className="ecg" viewBox="0 0 64 22" aria-hidden><path d="M0 11h18l4-8 6 16 5-12 3 4h28" /></svg>
            {s.analyzing}
          </div>
        ) : (
          <div className={`content ${streaming ? "streaming" : ""}`}><Markdown text={m.content} /></div>
        )}

        {!streaming && !m.error && m.content && (
          <div className="actions">
            <button className="act" onClick={copy}>{copied ? <><Check />{s.copied}</> : <><Copy />{s.copy}</>}</button>
            {isLast && canRegenerate && <button className="act" onClick={onRegenerate}><Regen />{s.regenerate}</button>}
            {!m.recommendation && !m.recLoading && (
              <button className="act primary-act" onClick={() => onRecommend(index, {})}><Leaf size={14} color="currentColor" />{s.getHelp}</button>
            )}
          </div>
        )}

        {(m.recommendation || m.recLoading || m.recError) && (
          <Recommendations s={s} rec={m.recommendation} loading={m.recLoading} error={m.recError} meta={meta} onRefine={(f) => onRecommend(index, f)} />
        )}
      </div>
    </div>
  );
}

export default memo(MessageItem);
