#!/usr/bin/env python3
"""Start/stop/status for the project-local services; no login items are installed."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'data'/'runtime'
RUN.mkdir(parents=True,exist_ok=True)
PYTHON=ROOT/'.venv/bin/python'
OLLAMA=ROOT/'.runtime/ollama/ollama'

def responds(url):
    try:
        with urllib.request.urlopen(url,timeout=2) as r:return r.status==200
    except Exception:return False

def start():
    env=dict(os.environ)
    env.update(OLLAMA_HOST='127.0.0.1:11434',OLLAMA_MODELS=str(ROOT/'data/ollama-models'),OLLAMA_NO_CLOUD='1',OLLAMA_MAX_LOADED_MODELS='1',PYTHONPYCACHEPREFIX=str(ROOT/'data/pycache'))
    services=[('ollama',[str(OLLAMA),'serve'],ROOT,'http://127.0.0.1:11434/api/tags'),('api',[str(PYTHON),'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000','--no-access-log'],ROOT,'http://127.0.0.1:8000/health'),('web',['/opt/homebrew/bin/node',str(ROOT/'frontend/node_modules/next/dist/bin/next'),'start','--hostname','127.0.0.1'],ROOT/'frontend','http://127.0.0.1:3000')]
    for name,command,cwd,url in services:
        if responds(url):
            print(f'{name}: already running');continue
        with (RUN/f'{name}.log').open('ab') as log:
            proc=subprocess.Popen(command,cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
        (RUN/f'{name}.pid').write_text(str(proc.pid))
        for _ in range(40):
            if responds(url):break
            if proc.poll() is not None:raise SystemExit(f'{name} failed. See {RUN/name}.log')
            time.sleep(.5)
        else:raise SystemExit(f'{name} is not ready. See {RUN/name}.log')
        print(f'{name}: ready')
    print('Open http://localhost:3000')

def stop():
    def owned(pid):
        result=subprocess.run(['lsof','-a','-p',str(pid),'-d','cwd','-Fn'],capture_output=True,text=True)
        return any(line in {'n'+str(ROOT),'n'+str(ROOT/'frontend')} for line in result.stdout.splitlines())
    for name in ['web','api','ollama']:
        path=RUN/f'{name}.pid'
        if path.exists():
            pid=int(path.read_text())
            # Verify ownership by command before signalling a potentially reused PID.
            result=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True)
            command=result.stdout
            if str(ROOT) in command or owned(pid):
                try:os.kill(pid,signal.SIGTERM)
                except ProcessLookupError:pass
                for _ in range(100):
                    result=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True)
                    if str(ROOT) not in result.stdout and not owned(pid):break
                    time.sleep(.1)
                else:
                    raise SystemExit(f'{name} is still shutting down; retry stop before restarting.')
            path.unlink()
    print('Stopped services started by this launcher.')

def status():
    for name,url in [('ollama','http://127.0.0.1:11434/api/tags'),('api','http://127.0.0.1:8000/health'),('web','http://127.0.0.1:3000')]: print(name+': '+('ready' if responds(url) else 'stopped'))

if __name__=='__main__':
    action=sys.argv[1] if len(sys.argv)>1 else 'start'
    if action not in ['start','stop','status']:raise SystemExit('Use start, stop, or status')
    globals()[action]()
