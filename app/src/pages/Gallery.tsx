import { useMemo, useState, useCallback, useEffect } from "react";
import { useTranslation } from "react-i18next";
import scenes from "../data/scenes.json";
import { publicUrl } from "../lib/publicUrl";
import {
  fetchLatestSentinel2Scenes,
  type RefreshStatus,
  type StacScene,
} from "../lib/stacRefresh";

type Scene = (typeof scenes)[number];

const LS_KEY = "observatory.stac.lastRefresh";

type StoredRefresh = {
  updatedAt: string;
  scenes: StacScene[];
};


type FarmMeta = {
  source?: string;
  last_updated?: string;
  generated_on?: string;
  dates?: Array<{ date?: string; product_id?: string; tile?: string; cloud_cover?: number }>;
};

function FarmArtifactsMeta({
  locale,
  missingLabel,
  lastUpdatedLabel,
}: {
  locale: string;
  missingLabel: string;
  lastUpdatedLabel: string;
}) {
  const [meta, setMeta] = useState<FarmMeta | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(publicUrl("data/timeseries.json"))
      .then((r) => {
        if (!r.ok) throw new Error("missing");
        return r.json();
      })
      .then((j: FarmMeta) => {
        if (!cancelled) setMeta(j);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (failed) return <p className="text-xs text-sand-800/70">{missingLabel}</p>;
  if (!meta) return <p className="text-xs text-sand-800/50">…</p>;

  const latest = [...(meta.dates ?? [])].sort((a, b) => (a.date ?? "").localeCompare(b.date ?? "")).at(-1);
  const stamp = meta.last_updated || meta.generated_on || null;
  let stampLabel = "—";
  if (stamp) {
    try {
      stampLabel = new Intl.DateTimeFormat(locale === "ar" ? "ar-OM" : "en-GB", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(stamp));
    } catch {
      stampLabel = stamp;
    }
  }

  return (
    <div className="space-y-1 text-xs text-sand-800/80">
      <div>
        <span className="font-semibold">{lastUpdatedLabel}: </span>
        {stampLabel}
      </div>
      {meta.source && <div>{meta.source}</div>}
      {latest && (
        <div className="font-mono break-all">
          {latest.date} · {latest.tile} · cloud {latest.cloud_cover ?? "—"}% · {latest.product_id}
        </div>
      )}
    </div>
  );
}

export default function Gallery() {
  const { t, i18n } = useTranslation();
  const [tile, setTile] = useState("all");
  const [season, setSeason] = useState("all");
  const [type, setType] = useState("all");
  const [active, setActive] = useState<Scene | null>(null);
  const [status, setStatus] = useState<RefreshStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [live, setLive] = useState<StacScene[]>([]);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as StoredRefresh;
      if (parsed?.scenes?.length) {
        setLive(parsed.scenes);
        setUpdatedAt(parsed.updatedAt);
        setStatus("updated");
      }
    } catch {
      /* ignore */
    }
  }, []);

  const tiles = useMemo(() => Array.from(new Set(scenes.map((s) => s.tile))).sort(), []);

  const filtered = scenes.filter((s) => {
    if (tile !== "all" && s.tile !== tile) return false;
    if (season !== "all" && s.season !== season) return false;
    if (type !== "all" && s.type !== type) return false;
    return true;
  });

  const label = (s: Scene) => (i18n.language === "ar" ? s.label_ar : s.label_en);

  const formatUpdated = (iso: string | null) => {
    if (!iso) return "—";
    try {
      return new Intl.DateTimeFormat(i18n.language === "ar" ? "ar-OM" : "en-GB", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(iso));
    } catch {
      return iso;
    }
  };

  const statusLabel =
    status === "refreshing"
      ? t("gallery.refreshing")
      : status === "updated"
        ? t("gallery.refreshOk")
        : status === "failed"
          ? t("gallery.refreshFail")
          : t("gallery.refreshIdle");

  const onRefresh = useCallback(async () => {
    setStatus("refreshing");
    setError(null);
    try {
      const items = await fetchLatestSentinel2Scenes(6);
      const now = new Date().toISOString();
      setLive(items);
      setUpdatedAt(now);
      setStatus("updated");
      localStorage.setItem(LS_KEY, JSON.stringify({ updatedAt: now, scenes: items }));
    } catch (e) {
      setStatus("failed");
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-sand-900">{t("gallery.title")}</h1>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-sand-800/90">{t("gallery.blurb")}</p>
      </div>

      <section className="space-y-3 rounded-2xl border border-sand-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-crop-600/10 px-2.5 py-1 text-xs font-semibold text-crop-700">
            {t("gallery.sourceBadgePc")}
          </span>
          <span className="rounded-full bg-sand-100 px-2.5 py-1 text-xs font-semibold text-sand-800">
            {t("gallery.sourceBadgeS2")}
          </span>
          <span className="rounded-full bg-sand-100 px-2.5 py-1 text-xs font-semibold text-sand-800">
            {t("gallery.sourceBadgeStac")}
          </span>
        </div>

        <aside className="rounded-xl border border-amber-200 bg-amber-50/80 p-3 text-xs text-sand-900/90 space-y-1">
          <div className="font-semibold text-earth-600">{t("honesty.title")}</div>
          <ul className="list-disc space-y-1 ps-4">
            <li>{t("honesty.cloud")}</li>
            <li>{t("honesty.proxy")}</li>
            <li>{t("honesty.pest")}</li>
            <li>{t("honesty.aou")}</li>
            <li>{t("honesty.stale")}</li>
            <li>{t("honesty.mountain")}</li>
          </ul>
        </aside>


        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="text-sm text-sand-800/80">
            <div>
              <span className="font-semibold">{t("gallery.lastUpdated")}: </span>
              {formatUpdated(updatedAt)}
            </div>
            <div className="text-xs">
              Status: <span className="font-medium">{statusLabel}</span>
              {error ? <span className="text-red-700"> — {error}</span> : null}
            </div>
          </div>
          <button
            type="button"
            onClick={() => void onRefresh()}
            disabled={status === "refreshing"}
            className="rounded-full bg-crop-600 px-5 py-2 text-sm font-semibold text-white hover:bg-crop-700 disabled:opacity-60"
          >
            {status === "refreshing" ? t("gallery.refreshing") : t("gallery.refresh")}
          </button>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-crop-700">{t("gallery.liveTitle")}</h2>
          <p className="text-sm text-sand-800/80">{t("gallery.liveBlurb")}</p>
        </div>

        {live.length === 0 ? (
          <p className="text-sm text-sand-800/70">{t("gallery.noLive")}</p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {live.map((s) => (
              <article
                key={s.id}
                className="overflow-hidden rounded-2xl border border-sand-200 bg-sand-50 text-start shadow-sm"
              >
                {s.previewUrl ? (
                  <img
                    src={s.previewUrl}
                    alt={s.id}
                    className="h-36 w-full object-cover bg-sand-200"
                    loading="lazy"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = "none";
                    }}
                  />
                ) : null}
                <div className="space-y-1 p-3 text-xs">
                  <div className="font-semibold text-sand-900">{s.date ?? "—"}</div>
                  <div>
                    {t("gallery.sensor")}: {s.tile ?? "—"} · {t("gallery.cloud")}:{" "}
                    {s.cloudCover != null ? `${s.cloudCover.toFixed(1)}%` : "—"}
                  </div>
                  <div className="break-all font-mono text-[10px] text-sand-800/70">
                    {t("gallery.productId")}: {s.id}
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}

        <p className="text-xs text-sand-800/60">{t("gallery.howRefresh")}</p>
      </section>

      
      <section className="space-y-2 rounded-2xl border border-sand-200 bg-sand-50 p-4 text-sm">
        <h2 className="text-lg font-semibold text-crop-700">{t("gallery.farmDataTitle")}</h2>
        <p className="text-sand-800/80">{t("gallery.farmDataBlurb")}</p>
        <FarmArtifactsMeta locale={i18n.language} missingLabel={t("gallery.farmDataMissing")} lastUpdatedLabel={t("gallery.lastUpdated")} />
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold text-crop-700">{t("gallery.staticNote")}</h2>
          <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-earth-600">
            {t("provisional.badge")}
          </span>
        </div>

        <div className="flex flex-wrap gap-2">
          <select
            className="rounded-full border border-sand-300 bg-white px-3 py-1.5 text-sm"
            value={tile}
            onChange={(e) => setTile(e.target.value)}
          >
            <option value="all">{t("gallery.allTiles")}</option>
            {tiles.map((x) => (
              <option key={x} value={x}>
                {x}
              </option>
            ))}
          </select>
          <select
            className="rounded-full border border-sand-300 bg-white px-3 py-1.5 text-sm"
            value={season}
            onChange={(e) => setSeason(e.target.value)}
          >
            <option value="all">{t("gallery.allSeasons")}</option>
            <option value="wheat">{t("gallery.wheat")}</option>
            <option value="offseason">{t("gallery.offseason")}</option>
          </select>
          <select
            className="rounded-full border border-sand-300 bg-white px-3 py-1.5 text-sm"
            value={type}
            onChange={(e) => setType(e.target.value)}
          >
            <option value="all">{t("gallery.allTypes")}</option>
            <option value="truecolor">{t("gallery.truecolor")}</option>
            <option value="ndvi">{t("gallery.ndvi")}</option>
          </select>
        </div>

        {filtered.length === 0 ? (
          <p className="text-sm text-sand-800/70">{t("gallery.empty")}</p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => setActive(s)}
                className="overflow-hidden rounded-2xl border border-sand-200 bg-white text-start shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
              >
                <img
                  src={publicUrl(`previews/${s.file}`)}
                  alt={label(s)}
                  className="h-40 w-full object-cover"
                />
                <div className="space-y-1 p-3">
                  <div className="text-sm font-semibold text-sand-900">{label(s)}</div>
                  <div className="text-xs text-sand-800/60">
                    {s.tile} · {s.date} · {s.type}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

      {active && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-sand-900/70 p-4"
          onClick={() => setActive(null)}
        >
          <div
            className="max-h-[90vh] w-full max-w-4xl overflow-auto rounded-2xl bg-white shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={publicUrl(`previews/${active.file}`)}
              alt={label(active)}
              className="w-full object-contain"
            />
            <div className="flex flex-wrap items-center justify-between gap-3 p-4">
              <div>
                <div className="font-semibold">{label(active)}</div>
                <div className="text-xs text-sand-800/60">
                  {t("gallery.sensor")}: {active.tile} · {t("gallery.date")}: {active.date}
                </div>
              </div>
              <button
                type="button"
                className="rounded-full bg-crop-600 px-4 py-2 text-sm font-semibold text-white"
                onClick={() => setActive(null)}
              >
                {t("gallery.close")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
