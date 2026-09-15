# Job Hunter

**Focus your search. Make your move.**

Job Hunter brings job discovery, profile matching, tailored resumes and outreach into one focused workspace. Spend less time organizing your search and more time preparing for the right opportunities—all on **your own computer**.

**Each person installs their own copy.** Profiles and resumes are saved locally and are not shared with other users or included in this repository. This is a single-person local app, not a hosted website with multiple user accounts.

## What you can do

- Discover jobs from public feeds and company career boards.
- Rank openings against your skills and experience, with evidence and gaps.
- Upload several PDF, DOCX or TXT resumes and compare their relevance to a job.
- Generate a **one-page ATS resume** from your saved profile.
- Draft and edit cover letters, LinkedIn connection notes and referral messages.
- Use a saved job or paste a job link and description.
- Find contact names mentioned in a posting and open relevant LinkedIn searches.
- Practice interviews and optionally compare local AI models.

Drafting, PDF creation, matching and public discovery work **without paid API keys or an AI model**. An internet connection is needed to download the app and fetch live jobs. AI models are optional downloads.

## Quick start — recommended for beginners

Use Docker to avoid installing Python and Node.js separately. These steps work on Windows, macOS and Linux with Docker Compose.

### 1. Install and open Docker

Install [Docker Desktop](https://docs.docker.com/get-started/get-docker/) for your system, open it and wait until it says the engine is running. Follow any restart or virtualization instructions in the installer. Check Docker's licensing terms for your usage.

### 2. Download this project

On [this repository](https://github.com/datadriven-saurabh/job-hunter), choose **Code → Download ZIP**. Extract the ZIP into a folder you own, such as Documents. Do not run commands from inside the ZIP.

If you already use Git, you can download it this way instead:

```sh
git clone https://github.com/datadriven-saurabh/job-hunter.git
cd job-hunter
```

If GitHub asks you to sign in, use your own account with access to the repository. Never paste a token or password into this app's files.

### 3. Open a terminal in the project folder

- **Windows:** open the extracted folder in File Explorer, right-click empty space and choose **Open in Terminal**.
- **macOS:** open Terminal, type `cd ` with a trailing space, drag the extracted folder into Terminal, then press Enter.
- **Linux:** right-click the extracted folder and choose **Open in Terminal**, or use `cd`.

You should be in the folder containing `README.md` and `docker-compose.yml`.

### 4. Start the app

Copy this line into the terminal and press Enter:

```sh
docker compose up --build -d
```

The first run downloads dependencies and a browser runtime, so it can take several minutes and use several GB of disk space. Later starts are faster. If the command reports an error, see [Troubleshooting](docs/TROUBLESHOOTING.md).

### 5. Open your workspace

Open **[http://localhost:3000](http://localhost:3000)** in your browser. Wait for **Local engine connected**.

Start with **Create my profile**, enter your own details, then set **Preferences**. For a practice run you can load the clearly labeled fictitious demo; replace its details before making a real application.

See the step-by-step [user guide](docs/USER_GUIDE.md) for the full workflow. No account with this app is needed.

### Start again, stop or update

Run these commands from the same project folder:

| Task | Command |
| --- | --- |
| Start again | `docker compose up -d` |
| Check services | `docker compose ps` |
| Read recent logs | `docker compose logs --tail=80` |
| Stop | `docker compose down` |

Stopping does **not** delete your local `data` folder. Do not delete that folder if you want to keep your profile, applications and documents.

To update a Git installation: stop the app, back up `data`, run `git pull --ff-only`, then `docker compose up --build -d`. For ZIP installations, extract the new release into a new folder and copy your backed-up `data` folder into it before starting. Stop the old copy first so the ports are free.

## What to enter first

1. **My profile:** contact details, work authorization, professional summary, skills, experience and education. This is the factual source for Application Studio.
2. **Preferences:** job titles and locations you want, employment type, and any required search terms. Start with broad filters.
3. **My documents:** optionally upload alternative resumes. Supported: text-readable PDF, DOCX and UTF-8 TXT, up to 10 MB per file. Scanned PDFs need OCR first.
4. **Find opportunities:** choose a source and enter a role. Employer platforms such as Greenhouse require a company board identifier.
5. **Application studio:** choose a job and create a one-page resume plus editable outreach drafts. Read them before sharing.

The **profile-fit score** helps prioritize jobs; **resume text similarity** helps choose between resume versions. Neither is a hiring probability. [How matching works](docs/USER_GUIDE.md#understand-your-scores)

## Optional features

- [Native setup without Docker](docs/NATIVE_SETUP.md) — macOS, Linux and Windows commands.
- [Local AI models](docs/LOCAL_AI.md) — optional Ollama setup, including Docker instructions.
- [Chrome autofill and application review](docs/USER_GUIDE.md#optional-chrome-autofill) — manual installation, no automatic sending.
- [Developer guide](docs/DEVELOPMENT.md) — tests, architecture, source adapters and contribution checks.

The base Docker setup has live submission and AI generation **disabled**. Preparing documents never sends an application or LinkedIn message.

## Your data and other users

| Item | Where it lives |
| --- | --- |
| Profile, preferences, application history | `data/career.db` on your computer |
| Uploaded resumes | `data/resumes/` |
| Prepared application documents | `data/documents/` |
| Application Studio drafts and PDFs | `data/kits/` |
| Native configuration | Your local `.env` file |
| Local AI models | Ollama's local storage; optional Docker volume for container setup |

Only source code, fictitious demo data and setup examples are tracked by Git. `.env`, local databases, uploaded files, generated resumes, personal notes and downloaded models are excluded. A fresh installation does not contain the developer's profile, account credentials or resumes.

Use a separate folder and OS account for each person on a shared computer. The app has no login boundary between people who can access the same running instance or files. Keep the supplied localhost-only port bindings; do not expose it publicly. Public job discovery contacts job websites; optional external application submission shares the data you review with the employer. [Data and sharing details](docs/PRIVACY.md)

## Current scope

Public sources include LinkedIn guest listings, Remotive, Remote OK, We Work Remotely, Arbeitnow Europe/UK, and Greenhouse, Lever, Ashby and SmartRecruiters company boards. HiringCafe public-page extraction can be blocked. Other directory entries open in your browser for manual import. Sources may be unavailable or provide limited snapshots; logging into a website does not connect its private data to this app.

Contact suggestions are names found in job text or search leads, not a verified LinkedIn connection graph. Resume generation uses supplied facts and checks the PDF is one page; it does not guarantee acceptance by every ATS. Local matching has a finite skills vocabulary and requires human review of eligibility and qualifications.

## Tester distribution

Use a fresh GitHub download or the source-only release ZIP. **Do not zip and share your working project folder**: it contains local files that Git ignores. Start with fictitious data, keep live submission disabled, and use one installation per tester. See the [security review](docs/SECURITY_REVIEW.md) and [security policy](SECURITY.md).

## Get help

Check [Troubleshooting](docs/TROUBLESHOOTING.md). If you open a GitHub issue, include your OS, whether you used Docker or native setup, and the relevant error message. Remove emails, phone numbers, resumes, tokens and other personal details from logs and screenshots before sharing them.

## Evidence-based application kits

Application Studio now generates one-page ATS resumes, cover letters, LinkedIn referral drafts and answers to application questions. It uses your verified achievements and stories, shows missing facts, and blocks exports that fail the required format or length. Job details include source, posting freshness and explicit visa-sponsorship evidence. Optional local model tiers add staged job analysis.

Follow the [Career engine guide](docs/CAREER_ENGINE.md) for a step-by-step workflow, model setup, validation limits, API routes and privacy details. The fixed resume reference uses synthetic information; your own uploads and generated documents stay in your ignored local data folder.

### Keep your opportunities organized

Use the **Sort opportunities by** dropdown to order matches by score, posting date/time, source, location, company, or application priority. Choose ascending or descending order; missing values stay last.

Click an opportunity's trash icon, or select rows and choose **Delete selected**, to remove unwanted openings from your dashboard. Only the visible page is included by Select all. Deleted openings can be restored from **Deleted opportunities** beneath the table, including after restarting the app. The same saved opening stays deleted if a search finds it again. Prepared documents remain on your computer. Opportunities currently being prepared or submitted cannot be deleted until that operation finishes.
