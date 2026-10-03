"""Bounded source fetching with the caller's tenant identity in every worker."""
from concurrent.futures import ThreadPoolExecutor, wait
from contextvars import copy_context

# Shared pool bounds work across simultaneous searches, including timed-out calls.
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='job-source')


SOURCE_TIMEOUT_SECONDS = 300


def fetch_sources(providers, fetch, timeout=SOURCE_TIMEOUT_SECONDS):
    futures = [_pool.submit(copy_context().run, fetch, provider) for provider in providers]
    done, pending = wait(futures, timeout=timeout)
    for future in pending:
        future.cancel()
    results = []
    for future in futures:
        if future not in done:
            results.append(TimeoutError('This source took too long. Other sources completed; retry this board separately.'))
        else:
            try:
                results.append(future.result())
            except Exception as exc:
                results.append(exc)
    return results
