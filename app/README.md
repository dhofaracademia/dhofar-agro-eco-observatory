# Najd Planting Monitor / رصد زراعة نجد

Bilingual (Arabic + English) MVP for public satellite browse imagery of irrigated desert farms in Najd, Dhofar, Oman.

## Run

```bash
# install deps, then:
#   package-manager install
#   package-manager run dev
```

Usually serves at http://localhost:5173. Language switch: **EN | ع**.

## Build

```bash
# package-manager run build
# package-manager run preview
```

## Stack

Vite · React · TypeScript · Tailwind · react-i18next · React Router · Leaflet

## Notes

- Images in `public/previews/` are browse previews, not full radiometric COGs.
- Full Sentinel-2 COG analysis comes later.
