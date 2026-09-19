# Using Job Hunter

## 1. Create your profile

Open My profile. Enter your actual contact information, work authorization and career facts. Add each role with dates and achievements, then your education. Save.

A good achievement says what you did, how you did it and what changed. Use a measured result only when it is true. The app does not invent credentials, experience or metrics.

The demo contains Alex Morgan and fictitious opportunities. It is for learning the interface. It does not overwrite an existing profile, and demo applications cannot be sent externally.

## 2. Choose preferences

Set your target roles and locations. Start broadly, such as `Data Analyst` and `Remote`, then narrow the results. Choose a default maximum posting age if you only want recent, source-dated listings. Remote work may still be limited to particular countries or time zones. Set your actual work authorization in My profile; the app cannot verify visa eligibility.

Required search keywords are strict filters. Requiring several tools can exclude useful openings. Unknown employment types remain available for review.

## 3. Find jobs

Click Find opportunities. Choose a public feed or a company board, enter keywords, choose the maximum posting age for this search, then Find openings. **Any age** retains jobs with unknown dates. A specific window excludes listings that are too old and listings whose source did not provide a usable posting date. The filter affects newly discovered results; it does not remove saved or reviewing opportunities.

A **company board identifier** is the employer's part of its career URL. For example, in `https://jobs.lever.co/example-company`, the identifier is `example-company`. This is a format example, not a real board to use. Greenhouse, Lever, Ashby and SmartRecruiters need a real employer identifier.

Source reports distinguish new jobs, previously seen or duplicate postings, keyword candidates and preference conflicts. Searches skip saved jobs, including deleted entries; changing filters can reconsider previously excluded candidates. They do not report the total size of a website's job database. Results may be cached to avoid excessive requests. A zero can mean no keyword matches; HTTP 403/429 means the site blocked or limited a request. Do not repeatedly retry a blocked source.

If a job isn't available through discovery, use Application Studio to paste its URL and full description. That creates a draft kit without adding it to the application tracker. To track it, choose **Import a posting manually** in Find opportunities; tracker imports still use your preference filters. Enter the source posting date when known. It is required for an import to pass an active maximum-age preference.

## 4. Understand your scores

**Profile fit** prioritizes jobs using current profile evidence:

- 65% recognized job-skill coverage.
- 25% target-role alignment.
- 10% general experience.

Open a job's **Why this job ranks here** panel to inspect the source excerpts and gaps. Missing evidence means the skill wasn't found in your profile, not proof that you don't have it. Add skills only if accurate. Scores update when your profile or preferences change.

Priority labels: Apply first, Consider, Stretch / low fit, and Review details. Short descriptions, preference conflicts and detected location/language restrictions need review. Scores are transparent heuristics, not hiring probabilities. Review the actual posting for qualifications the parser may miss.

**Resume text similarity** compares your uploaded resume versions with the job description. It is separate from profile fit. It helps choose a version; it does not measure your chance of getting hired.

## 5. Upload resumes

In My documents, choose Upload resumes. You can select several files. Each may be up to 10 MB: text-readable PDF, DOCX, or UTF-8 TXT. A scanned image PDF needs OCR before upload.

The app stores each original and extracts a local keyword corpus. Uploading opens an editable profile draft and suggested job titles. It does **not** replace My profile until you review and save the draft. You can review extracted text, rename versions so matching suggestions are recognizable, build a new draft from any version, or delete an upload. Deleting an upload retains the already-saved profile and existing job kits.

## 6. Review opportunities and create a one-page application kit

In New opportunities, choose **Review** for one job or select several and choose **Move selected to Reviewing**. Those jobs leave New, remain stable across later searches, and start their Application Studio kits in the background. Open Reviewing to see preparation status and open the saved workspace. If preparation is interrupted, Application Studio shows a retry action.

Open Application studio, or use its shortcut in a job's detail panel.

1. Select a saved job, or enter a public posting URL and click Read public job link.
2. Check the title, employer and description. For blocked or unsupported pages, paste the missing information yourself.
3. Optionally enter the name of a recipient you have verified.
4. Wait for the background kit or click Create validated application kit. Creating again saves a new version; earlier versions remain selectable.
5. Preview/download the one-page PDF. Edit the cover letter, connection note and referral message as needed.
6. Click Save edited drafts before downloading the text; downloads contain the last saved version.

**Application Studio uses My profile**, not an uploaded resume variant. It selects relevant existing bullets, preserves role/date facts and validates one-page output. The full history stays in your profile. If unusually long text cannot fit legibly, shorten it instead of expecting tiny text or clipping.

Standard **Prepare applications** also uses the fixed one-page template and verified My profile facts. The preparation dialog shows the closest text match, but its generation source is Profile resume. If an uploaded version has better achievements, review its extracted text in My documents, then add and verify those facts in Application Studio → Candidate evidence. Original uploads remain downloadable for manual applications. Changing a resume selection invalidates previously prepared documents.

## 7. Find people and draft referral requests

The kit shows contact names explicitly found in job descriptions, with the supporting excerpt. Other links open LinkedIn searches for related employees, recruiters and possible team leads.

These are leads, not verified current employees or confirmed hiring managers. The app is not connected to your private LinkedIn connection graph. Check the person's identity, current employer and role in your own browser.

The short connection note and longer referral message are editable drafts. No connection request, LinkedIn message or email is sent automatically. Copy only the text you want to use, personalize it and send it yourself after reviewing.

## 8. Track applications and practice

Use Applications to view your pipeline. **I submitted this** records a submission you made yourself; it doesn't submit a form. Update interview, offer or archived status as your search progresses.

Interview coach provides template-based practice without a model. With local AI enabled, it uses your installed selected model. Feedback is practice guidance, not a factual assessment of your employment prospects.

## Optional Chrome autofill

1. Open Chrome and visit `chrome://extensions`.
2. Turn on Developer mode and click Load unpacked.
3. Select this project's **extension** folder, not the project root.
4. Copy the extension’s 32-letter ID from `chrome://extensions`. Add `TRUSTED_EXTENSION_IDS=that_id` to your local `.env` (create it from `.env.example` if needed), then restart the API. Docker users run `docker compose up -d` to apply the setting. Only explicitly trusted extensions can access the API.
5. Open a saved job's exact application URL.
6. Open the extension, select that job and choose Fill this application.
7. Review all fields, attach your resume and complete the employer's remaining steps yourself.

To capture a hiring post shared by someone on LinkedIn, open that individual post, open the extension, and choose **Capture visible LinkedIn post**. Enter or correct the exact job title, company, location, and application URL, review the captured post text, then choose **Import and match**. The extension reads only the visible post after you click; it does not crawl your feed, access your connection graph, bypass LinkedIn controls, or send a connection request.

The extension fills supported visible empty contact fields. It does not overwrite existing answers or submit. It cannot solve every form or login flow. It connects to the API on localhost:8000.

## Optional live submission — advanced

Leave this off while learning the app. Both the server's `ENABLE_LIVE_SUBMISSION=true` setting and the saved headless-application preference must be enabled. The default setup disables it. Enabling only a UI preference is insufficient.

Prepare, download and review documents, then use the explicit reviewed-submission control for eligible non-demo Lever/Greenhouse jobs. Supported URLs, score thresholds, a real profile and the daily limit are checked. Missing required fields, authentication, CAPTCHA or an unconfirmed result require human review. Generic browser support is not guaranteed for every employer. Unconfirmed submissions are not automatically retried.

In native setup, edit `.env` and restart. Docker uses its Compose environment; native `.env` AI/submission settings do not override the base Docker configuration.

## Search all supported sources

In Find opportunities, choose **Select all public boards** to check the currently available public sources (21 at release). To include Greenhouse, Lever, Ashby or SmartRecruiters, check each one and enter a real employer board slug. Public-page adapters inspect at most 10 new posting pages per check, so results are a limited snapshot. Known blocked sources are removed from the picker and kept in **Job board directory** for manual import. Newly blocked boards report Unavailable and are paused for one hour across searches. A working browser login does not grant the app API access. [Current source checks](PRODUCT_REVIEW.md#public-source-checks)

Discover jobs shows 100 opportunities per page; use Next page and Previous page to reach the rest. Select all selects only the visible page.

## Recover an edit conflict

If saving says your profile changed in another editor, keep a copy of your unsaved changes. Reopen My profile or use Reload saved evidence, then reapply those changes to the latest saved profile. This prevents an old editor from overwriting newer facts.
