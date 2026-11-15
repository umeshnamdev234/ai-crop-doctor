"use client";

import type { Strings } from "@/lib/i18n";
import { Activity, Bug, ImageIc, Leaf } from "./Icons";

export type Suggestion = Strings["suggestions"][number];

const ICONS = [<ImageIc key="i" />, <Activity key="a" />, <Leaf key="l" size={18} color="currentColor" />, <Bug key="b" />];

function greeting(s: Strings) {
  const h = new Date().getHours();
  return h < 12 ? s.greetMorning : h < 17 ? s.greetAfternoon : s.greetEvening;
}

export default function EmptyState({ s, onPick }: { s: Strings; onPick: (sg: Suggestion) => void }) {
  return (
    <div className="hero">
      <div className="hero-orb"><Leaf size={38} /></div>
      <h1>
        {greeting(s)}. <span className="grad-text">{s.heroTitle}</span>
      </h1>
      <p>{s.heroText}</p>
      <div className="cards">
        {s.suggestions.map((sg, i) => (
          <button key={sg.title} className="card" onClick={() => onPick(sg)}>
            <div className="card-ic">{ICONS[i % ICONS.length]}</div>
            <div>
              <b>{sg.title}</b>
              <span>{sg.prompt}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
