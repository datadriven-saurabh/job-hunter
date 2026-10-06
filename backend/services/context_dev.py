"""The sole server-side Context.dev client for public job-search queries."""
import os

from context.dev import APIConnectionError, APIStatusError, APITimeoutError, ContextDev


class ContextSearchError(ValueError):
    pass


JOB_DOMAINS = [
    'jobs.ashbyhq.com', 'jobs.lever.co', 'job-boards.greenhouse.io',
    'boards.greenhouse.io', 'jobs.smartrecruiters.com', 'apply.workable.com',
]


def search_web(query: str, *, max_retries: int = 1) -> dict:
    """Return one bounded search batch; never send profile or resume contents."""
    key = os.getenv('CONTEXT_DEV_API_KEY', '').strip()
    if not key:
        raise ContextSearchError('Context.dev is not configured. Set CONTEXT_DEV_API_KEY on the server.')
    try:
        with ContextDev(api_key=key, timeout=75.0, max_retries=max_retries) as client:
            response = client.web.search(
                query=query,
                num_results=10,
                include_domains=JOB_DOMAINS,
                markdown_options={
                    'enabled': True,
                    'use_main_content_only': True,
                    'include_links': False,
                    'max_age_ms': 7 * 24 * 60 * 60 * 1000,
                    'pdf': {'should_parse': False},
                },
                timeout_opts={'milliseconds': 60000, 'behavior': 'return-partial'},
            )
    except APIStatusError as exc:
        raise ContextSearchError(f'Context.dev search unavailable (HTTP {exc.status_code}).') from None
    except (APIConnectionError, APITimeoutError):
        raise ContextSearchError('Context.dev search timed out or could not connect.') from None
    return {
        'results': [
            {
                'url': item.url,
                'title': item.title,
                'snippet': item.description,
                'markdown': item.markdown.markdown if item.markdown.code == 'SUCCESS' else None,
            }
            for item in response.results
        ],
        'partial': bool(response.partial),
        'request_id': response.request_id,
        'credits_used': response.key_metadata.credits_consumed if response.key_metadata else None,
    }
