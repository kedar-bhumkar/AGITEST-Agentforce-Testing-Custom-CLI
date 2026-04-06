# Agentforce Interactive Test Kit

One-command wizard to test any Agentforce agent. Auto-discovers agents and topics, generates test cases, deploys, runs in parallel, and scores results.

## Prerequisites

- **sf CLI** — `npm install -g @salesforce/cli` or `brew install sf`
- **Python 3.8+** — `python3` must be on your PATH
- **Bash** — macOS/Linux terminal, or Git Bash on Windows

## Quick Start

```bash
chmod +x run.sh
./run.sh
```

The wizard walks you through 12 steps:

| Step | What it does |
|------|-------------|
| 1 | Banner + preflight checks |
| 2 | Org connection (Production / Sandbox / Custom URL) |
| 3 | Verify connection + Agent Testing Center |
| 4 | Auto-discover all agents in the org |
| 5 | Select one agent |
| 6 | Auto-discover all topics (GenAiPlugins) with labels & descriptions |
| 7 | Select topics (all or subset) |
| 8 | Choose whether to generate test cases |
| 9 | Set number of tests per topic (default: 10) |
| 10 | Generate AiEvaluationDefinition XML specs |
| 11 | Confirm deployment |
| 12 | Deploy, run in parallel, score, and report |

## Re-running

```bash
# Re-run with existing specs (skip generation)
./run.sh

# Or delete specs/ to regenerate
rm -rf specs/ && ./run.sh
```

## File Structure

```
agentforce-test-kit/
├── run.sh           # The interactive wizard (self-contained)
├── specs/           # Generated XML test specs (one per topic)
├── results/         # JSON results from each test run
└── README.md
```

## Test Categories

Generated tests are split across 4 categories:

- **Happy Path (40%)** — Direct questions matching the topic
- **Rephrased (20%)** — Same intent with casual, formal, or typo-filled phrasing
- **Edge Cases (20%)** — Empty input, multi-intent, boundary conditions
- **Guardrails (20%)** — Prompt injection, PII requests, off-topic, competitors

## Scoring

| Score | Rating |
|-------|--------|
| ≥ 90% | PRODUCTION READY |
| ≥ 80% | STRONG |
| ≥ 70% | ACCEPTABLE |
| ≥ 60% | BELOW STANDARD |
| < 60% | BLOCKED |

## Works On

- macOS (native terminal)
- Linux (bash)
- Windows (Git Bash / WSL)
