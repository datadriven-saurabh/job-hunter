import copy
import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
import httpx
from pydantic import BaseModel
from backend import database as db

CONFIG_PATH = db.ROOT/'config/ai.json'


def settings():
    value=json.loads(CONFIG_PATH.read_text())
    saved=(db.config() or {}).get('llm_provider_config',{})
    value['tiers'].update({k:v for k,v in saved.get('model_tiers',{}).items() if v})
    for tier in ['medium','strong']:
        if not value['tiers'][tier]:value['tiers'][tier]=saved.get('reasoning_model','qwen3:4b')
    return value


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()


class ModelUnavailable(ValueError):pass


class ModelRouter:
    def __init__(self, overrides=None):
        self.config=settings()
        if overrides:self.config['tiers'].update(overrides)
        self.events=[]

    def get(self,task):
        tier=self.config['tasks'][task]
        return {'tier':tier,'model':self.config['tiers'][tier]}

    def _url(self):
        from schemas import LLMProviderConfig
        saved=(db.config() or {}).get('llm_provider_config',{})
        return LLMProviderConfig(**saved).local_ollama_base_url.rstrip('/')

    def _log(self,event):
        self.events.append(event)
        path=db.DATA/'ai-usage.jsonl'
        with path.open('a') as stream:stream.write(json.dumps(dict(event,created_at=datetime.now(timezone.utc).isoformat()))+'\n')

    def _identity(self,model):
        if os.getenv("ENABLE_LOCAL_LLM") != "true":raise ModelUnavailable("Local AI disabled.")
        try:
            r=httpx.get(self._url()+'/api/tags',timeout=3,trust_env=False);r.raise_for_status()
            found=next((m for m in r.json().get('models',[]) if m['name']==model or m['name']==model+':latest'),None)
            if found:return found.get('digest') or found['name']
        except Exception:pass
        raise ModelUnavailable('Configured local model is not installed or Ollama is unavailable: '+str(model))

    def run(self,task,prompt,schema,*,validator=None):
        if os.getenv('ENABLE_LOCAL_LLM')!='true':raise ModelUnavailable('Local AI is disabled; evidence-only generation is available.')
        route=self.get(task);model=route['model'];tier=route['tier']
        candidates=[(tier,model),(tier,model)]
        if tier=='small' and self.config['tiers']['medium']!=model:candidates.append(('medium',self.config['tiers']['medium']))
        errors=[]
        for attempt,(used_tier,used_model) in enumerate(candidates):
            started=time.monotonic();event={'task':task,'tier':used_tier,'model':used_model,'retry_count':attempt,'fallback_used':used_tier!=tier,'cache_hit':False,'input_tokens':0,'output_tokens':0}
            try:
                identity=self._identity(used_model)
                key=digest([self.config['version'],prompt,used_model,identity,schema.model_json_schema()])
                path=db.DATA/'ai-cache'/f'{key}.json'
                if path.exists():
                    result=schema.model_validate(json.loads(path.read_text()))
                    if validator:validator(result)
                    event.update(cache_hit=True,latency_ms=0,prompt_version=prompt['version']);self._log(event);return result
                body={'model':used_model,'system':prompt['system'],'prompt':prompt['context']+('\nValidation feedback: '+errors[-1] if errors else ''),'stream':False,'format':schema.model_json_schema(),'options':{'temperature':0,'num_ctx':self.config['context_tokens'],'num_predict':self.config['output_tokens']},'keep_alive':'5m'}
                if used_model.startswith('qwen3'):body['think']=False
                r=httpx.post(self._url()+'/api/generate',json=body,timeout=self.config['timeout_seconds'],trust_env=False);r.raise_for_status();raw=r.json()
                result=schema.model_validate_json(raw['response'])
                if validator:validator(result)
                path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.'+uuid.uuid4().hex+'.tmp');tmp.write_text(result.model_dump_json());tmp.replace(path)
                event.update(input_tokens=raw.get('prompt_eval_count',0),output_tokens=raw.get('eval_count',0),prompt_version=prompt['version'],model_version=identity)
                event['latency_ms']=round((time.monotonic()-started)*1000);self._log(event);return result
            except Exception as exc:
                # No prompts, profiles, model outputs, or exception bodies in telemetry.
                errors.append('Output failed schema or evidence validation; use only the supplied evidence and required fields.')
                event.update(status='failed',error_type=type(exc).__name__,latency_ms=round((time.monotonic()-started)*1000));self._log(event)
                if isinstance(exc,ModelUnavailable):break
        raise ModelUnavailable('No validated model output was available. Use verified evidence or review missing fields.')

    def embed(self,text):
        if os.getenv('ENABLE_LOCAL_LLM')!='true':raise ModelUnavailable('Local AI disabled.')
        route=self.get('embeddings');identity=self._identity(route['model'])
        key=digest(['embedding-v1',text,identity]);path=db.DATA/'ai-cache'/f'{key}.json'
        started=time.monotonic();hit=path.exists()
        if hit:vector=json.loads(path.read_text())
        else:
            r=httpx.post(self._url()+'/api/embed',json={'model':route['model'],'input':text,'truncate':False},timeout=self.config['timeout_seconds'],trust_env=False);r.raise_for_status()
            vector=r.json()['embeddings'][0]
            if not vector or not all(isinstance(x,(float,int)) for x in vector):raise ValueError('Invalid embedding')
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(vector))
        self._log({'task':'embeddings',**route,'cache_hit':hit,'latency_ms':round((time.monotonic()-started)*1000),'model_version':identity})
        return vector
