/**
 * Deterministic emerging-signal math (docs/PRD.md §7).
 *
 *   growth_rate = (current - previous) / max(previous, 1)
 *
 * A signal is emerging only when current volume clears `minVolume` AND
 * growth clears `minGrowth`. The LLM never decides these numbers — this
 * module is the single source of truth for the formula and is unit-tested.
 */
export interface GrowthThresholds {
  minVolume: number;
  minGrowth: number;
}

export interface GrowthResult {
  current: number;
  previous: number;
  growthRate: number;
  meetsVolumeThreshold: boolean;
  isEmerging: boolean;
}

export function computeGrowth(
  current: number,
  previous: number,
  thresholds: GrowthThresholds
): GrowthResult {
  if (current < 0 || previous < 0) {
    throw new RangeError("counts must be non-negative");
  }
  const growthRate = (current - previous) / Math.max(previous, 1);
  const meetsVolumeThreshold = current >= thresholds.minVolume;
  const isEmerging = meetsVolumeThreshold && growthRate >= thresholds.minGrowth;
  return { current, previous, growthRate, meetsVolumeThreshold, isEmerging };
}
