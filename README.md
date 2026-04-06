# AGITEST — Agentforce Testing Custom CLI

Interactive CLI wizard to test any Salesforce Agentforce agent. Auto-discovers agents and topics, generates test cases, runs them via Testing Center or direct Agent API, and evaluates results using your choice of LLM.

## Features

- **Two testing modes** — Testing Center (deploy & run via AI Evaluations API) or Agent API (direct REST calls)
- **LLM evaluation** — Claude, OpenAI GPT-4o, Google Gemini, or Local Ollama
- **LLM test generation** — generate realistic, adversarial test cases using any of the 4 LLM providers
- **Template generation** — fast offline test generation, no API key needed
- **Auto-discovery** — agents, topics, and Bot IDs resolved automatically via SOQL
- **Context variable support** — pass `$Context.*` and custom variables per test case via spec XML
- **Zero-prompt reruns** — `--run lastrun` replays the exact previous run settings
- **OAuth Client Credentials** — uses External Client App for secure Agent API auth
- **Cross-platform** — macOS, Linux, Windows (Git Bash)

## Prerequisites

- **sf CLI** — `npm install -g @salesforce/cli` or `brew install sf`
- **Python 3.8+** — `python3` must be on your PATH
- **Bash** — macOS/Linux terminal, or Git Bash on Windows

## Quick Start

```bash
chmod +x run.sh
./run.sh
```

The interactive wizard walks through 14 steps, handling everything from org auth to scored results.

## Direct Mode (no prompts)

```bash
# Agent API + Claude evaluation, 5 tests per topic
./run.sh --run Meddy_virtual_assistant \
         --org myorg@salesforce.com \
         --method agent_api \
         --llm claude \
         --tests 5

# Testing Center
./run.sh --run Meddy_virtual_assistant \
         --org myorg@salesforce.com \
         --method testing_center

# Repeat last run exactly
./run.sh --run lastrun
```

## All Parameters

| Parameter | Description |
|-----------|-------------|
| `--run <BotApiName>` | Direct mode — skip all prompts |
| `--run lastrun` | Repeat exact settings from previous run |
| `--org <username>` | Org username or alias |
| `--method <m>` | `testing_center` (default) or `agent_api` |
| `--tests <N>` | Tests per topic (default: 10) |
| `--llm <p>` | LLM for evaluation: `openai`, `claude`, `gemini`, `ollama` |
| `--llm-key <k>` | API key for chosen LLM |
| `--llm-model <m>` | Override default model |
| `--consumer-key <k>` | External Client App consumer key (Agent API) |
| `--consumer-secret <s>` | External Client App consumer secret (Agent API) |
| `--help` | Show usage |

## Environment Variables (`.env`)

Create a `.env` file in the project root — it is auto-loaded at startup:

```bash
# Agent API OAuth (External Client App)
export SF_AGENT_API_CONSUMER_KEY="3MVG9..."
export SF_AGENT_API_CONSUMER_SECRET="FEA..."

# LLM API keys (only the one you use is needed)
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="AI..."
```

## Agent API Setup

To use Agent API mode, you need a Salesforce External Client App with OAuth Client Credentials Flow:

1. **Setup → External Client Apps Manager → New External Client App**
2. Enable OAuth with scopes: `api`, `chatbot_api`, `sfap_api`, `refresh_token`
3. Enable **Client Credentials Flow**
4. Enable **Issue JWT-based access tokens for named users**
5. Set a **Run As** user with appropriate permissions
6. Set **Permitted Users** to *All users may self-authorize*
7. Copy Consumer Key & Secret into `.env`

## Context Variables in Spec Files

You can pass context variables per test case in the XML spec:

```xml
<inputs>
    <utterance>What is my account balance?</utterance>
    <contextVariables>
        <name>accountId</name>
        <value>001Hp000003XYZABC</value>
    </contextVariables>
</inputs>
```

- `$Context.*` variables → passed at session creation (read-only after that, except `$Context.EndUserLanguage`)
- Custom variables → passed at session creation and updatable per message
- Requires **"Allow value to be set by API"** checked in Agentforce Builder for each variable

## Test Generation

| Engine | Quality | API key needed |
|--------|---------|----------------|
| Template | Generic / adversarial | No |
| LLM (Claude / OpenAI / Gemini / Ollama) | Contextual, realistic | Yes |

LLM-generated tests follow a distribution:

| Category | % | Description |
|----------|---|-------------|
| Happy Path | 40% | Realistic utterances the topic should handle |
| Rephrase | 15% | Typos, slang, ALL CAPS, non-native phrasing |
| Edge Case | 15% | Ambiguous, multi-intent, empty/gibberish |
| Guardrail | 15% | Off-topic, prompt injection, PII requests |
| Adversarial | 15% | Subtle social engineering, topic drift |

## Scoring

| Score | Rating |
|-------|--------|
| ≥ 90% | ★★★★★ PRODUCTION READY |
| ≥ 80% | ★★★★☆ STRONG |
| ≥ 70% | ★★★☆☆ ACCEPTABLE |
| ≥ 60% | ★★☆☆☆ BELOW STANDARD |
| < 60% | ★☆☆☆☆ BLOCKED |

## File Structure

```
agentforce-test-kit/
├── run.sh           # Self-contained CLI (all logic in one file)
├── specs/           # AiEvaluationDefinition XML specs (one per topic)
├── results/         # JSON results from each test run
├── .env             # Your credentials (gitignored)
├── .last_run.json   # Saved settings for --run lastrun (gitignored)
└── README.md
```
