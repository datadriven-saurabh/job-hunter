# Tester security review — 15 September 2026

## Release decision and scope

Suitable for a limited local tester trial after applying this update, using a fresh source-only installation, trusted local OS/browser access, and live submission disabled. This is not approval for public hosting or a shared multi-user server.

Reviewed the FastAPI routes, browser/extension boundary, public URL fetching, uploads, document generation, optional submission, local-model requests, Next.js configuration, dependency advisories, Git history and source distribution contents. This was a code/configuration review with focused regression tests, not an independent penetration test, parser fuzzing campaign or container/OS vulnerability assessment.

## Findings addressed

| Finding | Risk | Change |
| --- | --- | --- |
| Old Python dependency set | Scanner reported 40 advisory matches in 15 packages, including framework/upload and LangGraph dependencies; exploitability varies by code path. | Upgraded to a tested Python 3.12 environment and current compatible dependencies; added exact dependency constraints for reproducibility. |
| Any Chrome extension origin trusted | Origin-bearing requests from unrelated extensions could read profile/documents or mutate the workspace. | Reject unknown extension origins. The optional helper now requires its exact ID in `TRUSTED_EXTENSION_IDS`. |
| Cross-site request and browser-cache exposure | Requests without Origin could reach routes, and private API responses lacked an explicit cache policy. | Reject cross-site Fetch Metadata requests without an approved Origin; set no-store, nosniff, no-referrer and frame protections. |
| Upload body checked too late | Multipart parsing could consume resources before the 10 MB file limit ran. | Bound the whole request before parsing: 11 MB for multipart upload, 1 MB for other routes, including chunked bodies. The file itself remains limited to 10 MB. |
| Public fetching read entire responses before checking size | A large response could consume unnecessary memory; redirect port/credentials checks were incomplete. | Stream bounded responses, validate HTTPS/host/port/credentials at every redirect, and use the same helper for Greenhouse/Lever. |
| Optional browser worker guarded only navigation | Other request types could contact arbitrary destinations from a loaded page. | Apply HTTPS/host restrictions to all routed HTTP requests; block service workers. Some employer forms may require manual completion. |
| Ambient proxy/tracing settings | An inherited proxy or cloud tracing setting could violate the local-only data expectation. | Local-model HTTP calls ignore environment proxies; application startup disables LangChain/LangSmith cloud tracing. |
| Remote font request | Opening the UI contacted Google Fonts, exposing network metadata. | Removed external font loading; use local/system fonts. Disable Next.js telemetry in project configuration and Docker builds. |
| Local file permissions | New personal files could inherit permissive OS defaults. | Use owner-only permissions for the data directory and restrictive file creation on POSIX systems. Windows relies on its OS account permissions. |
| Distribution context gap | Frontend Docker context did not exclude local `.env` files. | Exclude frontend local environment files and logs; document source-only packaging. |

## Validation evidence

- Initial installed Python environment: **40 advisory matches / 15 packages**.
- Patched clean Python 3.12 environment: **0 known vulnerabilities reported by pip-audit**.
- Locked frontend dependency set: **0 vulnerabilities reported by npm audit**.
- Next.js 16.3.5 exceeds the 16.3.3 fix version in the [maintainer's August security advisory](https://nextjs.org/blog/august-2026-security-release).
- **27 tests passed**, including the synthetic Chromium form test; frontend production build and dependency compatibility checks passed. Both Docker Compose configurations validate.
- Regression checks cover hostile origins, trusted-extension configuration, DNS-rebinding Host rejection, cache headers, declared/chunked body limits, restricted redirects/ports, response limits and local proxy avoidance.
- Existing tests cover resume parsing, traversal-style upload filenames, URL restrictions, factual PDFs, workflow states and submission gates.
- Reviewed reachable Git-history blobs and current source against actual saved contact values locally, plus credential patterns. **No matches for the owner's saved name, email, phone or LinkedIn URL were found in source/history. No private data files were tracked.** Values were not sent to advisory services or written to this report.
- Public GitHub repository/maintainer identity and synthetic example profiles are intentional. Historical ignore rules mention a personal-note filename, but its content is excluded.

## Remaining limits

1. **No authentication between local processes/users.** Origin/Host checks protect browser boundaries, not malicious programs, privileged extensions or someone with access to the same files. Do not share a running instance or expose ports publicly.
2. **Local data is not encrypted by the app.** Use OS account permissions and disk encryption. Backups, exported PDFs and logs may contain personal information. Never share a working-folder ZIP.
3. **Untrusted document parsing is not sandboxed.** File/body/page limits reduce resource risk but cannot prove every malicious PDF/DOCX safe. Test with resumes you control; do not accept anonymous uploads.
4. **External application forms are outside this review.** Live submission is disabled in distributed defaults. Optional manual autofill shares selected details with the page the user chooses; review the destination and answers. No real applications or messages were sent during security testing.
5. **Docker images and Windows/Linux native runtime execution were not verified in this review.** Docker configurations were validated; the local Docker engine was unavailable. Keep Docker, browsers, Python and Node patched independently.
6. Dependency results are a point-in-time check, not a security guarantee. Refresh the locks and rerun audits before subsequent tester releases.

## How to distribute

Share the repository download or a ZIP made with `git archive` from the reviewed commit. This exports tracked source, not `.git`, `.env`, `data`, `.runtime`, generated documents or local dependency folders. Inspect the archive before sharing. Never include an existing database to make onboarding easier: use the built-in fictitious demo instead.

Existing users of the old Python 3.9 environment must create a fresh Python 3.11/3.12 virtual environment and install the updated requirements. Preserve personal data privately; do not copy the previous environment into a release.
