import policy from '../data/qualityPolicy.json' with { type: 'json' };
export const MIN_VALID_PIXELS = policy.min_valid_pixels;
export type QualityInput = { cloud_cover?: number | null; pixel_count?: number | null; assessability?: string; observation_role?: string };
/** Heuristic image completeness, never probability of a correct diagnosis.
 * Zero means insufficient/unknown evidence. Scene clarity cannot replace local pixels.
 * Keep in sync with engines/data_quality.py through shared policy and parity tests.
 */
export function dataQualityConfidence(props: QualityInput): number {
  const cloud = props.cloud_cover, pixels = props.pixel_count;
  if (props.assessability === 'unassessable' || props.observation_role === 'retained_last_good') return 0;
  if (typeof pixels !== 'number' || !Number.isFinite(pixels) || !Number.isInteger(pixels) || pixels < MIN_VALID_PIXELS) return 0;
  if (typeof cloud !== 'number' || !Number.isFinite(cloud) || cloud < 0 || cloud > 100) return 0;
  const fraction = Math.min(1, pixels / policy.expected_pixels);
  if (fraction < policy.min_valid_fraction) return 0;
  const weighted = policy.scene_weight * Math.max(0, 100 - cloud * policy.cloud_penalty) + policy.pixel_weight * fraction * 100;
  return Math.round(Math.min(policy.max_score, weighted, fraction * 100) * 10) / 10;
}
