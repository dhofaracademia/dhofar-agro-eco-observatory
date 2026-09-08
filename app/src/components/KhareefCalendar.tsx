import { useTranslation } from "react-i18next";

const STAGES = [
  "pre",
  "onset",
  "peak",
  "weakening",
  "end",
  "post",
] as const;

/** Visual-only Khareef stage strip for MVP (not driven by live climate data). */
export default function KhareefCalendar({ active = "peak" }: { active?: (typeof STAGES)[number] }) {
  const { t } = useTranslation();

  return (
    <section className="rounded-2xl border border-sand-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-crop-700">{t("khareef.title")}</h2>
        <p className="text-xs text-sand-800/60">{t("khareef.note")}</p>
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
        {STAGES.map((s) => {
          const isActive = s === active;
          return (
            <div
              key={s}
              className={`rounded-xl border px-3 py-2 text-center text-xs font-medium ${
                isActive
                  ? "border-crop-600 bg-crop-600/10 text-crop-700 ring-1 ring-crop-600/40"
                  : "border-sand-200 bg-sand-50 text-sand-800/80"
              }`}
            >
              <div className="font-semibold">{t(`khareef.stages.${s}`)}</div>
              <div className="mt-0.5 text-[10px] font-normal text-sand-800/50">
                {t(`khareef.hints.${s}`)}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
