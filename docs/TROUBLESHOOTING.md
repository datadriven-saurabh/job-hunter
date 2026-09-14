# Troubleshooting

Run commands from the folder containing `docker-compose.yml`. For the optional AI overlay, include both `-f` options shown in the AI guide.

| Problem | What to try |
| --- | --- |
| `docker` not found | Install Docker Desktop and reopen the terminal. |
| Cannot connect to Docker daemon | Open Docker Desktop and wait until its engine is running. |
| Cannot open localhost:3000 | Run `docker compose ps`, then `docker compose logs --tail=80`. Wait for the build/start to finish. Use HTTP, not HTTPS. |
| Port already allocated | Stop your previous Job Hunter instance. If using native setup, run its stop command. Do not run Docker and native copies on the same ports. |
| Local engine disconnected | Check backend logs and open `http://localhost:8000/health`. Restart the backend after correcting the reported error. |
| Build/download fails | Check internet access and free disk space, then retry `docker compose up --build -d`. Do not delete `data`. |
| Zero matching jobs | Broaden titles/locations and required terms. Compare fetched vs matched counts: fetched jobs can all be excluded by filters. |
| HTTP 403, 429 or unavailable source | The site refused access or limited requests. Wait, use another source, or paste the job description into Application Studio. Logging into Chrome does not give backend requests that session. |
| Company board returns nothing | Enter the employer's board identifier, not a full job URL; verify its careers page uses that platform. |
| PDF upload has no text | Use a text-readable PDF, DOCX or TXT. Scanned images need OCR before upload. |
| Resume contains demo facts | Replace the demo in My profile. Studio uses the saved profile; an uploaded alternative does not replace those facts. |
| Model missing or unavailable | Start Ollama, pull a model and refresh Model Lab. Enable local AI as described in the AI guide and restart the API. |
| Native start reports missing environment/build | Complete every step in the native setup guide, including pip install and npm build. |

## Safe recovery

Stop the app, back up `data`, then rebuild/restart. Avoid deleting your database as a troubleshooting step. A fresh folder from GitHub plus a copy of your backup is safer than overwriting files at random.

When reporting a bug, include your OS, Docker/native choice, action taken and redacted error message. Do not attach your `.env`, database, resume or private logs to a public issue.
