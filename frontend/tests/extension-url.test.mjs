import test from 'node:test';
import assert from 'node:assert/strict';
import '../../extension/job-url.js';

test('extension refuses another job on the same path',()=>{
 assert.equal(jobHunterSamePosting('https://example.com/job?id=2','https://example.com/job?id=1'),false);
 assert.equal(jobHunterSamePosting('https://example.com/job?reference=2','https://example.com/job?reference=1'),false);
 assert.equal(jobHunterSamePosting('https://evil.example/job?id=1','https://example.com/job?id=1'),false);
});
test('extension tolerates tracking changes while preserving HTTPS',()=>{
 assert.equal(jobHunterSamePosting('https://example.com/job/?id=1&utm_source=x','https://example.com/job?id=1'),true);
 assert.equal(jobHunterSamePosting('http://example.com/job','https://example.com/job'),false);
 assert.equal(jobHunterSamePosting('not a URL','https://example.com/job'),false);
});
