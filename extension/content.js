if(!window.__autoCareerLoaded){
window.__autoCareerLoaded=true;
chrome.runtime.onMessage.addListener((request,sender,sendResponse)=>{
 if(request.action==='CAPTURE_LINKEDIN_POST'){
  if(location.hostname!=='www.linkedin.com'&&location.hostname!=='linkedin.com'){sendResponse({error:'Open a LinkedIn post first.'});return;}
  const canonical=document.querySelector('link[rel="canonical"]')?.href||location.href;
  const updateId=decodeURIComponent(location.href).match(/urn:li:(?:activity|share):\d+/)?.[0];
  const candidates=[...document.querySelectorAll('article, [data-urn], .feed-shared-update-v2')];
  const post=candidates.find(el=>updateId&&el.getAttribute('data-urn')?.includes(updateId.split(':').pop()))||candidates.find(el=>el.getClientRects().length>0);
  if(!post){sendResponse({error:'No visible LinkedIn post was found. Open the individual post and try again.'});return;}
  const text=(post.querySelector('.feed-shared-update-v2__description, .update-components-text, .feed-shared-text')?.innerText||post.innerText||'').trim().slice(0,45000);
  const author=(post.querySelector('.update-components-actor__name, .feed-shared-actor__name')?.innerText||'').trim().replace(/\s+/g,' ');
  const links=[...post.querySelectorAll('a[href]')].map(a=>a.href).filter(href=>/^https:\/\//.test(href)&&!href.includes('linkedin.com'));
  sendResponse({post_url:canonical,description:text,author,job_url:links[0]||canonical});return;
 }
 if(request.action!=='AUTOFILL_FORM')return;
 const mappings={email:['input[type="email"]','input[name*="email" i]'],first_name:['input[name*="first" i]','input[id*="first" i]'],last_name:['input[name*="last" i]','input[id*="last" i]'],full_name:['input[name="name"]','input[name="full_name"]'],phone:['input[type="tel"]','input[name*="phone" i]'],linkedin_url:['input[name*="linkedin" i]'],github_url:['input[name*="github" i]']};
 let filledCount=0;const seen=new Set();
 for(const [key,selectors] of Object.entries(mappings)){
  if(!request.formData[key])continue;
  for(const selector of selectors){
   const input=[...document.querySelectorAll(selector)].find(el=>!el.disabled&&!el.readOnly&&el.type!=='hidden'&&el.getClientRects().length>0&&!el.value&&!seen.has(el));
   if(input){Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,request.formData[key]);input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}));seen.add(input);filledCount++;break;}
  }
 }
 sendResponse({status:'SUCCESS',fieldsFilled:filledCount});
});}
