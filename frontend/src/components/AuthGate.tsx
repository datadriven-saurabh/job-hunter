'use client';
import {useEffect,useState} from 'react';
import {useRouter} from 'next/navigation';
import {getSupabase,hosted} from '@/lib/supabase';
import {confirmationError} from '@/lib/authRedirect';
export default function AuthGate({children}:{children:React.ReactNode}){
 const router=useRouter(),[ready,setReady]=useState(!hosted);
 useEffect(()=>{
  let active=true,unsubscribe=()=>{};
  (async()=>{
   const failure=confirmationError(window.location.href);
   if(failure){window.history.replaceState(null,'',window.location.pathname);router.replace(`/login?confirmation=${failure}`);return}
   try{
    const supabase=await getSupabase();
    if(!active)return;
    if(!supabase){setReady(true);return}
    // getSession waits for Supabase to consume and persist the email callback.
    const {data,error}=await supabase.auth.getSession();
    if(!active)return;
    if(error){router.replace('/login?confirmation=invalid');return}
    if(data.session)setReady(true);else{router.replace('/login');return}
    const auth=supabase.auth.onAuthStateChange((_event,session)=>{if(!active)return;if(!session){setReady(false);router.replace('/login')}else setReady(true)});
    unsubscribe=()=>auth.data.subscription.unsubscribe();
   }catch{if(active)router.replace('/login?unavailable=1')}
  })();
  return()=>{active=false;unsubscribe()};
 },[router]);
 if(!ready)return <main className="auth-shell"><section className="auth-card"><h1>Job Hunter</h1><p>Confirming your session and opening your workspace…</p></section></main>;
 return <>{children}</>;
}
