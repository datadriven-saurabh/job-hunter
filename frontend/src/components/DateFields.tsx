'use client';
import {useEffect,useState} from 'react';
export function MonthField({label,value,onChange,allowPresent=false}:{label:string;value:string;onChange:(v:string)=>void;allowPresent?:boolean}){
 const present=value==='Present';
 const [native,setNative]=useState(true);
 useEffect(()=>{const input=document.createElement('input');input.type='month';setNative(input.type==='month')},[]);
 const [year,month]=present?['','']:value.split('-');
 return <div className="date-field">{native?<label>{label}<input type="month" required={!present} disabled={present} min="1950-01" max="2100-12" value={present?'':value} onChange={e=>onChange(e.target.value)}/></label>:<><span>{label}</span><div className="month-selects"><select aria-label={`${label} month`} required={!present} disabled={present} value={month||''} onChange={e=>onChange(`${year||''}-${e.target.value}`)}><option value="">Month</option>{Array.from({length:12},(_,i)=><option key={i} value={String(i+1).padStart(2,'0')}>{new Date(2000,i).toLocaleString('en',{month:'long'})}</option>)}</select><select aria-label={`${label} year`} required={!present} disabled={present} value={year||''} onChange={e=>onChange(`${e.target.value}-${month||''}`)}><option value="">Year</option>{Array.from({length:151},(_,i)=><option key={i} value={2100-i}>{2100-i}</option>)}</select></div></>}{allowPresent&&<label className="check-label"><input type="checkbox" checked={present} onChange={e=>onChange(e.target.checked?'Present':'')}/> I currently work here</label>}</div>
}
export function YearField({value,onChange}:{value:string;onChange:(v:string)=>void}){
 const current=new Date().getFullYear();const years=Array.from({length:current+11-1950},(_,i)=>String(current+10-i));
 return <label>Graduation year<select required value={value} onChange={e=>onChange(e.target.value)}><option value="">Select year</option>{years.map(year=><option key={year}>{year}</option>)}</select></label>
}
