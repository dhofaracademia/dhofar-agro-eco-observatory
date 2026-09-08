import { useTranslation } from "react-i18next";
import type { ObservatoryMode } from "../lib/mode";

export default function ObservatoryModeToggle({
  mode,
  onChange,
}: {
  mode: ObservatoryMode;
  onChange: (m: ObservatoryMode) => void;
}) {
  const { t } = useTranslation();
  const btn = (m: ObservatoryMode, label: string) => (
    <button
      type="button"
      onClick={() => onChange(m)}
      className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
        mode === m
          ? "bg-crop-600 text-white shadow-sm"
          : "bg-white text-sand-800 hover:bg-sand-100 border border-sand-300"
      }`}
      aria-pressed={mode === m}
    >
      {label}
    </button>
  );

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">
        {t("mode.label")}
      </span>
      {btn("agricultural", t("mode.agricultural"))}
      {btn("restoration", t("mode.restoration"))}
    </div>
  );
}
