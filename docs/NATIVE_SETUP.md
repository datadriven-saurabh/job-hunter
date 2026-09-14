# Native setup without Docker

Use this option if you are comfortable running commands or want native Ollama performance. For the simplest first installation, follow the Docker instructions in [README](../README.md).

## Install prerequisites

- [Python](https://www.python.org/downloads/): use Python 3.11 or 3.12 for this project's dependency range.
- [Node.js](https://nodejs.org/en/download): use Node.js 22 LTS (the Docker build also uses Node 22).
- Download/extract the project as described in the README.

Reopen your terminal after installation. Run `node --version` and `npm --version`; each should print a version. On Windows, enable **Add Python to PATH** in the Python installer. If PowerShell blocks `npm.ps1`, use `npm.cmd` in place of `npm`; you do not need to change execution policy.

## macOS / Linux

Open Terminal in the project folder. Run each line separately:

```sh
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
npm --prefix frontend ci
npm --prefix frontend run build
cp .env.example .env
```

If `python3 --version` is not the version you installed, use that executable (for example `python3.12`) for the environment-creation command. On Linux, your distribution may require the `python3-venv` package. Do not use `sudo pip`.

Start the app:

```sh
.venv/bin/python scripts/local.py start
```

Open [localhost:3000](http://localhost:3000). The launcher finds Node.js from PATH and works without Ollama installed. Services started by the launcher run in the background.

```sh
.venv/bin/python scripts/local.py status
.venv/bin/python scripts/local.py stop
```

On macOS, after completing setup, you can also double-click `Start Job Hunter.command`. If macOS does not allow it, use the terminal start command above. The `.command` file is not a Windows/Linux launcher.

If a Linux process does not stop through the launcher, inspect its terminal/process and stop that specific service; do not kill all Python or Node processes. You can also use the separate foreground terminals below on macOS/Linux, replacing the Windows Python path with `.venv/bin/python`.

## Windows — PowerShell

Open PowerShell in the project folder. Run each line separately:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
Copy-Item .env.example .env
```

If you installed Python 3.11, use `py -3.11` instead. These commands do not require activating the environment.

Open **two terminals** in the project folder. Keep both running.

Terminal 1 — API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Terminal 2 — website:

```powershell
npm.cmd --prefix frontend run start
```

Open [localhost:3000](http://localhost:3000). To stop, press **Ctrl+C** in each terminal. Use these same two commands to start again; installation is only needed once.

## Optional application browser

Drafts and PDFs do not need Playwright Chromium. To enable the optional browser application worker, install its browser:

macOS/Linux:

```sh
.venv/bin/python -m playwright install chromium
```

Windows:

```powershell
.\.venv\Scripts\python.exe -m playwright install chromium
```

Linux may need Playwright's documented system dependencies. The Docker image already installs them. Browser installation does not enable submission; see the [user guide](USER_GUIDE.md).

## Updates

Stop services and back up `data` first. Pull/download the new code, rerun the pip install and npm ci/build commands above, then start again. **Do not copy `.env.example` over an existing `.env` when updating**; that would reset your local settings.

Logs from the background launcher are under `data/runtime/`. Foreground processes print logs in their terminals. Never share logs without removing personal details.

The September 2026 security update requires a fresh Python 3.11/3.12 environment if your previous installation used Python 3.9. Stop the app, rename the old `.venv` as a private backup, and repeat environment creation and installation. Keep `data` and `.env`. Do not reuse the old environment for testing.
