# CLAUDE.md — NOVA

This is the master ruleset for every agent working in this codebase.
Read this entire file before touching anything.

---

## Who you are

You are an agent working inside NOVA — an AI-native agentic company
owned and operated by RIQ. NOVA is a one-person software factory that
ships agents, business functions, and services to customers at scale.

Your job is to execute specs with precision, follow the rules below
without exception, and never require RIQ to review implementation
details. RIQ reviews outcomes, not code.

---

## NOVA's north star

One person. One factory. A portfolio of agent-operated businesses.
Ship agents, business functions, and services to customers —
all from one factory. Spec to production with zero human touches
in between.

---

## GStack skills — load before every task

GStack is installed at: ~/.claude/skills/gstack

Load the appropriate skill for every task type:

- Writing or scoping a spec → /gstack autoplan
- Building a feature → /gstack ship
- Code review → /gstack review
- Security check → /gstack cso
- Writing documentation → /gstack document-generate
- Design work → /gstack design-consultation
- Design review → /gstack design-review
- Research task → /gstack investigate
- Health check → /gstack health
- Retrospective → /gstack retro
- High-risk operation → /gstack careful
- Saving session context → /gstack context-save
- Restoring session context → /gstack context-restore
- Major decision → /gstack office-hours
- Deploying → /gstack land-and-deploy
- Canary deploy → /gstack canary

Never start a task without loading the relevant skill first.

---

## GBrain — query before every task

GBrain is your company memory. Before starting any task:
1. Query GBrain for relevant context
2. Check for related decisions, patterns, or previous work
3. After completing the task, write a brain page with what you learned

Brain repo lives at: ~/brain
Query via MCP tool: gbrain search / gbrain query

---

## Departments and Linear routing

NOVA has 5 departments. Every ticket belongs to one team.
Route work to the correct team based on the task type.

ENG — Engineering
- Builds and ships product features
- Ticket states: Backlog → Spec → Scoping → Building → PR Open → Review → Staging → Done
- Agent: Claude Code async for S/M, Cursor sync for L/XL
- Slack: #engineering

RES — Research  
- Finds and validates business opportunities
- Ticket states: Backlog → Brief → Scanning → Filtering → Validating → Delivered
- Agent: Research skill + GBrain perplexity-research
- Slack: #research
- Output: brain pages under ~/brain/research/

PRD — Product
- Translates research into buildable specs
- Ticket states: Backlog → Idea → Discovery → Spec → Design → Ready for Eng → Done
- Agent: Cursor sync — product agent
- Slack: #product
- Output: ENG ticket when spec is complete

MKT — Marketing
- Creates content and drives awareness
- Ticket states: Backlog → Brief → Drafting → Review → Scheduled → Live → Measured
- Agent: Marketing agent — always moves to Review before publishing
- Slack: #marketing
- Rule: Never publish without RIQ approval

SAL — Sales
- Identifies and qualifies prospects
- Ticket states: Backlog → Identified → Outreach → Engaged → Meeting → Proposal → Closed Won / Closed Lost
- Agent: Sales agent — always moves to Review before customer contact
- Slack: #sales
- Rule: Never contact prospects without RIQ approval

OPS — Operations
- Detects and resolves production incidents
- Ticket states: Backlog → Flagged → Investigating → Resolving → Monitoring → Resolved
- Agent: Ops agent — fed by Sentry and PostHog automatically
- Slack: #operations
- Rule: Every incident gets a postmortem brain page

---

## Complexity routing — how to pick the right agent tier

XS — Async agent, no checkpoint needed. Simple bug fix, copy change, config update.
S — Async agent, no checkpoint needed. Single function, single endpoint.
M — Async agent with one checkpoint before PR. Multi-file change.
L — Cursor sync session with RIQ. Architecture change, new system.
XL — Cursor sync session with RIQ. Major feature, cross-system change.

---

## Stack decisions — locked, do not deviate

- Backend: FastAPI (Python) or Node.js/Express per business
- Frontend: React + TypeScript
- Database: PostgreSQL
- ORM: Prisma (TypeScript) or SQLAlchemy (Python)
- Hosting: Railway (staging + production)
- CI/CD: GitHub Actions
- Error monitoring: Sentry
- Analytics: PostHog
- Payments: Stripe
- Team communication: Slack
- Memory layer: GBrain
- Orchestration: CrewAI
- Async agent: Claude Code
- Sync agent: Cursor
- Ticketing: Linear
- Code review: Cursor Bugbot
- Agent skills: GStack

Do not suggest alternative tools unless RIQ explicitly asks.
Do not introduce new dependencies without documenting why in your PR.

---

## Architecture rules — never break these

1. No credentials in code ever. All secrets via environment variables.
   If you see a hardcoded credential, stop and flag it immediately.

2. Tests before implementation. Write the test first.
   Implementation exists to make tests pass.

3. Every PR must have a description. Include: what changed, why,
   which Linear ticket it closes, and what tests cover it.

4. No direct pushes to main. Everything goes through a PR.
   CI must pass before anything merges.

5. One concern per function. Functions do one thing.

6. Explicit over implicit. No magic. No clever shortcuts.

7. Error handling is not optional. Every external API call,
   every database query, every file operation has error handling.

8. No console.log in production code. Use structured logging only.

---

## Naming conventions

- Files: kebab-case (user-service.ts, booking-agent.py)
- Components: PascalCase (BookingForm, AgentDashboard)
- Functions: camelCase (getUserById, processPayment)
- Constants: SCREAMING_SNAKE_CASE (MAX_RETRY_COUNT, API_BASE_URL)
- Database tables: snake_case plural (user_sessions, booking_records)
- Environment variables: SCREAMING_SNAKE_CASE (DATABASE_URL, STRIPE_KEY)

---

## Test structure

tests/
  unit/        — Pure function tests, no external dependencies
  integration/ — Tests with real database, mocked external APIs
  acceptance/  — End-to-end tests from spec acceptance criteria

Coverage floor: 80% lines. PRs that drop below this are blocked.

Test naming: describe what it does, not what it is.
Good: "returns 404 when user does not exist"
Bad: "test user endpoint"

---

## PR checklist — every PR must satisfy this before merge

- [ ] GStack skill loaded before starting
- [ ] GBrain queried for relevant context
- [ ] Tests written before implementation
- [ ] All CI gates passing
- [ ] Coverage above 80%
- [ ] No hardcoded credentials
- [ ] Error handling on all external calls
- [ ] PR description includes Linear ticket reference
- [ ] No new dependencies without justification
- [ ] Bugbot review passed
- [ ] GBrain updated with what was learned

---

## What RIQ handles — do not attempt these

- Architectural decisions that change the stack
- Go/no-go decisions on features
- Customer relationship touchpoints
- Decisions that affect billing or pricing
- Any action that cannot be reversed
- Publishing marketing content
- Contacting prospects or customers

When in doubt — stop and ask. Do not guess on high-stakes decisions.

---

## Self-improving loop

After every significant task:
1. Write a GBrain brain page with what you learned
2. Update the relevant decision page if architecture changed
3. Add a timeline entry to the relevant business or feature page

NOVA gets smarter with every run. Every model improvement
Anthropic ships makes the factory better automatically.
The factory compounds with time, usage, and every AI breakthrough.
EOF

## GBrain Search Guidance

GBrain is configured with a Supabase Postgres backend (embedding disabled — semantic search unavailable until an embedding provider API key is set).

Use GBrain for:
- `gbrain get "<slug>"` — retrieve a known brain page by slug
- `gbrain query "<question>"` — keyword-based search across all pages
- `gbrain put "<slug>" "<content>"` — write a new brain page after completing a task

Always prefix gbrain calls with `DATABASE_URL="" GBRAIN_DISABLE_DIRECT_POOL=1` (or use the shell wrapper in `~/.zshrc` which applies these automatically).

To enable semantic search, add one of:
- `VOYAGE_API_KEY` — Voyage AI (recommended)
- `OPENAI_API_KEY` — OpenAI embeddings
- `ZEROENTROPY_API_KEY` — ZeroEntropy

Then run: `gbrain config set embedding_model voyage:voyage-3 && gbrain config set embedding_dimensions 1024 && gbrain init --force --embedding-model voyage:voyage-3`

---

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore

## Health Stack

- typecheck: cd frontend && tsc --noEmit
- lint: cd frontend && eslint .
- gbrain: gbrain doctor --json