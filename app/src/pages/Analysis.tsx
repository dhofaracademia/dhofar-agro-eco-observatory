import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import AlertMap from "../components/AlertMap";
import AouOfflineBadge from "../components/AouOfflineBadge";
import NajdSeasonalChip from "../components/NajdSeasonalChip";
import { publicUrl } from "../lib/publicUrl";
import SourceCitation from "../components/SourceCitation";

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
};

type AlertsMeta = {
  properties?: {
    source?: string;
    date?: string;
    alert_counts?: Record<string, number>;
    note?: string;
  };
  features?: { properties: { product_id?: string; tile?: string; cloud_cover?: number; date?: string; source?: string } }[];
};

const COUNT_KEYS = ["healthy", "water_attention", "vigor_attention", "bare", "unclear"] as const;
const COUNT_COLORS: Record<string, string> = {
  healthy: "#2f6b3a",
  water_attention: "#0284c7",
  vigor_attention: "#d97706",
  bare: "#d6c3a3",
  unclear: "#78716c",
};

export default function Analysis() {
  const { t } = useTranslation();
  const issues = t("analysis.issues", { returnObjects: true }) as { t: string; d: string }[];
  const [ts, setTs] = useState<Timeseries | null>(null);
  const [alerts, setAlerts] = useState<AlertsMeta | null>(null);
  const [error, setError] = useState(false);

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
    ])
      .then(([timeseries, geo]) => {
        if (!cancelled) {
          setTs(timeseries);
          setAlerts(geo);
        }
      })
      .catch(() => {
        if (!cancelled) setError(true);
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

  const chart = useMemo(() => {
    if (!ts?.dates?.length) return null;
    const points = [...ts.dates].sort((a, b) => a.date.localeCompare(b.date));
    const w = 560;
    const h = 160;
    const pad = 28;
    const ndviVals = points.map((p) => p.ndvi.mean);
    const ndmiVals = points.map((p) => p.ndmi.mean);
    const all = [...ndviVals, ...ndmiVals];
    const minY = Math.min(...all) - 0.02;
    const maxY = Math.max(...all) + 0.02;
    const x = (i: number) => pad + (i * (w - pad * 2)) / Math.max(points.length - 1, 1);
    const y = (v: number) => h - pad - ((v - minY) / (maxY - minY || 1)) * (h - pad * 2);
    const line = (vals: number[]) =>
      vals.map((v, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
    return { points, w, h, pad, lineNdvi: line(ndviVals), lineNdmi: line(ndmiVals), x, y };
  }, [ts]);

  const statuses = [
    { key: "established", color: "bg-crop-600" },
    { key: "sparse", color: "bg-amber-500" },
    { key: "irrigation", color: "bg-sky-600" },
    { key: "salinity", color: "bg-violet-600" },
    { key: "abandoned", color: "bg-stone-500" },
  ] as const;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-sand-900">{t("analysis.title")}</h1>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-sand-800/90">{t("analysis.blurb")}</p>
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
        <NajdSeasonalChip />
        {error && <p className="text-sm text-red-700">{t("live.error")}</p>}
        {!ts && !error && <p className="text-sm text-sand-800/70">{t("live.loading")}</p>}
        <SourceCitation info={primarySource} />
        <p className="text-xs text-sand-800/60">{t("live.note")}</p>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-crop-700">{t("live.alertCounts")}</h2>
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
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-crop-700">{t("live.timeseries")}</h2>
        <p className="text-sm text-sand-800/90">{t("live.timeseriesBlurb")}</p>
        {chart && (
          <div className="overflow-x-auto rounded-2xl border border-sand-200 bg-white p-4 shadow-sm">
            <svg viewBox={`0 0 ${chart.w} ${chart.h}`} className="h-44 w-full min-w-[20rem]">
              <path d={chart.lineNdvi} fill="none" stroke="#2f6b3a" strokeWidth="2.5" />
              <path d={chart.lineNdmi} fill="none" stroke="#0284c7" strokeWidth="2.5" />
              {chart.points.map((p, i) => (
                <g key={p.date}>
                  <circle cx={chart.x(i)} cy={chart.y(p.ndvi.mean)} r="3.5" fill="#2f6b3a" />
                  <circle cx={chart.x(i)} cy={chart.y(p.ndmi.mean)} r="3.5" fill="#0284c7" />
                  <text x={chart.x(i)} y={chart.h - 8} textAnchor="middle" className="fill-sand-800" style={{ fontSize: 10 }}>
                    {p.date.slice(5)}
                  </text>
                </g>
              ))}
            </svg>
            <div className="mt-2 flex flex-wrap gap-4 text-xs">
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2 w-4 rounded bg-crop-600" /> {t("live.ndviMean")}
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2 w-4 rounded bg-sky-600" /> {t("live.ndmiMean")}
              </span>
            </div>
            <div className="mt-4 overflow-x-auto">
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
                  {chart.points.map((p) => (
                    <tr key={p.product_id} className="border-t border-sand-100">
                      <td className="py-1.5 pe-3">{p.date}</td>
                      <td className="py-1.5 pe-3">{p.tile}</td>
                      <td className="py-1.5 pe-3">{p.ndvi.mean.toFixed(3)}</td>
                      <td className="py-1.5 pe-3">{p.ndmi.mean.toFixed(3)}</td>
                      <td className="py-1.5 pe-3">{p.alert_counts.water_attention ?? 0}</td>
                      <td className="py-1.5 pe-3">{p.alert_counts.vigor_attention ?? 0}</td>
                      <td className="max-w-[14rem] truncate py-1.5 font-mono" title={p.product_id}>
                        {p.product_id}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-crop-700">{t("live.attentionMap")}</h2>
        <AlertMap heightClass="h-[26rem]" />
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-crop-700">{t("analysis.indicesTitle")}</h2>
        <div className="grid gap-3 md:grid-cols-3">
          {[
            ["ndviName", "ndviFormula", "ndviDesc"],
            ["saviName", "saviFormula", "saviDesc"],
            ["ndmiName", "ndmiFormula", "ndmiDesc"],
          ].map(([name, formula, desc]) => (
            <div key={name} className="rounded-2xl border border-sand-200 bg-white p-4 shadow-sm">
              <h3 className="font-semibold text-sand-900">{t(`analysis.${name}`)}</h3>
              <code className="mt-2 block rounded-lg bg-sand-100 px-2 py-1 text-xs">{t(`analysis.${formula}`)}</code>
              <p className="mt-2 text-sm text-sand-800/90">{t(`analysis.${desc}`)}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-crop-700">{t("analysis.statusTitle")}</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {statuses.map(({ key, color }) => (
            <div key={key} className="rounded-2xl border border-sand-200 bg-white p-4 shadow-sm">
              <div className="mb-2 flex items-center gap-2">
                <span className={`h-3 w-3 rounded-full ${color}`} />
                <h3 className="font-semibold">{t(`analysis.${key}`)}</h3>
              </div>
              <p className="text-sm text-sand-800/90">{t(`analysis.${key}Desc`)}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-sand-200 bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-lg font-semibold text-crop-700">{t("analysis.issuesTitle")}</h2>
        <ul className="space-y-3">
          {Array.isArray(issues) &&
            issues.map((item) => (
              <li key={item.t} className="border-s-4 border-crop-600 ps-3">
                <div className="text-sm font-semibold">{item.t}</div>
                <div className="text-xs text-sand-800/80">{item.d}</div>
              </li>
            ))}
        </ul>
      </section>
    </div>
  );
}
