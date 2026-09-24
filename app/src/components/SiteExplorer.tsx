import { useEffect, useId, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { MapContainer, TileLayer, GeoJSON, CircleMarker, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import hubs from '../data/hubs.json';
import ReadingExplanation from './ReadingExplanation';
import { comparison, containsPoint, parseCoordinates, type Observation } from '../lib/siteInsights';
import type { AouFeature } from '../lib/aou';

const KEY = 'dhofar.saved-observation-units.v1';
type Unit = { aou_id: string; observations: Observation[] };
function MapFocus({ point, feature }: { point: [number, number] | null; feature?: AouFeature }) {
  const map = useMap();
  useEffect(() => {
    if (point) map.setView(point, 14);
    else if (feature) map.fitBounds(L.geoJSON(feature as never).getBounds(), { padding: [30, 30], maxZoom: 15 });
  }, [map, point, feature]);
  return null;
}
function PickPoint({ onPick }: { onPick: (p: [number, number]) => void }) {
  useMapEvents({ click: e => onPick([e.latlng.lat, e.latlng.lng]) });
  return null;
}

export default function SiteExplorer({ features, units, selectedId, onSelect }: {
  features: AouFeature[]; units: Unit[]; selectedId: string; onSelect: (id: string) => void;
}) {
  const { t, i18n } = useTranslation();
  const uid = useId();
  const [query, setQuery] = useState('');
  const [point, setPoint] = useState<[number, number] | null>(null);
  const [message, setMessage] = useState('');
  const [saved, setSaved] = useState<string[]>(() => {
    try { const ids: unknown = JSON.parse(localStorage.getItem(KEY) || '[]'); return Array.isArray(ids) ? ids.filter((id): id is string => typeof id === 'string' && /^AOU-NJ-\d{6}$/.test(id)).slice(0, 20) : []; }
    catch { return []; }
  });
  const feature = features.find(f => f.properties.aou_id === selectedId);
  const unit = units.find(u => u.aou_id === selectedId);
  const change = useMemo(() => comparison(unit?.observations || []), [unit]);
  const currentRejected = feature?.properties.assessability !== 'assessable' || feature?.properties.observation_role === 'retained_last_good';
  const reason = currentRejected ? 'quality' : change.reason;
  const label = (id: string) => t('explore.unit', { number: Number(id.split('-').at(-1)) });
  const choose = (id: string) => { onSelect(id); setPoint(null); setMessage(''); };
  const locate = (p: [number, number]) => {
    setPoint(p);
    const found = features.find(f => containsPoint(f.geometry, p[0], p[1]));
    onSelect(found?.properties.aou_id || '');
    setMessage(found ? 'covered' : 'outside');
  };
  const search = () => {
    const match = hubs.hubs.find(h => [h.name_ar, h.name_en, h.id].some(n => n.toLowerCase() === query.trim().toLowerCase()));
    const coords = match ? [match.lat, match.lon] as [number, number] : parseCoordinates(query);
    if (!coords) { onSelect(''); setPoint(null); setMessage('invalid'); return; }
    locate(coords);
  };
  const toggleSave = () => {
    if (!feature) return;
    const next = saved.includes(selectedId) ? saved.filter(id => id !== selectedId) : [...saved, selectedId].slice(-20);
    try { localStorage.setItem(KEY, JSON.stringify(next)); setSaved(next); setMessage('savedNotice'); }
    catch { setMessage('saveError'); }
  };
  const formatDate = (value?: string) => value ? new Intl.DateTimeFormat(i18n.language === 'ar' ? 'ar-OM' : 'en-GB', { dateStyle: 'medium', timeZone: 'Asia/Muscat' }).format(new Date(`${value.slice(0, 10)}T12:00:00Z`)) : t('simple.unavailable');
  const number = (value: number) => new Intl.NumberFormat(i18n.language === 'ar' ? 'ar-OM' : 'en-GB', { minimumFractionDigits: 3, maximumFractionDigits: 3, signDisplay: 'exceptZero' }).format(value);
  return (
    <section className="space-y-4 rounded-2xl border border-sand-200 bg-white p-4 sm:p-6" aria-labelledby={`${uid}-title`}>
      <h2 id={`${uid}-title`} className="text-xl font-bold text-crop-700">{t('explore.title')}</h2>
      <p className="text-sm leading-relaxed">{t('explore.intro', { count: features.length })}</p>
      <form onSubmit={e => { e.preventDefault(); search(); }} className="flex flex-wrap items-end gap-3">
        <div className="min-w-0 flex-1 basis-64">
          <label htmlFor={`${uid}-search`} className="block text-sm font-semibold">{t('explore.searchLabel')}</label>
          <input id={`${uid}-search`} list={`${uid}-places`} value={query} onChange={e => setQuery(e.target.value)} placeholder={t('explore.placeholder')} className="mt-2 w-full rounded-xl border border-sand-300 p-3" />
          <datalist id={`${uid}-places`}>{hubs.hubs.map(h => <option key={h.id} value={i18n.language === 'ar' ? h.name_ar : h.name_en} />)}</datalist>
        </div>
        <button className="rounded-full bg-crop-700 px-5 py-3 font-semibold text-white" type="submit">{t('explore.search')}</button>
      </form>
      <p className="text-xs text-sand-800/80">{t('explore.coordinatesHelp')}</p>
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-0 flex-1 basis-64"><label htmlFor={`${uid}-unit`} className="block text-sm font-semibold">{t('explore.choose')}</label>
          <select id={`${uid}-unit`} value={selectedId} onChange={e => choose(e.target.value)} className="mt-2 w-full rounded-xl border border-sand-300 p-3">
            <option value="">{t('explore.select')}</option>
            {features.map(f => <option key={f.properties.aou_id} value={f.properties.aou_id || ""}>{label(f.properties.aou_id!)} · {f.properties.aou_id}</option>)}
          </select>
        </div>
        {feature && <button type="button" aria-pressed={saved.includes(selectedId)} onClick={toggleSave} className="rounded-full border border-crop-700 px-5 py-3 text-sm font-semibold text-crop-700">{t(saved.includes(selectedId) ? 'explore.unsave' : 'explore.save')}</button>}
      </div>
      {saved.length > 0 && <div className="flex flex-wrap items-center gap-2"><span className="text-sm font-semibold">{t('explore.saved')}</span>{saved.map(id => features.some(f => f.properties.aou_id === id) ? <button key={id} type="button" onClick={() => choose(id)} className="rounded-full bg-sand-100 px-3 py-2 text-sm underline">{label(id)}</button> : <span key={id} className="text-xs">{label(id)} — {t('explore.missingSaved')} <button type="button" onClick={() => { const next = saved.filter(x => x !== id); try { localStorage.setItem(KEY, JSON.stringify(next)); setSaved(next); } catch { setMessage('saveError'); } }} className="underline">{t('explore.remove')}</button></span>)}</div>}
      {message && <p role="status" aria-live="polite" className="rounded-xl bg-sand-100 p-3 text-sm leading-relaxed">{t(`explore.${message}`)}</p>}
      <div className="h-72 overflow-hidden rounded-xl border border-sand-200 sm:h-96">
        <MapContainer center={[18.02, 53.84]} zoom={11} scrollWheelZoom={false}>
          <TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <MapFocus point={point} feature={feature} /><PickPoint onPick={locate} />
          <GeoJSON bubblingMouseEvents={false} key={selectedId || 'all'} data={{ type: 'FeatureCollection', features } as never}
            style={f => ({ color: f?.properties.aou_id === selectedId ? '#b45309' : '#2f6b3a', weight: 3, fillOpacity: 0.35 })}
            onEachFeature={(f, layer) => { layer.on('click', e => { L.DomEvent.stopPropagation(e); choose(f.properties.aou_id); }); }} />
          {point && <CircleMarker center={point} radius={7} pathOptions={{ color: '#1d4ed8', fillOpacity: 0.8 }} />}
        </MapContainer>
      </div>
      <p className="text-xs text-sand-800/80">{t('explore.mapHelp')}</p>
      {!feature ? <p className="rounded-xl bg-sand-50 p-4 text-sm">{t('explore.selectHint')}</p> : <article className="space-y-4" aria-live="polite">
        <h3 className="text-lg font-semibold">{label(selectedId)}</h3>
        <p className="text-sm">{t('simple.observed')}: <strong>{formatDate(feature.properties.date)}</strong></p>
        <ReadingExplanation reading={{ ...feature.properties, n_clear_dates: feature.properties.n_clear_dates ?? unit?.observations.length }} />
        <div className="rounded-xl border border-sand-200 p-4">
          <h4 className="font-semibold text-crop-700">{t('explore.changeTitle')}</h4>
          {reason ? <p className="mt-2 text-sm leading-relaxed">{t(`explore.comparison_${reason}`)}</p> : change.latest && change.previous && <>
            <p className="mt-2 text-sm">{t('explore.period', { from: formatDate(change.previous.date), to: formatDate(change.latest.date) })}</p>
            <div className="mt-3 overflow-x-auto"><table className="w-full text-start text-sm"><caption className="sr-only">{t('explore.changeTitle')}</caption><thead><tr>{['indicator', 'before', 'after', 'difference'].map(k => <th key={k} className="p-2 text-start">{t(`explore.${k}`)}</th>)}</tr></thead>
              <tbody>{(['ndvi', 'ndmi'] as const).map(key => <tr key={key} className="border-t border-sand-100"><th className="p-2 text-start font-medium">{t(`simple.terms.${key}.title`)}</th><td className="p-2">{change.previous![key]!.toFixed(3)}</td><td className="p-2">{change.latest![key]!.toFixed(3)}</td><td className="p-2" dir="ltr">{number(change[key]!)}</td></tr>)}</tbody></table></div>
            <p className="mt-3 text-sm leading-relaxed">{t('explore.descriptiveOnly')}</p>
          </>}
        </div>
        <details className="text-sm"><summary className="cursor-pointer font-semibold">{t('explore.evidence')}</summary><dl className="mt-3 grid gap-3 sm:grid-cols-2">
          <div><dt>{t('explore.clearArea')}</dt><dd>{typeof feature.properties.valid_area_fraction === 'number' ? `${Math.round(feature.properties.valid_area_fraction * 100)}%` : t('simple.unavailable')}</dd></div>
          <div><dt>{t('explore.observations')}</dt><dd>{feature.properties.n_clear_dates ?? t('simple.unavailable')}</dd></div>
          <div><dt>{t('live.source')}</dt><dd>Copernicus Sentinel-2 L2A / Microsoft Planetary Computer</dd></div>
          <div><dt>{t('explore.identifier')}</dt><dd>{selectedId}</dd></div>
        </dl><p className="mt-3 leading-relaxed">{t('explore.limits')}</p></details>
      </article>}
    </section>
  );
}
