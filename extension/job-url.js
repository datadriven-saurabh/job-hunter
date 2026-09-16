// Preserve job-identifying query parameters, while ignoring common tracking tags.
globalThis.jobHunterSamePosting = (actualUrl, expectedUrl) => {
  const normalize = value => {
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.username || url.password) return null;
    for (const key of [...url.searchParams.keys()]) {
      if (key.toLowerCase().startsWith('utm_') || ['ref','refid','source','tracking','trk','trackingid'].includes(key.toLowerCase())) url.searchParams.delete(key);
    }
    url.searchParams.sort();
    return url.origin + url.pathname.replace(/\/$/,'') + url.search;
  };
  try { const actual=normalize(actualUrl); return actual!==null && actual===normalize(expectedUrl); }
  catch { return false; }
};
