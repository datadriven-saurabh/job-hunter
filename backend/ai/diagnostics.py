"""Authenticated synthetic connection checks; credentials never leave the server."""
import json
from pydantic import BaseModel, ConfigDict, Field
from backend.ai.router import ModelRouter, ModelUnavailable


class ConnectionEvidence(BaseModel):
    model_config = ConfigDict(extra='forbid')
    matched: list[str] = Field(max_length=3)
    missing: list[str] = Field(max_length=3)


def active_routes():
    router = ModelRouter()
    return list({(r['provider'], r['model']): r for task in ('job_extraction', 'scoring')
                 for r in router._cloud_candidates(task)}.values())


def connection_status():
    return {'routes': active_routes(), 'grounded_fallback': True,
            'method': 'A connection check uses synthetic SQL/Python evidence. No profile or documents are sent.'}


def check_connections():
    prompt = {'version': 'connection-check-v1',
              'system': 'Extract exact supported skills from evidence. Return matched and missing arrays. Never invent skills.',
              'context': json.dumps({'evidence': 'I built SQL dashboards and Python pipelines.',
                                     'required_skills': ['SQL', 'Python', 'dbt'],
                                     'TARGET_JOB_DESCRIPTION': {'job_title': 'Synthetic connection check',
                                         'company_name': 'Example',
                                         'description': 'Evidence: I built SQL dashboards and Python pipelines. Required skills to check: SQL, Python, dbt.'}})}

    def validate(result):
        if sorted(result.matched) != ['Python', 'SQL'] or result.missing != ['dbt']:
            raise ValueError('Synthetic evidence check failed')

    def probe(routes, task):
        router = ModelRouter()
        router.cache_enabled = False
        router.config['cloud_output_tokens'][task] = 256
        router._cloud_candidates = lambda _task: routes
        try:
            router._run_cloud(task, prompt, ConnectionEvidence, validate)
            status = 'passed'
        except ModelUnavailable:
            status = 'rules_ready' if not routes else 'failed'
        return {'status': status, 'events': router.events}

    routes = active_routes()
    results = [{**route, **probe([route], 'scoring' if route['model'].endswith('120b') else 'job_extraction')}
               for route in routes[:5]]
    # Bypass the primary provider for this request only. Global routing is unchanged.
    backup = [route for route in routes if route['provider'] != routes[0]['provider']] if routes else []
    fallback = probe(backup, 'job_extraction')
    return {**connection_status(), 'results': results, 'fallback_check': fallback}
