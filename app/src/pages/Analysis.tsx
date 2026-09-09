import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import AlertMap from "../components/AlertMap";
import AouOfflineBadge from "../components/AouOfflineBadge";
import NajdSeasonalChip from "../components/NajdSeasonalChip";
import { publicUrl } from "../lib/publicUrl";
import SourceCitation from "../components/SourceCitation";
import DecisionChrome, {
  type ConfidenceUnit,
  type EvidenceGapUnit,
  type SuitabilityUnit,
} from "../components/DecisionChrome";

type DatePoint = {
  date: string;
  source: string;
  product_id: string;
  tile: string;
  cloud_cover: number;
  citation?: string;
  ndvi: { mean: number; p50?: number };
  ndmi: { mean: number; p50?: number };
  alert_counts: Record<string, number>;
};

type Timeseries = {
  source: string;
  citation?: string;
  dates: DatePoint[];
  method?: { indices?: string[] };
  formula_ref?: string;
};

type AlertProps = {
  alert?: string;
  ndvi?: number;
  ndmi?: number;
  ndre?: number | null;
  ndre_available?: boolean;
  ndre_status?: string;
  aou_id?: string | null;
  agricultural_probability?: number;
  ag_class?: string;
  water_stress_score?: number;
  vigor_stress_score?: number;
  possible_biotic_stress?: boolean;
  data_quality_confidence?: number;
  biotic_disclaimer_en?: string;
  biotic_disclaimer_ar?: string;
  product_id?: string;
  tile?: string;
  cloud_cover?: number;
  date?: string;
  source?: string;
  geometry_kind?: string;
};

type AlertsMeta = {
  properties?: {
    source?: string;
    date?: string;
    alert_counts?: Record<string, number>;
    note?: string;
    aou_count?: number;
    possible_biotic_stress_count?: number;
    formula_ref?: string;
  };
  features?: { properties: AlertProps; geometry?: unknown }[];
};

type AouFeature = {
  type: "Feature";
  properties: {
    aou_id: string;
    agricultural_probability?: number;
    ag_class?: string;
    area_ha_est?: number;
    ndvi?: number;
    ndmi?: number;
    ndre?: number | null;
    ndre_available?: boolean;
    date?: string;
  };
};

type AouObsUnit = {
  aou_id: string;
  observations: {
    date?: string;
    ndvi?: number | null;
    ndmi?: number | null;
    ndre?: number | null;
    water_stress_score?: number;
    vigor_stress_score?: number;
    possible_biotic_stress?: boolean;
    agricultural_probability?: number;
    ag_class?: string;
    data_quality_confidence?: number;
    alert?: string;
    series_scope?: string;
  }[];
  window_context_series?: {
    date?: string;
    ndvi?: number | null;
    ndmi?: number | null;
    series_scope?: string;
    note?: string;
  }[];
  honesty?: string;
};

const COUNT_KEYS = ["healthy", "water_attention", "vigor_attention", "bare", "unclear"] as const;
const COUNT_COLORS: Record<string, string> = {
  healthy: "#2f6b3a",
  water_attention: "#0284c7",
  vigor_attention: "#d97706",
  bare: "#d6c3a3",
  unclear: "#78716c",
};

const LEVELS = ["overview", "spatial", "temporal", "decision"] as const;

function SeriesChart({
  title,
  color,
  points,
  caption,
}: {
  title: string;
  color: string;
  points: { date: string; value: number }[];
  caption?: string;
}) {
  if (!points.length) return null;
  const w = 560;
  const h = 140;
  const pad = 28;
  const vals = points.map((p) => p.value);
  const minY = Math.min(...vals) - 0.02;
  const maxY = Math.max(...vals) + 0.02;
  const x = (i: number) => pad + (i * (w - pad * 2)) / Math.max(points.length - 1, 1);
  const y = (v: number) => h - pad - ((v - minY) / (maxY - minY || 1)) * (h - pad * 2);
  const line = vals.map((v, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
  return (
    <div className="rounded-2xl border border-sand-200 bg-white p-4 shadow-sm">
      <h3 className="mb-2 text-sm font-semibold text-sand-900">{title}</h3>
      <svg viewBox={`0 0 ${w} ${h}`} className="h-36 w-full min-w-[18rem]">
        <path d={line} fill="none" stroke={color} strokeWidth="2.5" />
        {points.map((p, i) => (
          <g key={p.date}>
            <circle cx={x(i)} cy={y(p.value)} r="3.5" fill={color} />
            <text x={x(i)} y={h - 8} textAnchor="middle" className="fill-sand-800" style={{ fontSize: 10 }}>
              {p.date.slice(5)}
            </text>
          </g>
        ))}
      </svg>
      {caption && <p className="mt-1 text-xs text-sand-800/60">{caption}</p>}
    </div>
  );
}

export default function Analysis() {
  const { t } = useTranslation();
  const [level, setLevel] = useState<(typeof LEVELS)[number]>("overview");
  const [ts, setTs] = useState<Timeseries | null>(null);
  const [alerts, setAlerts] = useState<AlertsMeta | null>(null);
  const [aouRegistry, setAouRegistry] = useState<AouFeature[]>([]);
  const [aouObs, setAouObs] = useState<AouObsUnit[]>([]);
  const [selectedAou, setSelectedAou] = useState<string>("");
  const [error, setError] = useState(false);
  const [suitabilityUnits, setSuitabilityUnits] = useState<SuitabilityUnit[]>([]);
  const [confidenceUnits, setConfidenceUnits] = useState<ConfidenceUnit[]>([]);
  const [evidenceUnits, setEvidenceUnits] = useState<EvidenceGapUnit[]>([]);
  const [decisionLoading, setDecisionLoading] = useState(true);
  const [decisionError, setDecisionError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetch(publicUrl("data/timeseries.json")).then((r) => {
        if (!r.ok) throw new Error("ts");
        return r.json();
      }),
      fetch(publicUrl("data/latest_alerts.geojson")).then((r) => {
        if (!r.ok) throw new Error("alerts");
        return r.json();
      }),
      fetch(publicUrl("data/aou/aou_registry.geojson"))
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null),
      fetch(publicUrl("data/aou/aou_observations.json"))
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null),
    ])
      .then(([timeseries, geo, registry, observations]) => {
        if (cancelled) return;
        setTs(timeseries);
        setAlerts(geo);
        const feats = (registry?.features || []) as AouFeature[];
        setAouRegistry(feats);
        setAouObs((observations?.units || []) as AouObsUnit[]);
        if (feats.length && !selectedAou) {
          setSelectedAou(feats[0].properties.aou_id);
        }
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    let cancelled = false;
    setDecisionLoading(true);
    Promise.all([
      fetch(publicUrl("data/decision/aou_suitability_components.json")).then((r) => {
        if (!r.ok) throw new Error("suitability");
        return r.json();
      }),
      fetch(publicUrl("data/decision/aou_confidence.json")).then((r) => {
        if (!r.ok) throw new Error("confidence");
        return r.json();
      }),
      fetch(publicUrl("data/decision/aou_evidence_gaps.json")).then((r) => {
        if (!r.ok) throw new Error("gaps");
        return r.json();
      }),
    ])
      .then(([suitability, confidence, gaps]) => {
        if (cancelled) return;
        setSuitabilityUnits((suitability?.units || []) as SuitabilityUnit[]);
        setConfidenceUnits((confidence?.units || []) as ConfidenceUnit[]);
        setEvidenceUnits((gaps?.units || []) as EvidenceGapUnit[]);
        setDecisionError(false);
      })
      .catch(() => {
        if (!cancelled) setDecisionError(true);
      })
      .finally(() => {
        if (!cancelled) setDecisionLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const latest = useMemo(() => {
    if (!ts?.dates?.length) return null;
    return [...ts.dates].sort((a, b) => a.date.localeCompare(b.date)).at(-1) ?? null;
  }, [ts]);

  const primarySource = useMemo(() => {
    const sample = alerts?.features?.find((f) => f.properties?.product_id)?.properties;
    return {
      source: alerts?.properties?.source || latest?.source || ts?.source,
      date: alerts?.properties?.date || latest?.date || sample?.date,
      product_id: latest?.product_id || sample?.product_id,
      tile: latest?.tile || sample?.tile,
      cloud_cover: latest?.cloud_cover ?? sample?.cloud_cover,
      citation: latest?.citation || ts?.citation,
    };
  }, [alerts, latest, ts]);

  const counts = alerts?.properties?.alert_counts || latest?.alert_counts || {};

  const windowNdvi = useMemo(() => {
    if (!ts?.dates?.length) return [];
    return [...ts.dates]
      .sort((a, b) => a.date.localeCompare(b.date))
      .map((p) => ({ date: p.date, value: p.ndvi.mean }));
  }, [ts]);

  const windowNdmi = useMemo(() => {
    if (!ts?.dates?.length) return [];
    return [...ts.dates]
      .sort((a, b) => a.date.localeCompare(b.date))
      .map((p) => ({ date: p.date, value: p.ndmi.mean }));
  }, [ts]);

  const selectedUnit = useMemo(
    () => aouObs.find((u) => u.aou_id === selectedAou) || null,
    [aouObs, selectedAou],
  );
  const selectedFeat = useMemo(
    () => aouRegistry.find((f) => f.properties.aou_id === selectedAou) || null,
    [aouRegistry, selectedAou],
  );

  const selectedSuitability = useMemo(
    () => suitabilityUnits.find((u) => u.aou_id === selectedAou) || null,
    [suitabilityUnits, selectedAou],
  );
  const selectedConfidence = useMemo(
    () => confidenceUnits.find((u) => u.aou_id === selectedAou) || null,
    [confidenceUnits, selectedAou],
  );
  const selectedEvidence = useMemo(
    () => evidenceUnits.find((u) => u.aou_id === selectedAou) || null,
    [evidenceUnits, selectedAou],
  );

  const decisionAouIds = useMemo(() => {
    const ids = new Set<string>();
    suitabilityUnits.forEach((u) => ids.add(u.aou_id));
    confidenceUnits.forEach((u) => ids.add(u.aou_id));
    // Prefer registry order for Najd AOUs when available
    const fromRegistry = aouRegistry
      .map((f) => f.properties.aou_id)
      .filter((id) => ids.has(id));
    if (fromRegistry.length) return fromRegistry;
    return [...ids].sort();
  }, [suitabilityUnits, confidenceUnits, aouRegistry]);

  const aouNdviSeries = useMemo(() => {
    if (!selectedUnit) return [];
    const obs = selectedUnit.observations
      .filter((o) => o.date && o.ndvi != null)
      .map((o) => ({ date: o.date as string, value: o.ndvi as number }));
    if (obs.length) return obs;
    // Honest stub: window series when AOU multi-date not yet available
    return (selectedUnit.window_context_series || [])
      .filter((o) => o.date && o.ndvi != null)
      .map((o) => ({ date: o.date as string, value: o.ndvi as number }));
  }, [selectedUnit]);

  const aouNdmiSeries = useMemo(() => {
    if (!selectedUnit) return [];
    const obs = selectedUnit.observations
      .filter((o) => o.date && o.ndmi != null)
      .map((o) => ({ date: o.date as string, value: o.ndmi as number }));
    if (obs.length > 1) return obs;
    return (selectedUnit.window_context_series || [])
      .filter((o) => o.date && o.ndmi != null)
      .map((o) => ({ date: o.date as string, value: o.ndmi as number }));
  }, [selectedUnit]);

  const aouSeriesIsWindowStub =
    !!selectedUnit && selectedUnit.observations.length <= 1 && aouNdviSeries.length > 0;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-sand-900">{t("analysis.title")}</h1>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-sand-800/90">{t("analysis.blurb")}</p>
      </div>

      <div className="flex flex-wrap gap-2" role="tablist" aria-label={t("analysis.levelsLabel")}>
        {LEVELS.map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={level === key}
            onClick={() => setLevel(key)}
            className={`rounded-full border px-3 py-1.5 text-sm font-semibold transition ${
              level === key
                ? "border-crop-700 bg-crop-700 text-white"
                : "border-sand-300 bg-white text-sand-800 hover:bg-sand-100"
            }`}
          >
            {t(`analysis.levels.${key}`)}
          </button>
        ))}
      </div>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold text-crop-700">{t("live.liveTitle")}</h2>
          <span className="rounded-full border border-amber-300 bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-950">
            {t("provisional.badge")}
          </span>
          <AouOfflineBadge showHelper={false} />
          <NajdSeasonalChip compact />
        </div>
        <p className="text-sm text-sand-800/90">{t("live.liveBlurb")}</p>
        <p className="text-xs text-amber-950/90">{t("map.aouNotByStac")}</p>
        <p className="text-xs text-sand-800/60">{t("provisional.aou")}</p>
        <p className="text-xs text-sand-800/70">{t("analysis.formulaRef")}</p>
        <NajdSeasonalChip />
        {error && <p className="text-sm text-red-700">{t("live.error")}</p>}
        {!ts && !error && <p className="text-sm text-sand-800/70">{t("live.loading")}</p>}
        <SourceCitation info={primarySource} />
        <p className="text-xs text-sand-800/60">{t("live.note")}</p>
      </section>

      {level === "overview" && (
        <>
          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-crop-700">{t("analysis.overviewTitle")}</h2>
            <p className="text-sm text-sand-800/90">{t("analysis.overviewBlurb")}</p>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {COUNT_KEYS.map((k) => (
                <div key={k} className="rounded-2xl border border-sand-200 bg-white p-4 shadow-sm">
                  <div className="mb-1 flex items-center gap-2 text-sm font-semibold">
                    <span className="h-3 w-3 rounded-sm" style={{ background: COUNT_COLORS[k] }} />
                    {t(`live.${k}`)}
                  </div>
                  <div className="text-2xl font-bold text-sand-900">{counts[k] ?? "—"}</div>
                  <div className="text-xs text-sand-800/50">{t("live.cells")}</div>
                </div>
              ))}
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-sand-200 bg-white p-4 shadow-sm">
                <div className="text-xs font-semibold uppercase text-sand-800/50">{t("analysis.aouCount")}</div>
                <div className="text-2xl font-bold">{alerts?.properties?.aou_count ?? aouRegistry.length}</div>
              </div>
              <div className="rounded-2xl border border-sand-200 bg-white p-4 shadow-sm">
                <div className="text-xs font-semibold uppercase text-sand-800/50">{t("analysis.bioticCount")}</div>
                <div className="text-2xl font-bold">{alerts?.properties?.possible_biotic_stress_count ?? 0}</div>
                <div className="text-xs text-sand-800/50">{t("analysis.bioticRiskOnly")}</div>
              </div>
              <div className="rounded-2xl border border-sand-200 bg-white p-4 shadow-sm">
                <div className="text-xs font-semibold uppercase text-sand-800/50">{t("analysis.latestDate")}</div>
                <div className="text-2xl font-bold">{alerts?.properties?.date || latest?.date || "—"}</div>
              </div>
            </div>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-crop-700">{t("analysis.indicesTitle")}</h2>
            <div className="grid gap-3 md:grid-cols-4">
              {[
                ["ndviName", "ndviFormula", "ndviDesc"],
                ["ndmiName", "ndmiFormula", "ndmiDesc"],
                ["ndreName", "ndreFormula", "ndreDesc"],
                ["saviName", "saviFormula", "saviDesc"],
              ].map(([name, formula, desc]) => (
                <div key={name} className="rounded-2xl border border-sand-200 bg-white p-4 shadow-sm">
                  <h3 className="font-semibold text-sand-900">{t(`analysis.${name}`)}</h3>
                  <code className="mt-2 block rounded-lg bg-sand-100 px-2 py-1 text-xs">{t(`analysis.${formula}`)}</code>
                  <p className="mt-2 text-sm text-sand-800/90">{t(`analysis.${desc}`)}</p>
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      {level === "spatial" && (
        <>
          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-crop-700">{t("analysis.spatialTitle")}</h2>
            <p className="text-sm text-sand-800/90">{t("analysis.spatialBlurb")}</p>
            <AlertMap heightClass="h-[26rem]" />
          </section>
          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-crop-700">{t("analysis.aouListTitle")}</h2>
            <p className="text-xs text-sand-800/70">{t("aou.notOfficialFarm")}</p>
            <div className="overflow-x-auto rounded-2xl border border-sand-200 bg-white shadow-sm">
              <table className="min-w-full text-left text-xs">
                <thead className="text-sand-800/60">
                  <tr>
                    <th className="px-3 py-2">{t("analysis.colAou")}</th>
                    <th className="px-3 py-2">{t("analysis.colAgProb")}</th>
                    <th className="px-3 py-2">{t("analysis.colAgClass")}</th>
                    <th className="px-3 py-2">{t("analysis.colArea")}</th>
                    <th className="px-3 py-2">NDVI</th>
                    <th className="px-3 py-2">NDMI</th>
                  </tr>
                </thead>
                <tbody>
                  {aouRegistry.map((f) => (
                    <tr
                      key={f.properties.aou_id}
                      className={`cursor-pointer border-t border-sand-100 hover:bg-sand-50 ${
                        selectedAou === f.properties.aou_id ? "bg-crop-50" : ""
                      }`}
                      onClick={() => {
                        setSelectedAou(f.properties.aou_id);
                        setLevel("temporal");
                      }}
                    >
                      <td className="px-3 py-2 font-mono font-semibold text-crop-700">{f.properties.aou_id}</td>
                      <td className="px-3 py-2">{f.properties.agricultural_probability ?? "—"}</td>
                      <td className="px-3 py-2">{f.properties.ag_class ?? "—"}</td>
                      <td className="px-3 py-2">{f.properties.area_ha_est ?? "—"}</td>
                      <td className="px-3 py-2">{f.properties.ndvi ?? "—"}</td>
                      <td className="px-3 py-2">{f.properties.ndmi ?? "—"}</td>
                    </tr>
                  ))}
                  {!aouRegistry.length && (
                    <tr>
                      <td className="px-3 py-4 text-sand-800/60" colSpan={6}>
                        {t("analysis.noAouYet")}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}

      {level === "temporal" && (
        <>
          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-crop-700">{t("analysis.temporalTitle")}</h2>
            <p className="text-sm text-sand-800/90">{t("analysis.temporalBlurb")}</p>
            <div className="flex flex-wrap items-center gap-2">
              <label className="text-sm font-semibold" htmlFor="aou-select">
                {t("analysis.selectAou")}
              </label>
              <select
                id="aou-select"
                className="rounded-lg border border-sand-300 bg-white px-3 py-1.5 text-sm"
                value={selectedAou}
                onChange={(e) => setSelectedAou(e.target.value)}
              >
                {aouRegistry.map((f) => (
                  <option key={f.properties.aou_id} value={f.properties.aou_id}>
                    {f.properties.aou_id}
                  </option>
                ))}
              </select>
            </div>
            {aouSeriesIsWindowStub && (
              <p className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-950">
                {t("analysis.aouSeriesStub")}
              </p>
            )}
            <div className="grid gap-3 lg:grid-cols-2">
              <SeriesChart
                title={`${t("live.ndviMean")} — ${selectedAou || t("analysis.windowScope")}`}
                color="#2f6b3a"
                points={aouNdviSeries.length ? aouNdviSeries : windowNdvi}
              />
              <SeriesChart
                title={`${t("live.ndmiMean")} — ${selectedAou || t("analysis.windowScope")}`}
                color="#0284c7"
                points={aouNdmiSeries.length ? aouNdmiSeries : windowNdmi}
              />
            </div>
            <p className="text-xs text-sand-800/60">{t("analysis.splitChartsNote")}</p>
            {selectedFeat?.properties?.ndre_available === false && (
              <p className="text-xs text-sand-800/70">{t("analysis.ndreUnavailable")}</p>
            )}
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-crop-700">{t("live.timeseries")}</h2>
            <p className="text-sm text-sand-800/90">{t("live.timeseriesBlurb")}</p>
            <div className="grid gap-3 lg:grid-cols-2">
              <SeriesChart title={t("analysis.windowNdvi")} color="#2f6b3a" points={windowNdvi} caption={t("analysis.windowScope")} />
              <SeriesChart title={t("analysis.windowNdmi")} color="#0284c7" points={windowNdmi} caption={t("analysis.windowScope")} />
            </div>
            {ts?.dates && (
              <div className="overflow-x-auto rounded-2xl border border-sand-200 bg-white p-4 shadow-sm">
                <table className="min-w-full text-left text-xs">
                  <thead className="text-sand-800/60">
                    <tr>
                      <th className="py-1 pe-3">{t("live.date")}</th>
                      <th className="py-1 pe-3">{t("live.tile")}</th>
                      <th className="py-1 pe-3">{t("live.ndviMean")}</th>
                      <th className="py-1 pe-3">{t("live.ndmiMean")}</th>
                      <th className="py-1 pe-3">{t("live.water_attention")}</th>
                      <th className="py-1 pe-3">{t("live.vigor_attention")}</th>
                      <th className="py-1">{t("live.productId")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...ts.dates]
                      .sort((a, b) => a.date.localeCompare(b.date))
                      .map((p) => (
                        <tr key={p.product_id} className="border-t border-sand-100">
                          <td className="py-1.5 pe-3">{p.date}</td>
                          <td className="py-1.5 pe-3">{p.tile}</td>
                          <td className="py-1.5 pe-3">{p.ndvi.mean.toFixed(3)}</td>
                          <td className="py-1.5 pe-3">{p.ndmi.mean.toFixed(3)}</td>
                          <td className="py-1.5 pe-3">{p.alert_counts?.water_attention ?? 0}</td>
                          <td className="py-1.5 pe-3">{p.alert_counts?.vigor_attention ?? 0}</td>
                          <td className="max-w-[14rem] truncate py-1.5 font-mono" title={p.product_id}>
                            {p.product_id}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}

      {level === "decision" && (
        <>
          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-crop-700">{t("analysis.decision.title")}</h2>
            <div className="flex flex-wrap items-center gap-2">
              <label className="text-sm font-semibold" htmlFor="aou-select-decision">
                {t("analysis.decision.selectAou")}
              </label>
              <select
                id="aou-select-decision"
                className="rounded-lg border border-sand-300 bg-white px-3 py-1.5 text-sm"
                value={selectedAou}
                onChange={(e) => setSelectedAou(e.target.value)}
              >
                {(decisionAouIds.length ? decisionAouIds : aouRegistry.map((f) => f.properties.aou_id)).map(
                  (id) => (
                    <option key={id} value={id}>
                      {id}
                    </option>
                  ),
                )}
              </select>
              <span className="rounded-full border border-amber-300 bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-950">
                {t("analysis.decision.provisionalStamp")}
              </span>
            </div>
            {decisionError && (
              <p className="text-sm text-red-700">{t("live.error")}</p>
            )}
            <DecisionChrome
              aouId={selectedAou}
              suitability={selectedSuitability}
              confidence={selectedConfidence}
              evidence={selectedEvidence}
              loading={decisionLoading}
            />
          </section>
        </>
      )}
    </div>
  );
}
