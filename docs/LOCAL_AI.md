# Optional local AI

Core discovery, profile matching, one-page resumes and outreach drafts work without a model. AI powers optional model-based tasks. No cloud API key is required; model downloads need internet and several GB of disk space.

## Native installation

1. Install [Ollama](https://ollama.com/download) for your OS and start it.
2. In Terminal or PowerShell, run `ollama pull qwen3:4b`. Wait for completion.
3. In your project's local `.env` file set `ENABLE_LOCAL_LLM=true`.
4. Restart the API (or stop/start the native launcher).
5. Open **Model Lab**, refresh installed models, and select the model you downloaded.

For additional small models, run `ollama pull qwen2.5:1.5b` or `ollama pull gemma3:1b`. These are candidates to compare, not a promise of better results. The app's small benchmark measures its specific extraction examples, not overall writing quality. Test output against your own facts.

If Ollama is not running, open its desktop app or run `ollama serve` in a separate terminal. An address-already-in-use message usually means it is already running. Keep its API on localhost.

## Docker installation

The optional overlay runs Ollama in the backend's network namespace so its API remains reachable only through loopback. From the project folder:

```sh
docker compose down
docker compose -f docker-compose.yml -f compose.ai.yml up --build -d
docker compose -f docker-compose.yml -f compose.ai.yml exec ollama ollama pull qwen3:4b
```

Open Model Lab and refresh. Pull other models with the same command, replacing `qwen3:4b`. Use both `-f` options for future starts, stops and logs. Models persist in a Docker volume; `down` preserves it, whereas `down -v` deletes it.

This configuration uses CPU inference. Native Ollama can be faster on supported hardware. Allow adequate Docker memory for the chosen model; use a smaller model if generation fails or is too slow.

To return to the base app, run `docker compose -f docker-compose.yml -f compose.ai.yml down`, then `docker compose up -d`. Your profile and documents remain in `data`.
