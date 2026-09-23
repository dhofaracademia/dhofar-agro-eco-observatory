import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { fetchReleaseData, getRelease } from '../lib/releaseData';
import { publicUrl } from '../lib/publicUrl';

type Status = { status?: string; last_checked_at?: string; schedule?: string };
type Stamp = { observation_date?: string; scene_capture_date?: string; last_updated?: string };
const states = new Set(['updated', 'no_new_scenes', 'no_scenes', 'no_new_clear_observation', 'failed']);

export default function ReadingStatus() {
  const { t, i18n } = useTranslation();
  const [stamp, setStamp] = useState<Stamp>({});
  const [status, setStatus] = useState<Status>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  const [newRelease, setNewRelease] = useState(false);
  const [checked, setChecked] = useState(false);
  const read = useCallback(async (signal?: AbortSignal) => {
    setBusy(true); setError(false);
    try {
      const [meta, monitor, pointer] = await Promise.all([
        fetchReleaseData('data/meta/run_meta.json').then(async (r) => {
          if (!r.ok) throw new Error('Missing metadata');
          return r.json() as Promise<Stamp>;
        }),
        fetch(publicUrl('data/meta/monitor_status.json'), { cache: 'no-store', signal }).then(async (r) => {
          if (r.status === 404 || r.ok && r.headers.get('content-type')?.includes('text/html')) return {} as Status;
          if (!r.ok) throw new Error('Status unavailable');
          return r.json() as Promise<Status>;
        }),
        fetch(publicUrl('data/latest_release.json'), { cache: 'no-store', signal }).then(async (r) => {
          if (r.status === 404 || r.ok && r.headers.get('content-type')?.includes('text/html')) return null;
          if (!r.ok) throw new Error('Manifest unavailable');
          return r.json() as Promise<{ release_id: string }>;
        }),
      ]);
      const pinned = await getRelease();
      if (signal?.aborted) return;
      setStamp(meta); setStatus(monitor); setChecked(true);
      setNewRelease(!!pointer && pointer.release_id !== pinned?.release_id);
    } catch {
      if (!signal?.aborted) setError(true);
    } finally {
      if (!signal?.aborted) setBusy(false);
    }
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    void read(controller.signal);
    return () => controller.abort();
  }, [read]);
  const date = (value?: string, time = false) => {
    if (!value) return t('simple.unavailable');
    const d = new Date(value.length === 10 ? `${value}T12:00:00Z` : value);
    if (Number.isNaN(d.getTime())) return t('simple.unavailable');
    return new Intl.DateTimeFormat(i18n.language === 'ar' ? 'ar-OM' : 'en-GB', {
      dateStyle: 'medium', ...(time ? { timeStyle: 'short' as const } : {}), timeZone: 'Asia/Muscat',
    }).format(d);
  };
  const obs = stamp.observation_date || stamp.scene_capture_date;
  const age = obs ? Math.floor((Date.now() - new Date(`${obs.slice(0, 10)}T00:00:00Z`).getTime()) / 86400000) : null;
  return (
    <section className="rounded-2xl border border-sand-200 bg-white p-4 sm:p-5" aria-label={t('simple.readingStatus')}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-semibold text-crop-700">{t('simple.readingStatus')}</h2>
        <button type="button" onClick={() => void read()} disabled={busy} className="rounded-full border border-crop-600 px-4 py-2 text-sm font-semibold text-crop-700 disabled:opacity-50">
          {busy ? t('simple.checking') : t('simple.checkPublished')}
        </button>
      </div>
      <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-3">
        {[[t('simple.observed'), date(obs)], [t('simple.processed'), date(stamp.last_updated, true)], [t('simple.checked'), date(status.last_checked_at, true)]].map(([label, value]) => (
          <div key={label}><dt className="text-sand-800/70">{label}</dt><dd className="mt-1 font-semibold">{value}</dd></div>
        ))}
      </dl>
      <p className="mt-3 text-sm" role="status" aria-live="polite">
        {error ? t('simple.statusError') : newRelease ? t('simple.newRelease') : checked ? t(`simple.statuses.${states.has(status.status || '') ? status.status : 'unconfigured'}`) : t('simple.checking')}
      </p>
      {newRelease && <button type="button" onClick={() => window.location.reload()} className="mt-2 rounded-full bg-crop-600 px-4 py-2 text-sm text-white">{t('simple.loadRelease')}</button>}
      {age != null && age > 0 && <p className="mt-2 text-sm text-sand-800">{t('simple.age', { count: age })}</p>}
      <details className="mt-3 text-sm">
        <summary className="cursor-pointer font-medium text-crop-700">{t('simple.howUpdates')}</summary>
        <p className="mt-2 leading-relaxed">{t('simple.updateExplanation')}</p>
        <p className="mt-2">{status.schedule === 'daily' ? t('simple.dailyConfirmed') : t('simple.scheduleUnconfirmed')}</p>
        <a className="mt-3 inline-block underline" href="https://github.com/dhofaracademia/dhofar-agro-eco-observatory/actions/workflows/monitor.yml" target="_blank" rel="noreferrer">{t('simple.adminRun')}</a>
        <p className="mt-1 text-xs text-sand-800/70">{t('simple.adminHint')}</p>
      </details>
    </section>
  );
}
