import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetchAouOfflineStamp, formatStampLabel } from "../lib/dataStamp";

/**
 * AOU offline run badge + STAC-does-not-refresh helper.
 * Shared by Map (Path B) and Analysis for parity.
 */
export default function AouOfflineBadge({
  showHelper = true,
  className = "",
}: {
  showHelper?: boolean;
  className?: string;
}) {
  const { t, i18n } = useTranslation();
  const [aouIso, setAouIso] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchAouOfflineStamp().then((iso) => {
      if (!cancelled) setAouIso(iso);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const stampText = formatStampLabel(aouIso, i18n.language);

  return (
    <div className={`flex max-w-full flex-col gap-1 ${className}`}>
      <span
        className="inline-flex max-w-full flex-wrap items-center gap-x-1 break-words rounded-full border border-amber-400/80 bg-amber-100 px-2.5 py-1 text-xs font-semibold leading-snug text-amber-950 shadow-sm"
        title={t("map.aouOfflineBadge", { date: stampText })}
      >
        {t("map.aouOfflineBadge", { date: stampText })}
      </span>
      {showHelper && (
        <p className="max-w-prose text-xs leading-snug text-amber-950/90">{t("map.aouNotByStac")}</p>
      )}
    </div>
  );
}
