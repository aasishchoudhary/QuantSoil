# Inference Control Plane

## Status

Phase 1 — provider-neutral inference boundary.

## Objective

Connect God's Eye to an OpenAI-compatible inference gateway without making any
LLM provider a system dependency.

The current development deployment uses the local FreeLLMAPI gateway. The
application contract is deliberately provider-neutral so another gateway or
provider can be introduced without changing world-state contracts.

## Boundaries

```
God's Eye task
    |
    v
deterministic task/model policy
    |
    v
InferenceClient
    |
    v
OpenAI-compatible /v1/chat/completions
    |
    v
FreeLLMAPI
    |
    +--> provider/model
    |
    v
untrusted model output
    |
    v
validation + provenance gate
    |
    v
world-state write (future phase)
```

### Non-negotiable invariants

1. Provider credentials come only from runtime configuration.
2. Credentials are never committed, logged, or placed in fixtures.
3. Model output is explicitly untrusted.
4. Inference failures are surfaced as typed application errors.
5. The adapter does not write world state.
6. Model selection is deterministic and auditable.
7. Provider-specific behavior stays behind the gateway boundary.

## Runtime configuration

```text
FREE_LLM_API_BASE_URL=http://127.0.0.1:3001/v1
FREE_LLM_API_KEY=<FreeLLMAPI unified API key>
GODS_EYE_INFERENCE_MODEL=gemini-3.6-flash
GODS_EYE_INFERENCE_TIMEOUT_SECONDS=30
```

The unified API key must be supplied through the deployment secret manager or
local environment. Never commit the value.

## Acceptance criteria

- The client can issue a request through the local gateway.
- An OpenAI-compatible response is parsed into a typed result.
- Invalid configuration fails before network access.
- Tests use synthetic credentials only.
- Model output remains marked untrusted.
