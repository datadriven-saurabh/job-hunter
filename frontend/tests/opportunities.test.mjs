import test from 'node:test';
import assert from 'node:assert/strict';
import {sortOpportunities} from '../src/lib/opportunity-sort.mjs';
const jobs=[
 {job_id:'a',match_score:.6,posted_at:'2025-01-01T12:00:00Z',source:'Lever',location:'Berlin'},
 {job_id:'b',match_score:.9,posted_at:'2025-01-01T13:00:00Z',source:'Ashby',location:'Zurich'},
 {job_id:'c',match_score:.8,posted_at:null,source:'',location:''}
];
const ids=(field,direction)=>sortOpportunities(jobs,field,direction).map(j=>j.job_id);
test('matching score in both directions',()=>{assert.deepEqual(ids('match','desc'),['b','c','a']);assert.deepEqual(ids('match','asc'),['a','c','b'])});
test('posting timestamps and unknown last',()=>{assert.deepEqual(ids('posted','desc'),['b','a','c']);assert.deepEqual(ids('posted','asc'),['a','b','c'])});
test('source and location ordering',()=>{assert.deepEqual(ids('source','asc'),['b','a','c']);assert.deepEqual(ids('source','desc'),['a','b','c']);assert.deepEqual(ids('location','asc'),['a','b','c']);assert.deepEqual(ids('location','desc'),['b','a','c'])});
test('does not mutate the dashboard input',()=>{ids('match','desc');assert.deepEqual(jobs.map(j=>j.job_id),['a','b','c'])});
