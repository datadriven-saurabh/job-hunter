# Public private-beta deployment

This guide deploys the existing Next.js interface to Vercel, the FastAPI service to Render, and private user data to Supabase. The infrastructure has a zero-cost option for a 3–4 person beta. Render's free service sleeps after 15 minutes without traffic, so the first request after a quiet period can take about a minute.

The hosted edition disables local Ollama management and browser-based submission. Job discovery, matching, resume upload and parsing, application tracking, Application Studio, private downloads, cover letters, referral drafts, and interview practice remain available.

## 1. Create the Supabase project

1. Sign in at [Supabase](https://supabase.com/dashboard/projects) and choose **New project**.
2. Use a generated database password and save it in a password manager. Do not put it in this repository.
3. Open **SQL Editor**, choose **New query**, and run these files in order:
   1. `supabase/migrations/001_initial_schema.sql`
   2. `supabase/migrations/002_rls.sql`
   3. `supabase/migrations/003_storage.sql`
4. Open **Project Settings → API** and copy the project URL and publishable/anon key.
5. Open **Project Settings → Database → Connect** and copy the **Session pooler** URI. Replace the password placeholder with the saved database password. This is `DATABASE_URL` and is server-only.
6. Under **Authentication → URL Configuration**, initially add `http://localhost:3000/**`. Add the Vercel URL after step 3.

The migrations create a private `resumes` bucket and a private `artifacts` bucket. Browser clients cannot query product tables directly. The backend uses a restricted `job_hunter_backend` role with the verified user's Supabase ID, and RLS checks `user_id = auth.uid()`.

## 2. Deploy the backend to Render

1. Sign in at [Render](https://dashboard.render.com/) with the GitHub account that can access the repository.
2. Choose **New → Blueprint** and select this repository. Render reads `render.yaml` and `Dockerfile.hosted`.
3. Choose the **Free** service plan and enter:

   | Variable | Value |
   | --- | --- |
   | `DATABASE_URL` | Supabase Session pooler URI; secret |
   | `SUPABASE_URL` | Supabase project URL |
   | `SUPABASE_ANON_KEY` | Supabase publishable/anon key |
   | `APP_URL` | Temporarily `http://localhost:3000`; replace after Vercel deploy |

4. Deploy and wait for `/health` to report `{"status":"healthy", ... "mode":"hosted"}`.
5. Copy the `https://...onrender.com` service URL.

Do not add a service-role key. This application does not need one for normal requests.

## 3. Deploy the frontend to Vercel

1. Sign in at [Vercel](https://vercel.com/new) with GitHub.
2. Import this repository and set **Root Directory** to `frontend`.
3. Add these build-time variables:

   | Variable | Value |
   | --- | --- |
   | `NEXT_PUBLIC_API_URL` | Render service URL, with no trailing slash |
   | `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase publishable/anon key |

4. Deploy and copy the `https://...vercel.app` URL.
5. In Render, change `APP_URL` to that exact Vercel origin and redeploy.
6. In Supabase **Authentication → URL Configuration**, set the site URL to the Vercel URL and add `https://YOUR-PROJECT.vercel.app/**` as a redirect URL.

Only the Supabase publishable/anon key is present in browser code. `DATABASE_URL` and optional LLM keys stay in Render or GitHub secrets.

## 4. Configure the six-hour refresh

In GitHub, open **Settings → Secrets and variables → Actions** and add:

- `DATABASE_URL`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`

The `Refresh public jobs` workflow runs every six hours and can also be run manually. It has a 20-minute timeout and a 500-job ceiling. It uses public sources only and does not bypass authentication, CAPTCHAs, robots restrictions, or access blocks.

## 5. Verify before inviting testers

1. Create two test accounts with different email addresses.
2. Complete each profile and upload a different TXT or PDF resume.
3. In account A, import or discover an opportunity and move it to Reviewing.
4. Copy account A's resume ID, job ID, and kit ID from browser network responses.
5. While signed in as B, request the matching API routes using those IDs. Each must return 404/403 or an empty result.
6. Repeat in the other direction.
7. Confirm B never sees A's profile, resume, opportunity, kit, answer, or document in the UI.
8. Run the repository tests and inspect both provider logs for secrets or raw resume text.

Do not invite testers until this two-account check passes against the deployed environment.

## Rollback

- Vercel: choose the last working deployment and **Promote to Production**.
- Render: open **Deploys**, select one of the retained deploys, and roll back.
- Database: migrations are forward-only. Before a destructive schema change, export a logical backup from Supabase and test the migration in a separate project.
- To take the beta offline immediately, pause/delete the Render service and remove the Supabase Auth redirect URL. Stored data remains private in Supabase until explicitly deleted.

## Required environment variables

Backend (Render): `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `APP_URL`.

Frontend (Vercel): `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

Optional server-only AI variables: `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`. These are never required for deterministic matching and grounded templates.
