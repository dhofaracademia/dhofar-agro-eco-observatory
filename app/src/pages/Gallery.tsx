import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import scenes from "../data/scenes.json";
import { publicUrl } from "../lib/publicUrl";

type Scene = (typeof scenes)[number];

export default function Gallery() {
  const { t, i18n } = useTranslation();
  const [tile, setTile] = useState("all");
  const [season, setSeason] = useState("all");
  const [type, setType] = useState("all");
  const [active, setActive] = useState<Scene | null>(null);

  const tiles = useMemo(
    () => Array.from(new Set(scenes.map((s) => s.tile))).sort(),
    [],
  );

  const filtered = scenes.filter((s) => {
    if (tile !== "all" && s.tile !== tile) return false;
    if (season !== "all" && s.season !== season) return false;
    if (type !== "all" && s.type !== type) return false;
    return true;
  });

  const label = (s: Scene) => (i18n.language === "ar" ? s.label_ar : s.label_en);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-sand-900">{t("gallery.title")}</h1>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-sand-800/90">{t("gallery.blurb")}</p>
      </div>

      <div className="flex flex-wrap gap-2">
        <select className="rounded-full border border-sand-300 bg-white px-3 py-1.5 text-sm" value={tile} onChange={(e) => setTile(e.target.value)}>
          <option value="all">{t("gallery.allTiles")}</option>
          {tiles.map((x) => <option key={x} value={x}>{x}</option>)}
        </select>
        <select className="rounded-full border border-sand-300 bg-white px-3 py-1.5 text-sm" value={season} onChange={(e) => setSeason(e.target.value)}>
          <option value="all">{t("gallery.allSeasons")}</option>
          <option value="wheat">{t("gallery.wheat")}</option>
          <option value="offseason">{t("gallery.offseason")}</option>
        </select>
        <select className="rounded-full border border-sand-300 bg-white px-3 py-1.5 text-sm" value={type} onChange={(e) => setType(e.target.value)}>
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
              <img src={publicUrl(`previews/${s.file}`)} alt={label(s)} className="h-40 w-full object-cover" />
              <div className="space-y-1 p-3">
                <div className="text-sm font-semibold text-sand-900">{label(s)}</div>
                <div className="text-xs text-sand-800/60">{s.tile} · {s.date} · {s.type}</div>
              </div>
            </button>
          ))}
        </div>
      )}

      {active && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-sand-900/70 p-4" onClick={() => setActive(null)}>
          <div className="max-h-[90vh] w-full max-w-4xl overflow-auto rounded-2xl bg-white shadow-xl" onClick={(e) => e.stopPropagation()}>
            <img src={publicUrl(`previews/${active.file}`)} alt={label(active)} className="w-full object-contain" />
            <div className="flex flex-wrap items-center justify-between gap-3 p-4">
              <div>
                <div className="font-semibold">{label(active)}</div>
                <div className="text-xs text-sand-800/60">
                  {t("gallery.sensor")}: {active.tile} · {t("gallery.date")}: {active.date}
                </div>
              </div>
              <button type="button" className="rounded-full bg-crop-600 px-4 py-2 text-sm font-semibold text-white" onClick={() => setActive(null)}>
                {t("gallery.close")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
