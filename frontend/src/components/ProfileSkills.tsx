'use client';
import {useState} from 'react';

export default function ProfileSkills({skills,extracted=[],onChange}:{skills:string[];extracted?:string[];onChange:(skills:string[])=>void}) {
 const [additional,setAdditional]=useState('');
 function add(){
  const unique=new Map(skills.map(s=>[s.trim().toLowerCase(),s.trim()]));
  for(const text of additional.split(',')){const term=text.trim();if(term)unique.set(term.toLowerCase(),term)}
  onChange([...unique.values()].filter(Boolean));setAdditional('');
 }
 return <section className="profile-skills" aria-label="Profile keywords and skills">
  <h3>Profile keywords & skills</h3>
  <p>{extracted.length?`${extracted.length} skills extracted from your resume. Review them and add any additional skills you have.`:'Skills from your resume and your own additions are used to match opportunities.'}</p>
  <div className="keyword-corpus">{skills.filter(Boolean).map((skill,i)=><span key={`${skill}-${i}`}>{skill}<button type="button" className="text-link" aria-label={`Remove skill ${skill}`} onClick={()=>onChange(skills.filter((_,index)=>index!==i))}> ×</button></span>)}</div>
  <label>Additional skills<input value={additional} onChange={e=>setAdditional(e.target.value)} onBlur={()=>{if(additional.trim())add()}} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();add()}}} placeholder="e.g. SEO, Google Ads, stakeholder management"/><small>Separate skills with commas. Press Enter or Add skills. Save your profile to keep changes.</small></label>
  <button type="button" className="outline compact" disabled={!additional.trim()} onClick={add}>Add skills</button>
 </section>
}
