/** Planetary Computer STAC search for observatory imagery refresh (browser-side). */
export type StacScene = {
  id: string;
  datetime: string | null;
  date: string | null;
  cloudCover: number | null;
  tile: string | null;
  collection: string;
  previewUrl: string | null;
  selfHref: string | null;
};

export type RefreshStatus = "idle" | "refreshing" | "updated" | "failed";

const STAC_SEARCH =
  (typeof import.meta !== "undefined" &&
    (import.meta as ImportMeta & { env?: Record<string, string> }).env?.VITE_STAC_SEARCH_URL) ||
  "https://planetarycomputer.microsoft.com/api/stac/v1/search";

/** Farm corridor AOI used across the observatory */
export const OBSERVATORY_BBOX = [53.4, 17.5, 54.3, 18.5] as const;

function previewForItem(id: string): string {
  const q = new URLSearchParams({
    collection: "sentinel-2-l2a",
    item: id,
    assets: "visual",
  });
  return `https://planetarycomputer.microsoft.com/api/data/v1/item/preview.png?${q.toString()}`;
}

export async function fetchLatestSentinel2Scenes(limit = 6): Promise<StacScene[]> {
  const end = new Date();
  const start = new Date(end.getTime() - 1000 * 60 * 60 * 24 * 60); // ~60 days
  const body = {
    collections: ["sentinel-2-l2a"],
    bbox: [...OBSERVATORY_BBOX],
    datetime: `${start.toISOString()}/${end.toISOString()}`,
    query: { "eo:cloud_cover": { lt: 30 } },
    limit,
    sortby: [{ field: "datetime", direction: "desc" }],
  };

  const res = await fetch(STAC_SEARCH, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/geo+json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`STAC search failed (${res.status})`);
  }
  const fc = (await res.json()) as {
    features?: Array<{
      id: string;
      collection?: string;
      properties?: Record<string, unknown>;
      links?: Array<{ rel?: string; href?: string }>;
      assets?: Record<string, { href?: string }>;
    }>;
  };
  const features = fc.features ?? [];
  return features.map((f) => {
    const props = f.properties ?? {};
    const dt = typeof props.datetime === "string" ? props.datetime : null;
    const cloud =
      typeof props["eo:cloud_cover"] === "number" ? (props["eo:cloud_cover"] as number) : null;
    const tile =
      typeof props["s2:mgrs_tile"] === "string" ? (props["s2:mgrs_tile"] as string) : null;
    const self =
      f.links?.find((l) => l.rel === "self")?.href ??
      f.assets?.rendered_preview?.href ??
      null;
    return {
      id: f.id,
      datetime: dt,
      date: dt ? dt.slice(0, 10) : null,
      cloudCover: cloud,
      tile,
      collection: f.collection ?? "sentinel-2-l2a",
      previewUrl: previewForItem(f.id),
      selfHref: self,
    };
  });
}
