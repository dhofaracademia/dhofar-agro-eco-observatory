import { useTranslation } from "react-i18next";

export type SourceInfo = {
  source?: string;
  date?: string;
  product_id?: string;
  tile?: string;
  cloud_cover?: number;
  citation?: string;
};

export default function SourceCitation({ info, compact = false }: { info: SourceInfo | null | undefined; compact?: boolean }) {
  const { t } = useTranslation();
  if (!info) return null;
  const cloud =
    typeof info.cloud_cover === "number" ? `${info.cloud_cover.toFixed(2)}%` : null;

  if (compact) {
    return (
      <p className="text-xs text-sand-800/70">
        <span className="font-medium">{info.source ?? "Sentinel-2 L2A"}</span>
        {info.date ? ` · ${info.date}` : ""}
        {info.tile ? ` · ${info.tile}` : ""}
        {info.product_id ? ` · ${info.product_id}` : ""}
      </p>
    );
  }

  return (
    <div className="rounded-2xl border border-sand-200 bg-sand-100/60 p-4 text-sm text-sand-800/90">
      <div className="grid gap-2 sm:grid-cols-2">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">{t("live.source")}</div>
          <div>{info.source ?? "—"}</div>
        </div>
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">{t("live.date")}</div>
          <div>{info.date ?? "—"}</div>
        </div>
        <div className="sm:col-span-2">
          <div className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">{t("live.productId")}</div>
          <code className="break-all text-xs">{info.product_id ?? "—"}</code>
        </div>
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">{t("live.tile")}</div>
          <div>{info.tile ?? "—"}</div>
        </div>
        {cloud && (
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">{t("live.cloud")}</div>
            <div>{cloud}</div>
          </div>
        )}
      </div>
      {info.citation && (
        <p className="mt-3 border-t border-sand-200 pt-3 text-xs text-sand-800/60">
          <span className="font-semibold">{t("live.citation")}: </span>
          {info.citation}
        </p>
      )}
    </div>
  );
}
