'use client';
import {useEffect,useState} from 'react';
import {api} from '@/lib/api';
export default function JobAnalysis({jobId}:{jobId:string}){
 const [run,setRun]=useState(''),[report,setReport]=useState<any>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>{setRun('');setReport(null);setError('')},[jobId]);
 useEffect(()=>{if(!run)return;let active=true;const load=async()=>{try{const r=await api(`/career/analyze/${run}`);if(active){setReport(r);if(r.status!=='running'){setRun('');setBusy(false)}}}catch(e){if(active){setError((e as Error).message);setRun('');setBusy(false)}}};load();const t=setInterval(load,3000);return()=>{active=false;clearInterval(t)}},[run]);
 async function analyze(){setBusy(true);setError('');try{const r=await api('/career/analyze','POST',{job_ids:[jobId]});setRun(r.id)}catch(e){setError((e as Error).message);setBusy(false)}}
 const result=report?.results?.[0];
 return <section className="job-signals"><h3>Local AI review</h3><p>Review requirements and profile evidence using your configured models. Scores are advisory; eligibility constraints remain visible.</p><button className="outline" disabled={busy} onClick={analyze}>{busy?'Analyzing locally…':'Analyze this opening'}</button>{error&&<p role="alert">{error}</p>}{report?.message&&<p>{report.message}</p>}{result&&<><p><strong>{result.decision?.replaceAll('_',' ')}</strong> · {result.status.replaceAll('_',' ')}{result.evaluated_score!=null&&` · AI fit ${result.evaluated_score}/100`}</p><p>Stages: {result.stages.join(', ').replaceAll('_',' ')}</p>{result.status==='rules_only'&&<p>No validated model assessment was available. The existing evidence-based fit still applies.</p>}<details><summary>Evidence and model usage</summary><pre>{JSON.stringify(report,null,2)}</pre></details></>}</section>
}
