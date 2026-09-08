/** Shared AOU / farm-monitor offline stamp helpers (Map + Analysis + Imagery). */
import { publicUrl } from "./publicUrl";

/** i18n key: gallery STAC refresh does not update the AOU layer. */
export const AOU_NOT_BY_STAC = "map.aouNotByStac" as const;

/** Asia/Muscat — used for absolute stamps and Najd seasonal context. */
export const OBSERVATORY_TZ = "Asia/Muscat" as const;

export type FormattedStamp = {
  absolute: string;
  relative: string;
  /** Short zone hint, e.g. "Muscat" / "مسقط" */
  zoneLabel: string;
};

type StampDoc = {
  last_updated?: string;
  generated_on?: string;
  dates?: Array<{ date?: string }>;
};

function pickIso(doc: StampDoc | null | undefined): string | null {
  if (!doc) return null;
  if (typeof doc.last_updated === "string" && doc.last_updated.trim()) return doc.last_updated.trim();
  if (typeof doc.generated_on === "string" && doc.generated_on.trim()) return doc.generated_on.trim();
  const dates = (doc.dates ?? [])
    .map((d) => d?.date)
    .filter((d): d is string => typeof d === "string" && d.length > 0)
    .sort();
  return dates.at(-1) ?? null;
}

function relativeUnit(diffSec: number): { value: number; unit: Intl.RelativeTimeFormatUnit } {
  const abs = Math.abs(diffSec);
  if (abs < 60) return { value: Math.round(diffSec), unit: "second" };
  if (abs < 3600) return { value: Math.round(diffSec / 60), unit: "minute" };
  if (abs < 86400) return { value: Math.round(diffSec / 3600), unit: "hour" };
  if (abs < 86400 * 30) return { value: Math.round(diffSec / 86400), unit: "day" };
  if (abs < 86400 * 365) return { value: Math.round(diffSec / (86400 * 30)), unit: "month" };
  return { value: Math.round(diffSec / (86400 * 365)), unit: "year" };
}

/** Calendar month 1–12 in Asia/Muscat. */
export function muscatMonth(now: Date = new Date()): number {
  const raw = new Intl.DateTimeFormat("en-GB", {
    timeZone: OBSERVATORY_TZ,
    month: "numeric",
  }).format(now);
  return Number(raw);
}

/**
 * Najd irrigated wheat is typically off-season in Sep–Oct (Muscat).
 * Bare cells then are often expected fallow — not necessarily monitor failure.
 */
export function isNajdBareOffSeason(now: Date = new Date()): boolean {
  const m = muscatMonth(now);
  return m === 9 || m === 10;
}

/** Format an ISO (or date-only) stamp into absolute + relative phrases (Muscat TZ). */
export function formatStamp(iso: string | null | undefined, locale: string): FormattedStamp {
  const isAr = locale?.startsWith("ar");
  const loc = isAr ? "ar-OM" : "en-GB";
  const zoneLabel = isAr ? "مسقط" : "Muscat";
  if (!iso) return { absolute: "—", relative: "—", zoneLabel };

  let d: Date;
  try {
    // Date-only → treat as UTC noon to avoid off-by-one in local zones
    d = /^\d{4}-\d{2}-\d{2}$/.test(iso) ? new Date(`${iso}T12:00:00Z`) : new Date(iso);
    if (Number.isNaN(d.getTime())) return { absolute: iso, relative: iso, zoneLabel };
  } catch {
    return { absolute: iso, relative: iso, zoneLabel };
  }

  let absolute = iso;
  try {
    absolute = new Intl.DateTimeFormat(loc, {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: OBSERVATORY_TZ,
    }).format(d);
  } catch {
    absolute = iso;
  }

  let relative = absolute;
  try {
    const diffSec = (d.getTime() - Date.now()) / 1000;
    const { value, unit } = relativeUnit(diffSec);
    relative = new Intl.RelativeTimeFormat(loc, { numeric: "auto" }).format(value, unit);
  } catch {
    relative = absolute;
  }

  return { absolute, relative, zoneLabel };
}

/** Absolute + relative + short Muscat label for badges. */
export function formatStampLabel(iso: string | null | undefined, locale: string): string {
  if (!iso) return "—";
  const s = formatStamp(iso, locale);
  return `${s.absolute} ${s.zoneLabel} (${s.relative})`;
}

async function fetchJson(path: string): Promise<StampDoc | null> {
  try {
    const res = await fetch(publicUrl(path));
    if (!res.ok) return null;
    return (await res.json()) as StampDoc;
  } catch {
    return null;
  }
}

/**
 * Resolve the AOU / farm-monitor offline run stamp.
 * Prefers timeseries.json, then meta/last_refresh.json.
 */
export async function fetchAouOfflineStamp(): Promise<string | null> {
  const fromTs = pickIso(await fetchJson("data/timeseries.json"));
  if (fromTs) return fromTs;
  return pickIso(await fetchJson("data/meta/last_refresh.json"));
}
