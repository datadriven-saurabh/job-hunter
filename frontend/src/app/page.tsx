'use client';
import AuthGate from '@/components/AuthGate';
import {useEffect} from 'react';
import {useRouter} from 'next/navigation';
function OpenDashboard(){const router=useRouter();useEffect(()=>{router.replace('/dashboard')},[router]);return <main className="auth-shell"><section className="auth-card"><h1>Job Hunter</h1><p>Opening your workspace…</p></section></main>}
export default function Home(){return <AuthGate><OpenDashboard/></AuthGate>}
