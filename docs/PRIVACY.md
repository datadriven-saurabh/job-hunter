# Data, credentials and sharing

This is a local, single-person application. Separate installations have separate databases. There is no hosted account system, authentication boundary or shared-user database. Someone with access to your running instance or local files can access your data.

## Stored locally

The `data` folder contains the SQLite database, profile, preferences, application history, uploads, generated documents, drafts, caches and runtime logs. Your `.env` contains local feature settings. Optional models are stored by Ollama or in the Docker model volume.

These files are not encrypted by this app. Use your operating system's account permissions and disk encryption if needed. To back up, stop the app and copy `data` to storage you control; also save your `.env` privately if using native setup. Restore by stopping the app and putting the backup in the project folder. Never upload that backup to the source repository.

## Network activity

- Public discovery contacts the selected job board or employer API with search/board parameters.
- Importing a job URL contacts that site. It does not use your browser login cookies.
- LinkedIn search links open in your browser, where your browser session applies.
- Local AI sends prompts to local Ollama. Downloading dependencies and models contacts their respective registries.
- Document preparation and outreach drafting do not send applications or messages.
- Optional live submission sends reviewed application details to the employer when explicitly enabled and confirmed. Keep it disabled unless you intend to use it.

Do not store job-board passwords, browser cookies, API tokens or SSH keys in project source. Sign into websites directly in your browser. The app does not need job-board credentials for its public feeds.

## What belongs in Git

Source, dependency manifests, synthetic demos and setup instructions belong in Git. `.gitignore` excludes local settings, databases, uploads, outputs, models and the original personal reference files. Ignore rules cannot protect a file already tracked or personal text copied into source. Review `git diff --cached` and `git status --short` before every contribution.

Keep the default localhost bindings. This app is not ready for public hosting or multiple users sharing a server. That requires authentication, authorization, per-user storage isolation and a separate security review.

To erase local information, stop the app and delete the `data` folder and your `.env`; this is permanent unless you have a backup. Delete Ollama models separately if desired. Copies you exported or sent elsewhere are not removed.
