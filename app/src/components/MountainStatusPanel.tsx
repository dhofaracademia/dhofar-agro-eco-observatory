import { useTranslation } from "react-i18next";
import SeedCatalogPanel from "./SeedCatalogPanel";

export default function MountainStatusPanel() {
  const { t } = useTranslation();
  return (
    <div className="space-y-3">
      <div className="rounded-2xl border border-amber-400 bg-amber-50 p-4 text-sm text-amber-950">
        <p className="font-semibold">{t("mountainStatus.banner")}</p>
        <p className="mt-2 text-xs">{t("mountainStatus.bannerHelp")}</p>
        <div className="mt-3 flex flex-wrap gap-2 text-[10px] font-semibold uppercase tracking-wide">
          <span className="rounded-full border border-amber-400 bg-white px-2 py-0.5">
            {t("mountainStatus.productKind")}
          </span>
          <span className="rounded-full border border-amber-400 bg-white px-2 py-0.5">
            {t("mountainStatus.timingDeferred")}
          </span>
          <span className="rounded-full border border-sand-400 bg-white px-2 py-0.5 text-sand-900">
            {t("mountainStatus.seedingHold")}
          </span>
        </div>
      </div>
      <p className="text-xs text-sand-800/70">{t("mountainStatus.noPlantHere")}</p>
      <SeedCatalogPanel domain="fog_escarpment" />
    </div>
  );
}
