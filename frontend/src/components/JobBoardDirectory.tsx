'use client';
import type {Source} from './JobDiscovery';
export default function JobBoardDirectory({sources}:{sources:Source[]}){
 const manual=sources.filter(s=>!s.available);
 return <details className="board-directory"><summary>Job board directory · {sources.length} boards · {manual.length} manual only</summary>
  <p>Automatic search includes boards with readable public listings. Blocked and sign-in sources are listed here for manual import. Open a posting in your browser, then import its URL and full description. Browser accounts are separate; Job Hunter does not store job-board passwords.</p>
  <div className="board-links">{sources.map(s=><a key={s.id} href={s.url} target="_blank" rel="noreferrer"><strong>{s.name} ↗</strong><small>{s.available?'Automatic discovery':'Manual import only'} · {s.note}</small></a>)}</div>
 </details>
}
