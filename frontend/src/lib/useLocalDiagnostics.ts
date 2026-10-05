'use client';
import {useEffect,useState} from 'react';

export function useLocalDiagnostics(){
 const [enabled,setEnabled]=useState(false);
 useEffect(()=>{setEnabled(['localhost','127.0.0.1','[::1]'].includes(window.location.hostname))},[]);
 return enabled;
}
