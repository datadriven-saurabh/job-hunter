export type SearchSource = {id:string;name:string;kind:string;available:boolean;cooldown_seconds?:number;estimated_seconds?:number;timing_samples?:number;average_fetch_seconds?:number|null};
export const searchCategories = [
 {id:'general',name:'General job boards',description:'Roles across industries and experience levels.',sources:['linkedin','workable','indeed','glassdoor','google','hiringcafe','linkedin_posts']},
 {id:'remote',name:'Remote work',description:'Boards focused on remote opportunities. Check each posting’s country requirements.',sources:['remoteok','wwr','remotive','workingnomads']},
 {id:'startups',name:'Startups & tech',description:'Startup, technology and venture-backed company roles.',sources:['builtin','yc','hackernews','wellfound','berlinstartupjobs','eustartups','jobfluent','hvcapital','earlybird','pointnine','aijobs','startupjobs','indexventures','otta','honeypot']},
 {id:'europe',name:'Europe & UK',description:'Regional boards covering European and UK opportunities.',sources:['arbeitnow','arbeitnow_uk','stepstone','germantechjobs','hyrise','landingjobs']},
 {id:'international',name:'International & relocation',description:'International hiring boards. Relocation support depends on the employer.',sources:['vanhack','relocate','eures','workinfinland','makeitingermany']},
 {id:'employers',name:'Employer career pages',description:'Direct employer openings and links to company career platforms.',sources:['jobbatical','ja_solar','greenhouse','lever','ashby','smartrecruiters']},
];

export function planCategory<T extends SearchSource>(categoryId:string,catalog:T[],sourceId='auto') {
 const category=searchCategories.find(c=>c.id===categoryId);
 const members=catalog.filter(s=>category?.sources.includes(s.id));
 const ready=members.filter(s=>(sourceId==='auto'||s.id===sourceId)&&s.available&&s.kind!=='company-board'&&!(s.cooldown_seconds||0));
 const estimate=(s:T)=>Math.max(1,s.estimated_seconds??20);
 // Timing is informational; slow sources remain selectable.
 const selected:T[]=[];let seconds=0;
 for(const source of [...ready].sort((a,b)=>estimate(a)-estimate(b)||a.id.localeCompare(b.id))){
  if(selected.length<3){selected.push(source);seconds+=estimate(source)}
 }
 const cooling=members.filter(s=>(sourceId==='auto'||s.id===sourceId)&&s.available&&s.kind!=='company-board'&&(s.cooldown_seconds||0)>0);
 const reason=selected.length?'':cooling.length?`This category is cooling down. Try again in ${Math.max(1,Math.ceil(Math.min(...cooling.map(s=>s.cooldown_seconds!))/60))} min, or choose another category.`:'No automatic sources are available in this category right now. Choose another category or import a posting.';
 return {members,selected,seconds,reason};
}

export function sourceTiming(source:SearchSource){
 const total=Math.ceil(source.estimated_seconds??20);
 const fetch=source.average_fetch_seconds;
 return fetch!=null?`Average fetch ~${Math.ceil(fetch)}s · total ~${total}s`:source.timing_samples?`Average total ~${total}s · fetch average not recorded yet`:`Estimated ~${total}s · no timing samples yet`;
}
