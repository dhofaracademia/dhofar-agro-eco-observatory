import { useTranslation } from 'react-i18next';
import type { AouAlertProps } from '../lib/aou';

/** Display published provenance only. Never infer missing historical metadata. */
export default function AgEvidenceCard({ reading }: { reading: Partial<AouAlertProps> }) {
  const { t } = useTranslation();
  const score = reading.agricultural_probability;
  const rejected = reading.assessability === 'unassessable' || reading.observation_role === 'retained_last_good';
  const evidence = reading.ag_evidence;
  const current = !rejected && typeof score === 'number' && Number.isFinite(score);
  const usable = current && evidence?.version === 'activity_evidence_v2'
    && evidence.calibrated_probability === false && Math.abs(evidence.score - score) < 0.011;
  return (
    <section className="mt-4 rounded-xl border border-sand-200 bg-white p-4" aria-label={t('agEvidence.title')}>
      <h4 className="font-semibold text-crop-700">{t('agEvidence.title')}</h4>
      <p className="mt-2 text-sm">{t('agEvidence.meaning')}</p>
      <p className="mt-2 font-semibold">{current ? `${score.toFixed(1)} / 100` : t('agEvidence.unavailable')}</p>
      <p className="mt-1 text-sm">{t('agEvidence.landUse')}</p>
      {usable && evidence.correlated_floor_collapse && (
        <p className="mt-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-950" data-testid="correlated-floor-warning">
          {t('agEvidence.floor')}
        </p>
      )}
      {(reading.alert === 'water_attention' || reading.alert === 'vigor_attention') && (
        <p className="mt-3 text-sm">{t('agEvidence.stressNote')}</p>
      )}
      {!usable ? <p className="mt-3 text-sm text-sand-800/70">{t('agEvidence.legacy')}</p> : (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer font-semibold">{t('agEvidence.details')}</summary>
          <p className="mt-2">{t('agEvidence.correlated')}</p>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-start text-xs">
              <thead><tr>{['component', 'source', 'points'].map(key => <th className="p-2 text-start" key={key}>{t(`agEvidence.${key}`)}</th>)}</tr></thead>
              <tbody>{Object.entries(evidence.contributions_points).map(([key, value]) => (
                <tr className="border-t border-sand-100" key={key}>
                  <td className="p-2">{t(`agEvidence.components.${key}`, { defaultValue: key })}</td>
                  <td className="p-2">{t(`agEvidence.sources.${evidence.sources[key]}`, { defaultValue: t('agEvidence.unknown') })}</td>
                  <td className="p-2 font-mono">{Number.isFinite(value) ? value.toFixed(2) : '—'}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
          {evidence.swir_coverage && <p className="mt-2">{t('agEvidence.swirCoverage', {
            measured: evidence.swir_coverage.measured_members, total: evidence.swir_coverage.clear_members,
          })}</p>}
          <p className="mt-2">{t('agEvidence.defaultNote')}</p>
        </details>
      )}
    </section>
  );
}
