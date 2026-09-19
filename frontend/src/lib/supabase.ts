import {createClient, type SupabaseClient} from '@supabase/supabase-js';

const apiBase=process.env.NEXT_PUBLIC_API_URL||'http://localhost:8000';
const staticUrl=process.env.NEXT_PUBLIC_SUPABASE_URL||'';
const staticKey=process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY||'';
export const hosted=Boolean(process.env.NEXT_PUBLIC_API_URL||staticUrl||staticKey);
let client:SupabaseClient|null=null;
let pending:Promise<SupabaseClient|null>|null=null;

function valid(url:string,key:string){
  const local=/^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(url);
  return Boolean((url.startsWith('https://')||local)&&!url.includes('@')&&(key.startsWith('sb_publishable_')||key.startsWith('eyJ')));
}

export async function getSupabase(){
  if(client)return client;
  if(pending)return pending;
  pending=(async()=>{
    let url=staticUrl,key=staticKey;
    if(!valid(url,key)&&hosted){
      const response=await fetch(`${apiBase}/auth-config`,{cache:'no-store',headers:{Accept:'application/json'}});
      if(!response.ok)throw new Error('Authentication service is unavailable. Please try again shortly.');
      const config=await response.json();url=String(config.url||'');key=String(config.publishable_key||'');
    }
    if(!valid(url,key)){if(hosted)throw new Error('Authentication configuration is unavailable. Please contact the administrator.');return null;}
    client=createClient(url,key,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}});
    return client;
  })().finally(()=>{pending=null});
  return pending;
}

export async function accessToken(){const supabase=await getSupabase();if(!supabase)return '';const {data}=await supabase.auth.getSession();return data.session?.access_token||''}
