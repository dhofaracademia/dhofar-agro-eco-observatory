import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { publicUrl } from "../lib/publicUrl";

type SpeciesRow = {
  species_id: string;
  domain: string;
  accepted_name?: string;
  species_name_sci?: string;
  ar_name?: string;
  en_name?: string;
  timing_window?: string[];
  vetting_status?: string;
  score_status?: string;
  status?: string;
  suitability_provisional_0_100?: number | null;
  habitat?: string;
};

type Catalog = {
  vetting_status?: string;
  score_status?: string;
  honesty_note_en?: string;
  honesty_note_ar?: string;
  species?: SpeciesRow[];
};

export default function SeedCatalogPanel({ domain }: { domain: "najd_arid" | "fog_escarpment" }) {
  const { t, i18n } = useTranslation();
  const ar = i18n.language?.startsWith("ar");
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(publicUrl("data/seed/species_catalog.json"))
      .then((r) => {
        if (!r.ok) throw new Error("catalog");
        return r.json();
      })
      .then((j: Catalog) => {
        if (!cancelled) setCatalog(j);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const rows = useMemo(
    () => (catalog?.species || []).filter((s) => s.domain === domain),
    [catalog, domain],
  );

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-sm font-semibold text-crop-700">
          {domain === "najd_arid" ? t("seed.najdTitle") : t("seed.fogTitle")}
        </h3>
        <span className="rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-950">
          scientist_locked_pending_ea
        </span>
        <span className="rounded-full border border-sand-300 bg-sand-50 px-2 py-0.5 text-[10px] font-semibold text-sand-800">
          {t("seed.unvalidated")}
        </span>
      </div>
      <p className="text-xs text-sand-800/80">
        {domain === "najd_arid" ? t("seed.najdBlurb") : t("seed.fogListOnly")}
      </p>
      <p className="text-xs text-sand-800/60">
        {ar ? catalog?.honesty_note_ar : catalog?.honesty_note_en}
      </p>
      {error && <p className="text-sm text-red-700">{t("seed.error")}</p>}
      <div className="overflow-x-auto rounded-2xl border border-sand-200 bg-white shadow-sm">
        <table className="min-w-full text-left text-xs">
          <thead className="text-sand-800/60">
            <tr>
              <th className="px-3 py-2">{t("seed.colName")}</th>
              <th className="px-3 py-2">{t("seed.colSci")}</th>
              <th className="px-3 py-2">{t("seed.colTiming")}</th>
              <th className="px-3 py-2">{t("seed.colStatus")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.species_id} className="border-t border-sand-100">
                <td className="px-3 py-2 font-semibold text-sand-900">
                  {ar ? s.ar_name || s.en_name : s.en_name || s.ar_name}
                </td>
                <td className="px-3 py-2 italic">{s.accepted_name || s.species_name_sci}</td>
                <td className="px-3 py-2 font-mono">
                  {(s.timing_window || []).join(" · ") || "—"}
                </td>
                <td className="px-3 py-2">
                  {s.vetting_status || "scientist_locked_pending_ea"} · {s.score_status || "unvalidated"}
                  {s.suitability_provisional_0_100 == null ? (
                    <span className="ms-1 text-sand-800/50">{t("seed.noScore")}</span>
                  ) : null}
                </td>
              </tr>
            ))}
            {!rows.length && !error && (
              <tr>
                <td className="px-3 py-3 text-sand-800/60" colSpan={4}>
                  {t("seed.empty")}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
