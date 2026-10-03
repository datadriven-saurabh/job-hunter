'use client';
import {useEffect,useState} from 'react';
import {Loader2} from 'lucide-react';
import Link from 'next/link';
import {useRouter,useSearchParams} from 'next/navigation';
import {getSupabase} from '@/lib/supabase';
import {authErrorMessage,confirmationError,confirmationMessage} from '@/lib/authRedirect';
export default function AuthForm({mode}:{mode:'login'|'signup'}){
 const router=useRouter(),params=useSearchParams();
 const [email,setEmail]=useState(''),[password,setPassword]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 useEffect(()=>{
  let active=true;
  const failure=confirmationError(window.location.href)||params.get('confirmation');
  if(failure){setError(confirmationMessage(failure));window.history.replaceState(null,'',window.location.pathname);return}
  (async()=>{try{const supabase=await getSupabase();if(!supabase)return;const {data,error}=await supabase.auth.getSession();if(active&&data.session&&!error)router.replace('/dashboard')}catch{if(active)setError('Authentication service is unavailable. Please try again shortly.')}})();
  return()=>{active=false};
 },[router,params]);
 async function submit(e:React.FormEvent){
  e.preventDefault();setBusy(true);setError('');setNotice('');
  try{
   const supabase=await getSupabase();if(!supabase){router.push('/dashboard');return}
   const result=mode==='login'?await supabase.auth.signInWithPassword({email,password}):await supabase.auth.signUp({email,password,options:{emailRedirectTo:`${window.location.origin}/dashboard`}});
   if(result.error){setError(authErrorMessage(result.error));return}
   if(result.data.session)router.replace(mode==='signup'?'/onboarding':'/dashboard');
   else setNotice('Check your email and open the confirmation link. You’ll be signed in automatically. After signing out, you can log in with your email and password.');
  }catch(e){setError(e instanceof Error?e.message:'Authentication service is unavailable.')}
  finally{setBusy(false)}
 }
 async function resend(){
  if(!email.trim()){setError('Enter your email address above to request a new confirmation link.');return}
  setBusy(true);setError('');setNotice('');
  try{
   const supabase=await getSupabase();if(!supabase)throw new Error('Email confirmation is available on the hosted site.');
   const {error}=await supabase.auth.resend({type:'signup',email:email.trim(),options:{emailRedirectTo:`${window.location.origin}/dashboard`}});
   if(error){setError(authErrorMessage(error));return}
   setNotice('If this address has an unconfirmed account, a new confirmation email has been sent. Open the newest link.');
  }catch(e){setError(e instanceof Error?e.message:'Could not resend confirmation.')}
  finally{setBusy(false)}
 }
 return <main className="auth-shell"><section className="auth-card"><div className="auth-brand">◎ <strong>Job Hunter</strong></div><p className="eyebrow">PRIVATE BETA</p><h1>{mode==='login'?'Welcome back':'Create your workspace'}</h1><p>{mode==='login'?'Sign in to your private job search workspace.':'Your resume, preferences, matches, and application drafts stay isolated from every other account.'}</p>{params.get('expired')&&<p className="error-banner">Your session expired. Sign in again.</p>}{params.get('unavailable')&&<p className="error-banner">Authentication is temporarily unavailable. Please try again.</p>}{error&&<p className="error-banner" role="alert">{error}</p>}{notice&&<p className="success-banner" role="status">{notice}</p>}<form onSubmit={submit}><label>Email<input type="email" required autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)}/></label><label>Password<input type="password" minLength={8} required autoComplete={mode==='signup'?'new-password':'current-password'} value={password} onChange={e=>setPassword(e.target.value)}/></label><button className="primary full" disabled={busy}>{busy?<><Loader2 size={16} className="spin"/> Please wait…</>:mode==='login'?'Sign in':'Create account'}</button></form><button className="text-link" disabled={busy} onClick={resend}>Resend confirmation email</button><p>{mode==='login'?<>New to Job Hunter? <Link href="/signup">Create an account</Link></>:<>Already have an account? <Link href="/login">Sign in</Link></>}</p></section></main>;
}
