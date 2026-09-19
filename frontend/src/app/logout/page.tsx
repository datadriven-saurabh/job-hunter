'use client';import {useEffect} from 'react';import {supabase} from '@/lib/supabase';
export default function Logout(){useEffect(()=>{(async()=>{await supabase?.auth.signOut();window.location.replace('/login')})()},[]);return <main className="auth-shell"><section className="auth-card"><p>Signing out…</p></section></main>}
