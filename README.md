# Cloud Orchestrated Agents

A practice project to learn how to build, run, and deploy AI-powered agentic workflows. This is the foundation for a future Agent-as-a-Service (AIaaS) product targeting small businesses.

## What This Is

A multi-agent system built with CrewAI where specialized AI agents collaborate to complete real-world tasks. Agents can search the web, process information, and produce structured output — all autonomously.

## Current State

Two agents working locally:
- **Researcher** — searches the web using real-time Google data via Serper
- **Writer** — takes research output and produces clean, readable content

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Orchestration | CrewAI 1.9.3 |
| LLM | OpenAI API |
| Web Search | Serper Dev |
| Language | Python 3.11 |
| IDE | Cursor |
| Version Control | Git + GitHub |

## Roadmap

- [x] Phase 1 — Single agent running locally
- [x] Phase 2 — Multi-agent crew with handoff
- [x] Phase 3 — Add real web search tool (Level 2 agents)
- [ ] Phase 4 — FastAPI backend wrapping the crew
- [ ] Phase 5 — React + TypeScript dashboard
- [ ] Phase 6 — Docker containerization
- [ ] Phase 7 — AWS deployment (DevSecOps partner)
- [ ] Phase 8 — Telegram / WhatsApp delivery channel

