if(!window.__autoCareerLoaded){
window.__autoCareerLoaded=true;
chrome.runtime.onMessage.addListener((request,sender,sendResponse)=>{
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
