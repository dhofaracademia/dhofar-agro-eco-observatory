/** Resolve a path under Vite `base` (GitHub Pages project URL). */
export function publicUrl(path: string): string {
  const base = import.meta.env.BASE_URL || "/";
  const clean = path.replace(/^\//, "");
  return `${base}${clean}`;
}
