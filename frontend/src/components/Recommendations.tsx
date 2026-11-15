"use client";

import { useState } from "react";
import type { Strings } from "@/lib/i18n";
import type { Centre, DirectoryMeta, Expert, Product, RecFilters, Recommendation } from "@/lib/types";
import { Alert, Leaf, Pill, Regen, Shield, Store, Users } from "./Icons";

type Tab = "experts" | "products" | "centres";

const initials = (name: string) => name.replace(/\(sample\)/i, "").trim().split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase();
const inr = (n: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);

interface Props {
  s: Strings;
  rec?: Recommendation;
  loading?: boolean;
  error?: string;
  meta: DirectoryMeta | null;
  onRefine: (filters: RecFilters) => void;
}

export default function Recommendations({ s, rec, loading, error, meta, onRefine }: Props) {
  const [filters, setFilters] = useState<RecFilters>(rec?.filters ?? {});
  const [tab, setTab] = useState<Tab>("experts");

  const update = (patch: Partial<RecFilters>) => {
    const next = { ...filters, ...patch };
    if ("state" in patch) next.district = undefined; // district belongs to a state
    setFilters(next);
    onRefine(next);
  };

  const districts = filters.state ? meta?.states[filters.state] ?? [] : [];
  const t = rec?.triage;
  const counts = { experts: rec?.experts.length ?? 0, products: rec?.products.length ?? 0, centres: rec?.centres.length ?? 0 };

  return (
    <section className="docs" aria-label={s.recTitle}>
      <header className="docs-head">
        <div className="docs-title">
          <span className="docs-ic"><Leaf size={16} /></span>
          <div>
            <b>{s.recTitle}</b>
            {rec?.triage.source === "keywords" && <small>{s.recFallback}</small>}
          </div>
        </div>
        {t && <span className={`urgency sev-${t.severity}`}>{s.severity[t.severity]}</span>}
      </header>

      {rec?.emergency_notice && (
        <div className="emergency" role="alert"><Alert /><div><b>{s.emergencyTitle}</b>{rec.emergency_notice}</div></div>
      )}

      {t && (
        <div className="triage">
          {t.crop && <span className="chip crop">{t.crop}</span>}
          <span className="chip">{s.problem[t.problem_type]}</span>
          {t.likely_issues.map((i) => <span key={i} className="chip issue">{i}</span>)}
        </div>
      )}

      <div className="doc-filters">
        <select aria-label="State" value={filters.state ?? ""} onChange={(e) => update({ state: e.target.value || undefined })} disabled={loading}>
          <option value="">{s.anyState}</option>
          {Object.keys(meta?.states ?? {}).map((st) => <option key={st} value={st}>{st}</option>)}
        </select>
        <select aria-label="District" value={filters.district ?? ""} onChange={(e) => update({ district: e.target.value || undefined })} disabled={loading || !filters.state}>
          <option value="">{s.anyDistrict}</option>
          {districts.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
        <select aria-label="Language" value={filters.language ?? ""} onChange={(e) => update({ language: e.target.value || undefined })} disabled={loading}>
          <option value="">{s.anyLanguage}</option>
          {meta?.languages.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
        <label className="toggle">
          <input type="checkbox" checked={!!filters.organic_only} onChange={(e) => update({ organic_only: e.target.checked })} disabled={loading} />
          {s.organicOnly}
        </label>
      </div>

      {error && (
        <div className="err-box">{error} <button className="act inline" onClick={() => onRefine(filters)}><Regen />{s.retry}</button></div>
      )}

      {loading && !rec && (
        <div className="thinking">
          <svg className="ecg" viewBox="0 0 64 22" aria-hidden><path d="M0 11h18l4-8 6 16 5-12 3 4h28" /></svg>
          {s.recMatching}
        </div>
      )}

      {rec && (
        <>
          <div className="tabs" role="tablist">
            {(["experts", "products", "centres"] as Tab[]).map((k) => (
              <button key={k} role="tab" aria-selected={tab === k} className={`tab ${tab === k ? "active" : ""}`} onClick={() => setTab(k)}>
                {k === "experts" ? <Users /> : k === "products" ? <Pill size={16} /> : <Store />}
                {s.tabs[k]} <span className="count">{counts[k]}</span>
              </button>
            ))}
          </div>

          {tab === "products" && rec.safety_reminder && (
            <div className="safety"><Shield /><div><b>{s.safetyTitle}</b>{rec.safety_reminder}</div></div>
          )}

          <div className={`doc-grid ${loading ? "dim" : ""}`}>
            {tab === "experts" && (rec.experts.length ? rec.experts.map((e) => <ExpertCard key={e.id} e={e} s={s} />) : <p className="muted">{s.noResults}</p>)}
            {tab === "products" && (rec.products.length ? rec.products.map((p) => <ProductCard key={p.id} p={p} s={s} />) : <p className="muted">{s.noProducts}</p>)}
            {tab === "centres" && (rec.centres.length ? rec.centres.map((c) => <CentreCard key={c.id} c={c} s={s} />) : <p className="muted">{s.noResults}</p>)}
          </div>
        </>
      )}
    </section>
  );
}

function Reasons({ r }: { r: string[] }) {
  return <div className="doc-reasons">{r.slice(1).map((x) => <span key={x}>{x}</span>)}</div>;
}

function ExpertCard({ e, s }: { e: Expert; s: Strings }) {
  const [note, setNote] = useState(false);
  return (
    <article className="doc-card">
      <div className="doc-top">
        <div className="doc-avatar" aria-hidden>{initials(e.name)}</div>
        <div className="doc-id">
          <b>{e.name}</b>
          <span>{e.expert_type}</span>
          <small>{e.qualifications}</small>
        </div>
        <div className="doc-rating" title={`${e.review_count} reviews`}>★ {e.rating.toFixed(1)}</div>
      </div>
      <div className="doc-facts">
        <span>{e.experience_years} {s.yrs}</span>
        <span>{e.district}, {e.state}</span>
        <span>{e.fee === 0 ? s.free : inr(e.fee)}</span>
        {e.phone_consult && <span className="tele">{s.phone}</span>}
        {e.field_visit && <span className="tele">{s.visit}</span>}
      </div>
      <Reasons r={e.match_reasons} />
      <div className="doc-foot">
        <span className="doc-next">{e.next_available ? <>{s.nextAvail}: <b>{e.next_available}</b></> : ""}</span>
        <button className="book" onClick={() => setNote((n) => !n)}>{s.contact}</button>
      </div>
      {note && <p className="doc-note">{s.contactNote}</p>}
    </article>
  );
}

function ProductCard({ p, s }: { p: Product; s: Strings }) {
  return (
    <article className="doc-card">
      <div className="doc-top">
        <div className="doc-avatar" aria-hidden>{p.organic ? <Leaf size={18} /> : <Pill size={18} stroke="#fff" />}</div>
        <div className="doc-id">
          <b>{p.name}</b>
          <span>{p.category}{p.organic ? ` · ${s.organic}` : ""}</span>
          <small>{p.active_ingredient}</small>
        </div>
        {p.price_inr != null && <div className="doc-rating">{inr(p.price_inr)}{p.unit ? ` / ${p.unit}` : ""}</div>}
      </div>
      <div className="prod-dose"><b>{s.dose}:</b> {p.dose}</div>
      <div className="doc-facts">
        {p.waiting_period_days != null && p.waiting_period_days > 0 && <span>{s.waiting}: <b>{p.waiting_period_days} {s.days}</b></span>}
      </div>
      <Reasons r={p.match_reasons} />
      <div className="prod-safety">{p.safety_notes}</div>
    </article>
  );
}

function CentreCard({ c, s }: { c: Centre; s: Strings }) {
  return (
    <article className="doc-card">
      <div className="doc-top">
        <div className="doc-avatar" aria-hidden><Store size={18} stroke="#fff" /></div>
        <div className="doc-id">
          <b>{c.name}</b>
          <span>{c.centre_type}</span>
          <small>{c.address}</small>
        </div>
        {c.free_service && <div className="doc-rating">{s.free}</div>}
      </div>
      <div className="doc-facts">{c.services.slice(0, 4).map((x) => <span key={x}>{x}</span>)}</div>
      <Reasons r={c.match_reasons} />
      <div className="doc-foot">
        <span className="doc-next">{c.next_open ? <>{s.openOn}: <b>{c.next_open}</b></> : ""}</span>
      </div>
    </article>
  );
}
