'use client';
import {useEffect,useState} from 'react';
import {Search,Loader2,ExternalLink,Check} from 'lucide-react';
import {api} from '@/lib/api';
import JobBoardDirectory from './JobBoardDirectory';
export type Source={id:string;name:string;kind:string;note:string;url?:string;available:boolean;cooldown_seconds?:number;estimated_seconds?:number;timing_samples?:number};
const companyIds=['greenhouse','lever','ashby','smartrecruiters'];
export default function JobDiscovery({config,hasProfile,onComplete}:{config:any;hasProfile:boolean;onComplete:()=>void}){
 const [catalog,setCatalog]=useState<Source[]>([]),[provider,setProvider]=useState('multi'),[sources,setSources]=useState(['remoteok','wwr']);
 const [keywords,setKeywords]=useState(config?.job_search_criteria.target_roles[0]||''),[location,setLocation]=useState(config?.job_search_criteria.target_locations[0]||''),[boards,setBoards]=useState<Record<string,string>>({}),[pageUrl,setPageUrl]=useState(''),[limit,setLimit]=useState(20),[maxAge,setMaxAge]=useState(config?.job_search_criteria.max_posting_age_days?.toString()||'');
 const [runId,setRunId]=useState(''),[progress,setProgress]=useState<any>(null),[toast,setToast]=useState('');
 const [busy,setBusy]=useState(false),[report,setReport]=useState<any>(null),[error,setError]=useState('');
 const [manual,setManual]=useState({company_name:'',job_title:'',job_url:'',description:'',location:'',posted_at:''});
 async function refreshSources(){const rows=await api<Source[]>('/jobs/sources?include_unavailable=true');setCatalog(rows);setSources(current=>current.filter(id=>rows.some(s=>s.id===id&&s.available&&!s.cooldown_seconds)));return rows;}
 useEffect(()=>{refreshSources().catch(e=>setError(e.message));const saved=sessionStorage.getItem('job-search-run');if(saved){setRunId(saved);setBusy(true)}},[]);
 useEffect(()=>{const timer=setInterval(()=>setCatalog(rows=>rows.map(row=>({...row,cooldown_seconds:Math.max(0,(row.cooldown_seconds||0)-1)}))),1000);return()=>clearInterval(timer)},[]);
 useEffect(()=>{if(!toast)return;const t=setTimeout(()=>setToast(''),4000);return()=>clearTimeout(t)},[toast]);
 useEffect(()=>{if(!runId)return;let stopped=false;let timer:ReturnType<typeof setTimeout>;
 const poll=async()=>{try{const value=await api(`/jobs/search-runs/${runId}`);if(stopped)return;setProgress(value);setError('');if(['complete','failed','interrupted'].includes(value.state)){setReport(value);setBusy(false);setRunId('');sessionStorage.removeItem('job-search-run');refreshSources().catch(()=>{});return;}}catch(e){if(!stopped){if(e instanceof Error&&e.message.includes('Search not found')){setError('This search is no longer available. You can start a new search.');setBusy(false);setRunId('');sessionStorage.removeItem('job-search-run');return;}setError('Progress is temporarily unavailable. Search may still be running; reconnecting…')}}
 if(!stopped)timer=setTimeout(poll,3000)};poll();return()=>{stopped=true;clearTimeout(timer)}},[runId]);
 const choose=(id:string)=>{if(sources.includes(id)){setSources(sources.filter(x=>x!==id));return}const row=catalog.find(s=>s.id===id);if(row?.cooldown_seconds){setToast(`Cooling down: retry ${row.name} in ${Math.ceil(row.cooldown_seconds/60)} min.`);return}if(sources.length>=3){setToast('Choose at most 3 boards per search.');return}if([...sources,id].reduce((n,x)=>n+(catalog.find(s=>s.id===x)?.estimated_seconds||20),0)>60){setToast('This selection is estimated to take over one minute. Choose fewer or faster boards.');return}setSources([...sources,id])};
 const activeCatalog=catalog.filter(s=>s.available);
 const selectedSources=provider==='multi'?sources:[provider];
 const companySources=selectedSources.filter(s=>companyIds.includes(s));
 const missingBoard=companySources.some(s=>!boards[s]?.trim());
 async function search(){
  setBusy(true);setError('');setReport(null);
  try{
   let result;
   if(provider==='demo'&&!hasProfile)result=await api('/demo','POST');
   else if(provider==='demo')result=await api('/jobs/search','POST',{provider:'demo'});
   else if(provider==='manual')result=await api('/jobs/import','POST',manual);
   else {const run=await api('/jobs/search-runs','POST',{provider:provider==='multi'?'linkedin':provider,sources:provider==='multi'?sources:[],boards,keywords,location,limit,page_url:pageUrl,max_posting_age_days:maxAge?Number(maxAge):null,override_posting_age:true});setRunId(run.run_id);sessionStorage.setItem('job-search-run',run.run_id);return;}
   setReport(result);
   const rows=await refreshSources().catch(()=>catalog);
   if(!['multi','demo','manual'].includes(provider)&&!rows.some(s=>s.id===provider&&s.available))setProvider('multi');
  }catch(e){setError(e instanceof Error?e.message:'Discovery failed')}
  finally{if(!sessionStorage.getItem('job-search-run'))setBusy(false)}
 }
 return <>
  <JobBoardDirectory sources={catalog}/>
  {toast&&<div className="toast" role="status">{toast}</div>}
  <p>Maximum 3 boards · combined estimate must be at most 60 seconds. Successful sources cool down for 10 minutes. Estimates include fetching and matching, and are not guaranteed deadlines.</p>
  {busy&&<p role="status"><Loader2 className="spin" size={16}/> {progress?.message||'Starting search…'} · {progress?.completed||0}/{progress?.total||selectedSources.length} boards finished. Results are saved as each board completes. You can close and reopen this dialog to check progress.</p>}
  <h2>Search beyond a single board.</h2>
  <p>Check for new openings. Previously saved jobs, including deleted opportunities, are skipped. Public feeds must still be checked to discover new postings.</p>
  <fieldset disabled={busy} className="discovery-controls">
   <label>Job source<select aria-label="Job source" value={provider} onChange={e=>{const row=catalog.find(s=>s.id===e.target.value);if(row?.cooldown_seconds){setToast(`Cooling down: retry in ${Math.ceil(row.cooldown_seconds/60)} minutes.`);return}setProvider(e.target.value);setReport(null)}}>
    <option value="multi">Search multiple boards</option>
    {activeCatalog.map(s=><option key={s.id} value={s.id}>{s.name}{s.kind==='company-board'?' · company board':''}</option>)}
    <option value="manual">Import a posting manually</option><option value="demo">Demo opportunities</option>
   </select></label>
   {provider==='multi'&&<><div className="detail-actions"><button className="outline compact" onClick={()=>setSources(activeCatalog.filter(s=>!s.cooldown_seconds).slice(0,1).map(s=>s.id))}>Select fastest available</button><button className="outline compact" onClick={()=>setSources([])}>Clear sources</button></div><div className="source-checkboxes">
    {activeCatalog.map(s=><label className="check-label" key={s.id}><input type="checkbox" checked={sources.includes(s.id)} aria-disabled={!!s.cooldown_seconds} onChange={()=>choose(s.id)}/>{s.name} · ~{Math.ceil(s.estimated_seconds||20)}s{s.cooldown_seconds?` · cooldown ${Math.ceil(s.cooldown_seconds/60)}m`:''}</label>)}
   </div></>}
   {companySources.map(id=><label key={id}>{catalog.find(s=>s.id===id)?.name||id} company board slug<input value={boards[id]||''} maxLength={80} onChange={e=>setBoards({...boards,[id]:e.target.value})} placeholder="Company identifier from its careers URL"/><small>These platforms host separate employer boards. Add a company identifier to search it.</small></label>)}
   {!['demo','manual'].includes(provider)&&<>
    <label>Job title or keywords<input value={keywords} maxLength={200} onChange={e=>setKeywords(e.target.value)} placeholder="e.g. Data Analyst"/></label>
    <div className="form-grid"><label>Search location<input value={location} maxLength={200} onChange={e=>setLocation(e.target.value)} placeholder="e.g. India or Remote"/><small>Overrides your saved location filter for this search.</small></label><label>Maximum posting age<select aria-label="Maximum posting age" value={maxAge} onChange={e=>setMaxAge(e.target.value)}><option value="">Any age</option>{[[1,'Past 24 hours'],[3,'Past 3 days'],[7,'Past week'],[14,'Past 2 weeks'],[30,'Past month'],[60,'Past 2 months'],[90,'Past 3 months']].map(([days,label])=><option value={days} key={days}>{label}</option>)}</select><small>Listings without a source date are excluded when this filter is active.</small></label><label>Results per source<select aria-label="Results per source" value={limit} onChange={e=>setLimit(Number(e.target.value))}>{[10,20,25,50,100].map(n=><option value={n} key={n}>{n}</option>)}</select></label></div>
    {catalog.find(s=>s.id===provider)?.note&&<p className="muted">{catalog.find(s=>s.id===provider)?.note}</p>}
   </>}
   {selectedSources.includes('hiringcafe')&&<label>HiringCafe page URL · optional<input type="url" value={pageUrl} maxLength={2000} onChange={e=>setPageUrl(e.target.value)} placeholder="https://hiringcafe.com/"/></label>}
   {provider==='manual'&&<>{[['company_name','Company','text'],['job_title','Job title','text'],['job_url','Application URL','url'],['location','Location','text'],['posted_at','Posting date · optional','date']].map(([key,label,type])=><label key={key}>{label}<input type={type} value={manual[key as keyof typeof manual]} onChange={e=>setManual({...manual,[key]:e.target.value})}/>{key==='posted_at'&&<small>Required if your saved maximum posting-age filter is active.</small>}</label>)}<label>Full job description<textarea rows={6} value={manual.description} onChange={e=>setManual({...manual,description:e.target.value})}/></label></>}
  </fieldset>
  <div className="demo-note">{provider==='demo'?'Sample roles only. Demo applications are never submitted.':'Public access only. Each source has a bounded snapshot; this is not a search of every job on every website. Public-page adapters read up to 10 new details; LinkedIn reads up to 25 cards. Feeds are cached and no account cookies are used. Blocked sources are removed from automatic search and remain in the manual directory. New access blocks pause a board for one hour.'}</div>
  {error&&<div className="error-banner" role="alert">{error}</div>}
  <button className="primary full" disabled={busy||missingBoard||provider==='multi'&&!sources.length||!hasProfile&&provider!=='demo'} onClick={search}>{busy?<Loader2 size={15} className="spin"/>:<Search size={15}/>} {busy?'Checking public sources for new jobs…':'Find openings'}</button>
  {!hasProfile&&provider!=='demo'&&<p>Save My profile before matching live jobs.</p>}
  {report&&<div className="discovery-report" role="status"><h3>{report.message}</h3>{report.sources?.map((r:any)=>{
   const source=catalog.find(s=>s.id===r.source);
   return <div key={r.source} className="source-report"><strong>{source?.name||r.source} · {r.status==='success'?`${r.matched} new / ${r.fetched} candidates${r.cached?' · cached':''}`:'Unavailable'}</strong>
    {r.already_seen>0&&<p>{r.already_seen} previously seen or duplicate postings skipped.</p>}
    {r.message&&<p>{r.message}</p>}
    {r.excluded_reasons&&Object.entries(r.excluded_reasons).map(([reason,count])=><p key={reason}>{String(count)} candidates conflict with: {reason}</p>)}
    {r.incomplete_descriptions>0&&<p>{r.incomplete_descriptions} listings have limited descriptions. Review the original posting before prioritizing.</p>}
    {r.status==='unavailable'&&<div className="detail-actions">{source?.url&&<a className="text-link" href={source.url} target="_blank" rel="noreferrer">Open {source.name} <ExternalLink size={12}/></a>}<button className="text-link" onClick={()=>{setProvider('manual');setReport(null)}}>Import a posting manually</button></div>}
   </div>
  })}<button className="outline full" onClick={onComplete}><Check size={15}/> View opportunities</button></div>}
 </>
}
