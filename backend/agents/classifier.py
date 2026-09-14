from urllib.parse import urlparse

def classify(job):
    host = urlparse(job['job_url']).hostname or ''
    text = job.get('description', '').lower()
    trusted = host in {'jobs.lever.co', 'boards.greenhouse.io', 'job-boards.greenhouse.io'}
    blocked = any(x in text for x in ['captcha', 'sign in to apply', 'create an account', 'cloudflare'])
    return 'HEADLESS_AUTO' if trusted and not blocked else 'HUMAN_IN_THE_LOOP_LINK'
