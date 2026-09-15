'use client';
import {useState} from 'react';
import {api} from '@/lib/api';
export default function DeletedOpportunities({onChanged}:{onChanged:()=>Promise<void>}){
 const [items,setItems]=useState<any[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 async function load(){try{setItems(await api('/applications/deleted'));setError('')}catch(e){setError((e as Error).message)}}
 return <details className="deleted-opportunities" onToggle={e=>{if(e.currentTarget.open)load()}}><summary>Deleted opportunities</summary><p>Removed from your dashboard and application list. Saved documents remain local. Restore an opening to bring it back.</p>{error&&<p role="alert">{error}</p>}{items.map(j=><div key={j.job_id}><span>{j.company_name} · {j.job_title}</span><button className="outline compact" disabled={busy} onClick={async()=>{setBusy(true);try{await api('/applications/restore','POST',{job_ids:[j.job_id]});await load();await onChanged()}catch(e){setError((e as Error).message)}finally{setBusy(false)}}}>Restore {j.company_name}</button></div>)}{!items.length&&<p>No deleted opportunities.</p>}</details>
}
