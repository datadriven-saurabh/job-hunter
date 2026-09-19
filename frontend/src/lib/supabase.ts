import {createClient} from '@supabase/supabase-js';
const url=process.env.NEXT_PUBLIC_SUPABASE_URL||'';
const key=process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY||'';
export const hosted=Boolean(url&&key);
export const supabase=hosted?createClient(url,key,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}}):null;
export async function accessToken(){if(!supabase)return '';const {data}=await supabase.auth.getSession();return data.session?.access_token||''}
