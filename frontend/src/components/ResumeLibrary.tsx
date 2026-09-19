'use client';
import {useEffect,useRef,useState} from 'react';
import {Upload,FileText,Download,Check,Loader2,X,Trash2,Pencil,UserRound} from 'lucide-react';
import {api,authHeaders,downloadPrivate} from '@/lib/api';
export type Resume={resume_id:string;label:string;file_type:string;original_name:string;keywords:string[];created_at:string|null};
export default function ResumeLibrary({onProfileDraft}:{onProfileDraft:(draft:any)=>void}){
 const [items,setItems]=useState<Resume[]>([]),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState(''),[preview,setPreview]=useState<any>(null),[name,setName]=useState('');
 const input=useRef<HTMLInputElement>(null);
 async function refresh(){setItems(await api<Resume[]>('/resumes'))}
 useEffect(()=>{refresh().catch(e=>setError(e.message))},[]);
 async function perform(fn:()=>Promise<void>){setBusy(true);setError('');try{await fn()}catch(e){setError(e instanceof Error?e.message:'Could not update resume')}finally{setBusy(false)}}
 async function upload(files:FileList|null){
  if(!files?.length)return;setBusy(true);setError('');setMessage('');let count=0;const errors=[];let draft:any=null;
  for(const file of Array.from(files)){
   try{
    if(file.size>10*1024*1024)throw new Error('Maximum file size is 10 MB.');
    const form=new FormData();form.append('file',file);
    const r=await fetch(`${process.env.NEXT_PUBLIC_API_URL||'http://localhost:8000'}/api/v1/resumes/upload`,{method:'POST',headers:await authHeaders(false),body:form});const data=await r.json();
    if(!r.ok)throw new Error(data.detail||'Upload failed.');count++;draft=data.profile_draft;
   }catch(e){errors.push(`${file.name}: ${e instanceof Error?e.message:'Upload failed'}`)}
  }
  await refresh().catch(e=>errors.push(e.message));setMessage(count?`${count} resume file${count===1?'':'s'} processed and indexed locally.`:'');setError(errors.join(' '));setBusy(false);if(input.current)input.current.value='';
  if(draft)onProfileDraft(draft);
 }
 async function review(resume:Resume){await perform(async()=>{const data=await api(`/resumes/${resume.resume_id}`);setPreview(data);setName(data.label)})}
 return <section className="resume-library">
  <div className="section-heading"><div><h2>Your resume library <span className="count">{items.filter(r=>r.resume_id!=='profile').length}</span></h2><p>Name each version by role. Uploads also create an editable profile draft with suggested job titles.</p></div><button className="primary" disabled={busy} onClick={()=>input.current?.click()}>{busy?<Loader2 size={15} className="spin"/>:<Upload size={15}/>} Upload resumes</button><input ref={input} aria-label="Upload resume files" className="visually-hidden" type="file" multiple accept=".pdf,.docx,.txt" onChange={e=>upload(e.target.files)}/></div>
  <div className="upload-note">PDF, DOCX, or TXT · Up to 10 MB each · Parsed locally · Review before saving your profile. For multiple uploads, the last file opens as the profile draft; choose any version below. Scanned PDFs need OCR first.</div>
  {message&&<p className="success-message" role="status"><Check size={14}/>{message}</p>}{error&&<p className="error-banner" role="alert">{error}</p>}
  <div className="resume-grid">{items.map(r=><article className="resume-card" key={r.resume_id}>
   <div className="section-title"><FileText size={22}/><span className="small-label">{r.file_type.toUpperCase()}</span></div><h3>{r.label}</h3><small>{r.original_name}</small>
   <div className="keyword-corpus">{r.keywords.slice(0,10).map(k=><span key={k}>{k}</span>)}</div>
   <div className="detail-actions"><button className="outline compact" disabled={busy} onClick={()=>review(r)}>Review text & keywords</button>{r.resume_id!=='profile'&&<>
    <button className="outline compact" aria-label={`Rename ${r.label}`} disabled={busy} onClick={()=>review(r)}><Pencil size={13}/> Rename</button>
    <button className="outline compact" aria-label={`Use ${r.label} for profile`} disabled={busy} onClick={()=>perform(async()=>onProfileDraft(await api(`/resumes/${r.resume_id}/profile-draft`,'POST')))}><UserRound size={13}/> Build profile</button>
    <button className="text-link" onClick={()=>perform(async()=>downloadPrivate(`/resumes/${r.resume_id}/download`,r.original_name))}><Download size={13}/> Original</button>
    <button className="text-link danger" aria-label={`Delete resume ${r.label}`} disabled={busy} onClick={()=>{if(window.confirm(`Delete ${r.label} and its original file and extracted text? Your saved profile and job kits stay unchanged.`))perform(async()=>{await api(`/resumes/${r.resume_id}`,'DELETE');if(preview?.resume_id===r.resume_id)setPreview(null);await refresh();setMessage('Resume deleted. Your saved profile and application kits are unchanged.')})}}><Trash2 size={13}/> Delete</button>
   </>}</div>
  </article>)}</div>
  {!items.length&&<div className="empty"><FileText/><h3>Start with your experience.</h3><p>Upload a resume to build your profile and compare versions with jobs.</p></div>}
  {preview&&<div className="resume-preview"><div className="section-title"><h3>{preview.label}</h3><button className="icon-button" aria-label="Close resume preview" onClick={()=>setPreview(null)}><X size={18}/></button></div>
   {preview.resume_id!=='profile'&&<form className="rename-resume" onSubmit={e=>{e.preventDefault();perform(async()=>{await api(`/resumes/${preview.resume_id}`,'PATCH',{label:name});setPreview({...preview,label:name.trim()});await refresh();setMessage('Resume renamed. This name appears in matching suggestions.')})}}><label>Resume name<input aria-label="Resume name" required maxLength={120} value={name} onChange={e=>setName(e.target.value)} placeholder="e.g. Analytics Engineer — Europe"/></label><button className="outline" disabled={busy||!name.trim()}>Save name</button></form>}
   <h4>Keyword corpus · {preview.keywords.length} terms</h4><div className="keyword-corpus">{preview.keywords.map((k:string)=><span key={k}>{k}</span>)}</div><pre>{preview.text}</pre>
  </div>}
 </section>
}
