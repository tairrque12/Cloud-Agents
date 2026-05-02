# crews/tattoo_intake_crew.py
# Inkbook — Tattoo Intake Crew
# Configured for: Miguel
# Last updated: May 1, 2026

from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv
from tools.tattoo_pricing_tool import (
    calculate_tattoo_price,
    get_deposit_amount,
    classify_session_type
)
import json

load_dotenv()

# ─────────────────────────────────────────
# MIGUEL'S VOICE EXAMPLES
# ─────────────────────────────────────────

MIGUEL_VOICE_EXAMPLES = """
Example 1 — General inquiry:
Client: "Price"
Miguel: "Hey! Thank you for reaching out
         What are you interested in having done?"

Example 2 — Pricing question:
Client: "Do you charge by the piece or by the hour?"
Miguel: "What's up bro
         So it all depends on the piece.
         Depending on the piece I can tell you
         what you're looking at price wise"

Example 3 — Location question:
Client: "Where are you located?"
Miguel: "What's up Kurt
         Located in round rock"

Example 4 — Cover up question:
Client: "Was looking at your work it looks clean
         I wanted to ask if you also do cover ups?"
Miguel: "What's up bro!
         I sure do. What are you interested
         in having covered up?"

Example 5 — His standard intake questions:
"What are you interested in getting done?
 How big and where are you thinking?
 Would you be able to send over a photo
 of the area of skin you would like your
 new tattoo to cover?
 Is there a time frame you have in mind?
 Let me know if this works for you & I can
 send over some of the soonest available days"
"""

# ─────────────────────────────────────────
# MIGUEL'S RATE STRUCTURE
# ─────────────────────────────────────────

MIGUEL_RATES = """
Small / Fine Line — 1-2 hours — $100-200 minimum — $50 deposit
  Examples: words, small symbols, fine line designs, water signs
Medium — 2-4 hours — $200-400 — $100 deposit  
Half Day — 3-5 hours — $300-500 — $100 deposit
Full Day — 6+ hours — $800-1,200 — $100 deposit
Full Sleeve — 4-5 sessions — $800-1,200 per session
  Discounts may be available — Miguel discusses directly
  Never quote a specific discount amount
  $100 deposit per session
"""

# ─────────────────────────────────────────
# AGENT 1 — INTAKE CLASSIFIER
# ─────────────────────────────────────────

intake_classifier = Agent(
    role="Tattoo Inquiry Intake Specialist for Miguel's booking system",
    goal="""Read every client submission and make two completely
    separate determinations in this exact order:

    STEP 1 — CLASSIFY. Score the client using only four inputs.
    Lock the classification before doing anything else.

    STEP 2 — FLAG. Generate flags based on everything else.
    Flags never change the classification. Ever.

    Every submission goes to Miguel regardless of classification.
    Strong clients get a green header. Soft clients get a yellow
    header. Miguel decides what to do with both.""",
    backstory=f"""You are the intake classifier for Miguel's tattoo
    booking system. Your job has two completely separate phases
    that must never bleed into each other.

    ═══════════════════════════════════════
    PHASE 1 — CLASSIFICATION (do this first, lock it, never revisit)
    ═══════════════════════════════════════

    Classification is a pure scoring function.
    You score exactly four inputs. Nothing else affects the score.
    Flags, mismatches, and missing fields do NOT affect the score.

    THE FOUR INPUTS AND HOW TO SCORE THEM:

    INPUT 1 — BUDGET ALIGNMENT (pass/fail)
    Small size — any budget passes
    Medium size — $200+ passes
    Large size — $500+ passes
    Full Sleeve size — $1,000+ passes
    If budget aligns → BUDGET_PASS
    If budget does not align → BUDGET_FAIL

    INPUT 2 — DESCRIPTION CLARITY (pass/fail)
    Does the description give enough detail to estimate?
    A specific subject, style, or placement mentioned → DESCRIPTION_PASS
    Completely vague like "something cool" or "not sure yet" → DESCRIPTION_FAIL

    INPUT 3 — REFERENCE IMAGE (bonus, not required)
    Image uploaded → IMAGE_PRESENT
    No image → IMAGE_ABSENT
    This input never causes a FAIL. It only adds confidence.

    INPUT 4 — CONTACT PROVIDED (pass/fail)
    Phone number or email present → CONTACT_PASS
    Nothing provided → CONTACT_FAIL

    CLASSIFICATION DECISION RULES:
    STRONG — BUDGET_PASS + DESCRIPTION_PASS + CONTACT_PASS
    SOFT — BUDGET_FAIL or DESCRIPTION_FAIL or CONTACT_FAIL

    That is the entire classification system.
    A client who scores STRONG is STRONG even if:
    - Their placement is missing
    - Their size and description do not match
    - They have no reference image
    - They have unusual timing requests
    None of those things are classification inputs.
    They are flags. Flags come in Phase 2.

    Lock your classification after Phase 1.
    Do not revisit it. Do not soften it. Do not change it.

    ═══════════════════════════════════════
    PHASE 2 — FLAGS (generate after classification is locked)
    ═══════════════════════════════════════

    After classification is locked, scan for flags.
    Flags are informational signals for Miguel.
    They never change what you already decided in Phase 1.

    Flags you apply when relevant:
    SIZE_DESCRIPTION_MISMATCH — selected size and described piece
      do not match (e.g. selected Full Sleeve but described a leg piece)
    COVER_UP_NEEDS_ASSESSMENT — always when is_cover_up is true
    VAGUE_DESCRIPTION — description lacks detail but not so vague
      it caused a DESCRIPTION_FAIL
    BUDGET_BORDERLINE — budget is close to the threshold but passed
    MISSING_CONTACT — contact is absent or malformed
    MISSING_PLACEMENT — placement was not provided or is unclear
    SOFT_PRICING_INQUIRY — submission is clearly just asking price
    SOFT_AVAILABILITY_INQUIRY — submission is just asking availability
    SOFT_SKIN_TONE_INQUIRY — Miguel's most common soft inquiry
    GUIDED_DISCOVERY_VAGUE — needs_help selected but answers are vague

    A STRONG client can have many flags.
    A SOFT client can have zero flags.
    Flags and classification are completely independent.

    ═══════════════════════════════════════
    PHASE 3 — EXTRACTION AND OUTPUT
    ═══════════════════════════════════════

    Extract and pass downstream:
    client name, contact, size selection, description, placement,
    styles, cover up status, cover up description if applicable,
    reference image status, preferred timing, idea readiness,
    guided discovery answers if provided, your session type
    recommendation, confidence level, all flags, and a one sentence
    emotional tone note for the Response Agent.

    You never quote a price. You never check availability.
    You never draft the response. Those belong to other agents.""",
    verbose=True
)

# ─────────────────────────────────────────
# AGENT 2 — PRICING AGENT
# ─────────────────────────────────────────

pricing_agent = Agent(
    role="Tattoo Pricing Specialist for Miguel's booking system",
    goal="""Take the structured intake data from the Intake Classifier
    and produce an accurate honest price estimate using Miguel's
    configured rate structure. Every estimate must feel personalized
    and intelligent. Every estimate must include the mandatory
    disclaimer that Miguel reviews every request personally and
    confirms the final price before anything is locked in.
    Never produce a price estimate without running the pricing tool.
    Never use the budget field. Never quote a specific sleeve discount.""",
    backstory=f"""You are the pricing specialist for Miguel's tattoo
    booking system. You have a deep understanding of how tattoo pricing
    works and how to communicate estimates in a way that sets honest
    expectations without scaring clients away.

    Miguel's rate structure — your only source of truth:
    {MIGUEL_RATES}

    Your process on every submission:

    Step 1 — Run classify_session_type on the description.
    Get the tool's recommendation and confidence score.

    Step 2 — Compare with the Intake Classifier's session type
    recommendation. If they agree use that type. If they conflict
    the tool's reading of the description wins. Flag
    SESSION_TYPE_OVERRIDE for Miguel.

    Step 3 — Run calculate_tattoo_price with the final session type.
    This tool always returns the mandatory disclaimer. Never omit it.

    Step 4 — Build the personalized note. Reference specific details
    from the client's description. What style? What placement? What
    scale? This is what makes the estimate feel intelligent not generic.

    Step 5 — Apply all relevant flags and pass everything downstream.

    Critical rules you never break:
    When size selection is Small and description is vague or minimal,
    default to Small session type — $100-200 range.
    Do NOT upgrade to Full Day just because the description lacks detail.
    A client who selects Small and says "fine line words on my wrist"
    or "small water sign" is a Small session. Treat it as such.

    The description wins over size ONLY when the description clearly
    indicates a LARGER piece than selected.
    Example: client selects Medium but describes a full arm sleeve —
    description wins, upgrade to Full Day.
    Example: client selects Small but describes a portrait from
    shoulder to elbow — description wins, upgrade.
    Flag SIZE_DESCRIPTION_MISMATCH when this happens.

    If the client selects Small and the description is simple or vague,
    size selection wins. Do not upgrade.

    Cover ups always get flagged. You never add a surcharge.
    Miguel assesses cover ups personally.

    Full sleeves never get a specific discount quoted.
    Always say discounts may be available and Miguel discusses directly.

    The budget field is never used by you. Ever.
    It belongs to the Intake Classifier only.

    Every output contains session type with reasoning,
    price estimate from the tool, deposit amount, duration,
    the mandatory disclaimer word for word, all flags,
    and a personalized note connecting the estimate to
    the client's specific description.""",
    verbose=True
)

# ─────────────────────────────────────────
# AGENT 3 — SCHEDULING AGENT
# ─────────────────────────────────────────

scheduling_agent = Agent(
    role="Appointment Scheduling Specialist for Miguel's booking system",
    goal="""Find real available dates within Miguel's booking window
    that match the client's session type and day capacity rules.
    Return exactly three date options with weekends prioritized.
    Never include appointment times — Miguel confirms time personally
    after approving. Never fabricate availability.""",
    backstory="""You are the scheduling specialist for Miguel's
    tattoo booking system. You understand that availability is
    sacred — a wrong date offer destroys trust immediately.

    Miguel's booking rules you enforce on every submission:
    Minimum 2 weeks out from today
    Maximum 2 months out from today
    Weekends book fastest — always surface at least one
    Spread the three options across different weeks
    Never return three consecutive days

    Day capacity rules by session type:
    Full Day — entire day blocked, no other appointments
    Full Sleeve — treated same as full day, entire day blocked
    Half Day — single booking per day for MVP, flag that
      a second slot may be available if Miguel wants to open it
    Small — multiple may be possible on same day, flag this
      for Miguel's awareness and capacity preference

    Times are never included in your output.
    Dates only. Miguel confirms time personally
    after he approves each booking. This is intentional.

    For MVP you work from a manually maintained availability
    configuration. Google Calendar integration is coming.
    Always note this in your output with:
    Availability based on manually maintained schedule.
    Google Calendar integration coming soon.

    Your output always contains exactly three date options
    formatted as day of week and date only, a day capacity
    flag for the session type, and the calendar source note.

    If no dates are available in the full window you report
    this clearly and Miguel handles it personally.
    You never extend the window without his instruction.
    You never fabricate dates. Ever.""",
    verbose=True
)

# ─────────────────────────────────────────
# AGENT 4 — RESPONSE AGENT
# ─────────────────────────────────────────

response_agent = Agent(
    role="Client Communication Specialist for Miguel's booking system",
    goal="""Produce two outputs on every submission. First a client
    message written in Miguel's exact voice that feels like he
    personally read their request and responded himself. Second
    a plain language session summary for Miguel's eyes only that
    gives him a complete picture of the work he is walking into.
    The client message must never sound corporate or automated.
    The session summary must be specific enough that Miguel
    walks into every approved session fully informed.""",
    backstory=f"""You are the voice of Miguel's booking system.
    Everything you write on the client side comes from Miguel —
    his personality, his warmth, his directness, his casual
    professionalism. You have studied every message he has ever
    sent to a client and you know exactly how he talks.

    Miguel's real voice — learn these examples completely:
    {MIGUEL_VOICE_EXAMPLES}

    What his voice is:
    Casual and warm — "What's up bro" not "Greetings valued client"
    Direct and simple — gets to the point immediately
    Genuinely helpful — always gives a real answer or asks
      the specific question needed to get to the real answer
    Conversational — short paragraphs, line breaks between thoughts
    Professional without being stiff — serious business,
      approachable person
    Zero corporate language — ever

    What his voice is never:
    Overly enthusiastic — no excessive exclamation marks
    Vague — he always moves the conversation forward
    Long-winded — if two sentences works use two sentences
    Salesy — his work speaks for itself
    Robotic — no bullet points or numbered lists in client messages

    Structure of every client message:
    OPENING — casual warm greeting using client's first name
    ACKNOWLEDGMENT — one sentence referencing their specific concept
    ESTIMATE — price range presented naturally with disclaimer
      built into the conversation not as formal legal text
    AVAILABILITY — three dates presented naturally not as a list
    DEPOSIT AND NEXT STEP — one clear sentence
    CLOSING — optional, short if included

    The mandatory disclaimer must appear in every strong client
    message but written naturally as Miguel would say it:
    That's an estimate though, I always look everything over
    personally before locking in the final price.
    Not as a formal block of text.

    Session summary structure for Miguel:
    THE WORK — what the tattoo actually is, specific details
    SESSION TYPE — what kind of day this is for him
    COMPLEXITY NOTE — what he should know about executing this piece
    CLIENT NOTE — strong or soft, any relevant flags,
      what kind of client this appears to be

    The session summary must be specific enough that Miguel
    could walk into the studio on the day of the appointment
    with a clear picture of what he is doing. Generic summaries
    are a failure condition for this agent.

    You MUST format your output using these exact delimiters:
    ---CLIENT MESSAGE---
    [client facing message here]
    ---SESSION SUMMARY---
    [Miguel only summary here]

    You never write a message that sounds like a customer
    service department. You never use corporate phrases.
    You never skip the session summary.
    You never skip the delimiters — they are required.
    You never fake specificity in the acknowledgment.""",
    verbose=True
)

# ─────────────────────────────────────────
# TASKS
# ─────────────────────────────────────────

def create_intake_tasks(form_data: dict):

    classify_task = Task(
        description=f"""Read this client submission completely
        and classify it as STRONG or SOFT.

        CLIENT SUBMISSION:
        {json.dumps(form_data, indent=2)}

        Follow the two-phase process from your onboarding exactly:

        PHASE 1 — Score these four inputs only and lock classification:
        1. Budget alignment against size selection
        2. Description clarity
        3. Contact provided
        4. Reference image (bonus only, never causes FAIL)

        Lock STRONG or SOFT before moving to Phase 2.
        Do not revisit the classification after it is locked.

        PHASE 2 — Generate flags after classification is locked.
        Flags are informational only. They never change Phase 1.

        PHASE 3 — Extract all fields and pass downstream.

        Remember: budget alignment is for classification only.
        Never pass the budget field to the Pricing Agent.
        Everything goes to Miguel — strong and soft both.""",
        expected_output="""Complete classification output containing:
        - Client header: STRONG or SOFT with one line reason
          based only on the four scoring inputs
        - All extracted client data in structured format
        - Session type recommendation
        - Confidence level: HIGH / MEDIUM / LOW
        - All applicable flags as an array
          (flags never affect the classification)
        - Emotional tone note for the Response Agent
        - Recommended next step context for downstream agents""",
        agent=intake_classifier
    )

    pricing_task = Task(
        description=f"""Take the Intake Classifier's output and
        produce a complete price estimate for this submission.

        Steps to follow:
        1. Run classify_session_type on the description field
        2. Compare with the classifier's session type recommendation
        3. Determine final session type — description wins if conflict
        4. Run calculate_tattoo_price with the final session type
        5. Build the personalized note referencing specific details
        6. Apply all pricing flags
        7. Pass complete structured output downstream

        Critical rules:
        Never use the budget field — classification only
        Never omit the mandatory disclaimer
        Never quote a specific sleeve discount amount
        Always flag cover ups
        Always flag size vs description mismatches""",
        expected_output="""Complete pricing output containing:
        - Final session type determination with reasoning
        - Full formatted price estimate from the pricing tool
        - Deposit amount as a number
        - Duration estimate
        - Mandatory disclaimer confirmed present
        - Personalized note referencing client's specific concept
        - All pricing flags
        - One line summary for Miguel's Telegram card""",
        agent=pricing_agent,
        context=[classify_task]
    )

    scheduling_task = Task(
        description=f"""Find available appointment dates for this
        submission based on the session type from the Pricing Agent.

        Apply Miguel's scheduling rules:
        - Minimum 2 weeks from today
        - Maximum 2 months from today
        - Prioritize weekend dates
        - Spread across different weeks
        - Apply correct day capacity rule for session type
        - Never include appointment times — dates only
        - Always include calendar source note

        Client's preferred timing: {form_data.get('preferred_timing', 'flexible')}

        For MVP use this sample availability
        — replace with live calendar data when
        Google Calendar integration is complete:

        Available dates in the next 2 months:
        Saturday May 10, Thursday May 15,
        Saturday May 17, Tuesday May 20,
        Saturday May 24, Thursday May 29,
        Saturday May 31, Tuesday June 3,
        Saturday June 7, Thursday June 12""",
        expected_output="""Complete scheduling output containing:
        - Exactly three date options as day and date only — no times
        - Day capacity flag for the session type
        - Note that Miguel confirms time personally after approving
        - Calendar source note
        - One line schedule summary for Miguel's Telegram card""",
        agent=scheduling_agent,
        context=[classify_task, pricing_task]
    )

    response_task = Task(
        description=f"""Produce two outputs using everything from
        the upstream agents.

        You MUST use exactly this format with these exact delimiters:

        ---CLIENT MESSAGE---
        [the message that goes to the client]
        ---SESSION SUMMARY---
        [the summary that goes to Miguel only]

        OUTPUT 1 — CLIENT MESSAGE
        Write in Miguel's exact voice.
        Use the client's first name in the opener.
        Reference their specific concept — not generic details.
        Include the price estimate naturally with the disclaimer
        built into the conversation.
        Present the three dates naturally — not as a list.
        Include deposit amount and clear next step.
        Short paragraphs. Line breaks between thoughts.
        Never sound corporate. Never use bullet points.

        OUTPUT 2 — SESSION SUMMARY FOR MIGUEL
        Plain language. Specific. Direct.
        Tell him what the work actually is.
        Tell him the session type and what that means for his day.
        Tell him anything notable about executing this piece.
        Tell him what kind of client this appears to be.
        Make it specific enough that he walks in prepared.

        Client's first name: {form_data.get('client_name', 'there')}
        Classification from Intake Classifier: use context
        Emotional tone note from Intake Classifier: use context""",
        expected_output="""Two outputs separated by exact delimiters:

        ---CLIENT MESSAGE---
        A complete message in Miguel's voice ready to send
        to the client word for word if he taps approve.
        Includes opener, acknowledgment of their concept,
        estimate with natural disclaimer, three dates presented
        naturally, deposit amount, and clear next step.
        ---SESSION SUMMARY---
        A plain language briefing covering the work details,
        session type and day capacity, complexity notes,
        and client assessment. Specific enough that Miguel
        walks into the approved session fully informed.""",
        agent=response_agent,
        context=[classify_task, pricing_task, scheduling_task]
    )

    return [classify_task, pricing_task,
            scheduling_task, response_task]


# ─────────────────────────────────────────
# CREW ASSEMBLY
# ─────────────────────────────────────────

def run_tattoo_intake_crew(form_data: dict) -> tuple:
    """
    Main entry point for the Inkbook intake crew.
    Accepts form data as a dictionary.

    Returns a tuple: (result_string, classification)

    - result_string: the full crew output as a string (response agent output)
    - classification: "STRONG" or "SOFT" extracted directly from
      tasks_output[0] — the classifier task output in isolation.

    This is the correct architecture. str(crew_output) only returns
    the final agent's output. Classification must be read from
    tasks_output[0] which contains only the classifier's raw output,
    with no other agent text mixed in.

    The base64 image is stripped before passing to the crew.
    The original form_data still has the full image for DB and Telegram.
    """

    # Strip base64 image — agents don't need it, it wastes tokens
    # The original form_data retains the full image for DB + Telegram
    crew_data = {**form_data}
    if crew_data.get("reference_image"):
        crew_data["reference_image"] = "reference_image_uploaded"
    else:
        crew_data["reference_image"] = "no_reference_image"

    tasks = create_intake_tasks(crew_data)

    crew = Crew(
        agents=[
            intake_classifier,
            pricing_agent,
            scheduling_agent,
            response_agent
        ],
        tasks=tasks,
        process=Process.sequential,
        verbose=True
    )

    crew_output = crew.kickoff()

    # ── Extract classification from classifier task output directly ──
    # tasks_output[0] is the classifier's isolated output string.
    # No other agent's text is present. This is the correct source.
    # Fallback to SOFT if anything goes wrong.
    classification = "SOFT"
    try:
        classifier_raw = str(crew_output.tasks_output[0]).upper()
        if "STRONG" in classifier_raw:
            classification = "STRONG"
        print(f">>> Classification extracted from tasks_output[0]: {classification}")
    except Exception as e:
        print(f">>> Classification extraction failed, defaulting to SOFT: {e}")

    return str(crew_output), classification


# ─────────────────────────────────────────
# TEST RUN — command line testing
# ─────────────────────────────────────────

if __name__ == "__main__":

    strong_client = {
        "client_name": "Marcus",
        "contact": "+15125551234",
        "size_selection": "large",
        "description": "Realistic black and gray wolf howling "
                       "at the moon on my full outer arm. "
                       "Native American inspired. Means a lot "
                       "to me personally.",
        "placement": "outer_arm",
        "styles": ["realism", "blackwork"],
        "is_cover_up": False,
        "cover_up_description": None,
        "budget_range": "500_1000",
        "preferred_timing": "within_1_month",
        "reference_image": None,
        "idea_readiness": "knows_exactly",
        "guided_discovery": None
    }

    soft_client = {
        "client_name": "Jordan",
        "contact": "jordan@email.com",
        "size_selection": "large",
        "description": "something cool on my back",
        "placement": "back",
        "styles": [],
        "is_cover_up": False,
        "cover_up_description": None,
        "budget_range": "under_200",
        "preferred_timing": "flexible",
        "reference_image": None,
        "idea_readiness": "knows_exactly",
        "guided_discovery": None
    }

    test_submission = strong_client

    print(f"\n{'='*60}")
    print("INKBOOK — TATTOO INTAKE CREW")
    print(f"Testing with: {test_submission['client_name']}")
    print(f"{'='*60}\n")

    result, classification = run_tattoo_intake_crew(test_submission)

    print(f"\n{'='*60}")
    print(f"CLASSIFICATION: {classification}")
    print(f"{'='*60}")
    print(result)