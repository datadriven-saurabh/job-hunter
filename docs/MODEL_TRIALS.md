# Free local model trial — September 15, 2026

The following models were tested on the development computer (16 GB unified memory). Model downloads and prompts stayed local; no hosted-model API fee was incurred. The downloads live in the ignored local model directory, not in this repository.

| Model | Exact cases passed | Total elapsed time |
| --- | --- | --- |
| Qwen3 4B (existing baseline) | 2 / 3 | 6.17 s |
| DeepSeek R1 8B | 1 / 3 | 12.36 s |
| Nemotron 3 Nano 4B | 0 / 3 | 10.83 s |

These are three synthetic skill-extraction cases in `backend/model_api.py`: overlapping skills, completely disjoint profile/job skills, and negated experience combined with an instruction-like job sentence. Exact matched/missing sets must agree with the fixture. Times include model loading and three requests; temperature is 0.2, so results can vary. This is a small application compatibility check, not an overall model-quality or resume-writing benchmark.

DeepSeek included irrelevant profile skills in the disjoint case and treated an injected Java instruction as a job requirement. Nemotron returned valid JSON after its thinking-mode compatibility fix, but still misclassified the evidence in all three cases. Qwen also failed the disjoint case. The existing model remains selected; the new models are installed and available for further tests in Model lab. Evidence validators remain necessary for every model.

Nemotron's default thinking mode produced an empty final response with the schema-constrained `/api/generate` request. Job Hunter now uses `think: false` for `nemotron-3-nano` structured generation, as it already does for Qwen3. Reasoning text is not substituted for a validated final response.

## Reproduce

With Ollama installed:

```sh
ollama pull deepseek-r1:8b
ollama pull nemotron-3-nano:4b
```

Open **Model lab**, select these two models and `qwen3:4b`, and choose **Run evidence benchmark**. Inspect individual outputs before choosing a model or changing task-specific routing. No user profile is included in this benchmark.

The [DeepSeek R1 8B model](https://ollama.com/library/deepseek-r1:8b) is a distilled local model, not the full hosted DeepSeek family. [Nemotron 3 Nano 4B](https://ollama.com/library/nemotron-3-nano:4b) is the small local variant; results do not describe larger Nemotron variants.

[Kimi K3](https://build.nvidia.com/moonshotai/kimi-k3/modelcard) was researched but not executed. NVIDIA lists it as a hosted trial service; it needs an account/API key and is subject to provider trial terms and limits. Its full model is unsuitable for this 16 GB machine. No hosted provider was enabled and no candidate information was sent to one. Free trial access should not be interpreted as unlimited free production hosting.
