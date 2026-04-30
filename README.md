# Inkbook — AI-Native Tattoo Booking Platform

Inkbook is an AI-native booking platform for tattoo artists.
It does not sell artists a tool to help them manage bookings.
It manages the bookings for them.

---

## The Problem

A professional tattoo artist with a significant Instagram
following receives 100-200 direct messages per day from
prospective clients. The overwhelming majority never convert
to appointments — not because the clients are not serious,
but because the artist cannot respond fast enough, quote
accurately enough, or follow up consistently enough while
also tattooing clients for eight hours a day.

**Miguel, our first artist, receives 150 DMs per day and
converts roughly 5 into confirmed appointments — a
conversion rate under 3.5%.**

Inkbook fixes that.

---

## How It Works

### The Client Experience

A prospective client taps the artist's booking link and
opens a chat window. They have a natural conversation with
a booking assistant — describe the tattoo idea, answer a
few quick questions, upload a reference image if they have
one. In under a minute they receive a personalized price
estimate and three available appointment dates.

No forms. No waiting days for a DM reply. Just a
conversation that feels like texting someone who knows
exactly what they are doing.

### The Artist Experience

The moment a client completes the chat, four AI agents
fire automatically. Within 60 seconds the artist receives
a structured approval card on Telegram containing:

- Client classification — 🟢 STRONG or 🟡 SOFT
- The client's tattoo concept and reference image
- A personalized price estimate in the artist's rate tier
- Three available appointment dates
- A complete drafted response written in the artist's voice
- A session summary so the artist knows exactly what
  work they are walking into

The artist has three actions. **APPROVE** — the drafted
response goes to the client automatically. **ADJUST** —
the artist edits before sending. **DECLINE** — a polite
decline goes to the client automatically.

Nothing reaches the client without the artist's approval.

---

## The AI Agent System

Five agents run on every submission using CrewAI and
OpenAI's language models.

**Intake Classifier**
Reads the full submission and classifies the client as
STRONG or SOFT based on budget alignment, description
clarity, and booking intent. Extracts structured data
for all downstream agents.

**Pricing Agent**
Maps the concept to the artist's configured rate structure.
Returns an accurate estimate range with a mandatory
disclaimer. Never quotes a final price. Never uses the
budget field — budget is for classification only.

**Scheduling Agent**
Finds real available dates within the artist's booking
window. Returns exactly three options with weekends
prioritized. Returns dates only — the artist confirms
time personally after approving.

**Response Agent**
Drafts the client-facing message in the artist's exact
voice trained on real DM examples. Produces two outputs
— a client message and a session summary for the artist
only. The client never sees the session summary.

**Approval Notifier**
Packages everything into a structured Telegram card and
delivers it to the artist for one-tap review.

---

## Tech Stack

**Frontend**
React · TypeScript · Tailwind CSS

**Backend**
Python 3.11 · FastAPI · CrewAI 1.9.3 · OpenAI

**Database**
PostgreSQL · SQLAlchemy (async)

**Infrastructure**
AWS ECS Fargate · RDS · API Gateway · Secrets Manager
GitHub Actions CI/CD · Docker

**Notifications**
Telegram Bot API · Twilio SMS · Stripe

**Tools**
ngrok (local webhook testing) · Render (MVP deployment)

---

## Project Structure
cloud-orchestrated-agents/
│
├── agents/                         # Agent specification documents
│   ├── agent_intake_classifier.md
│   ├── agent_pricing.md
│   ├── agent_scheduling.md
│   └── agent_response.md
│
├── api/                            # FastAPI backend
│   └── main.py                     # All routes and webhook receiver
│
├── config/                         # Artist configuration
│   └── miguel.json                 # Miguel's rates and availability
│
├── crews/                          # CrewAI orchestration
│   └── tattoo_intake_crew.py       # Four-agent intake crew
│
├── db/                             # Database layer
│   ├── schema.sql                  # PostgreSQL schema
│   ├── database.py                 # SQLAlchemy connection
│   └── models.py                   # ORM models
│
├── evals/                          # Agent quality test suite
│   └── test_cases.py
│
├── frontend/                       # React client-facing site
│
├── tools/                          # Custom agent tools
│   ├── tattoo_pricing_tool.py      # Pricing calculations
│   └── telegram_notifier.py       # Telegram card formatter and sender
│
└── README.md

---

## Agent Pipeline
Client submits chat
↓
FastAPI /api/miguel/intake
↓
Intake Classifier Agent
→ STRONG or SOFT classification
→ Structured data extraction
→ Emotional tone note
↓
Pricing Agent
→ Session type determination
→ Price estimate from configured rates
→ Mandatory disclaimer
→ Personalized note
↓
Scheduling Agent
→ Real available dates
→ Day capacity rules applied
→ Three options, weekends prioritized
→ Dates only — no times
↓
Response Agent
→ Client message in artist's voice
→ Session summary for artist only
→ Delimited output for clean separation
↓
Telegram Notifier
→ Formatted approval card to artist
→ APPROVE / ADJUST / DECLINE
↓
Telegram Webhook /api/telegram/webhook
→ APPROVE → client confirmation sent
→ ADJUST → artist types update → sent
→ DECLINE → polite decline sent

---

## Environment Variables

Create a `.env` file in the project root:
OPENAI_API_KEY=your_openai_key
SERPER_API_KEY=your_serper_key
TELEGRAM_BOT_TOKEN=your_bot_token
MIGUEL_CHAT_ID=your_chat_id
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_twilio_number
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/inkbook

---

## Running Locally

**Install dependencies**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Create the database**
```bash
createdb inkbook
psql inkbook < db/schema.sql
```

**Start the API server**
```bash
uvicorn api.main:app --reload --port 8000
```

**Start ngrok for Telegram webhook testing**
```bash
ngrok http 8000
```

**Register the Telegram webhook**
```bash
curl "https://api.telegram.org/bot{TOKEN}/setWebhook?url={NGROK_URL}/api/telegram/webhook"
```

**Test an intake submission**
```bash
curl -X POST http://localhost:8000/api/miguel/intake \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Marcus",
    "contact": "+15125551234",
    "size_selection": "large",
    "description": "Realistic black and gray wolf on my full outer arm",
    "placement": "outer_arm",
    "styles": ["realism", "blackwork"],
    "is_cover_up": false,
    "budget_range": "500_1000",
    "preferred_timing": "within_1_month",
    "idea_readiness": "knows_exactly"
  }'
```

---

## What is Working Right Now

- Four AI agents firing on every intake submission
- STRONG / SOFT client classification with correct headers
- Price estimates based on Miguel's configured rate structure
- Three available date options from manual availability config
- Client message drafted in Miguel's real voice
- Session summary separated from client message
- Telegram approval card delivered to Miguel's phone
- APPROVE triggers client confirmation
- ADJUST prompts Miguel for his edit then sends it
- DECLINE sends polite decline to client
- Unique intake ID on every submission
- Full end to end loop tested and working

---

## Roadmap

**In Progress**
- PostgreSQL database integration
- Reference image attachment on Telegram card
- Render deployment for live pilot URL

**Next**
- React chatbot frontend
- Google Calendar integration
- Twilio SMS client confirmations
- Stripe deposit link generation

**Later**
- Multi-artist platform architecture
- Artist dashboard
- Eval suite and CI/CD quality gates
- Referral and affiliate program
- Instagram DM integration

---

## First Customer

**Miguel** — Professional tattoo artist, Round Rock TX.
Founding artist. The product is being built around his
real workflow, his real pricing, and his real voice.

The pilot goal is to move his booking conversion rate
from under 3.5% to 20-25% on his 150 daily DMs.

---

## Business Model

Artists pay a monthly subscription.

- Starter — $49/month
- Pro — $149/month
- Elite — $299/month

Transaction fee of 3-4% on deposits processed through
the platform at scale.

Referral program launches after pilot validation —
artists earn commission on subscriptions from artists
they refer.

