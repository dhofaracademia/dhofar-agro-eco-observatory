import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

export type SuitabilityUnit = {
  aou_id: string;
  suitability_domain?: string;
  status?: string;
  suitability_score?: number;
  suitability_summary_label?: string;
  suitability_components?: Record<string, number>;
  why_this_site?: {
    headline?: string;
    drivers?: string[];
    cautions?: string[];
    recommended_next_step?: string;
    action_ladder_suggestion?: string | null;
  };
  honesty_note_en?: string;
  honesty_note_ar?: string;
  suitability_neq_confidence_note_en?: string;
  suitability_neq_confidence_note_ar?: string;
  cite_slots?: { observation_date?: string; product_id?: string; formula_ref?: string };
};

export type ConfidenceUnit = {
  aou_id: string;
  confidence_domain?: string;
  status?: string;
  data_quality_confidence?: number;
  overall_confidence?: number;
  temporal_coverage_confidence?: number;
  spatial_clarity_confidence?: number;
  honesty_note_en?: string;
  honesty_note_ar?: string;
  never_merge_with_suitability?: boolean;
  not_ecological_certainty?: boolean;
};

export type EvidenceGap = {
  id: string;
  code: string;
  present: boolean;
  narrative_en: string;
  narrative_ar: string;
  severity?: string;
};

export type EvidenceGapUnit = {
  aou_id: string;
  status?: string;
  evidence_gaps?: EvidenceGap[];
  gap_count?: number;
  missing_input_codes?: string[];
  honesty_note_en?: string;
  honesty_note_ar?: string;
};

const ACTION_ENUM = [
  "field_irrigation_inspection",
  "field_vigor_inspection",
  "biotic_field_verification",
  "continue_monitoring",
  "defer_insufficient_evidence",
] as const;

const SEVERITY_STYLE: Record<string, string> = {
  blocking: "border-red-300 bg-red-50 text-red-950",
  caution: "border-amber-300 bg-amber-50 text-amber-950",
  info: "border-sand-200 bg-sand-50 text-sand-900",
};

function fmtScore(v: number | undefined | null, digits = 1): string {
  if (v == null || Number.isNaN(Number(v))) return "—";
  return Number(v).toFixed(digits);
}

export default function DecisionChrome({
  aouId,
  suitability,
  confidence,
  evidence,
  loading,
}: {
  aouId: string;
  suitability: SuitabilityUnit | null;
  confidence: ConfidenceUnit | null;
  evidence: EvidenceGapUnit | null;
  loading?: boolean;
}) {
  const { t, i18n } = useTranslation();
  const ar = i18n.language?.startsWith("ar");
  // Manual enum stub only — suggestion stays null; control stays disabled
  const [manualAction] = useState<string>("");

  const activeGaps = useMemo(
    () => (evidence?.evidence_gaps || []).filter((g) => g.present === false),
    [evidence],
  );

  const components = suitability?.suitability_components || {};
  const why = suitability?.why_this_site;
  // Alias: confidence_score label bound to overall_confidence
  const confidenceScore = confidence?.overall_confidence;
  const suggestion = why?.action_ladder_suggestion ?? null;

  if (loading) {
    return <p className="text-sm text-sand-800/70">{t("analysis.decision.loading")}</p>;
  }

  if (!suitability && !confidence && !evidence) {
    return <p className="text-sm text-sand-800/70">{t("analysis.decision.missing")}</p>;
  }

  const neqNote = ar
    ? suitability?.suitability_neq_confidence_note_ar || t("analysis.decision.suitabilityNeqConfidence")
    : suitability?.suitability_neq_confidence_note_en || t("analysis.decision.suitabilityNeqConfidence");

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
        <p className="font-semibold">{t("analysis.decision.honestyTitle")}</p>
        <p className="mt-1">{t("analysis.decision.honestyBody")}</p>
        <div className="mt-2 flex flex-wrap gap-2 text-xs font-semibold">
          <span className="rounded-full border border-amber-400 bg-white px-2 py-0.5">
            {t("analysis.decision.provisionalStamp")}
          </span>
          <span className="rounded-full border border-amber-400 bg-white px-2 py-0.5">
            {t("analysis.decision.offlineSnapshot")}
          </span>
          <span className="rounded-full border border-amber-400 bg-white px-2 py-0.5">
            {t("analysis.decision.aouNotFarm")}
          </span>
          <span className="rounded-full border border-amber-400 bg-white px-2 py-0.5">
            {t("analysis.decision.noMountain")}
          </span>
        </div>
      </div>

      <p className="rounded-lg border border-crop-600/20 bg-crop-600/5 px-3 py-2 text-xs font-semibold text-crop-800">
        {neqNote}
      </p>

      {/* Two separate score cards — never a merged bar */}
      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-2xl border border-crop-600/30 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">
              {t("analysis.decision.suitability")}
            </div>
            <span className="rounded-full border border-sand-300 bg-sand-50 px-2 py-0.5 text-[10px] font-semibold text-sand-800">
              {suitability?.suitability_domain || t("analysis.decision.suitabilityDomain")}
            </span>
            <span className="rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-950">
              {suitability?.status || t("analysis.decision.provisionalStamp")}
            </span>
          </div>
          <div className="mt-1 text-3xl font-bold text-crop-700">
            {fmtScore(suitability?.suitability_score)}
            <span className="ms-1 text-sm font-semibold text-sand-800/50">/100</span>
          </div>
          <p className="mt-1 text-xs text-sand-800/60">
            {suitability?.suitability_summary_label || t("analysis.decision.componentsOnly")}
          </p>
          <p className="mt-2 text-[11px] text-sand-800/50">AOU {aouId}</p>
        </div>

        <div className="rounded-2xl border border-sand-300 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">
              {t("analysis.decision.confidenceScore")}
            </div>
            <span className="rounded-full border border-sand-300 bg-sand-50 px-2 py-0.5 text-[10px] font-semibold text-sand-800">
              {confidence?.confidence_domain || t("analysis.decision.confidenceDomain")}
            </span>
            <span className="rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-950">
              {confidence?.status || t("analysis.decision.provisionalStamp")}
            </span>
          </div>
          <div className="mt-1 text-3xl font-bold text-sand-900">
            {fmtScore(confidenceScore)}
            <span className="ms-1 text-sm font-semibold text-sand-800/50">/100</span>
          </div>
          <p className="mt-1 text-xs text-sand-800/60">{t("analysis.decision.confidenceSeparate")}</p>
          {/* Tertiary input chip — ≠ overall Confidence */}
          <div className="mt-3 inline-flex flex-wrap items-center gap-2 rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs text-sky-950">
            <span className="font-semibold">{t("analysis.decision.dataQualityChip")}</span>
            <span className="font-mono font-bold">{fmtScore(confidence?.data_quality_confidence, 0)}%</span>
            <span className="text-[10px] opacity-80">{t("analysis.decision.dataQualityChipHint")}</span>
          </div>
        </div>
      </div>

      {/* Suitability components */}
      {Object.keys(components).length > 0 && (
        <section className="rounded-2xl border border-sand-200 bg-white p-4 shadow-sm">
          <h3 className="mb-2 text-sm font-semibold text-crop-700">
            {t("analysis.decision.suitabilityComponents")}
          </h3>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(components).map(([key, val]) => (
              <div key={key} className="rounded-lg border border-sand-100 bg-sand-50 px-3 py-2 text-xs">
                <div className="font-mono text-sand-800/60">{key}</div>
                <div className="text-base font-bold text-sand-900">{fmtScore(val, 3)}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Why this site */}
      <section className="rounded-2xl border border-sand-200 bg-white p-4 shadow-sm">
        <h3 className="mb-2 text-sm font-semibold text-crop-700">{t("analysis.decision.whyThisSite")}</h3>
        {why?.headline && (
          <p className="mb-3 text-sm leading-relaxed text-sand-900">{why.headline}</p>
        )}
        {!!why?.drivers?.length && (
          <div className="mb-3">
            <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-sand-800/50">
              {t("analysis.decision.drivers")}
            </h4>
            <ul className="list-disc space-y-1 ps-5 text-sm text-sand-800/90">
              {why.drivers.map((d) => (
                <li key={d}>{d}</li>
              ))}
            </ul>
          </div>
        )}
        {!!why?.cautions?.length && (
          <div>
            <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-sand-800/50">
              {t("analysis.decision.cautions")}
            </h4>
            <ul className="list-disc space-y-1 ps-5 text-sm text-amber-950/90">
              {why.cautions.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* Evidence gaps — active only (present=false) */}
      <section className="rounded-2xl border border-sand-200 bg-white p-4 shadow-sm">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-semibold text-crop-700">{t("analysis.decision.evidenceGaps")}</h3>
          <span className="rounded-full border border-sand-300 bg-sand-50 px-2 py-0.5 text-xs font-semibold">
            {t("analysis.decision.gapCount")}: {evidence?.gap_count ?? activeGaps.length}
          </span>
        </div>
        <ul className="space-y-2">
          {activeGaps.map((g) => {
            const narrative = ar ? g.narrative_ar : g.narrative_en;
            const sev = g.severity || "info";
            return (
              <li
                key={g.id || g.code}
                className={`rounded-xl border px-3 py-2 text-sm ${SEVERITY_STYLE[sev] || SEVERITY_STYLE.info}`}
              >
                <div className="flex flex-wrap items-center gap-2 text-xs font-semibold">
                  <span className="font-mono">
                    {t("analysis.decision.gapType")}: {g.code}
                  </span>
                  <span className="rounded-full border border-current/20 bg-white/60 px-2 py-0.5">
                    {t("analysis.decision.severity")}: {sev}
                  </span>
                </div>
                <p className="mt-1 text-sm leading-relaxed">{narrative}</p>
              </li>
            );
          })}
          {!activeGaps.length && (
            <li className="text-xs text-sand-800/60">—</li>
          )}
        </ul>
      </section>

      {/* Manual action ladder — suggestion null; select disabled */}
      <section className="rounded-2xl border border-dashed border-sand-300 bg-sand-50 p-4">
        <h3 className="mb-1 text-sm font-semibold text-sand-900">{t("analysis.decision.actionLadder")}</h3>
        <p className="mb-2 text-xs text-sand-800/70">{t("analysis.decision.noAutoAction")}</p>
        <p className="mb-3 text-xs text-sand-800/60">{t("analysis.decision.actionLadderHint")}</p>
        <label className="mb-1 block text-xs font-semibold text-sand-800/60" htmlFor="action-ladder-manual">
          {t("analysis.decision.actionLadder")}
        </label>
        <select
          id="action-ladder-manual"
          className="w-full max-w-md cursor-not-allowed rounded-lg border border-sand-300 bg-white px-3 py-2 text-sm opacity-70"
          value={manualAction}
          disabled
          aria-disabled="true"
          title={t("analysis.decision.noAutoAction")}
        >
          <option value="">{t("analysis.decision.actionNone")}</option>
          {ACTION_ENUM.map((key) => (
            <option key={key} value={key}>
              {t(`analysis.decision.actionLadderOptions.${key}`)}
            </option>
          ))}
        </select>
        <p className="mt-2 font-mono text-[11px] text-sand-800/50">
          action_ladder_suggestion: {suggestion === null || suggestion === undefined ? "null" : String(suggestion)}
        </p>
      </section>
    </div>
  );
}
