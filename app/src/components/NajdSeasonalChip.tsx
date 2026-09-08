import { useTranslation } from "react-i18next";
import { isNajdBareOffSeason } from "../lib/dataStamp";

/**
 * Sep–Oct (Asia/Muscat): bare Najd cells are often expected off-season fallow.
 * Shows when Muscat month is 9 or 10; optional `always` for a persistent helper under the bare legend.
 */
export default function NajdSeasonalChip({
  always = false,
  compact = false,
}: {
  always?: boolean;
  compact?: boolean;
}) {
  const { t } = useTranslation();
  const inSeason = isNajdBareOffSeason();
  if (!always && !inSeason) return null;

  if (compact) {
    return (
      <span className="inline-flex max-w-full flex-wrap items-center break-words rounded-full border border-sky-300 bg-sky-50 px-2.5 py-1 text-xs font-semibold leading-snug text-sky-950">
        {t("map.najdOffSeasonChip")}
      </span>
    );
  }

  return (
    <div className="rounded-xl border border-sky-200 bg-sky-50/90 px-3 py-2 text-xs leading-snug text-sky-950">
      <div className="font-semibold">{t("map.najdOffSeasonChip")}</div>
      <p className="mt-0.5 text-sky-950/80">{t("map.najdOffSeasonHelper")}</p>
    </div>
  );
}
