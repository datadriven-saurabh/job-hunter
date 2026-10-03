'use client';
import type {Source} from './JobDiscovery';
export default function JobBoardDirectory({sources}:{sources:Source[]}){
 return <details className="board-directory"><summary>Sources in this category · {sources.length} boards</summary>
  <p>These boards currently provide readable public listings. Sources that are blocked or repeatedly return no listings are removed from search until they recover. You can still import any public posting by URL.</p>
  <div className="board-links">{sources.map(s=><a key={s.id} href={s.url} target="_blank" rel="noreferrer"><strong>{s.name} ↗</strong><small>{s.note}</small></a>)}</div>
 </details>
}
