import { MapContainer, TileLayer, Rectangle, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import hubsData from "../data/hubs.json";
import { useTranslation } from "react-i18next";

const icon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

export default function MapView() {
  const { i18n } = useTranslation();
  const { bbox, hubs } = hubsData;
  const bounds: [[number, number], [number, number]] = [
    [bbox.south, bbox.west],
    [bbox.north, bbox.east],
  ];

  return (
    <div className="h-[28rem] w-full overflow-hidden rounded-2xl border border-sand-200 shadow-sm">
      <MapContainer center={bbox.center as [number, number]} zoom={8} scrollWheelZoom={false}>
        <TileLayer
          attribution='&copy; OpenStreetMap'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Rectangle bounds={bounds} pathOptions={{ color: "#2f6b3a", weight: 2, fillOpacity: 0.08 }} />
        {hubs.map((h) => (
          <Marker key={h.id} position={[h.lat, h.lon]} icon={icon}>
            <Popup>{i18n.language === "ar" ? h.name_ar : h.name_en}</Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
