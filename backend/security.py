"""Browser-origin and request-size boundaries for the single-user local edition."""
import os
import re
from starlette.responses import JSONResponse

WEB_ORIGINS = {'http://localhost:3000', 'http://127.0.0.1:3000',
               'http://localhost:8000', 'http://127.0.0.1:8000'}


def extension_origins():
    return {'chrome-extension://' + value.strip()
            for value in os.getenv('TRUSTED_EXTENSION_IDS', '').split(',')
            if re.fullmatch('[a-p]{32}', value.strip())}


class LocalSecurityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = dict(scope['headers'])
        origin = headers.get(b'origin', b'').decode('latin1')
        extensions = extension_origins()
        if ((origin and origin not in WEB_ORIGINS | extensions)
                or (not origin and headers.get(b'sec-fetch-site') == b'cross-site')):
            return await JSONResponse({'detail': 'Untrusted origin'}, status_code=403)(scope, receive, send)
        # Bound the entire body before multipart parsing/spooling, including chunked uploads.
        limit = (11 if scope['path'] == '/api/v1/resumes/upload' else 1) * 1024 * 1024
        length = headers.get(b'content-length')
        if length is not None:
            try:
                size = int(length)
                if size < 0: raise ValueError()
            except ValueError:
                return await JSONResponse({'detail': 'Invalid content length'}, status_code=400)(scope, receive, send)
            if size > limit:
                return await JSONResponse({'detail': 'Request body too large'}, status_code=413)(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect': return
            body.extend(message.get('body', b''))
            if len(body) > limit:
                return await JSONResponse({'detail': 'Request body too large'}, status_code=413)(scope, receive, send)
            if not message.get('more_body', False): break
        delivered = False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
            return await receive()
        async def secure_send(message):
            if message['type'] == 'http.response.start':
                extra = [(b'cache-control', b'no-store'), (b'x-content-type-options', b'nosniff'),
                         (b'referrer-policy', b'no-referrer'), (b'x-frame-options', b'DENY')]
                if origin in extensions:
                    extra += [(b'access-control-allow-origin', origin.encode()), (b'vary', b'Origin'),
                              (b'access-control-allow-methods', b'GET, POST, PATCH, OPTIONS'),
                              (b'access-control-allow-headers', b'Content-Type')]
                names = {name for name, _ in extra}
                message['headers'] = [(k, v) for k, v in message.get('headers', []) if k.lower() not in names] + extra
            await send(message)
        if scope['method'] == 'OPTIONS' and origin in extensions:
            return await JSONResponse({}, status_code=200)(scope, replay, secure_send)
        return await self.app(scope, replay, secure_send)
