"""Optional local model adapter. No profile data is sent to a hosted model."""
import json
import os
from urllib.parse import urlparse
import httpx

def generate_json(prompt, config, schema=None):
    if os.getenv('ENABLE_LOCAL_LLM')!='true': return None
    base=config['llm_provider_config']['local_ollama_base_url']
    parsed=urlparse(base)
    if parsed.hostname not in {'localhost','127.0.0.1','::1'} or parsed.scheme not in {'http','https'}:
        raise ValueError('Local model URL must use a loopback address.')
    response=httpx.post(base.rstrip('/')+'/api/generate',json={'model':config['llm_provider_config']['reasoning_model'],'prompt':prompt,'stream':False,**({'think':False} if config['llm_provider_config']['reasoning_model'].startswith(('qwen3','nemotron-3-nano')) else {}),'format':schema or 'json','keep_alive':'10m','options':{'temperature':0.2,'num_ctx':8192,'num_predict':1800}},timeout=180,trust_env=False)
    response.raise_for_status()
    result=response.json()
    try:
        output=json.loads(result['response'])
    except (ValueError,KeyError) as exc:
        raise ValueError('The local model returned incomplete JSON. Try again or use a smaller request.') from exc
    if not isinstance(output,dict): raise ValueError('The local model must return a JSON object.')
    return output
