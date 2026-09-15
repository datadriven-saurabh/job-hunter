/** Sort a copy; unknown values stay last in either direction. */
export function sortOpportunities(jobs, field = 'match', direction = 'desc') {
  const value = job => {
    if (field === 'match') return Number.isFinite(job.match_score) ? job.match_score : null;
    if (field === 'priority') return Number.isFinite(job.application_priority?.score) ? job.application_priority.score : null;
    if (field === 'posted') { const n = Date.parse(job.posted_at || ''); return Number.isFinite(n) ? n : null; }
    const text = String(job[field === 'company' ? 'company_name' : field] || '').trim();
    return !text || /^(unknown|not specified|not listed)$/i.test(text) ? null : text;
  };
  return [...jobs].sort((a, b) => {
    const x = value(a), y = value(b);
    if (x == null && y != null) return 1;
    if (y == null && x != null) return -1;
    const comparison = x == null ? 0 : typeof x === 'number' ? x - y : x.localeCompare(y, undefined, {sensitivity:'base',numeric:true});
    return comparison * (direction === 'asc' ? 1 : -1) || String(a.job_id).localeCompare(String(b.job_id));
  });
}
