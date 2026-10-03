'use client';
import {useEffect,useState} from 'react';
import {Search,Loader2,ExternalLink,Check} from 'lucide-react';
import {api} from '@/lib/api';
import JobBoardDirectory from './JobBoardDirectory';
import {searchCategories,planCategory,sourceTiming} from '@/lib/searchCategories';
export type Source={id:string;name:string;kind:string;note:string;url?:string;available:boolean;cooldown_seconds?:number;estimated_seconds?:number;timing_samples?:number;average_fetch_seconds?:number|null};
export default function JobDiscovery({config,hasProfile,onComplete}:{config:any;hasProfile:boolean;onComplete:()=>void}){
 const [catalog,setCatalog]=useState<Source[]>([]),[provider,setProvider]=useState('search'),[category,setCategory]=useState('general'),[sourceChoice,setSourceChoice]=useState('auto'),[catalogLoaded,setCatalogLoaded]=useState(false);
 const [keywords,setKeywords]=useState(config?.job_search_criteria.target_roles[0]||''),[location,setLocation]=useState(config?.job_search_criteria.target_locations[0]||''),[limit,setLimit]=useState(20),[maxAge,setMaxAge]=useState(config?.job_search_criteria.max_posting_age_days?.toString()||'');
 const [runId,setRunId]=useState(''),[progress,setProgress]=useState<any>(null);
 const [busy,setBusy]=useState(false),[report,setReport]=useState<any>(null),[error,setError]=useState('');
 const [manual,setManual]=useState({company_name:'',job_title:'',job_url:'',description:'',location:'',posted_at:''});
 async function refreshSources(){const rows=await api<Source[]>('/jobs/sources');setCatalog(rows);setSourceChoice(current=>current==='auto'||rows.some(s=>s.id===current&&s.available)?current:'auto');setCatalogLoaded(true);return rows;}
 useEffect(()=>{refreshSources().catch(e=>setError(e.message));const saved=sessionStorage.getItem('job-search-run');if(saved){setRunId(saved);setBusy(true)}},[]);
 useEffect(()=>{const timer=setInterval(()=>setCatalog(rows=>rows.map(row=>({...row,cooldown_seconds:Math.max(0,(row.cooldown_seconds||0)-1)}))),1000);return()=>clearInterval(timer)},[]);
 useEffect(()=>{if(!runId)return;let stopped=false;let timer:ReturnType<typeof setTimeout>;
 const poll=async()=>{try{const value=await api(`/jobs/search-runs/${runId}`);if(stopped)return;setProgress(value);setError('');if(['complete','failed','interrupted'].includes(value.state)){setReport(value);setBusy(false);setRunId('');sessionStorage.removeItem('job-search-run');refreshSources().catch(()=>{});return;}}catch(e){if(!stopped){if(e instanceof Error&&e.message.includes('Search not found')){setError('This search is no longer available. You can start a new search.');setBusy(false);setRunId('');sessionStorage.removeItem('job-search-run');return;}setError('Progress is temporarily unavailable. Search may still be running; reconnecting…')}}
 if(!stopped)timer=setTimeout(poll,3000)};poll();return()=>{stopped=true;clearTimeout(timer)}},[runId]);
 const plan=planCategory(category,catalog,sourceChoice);
 const categories=searchCategories.filter(c=>!catalogLoaded||c.sources.some(id=>catalog.some(s=>s.id===id&&s.available&&s.kind!=='company-board')));
 useEffect(()=>{if(catalogLoaded&&!categories.some(c=>c.id===category))setCategory(categories[0]?.id||'general')},[catalogLoaded,catalog,category]);
 const selectedCategory=searchCategories.find(c=>c.id===category)!;
 const selectedSources=plan.selected.map(s=>s.id);
 async function search(){
  setBusy(true);setError('');setReport(null);setProgress(null);
  try{
   let result;
   if(provider==='demo'&&!hasProfile)result=await api('/demo','POST');
   else if(provider==='demo')result=await api('/jobs/search','POST',{provider:'demo'});
   else if(provider==='manual')result=await api('/jobs/import','POST',manual);
   else {
    const rows=await refreshSources();
    const currentPlan=planCategory(category,rows,sourceChoice);
    if(!currentPlan.selected.length)throw new Error(currentPlan.reason);
    const run=await api('/jobs/search-runs','POST',{sources:currentPlan.selected.map(s=>s.id),keywords,location,limit,max_posting_age_days:maxAge?Number(maxAge):null,override_posting_age:true});
    setRunId(run.run_id);sessionStorage.setItem('job-search-run',run.run_id);return;
   }
   setReport(result);
  }catch(e){setError(e instanceof Error?e.message:'Discovery failed')}
  finally{if(!sessionStorage.getItem('job-search-run'))setBusy(false)}
 }
 return <>
  {busy&&<p role="status"><Loader2 className="spin" size={16}/> {progress?.message||'Starting search…'} · {progress?.completed||0}/{progress?.total||selectedSources.length} boards finished. Results are saved as each board completes. You can close and reopen this dialog to check progress.</p>}
  <h2>{provider==='manual'?'Import a posting':provider==='demo'?'Explore demo opportunities':'Find your next opportunity'}</h2>
  <p>{provider==='search'?'Choose one category. We’ll select available boards and skip jobs you’ve already saved.':'Add opportunities to your workspace.'}</p>
  <fieldset disabled={busy} className="discovery-controls">
   {provider==='search'&&<>
    <label>Search category<select aria-label="Search category" value={category} onChange={e=>{setCategory(e.target.value);setSourceChoice('auto');setReport(null);setError('');setProgress(null)}}>
     {categories.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}
    </select><small>{selectedCategory.description}</small></label>
    <label>Source within this category<select aria-label="Source within this category" value={sourceChoice} onChange={e=>{setSourceChoice(e.target.value);setReport(null);setError('')}}>
     <option value="auto">Choose available sources automatically</option>
     {plan.members.filter(s=>s.available&&s.kind!=='company-board').map(s=><option key={s.id} value={s.id}>{s.name}{s.cooldown_seconds?` · retry in ${Math.ceil(s.cooldown_seconds/60)} min`:''}</option>)}
    </select></label>
    {!catalogLoaded?<p role="status">Loading available sources…</p>:plan.selected.length?<p className="muted">This search: {plan.selected.map(s=>`${s.name} (${sourceTiming(s)})`).join('; ')}. Times are estimates, not a search limit. Search continues in the background; you can close this dialog and check progress later.</p>:<p role="status">{plan.reason}</p>}
   </>}
   {!['demo','manual'].includes(provider)&&<>
    <label>Job title or keywords<input value={keywords} maxLength={200} onChange={e=>setKeywords(e.target.value)} placeholder="e.g. Data Analyst"/></label>
    <div className="form-grid"><label>Search location<input value={location} maxLength={200} onChange={e=>setLocation(e.target.value)} placeholder="e.g. India or Remote"/><small>Leave blank to search all locations. Overrides saved locations for this search.</small></label><label>Maximum posting age<select aria-label="Maximum posting age" value={maxAge} onChange={e=>setMaxAge(e.target.value)}><option value="">Any age</option>{[[1,'Past 24 hours'],[3,'Past 3 days'],[7,'Past week'],[14,'Past 2 weeks'],[30,'Past month'],[60,'Past 2 months'],[90,'Past 3 months']].map(([days,label])=><option value={days} key={days}>{label}</option>)}</select><small>Listings without a source date are excluded when this filter is active.</small></label><label>Results per source<select aria-label="Results per source" value={limit} onChange={e=>setLimit(Number(e.target.value))}>{[10,20,25,50,100].map(n=><option value={n} key={n}>{n}</option>)}</select></label></div>
   </>}
   {provider==='manual'&&<>{[['company_name','Company','text'],['job_title','Job title','text'],['job_url','Application URL','url'],['location','Location','text'],['posted_at','Posting date · optional','date']].map(([key,label,type])=><label key={key}>{label}<input type={type} value={manual[key as keyof typeof manual]} onChange={e=>setManual({...manual,[key]:e.target.value})}/>{key==='posted_at'&&<small>Required if your saved maximum posting-age filter is active.</small>}</label>)}<label>Full job description<textarea rows={6} value={manual.description} onChange={e=>setManual({...manual,description:e.target.value})}/></label></>}
  </fieldset>
  {provider==='search'&&<JobBoardDirectory sources={plan.members.filter(s=>s.available&&s.kind!=='company-board')}/>}
  <div className="demo-note">{provider==='demo'?'Sample roles only. Demo applications are never submitted.':'Results come from public listings and may not cover every opening. Check the original posting before applying.'}</div>
  {error&&<div className="error-banner" role="alert">{error}</div>}
  <button className="primary full" disabled={busy||provider==='search'&&(!catalogLoaded||!selectedSources.length)||!hasProfile&&provider!=='demo'} onClick={search}>{busy?<Loader2 size={15} className="spin"/>:<Search size={15}/>} {busy?'Checking public sources for new jobs…':provider==='manual'?'Import posting':provider==='demo'?'Load demo opportunities':'Find openings'}</button>
  <div className="detail-actions">{provider!=='search'&&<button className="text-link" disabled={busy} onClick={()=>{setProvider('search');setError('');setReport(null)}}>Back to category search</button>}{provider!=='manual'&&<button className="text-link" disabled={busy} onClick={()=>{setProvider('manual');setError('');setReport(null)}}>Import a posting manually</button>}{provider!=='demo'&&<button className="text-link" disabled={busy} onClick={()=>{setProvider('demo');setError('');setReport(null)}}>Try demo opportunities</button>}</div>
  {!hasProfile&&provider!=='demo' &&<p>Save My profile before matching live jobs.</p>}
  {report&&<div className="discovery-report" role="status"><h3>{report.message}</h3>{report.sources?.map((r:any)=>{
   const source=catalog.find(s=>s.id===r.source);
   return <div key={r.source} className="source-report"><strong>{source?.name||r.source} · {r.status==='success'?`${r.matched} new / ${r.fetched} candidates${r.cached?' · cached':''}`:'Unavailable'}</strong>
    {r.already_seen>0&&<p>{r.already_seen} previously seen or duplicate postings skipped.</p>}
    {r.source==='linkedin'&&r.coverage&&<p>Checked {r.coverage.cards_examined} public LinkedIn listings across {r.coverage.pages_scanned} {r.coverage.pages_scanned===1?'page':'pages'}{r.coverage.limited?'; more listings may be available.':'.'} This is a limited snapshot.</p>}
    {r.message&&<p>{r.message}</p>}
    {r.excluded_reasons&&Object.entries(r.excluded_reasons).map(([reason,count])=><p key={reason}>{String(count)} candidates conflict with: {reason}</p>)}
    {r.incomplete_descriptions>0&&<p>{r.incomplete_descriptions} listings have limited descriptions. Review the original posting before prioritizing.</p>}
    {r.status==='unavailable'&&<div className="detail-actions">{source?.url&&<a className="text-link" href={source.url} target="_blank" rel="noreferrer">Open {source.name} <ExternalLink size={12}/></a>}<button className="text-link" onClick={()=>{setProvider('manual');setReport(null)}}>Import a posting manually</button></div>}
   </div>
  })}<button className="outline full" onClick={onComplete}><Check size={15}/> View opportunities</button></div>}
 </>
}
