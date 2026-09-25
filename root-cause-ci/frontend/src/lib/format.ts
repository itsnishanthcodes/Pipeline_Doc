export const shortSha = (sha?: string | null) => (sha ? sha.slice(0, 7) : '');

export const percent = (value?: number | null) =>
  value === undefined || value === null ? 'n/a' : `${Math.round(value * 100)}%`;

export function timeAgo(iso?: string | null): string {
  if (!iso) return '';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const seconds = Math.round((Date.now() - then) / 1000);
  if (seconds < 45) return 'just now';
  const units: [number, Intl.RelativeTimeFormatUnit][] = [
    [60, 'second'], [60, 'minute'], [24, 'hour'], [7, 'day'], [4.35, 'week'], [12, 'month'], [Infinity, 'year'],
  ];
  let value = seconds;
  let unit: Intl.RelativeTimeFormatUnit = 'second';
  for (const [size, name] of units) {
    unit = name;
    if (Math.abs(value) < size) break;
    value /= size;
  }
  return new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' }).format(-Math.round(value), unit);
}

/** Human wording for failure categories produced by the classifier. */
export function categoryLabel(category?: string | null): string {
  const map: Record<string, string> = {
    CODE_REGRESSION: 'Code regression',
    CONFIGURATION_FAILURE: 'Configuration problem',
    DEPENDENCY_FAILURE: 'Dependency problem',
    INFRASTRUCTURE_FAILURE: 'Infrastructure problem',
    UNKNOWN: 'Unclassified failure',
    HEALTHY: 'Passing run',
  };
  return category ? map[category] ?? category.toLowerCase().replace(/_/g, ' ') : 'Unknown';
}

export function flakyLabel(classification?: string | null): string {
  const map: Record<string, string> = {
    LIKELY_FLAKY: 'Likely flaky',
    POSSIBLY_FLAKY: 'Possibly flaky',
    LIKELY_STABLE: 'Not flaky',
    INSUFFICIENT_HISTORY: 'Not enough history',
  };
  return classification ? map[classification] ?? classification : 'Unknown';
}

export type RunTone = 'pass' | 'fail' | 'pending' | 'neutral';

export function runTone(status?: string | null, conclusion?: string | null): RunTone {
  if (status && status !== 'completed') return 'pending';
  if (conclusion === 'success') return 'pass';
  if (conclusion === 'failure' || conclusion === 'timed_out' || conclusion === 'startup_failure') return 'fail';
  return 'neutral';
}

export function runLabel(status?: string | null, conclusion?: string | null): string {
  if (status && status !== 'completed') return status === 'queued' ? 'Queued' : 'Running';
  const map: Record<string, string> = {
    success: 'Passed', failure: 'Failed', timed_out: 'Timed out', cancelled: 'Cancelled', skipped: 'Skipped',
    startup_failure: 'Failed to start', neutral: 'Neutral', action_required: 'Needs approval',
  };
  return conclusion ? map[conclusion] ?? conclusion : 'No runs';
}
