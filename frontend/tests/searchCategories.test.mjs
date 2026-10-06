import test from 'node:test';
import assert from 'node:assert/strict';
import {planCategory, searchCategories, sourceTiming} from '../src/lib/searchCategories.ts';
const source=(id, extra={})=>({id,name:id,kind:'public-search',available:true,...extra});

test('one category excludes sources from every other category',()=>{
 const catalog=['linkedin','remoteok','arbeitnow','yc','vanhack','jobbatical','contextdev'].map(id=>source(id));
 for(const c of searchCategories){
  assert.equal(planCategory(c.id,catalog).selected.length,1);
  assert.ok(planCategory(c.id,catalog).selected.every(s=>c.sources.includes(s.id)));
 }
 const ids=searchCategories.flatMap(c=>c.sources);
 assert.equal(new Set(ids).size,ids.length);
});
test('automatic selection respects the three-board limit',()=>{
 const plan=planCategory('remote',[source('remoteok',{estimated_seconds:35}),source('wwr',{estimated_seconds:25}),source('remotive',{estimated_seconds:15}),source('workingnomads',{estimated_seconds:10})]);
 assert.deepEqual(plan.selected.map(s=>s.id),['workingnomads','remotive','wwr']);
 assert.equal(plan.seconds,50);
});
test('blocked, cooling and company-specific sources cannot start automatic searches',()=>{
 assert.equal(planCategory('general',[source('linkedin',{available:false}),source('workable',{cooldown_seconds:180})]).selected.length,0);
 assert.match(planCategory('general',[source('workable',{cooldown_seconds:180})]).reason,/3 min/);
 assert.equal(planCategory('employers',[source('greenhouse',{kind:'company-board'}),source('jobbatical')]).selected.length,1);
});
test('cooling boards become eligible after their cooldown ends',()=>{
 assert.equal(planCategory('remote',[source('remoteok',{cooldown_seconds:1})]).selected.length,0);
 assert.equal(planCategory('remote',[source('remoteok',{cooldown_seconds:0})]).selected.length,1);
});
test('empty categories explain unavailability while slow LinkedIn remains selectable',()=>{
 assert.match(planCategory('general',[]).reason,/No automatic sources/);
 const plan=planCategory('general',[source('linkedin',{estimated_seconds:120}),source('workable')],'linkedin');
 assert.deepEqual(plan.selected.map(s=>s.id),['linkedin']);
 assert.equal(plan.seconds,120);
 assert.equal(plan.reason,'');
 assert.match(sourceTiming(source('linkedin',{estimated_seconds:140,average_fetch_seconds:120,timing_samples:2})),/Average fetch ~120s/);
 assert.match(sourceTiming(source('linkedin')),/no timing samples/);
});
