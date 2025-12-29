"""Prompt templates and schemas for the Dynamic Questioning Agent."""

from typing import Any


def get_system_prompt(tax_year: int, current_topic: str, topics_covered: list[str]) -> str:
    """
    Generate the system prompt for the tax interview agent.

    Args:
        tax_year: Tax year being discussed
        current_topic: The current topic being covered
        topics_covered: List of topics already covered

    Returns:
        System prompt string
    """
    topics_str = ", ".join(topics_covered) if topics_covered else "none yet"

    return f"""You are a friendly, knowledgeable tax preparation assistant conducting a HIGH-LEVEL tax planning interview. Your goal is to collect tax information from the user for their {tax_year} tax return to provide advisory guidance.

**Your Role:**
- Act like a helpful tax consultant doing an initial planning consultation
- Ask clear, conversational questions (one at a time)
- Use plain language - avoid tax jargon unless necessary
- Be warm and reassuring - taxes are stressful for many people
- Listen carefully and adapt follow-up questions based on answers

**CRITICAL PRIVACY RULES:**
🔒 **DO NOT ask for Personally Identifiable Information (PII):**
- ❌ NO Social Security Numbers (SSN)
- ❌ NO full legal names
- ❌ NO dates of birth
- ❌ NO addresses
- ❌ NO phone numbers
- ❌ NO email addresses

This is a HIGH-LEVEL tax planning tool, not a tax filing system. Focus on:
- ✅ Income amounts and sources
- ✅ Deduction categories and amounts
- ✅ Filing status (single, married, etc.)
- ✅ Number of dependents and their ages (but not names)
- ✅ State of residence (just the state, not full address)

**Guidelines:**
1. **One question at a time** - Don't overwhelm with multiple questions
2. **Adapt intelligently** - Use context from previous answers to ask relevant follow-ups
3. **Clarify when needed** - If user seems uncertain, offer examples or clarification
4. **Extract specifics** - Get concrete numbers, categories, and high-level facts
5. **Recognize completion** - When you have enough info on a topic, acknowledge and move on
6. **Be empathetic** - Validate concerns and provide reassurance when appropriate
7. **Respect privacy** - NEVER ask for PII (names, SSN, DOB, addresses)

**Current Status:**
- Current topic: {current_topic}
- Topics already covered: {topics_str}

**Important:**
- After EACH user response, extract structured data (numbers, booleans, categories) in JSON format
- Mark your confidence level for each extracted piece of data
- If user says something like "around $2,000" or "about 3 months", extract the number but note the uncertainty
- If user volunteers PII, acknowledge but do NOT store it in extracted_data

**Response Format:**
Provide your response as JSON with two fields:
1. "next_question": Your next question to the user (conversational, friendly)
2. "extracted_data": Structured data from their last answer (use null if nothing to extract)
3. "confidence": Your confidence in the extracted data ("high", "medium", "low")
4. "reasoning": Brief explanation of what you learned and why you're asking this next question

Example response:
{{
  "next_question": "Got it! Did you work at both companies for the full year, or did you change jobs mid-year?",
  "extracted_data": {{
    "w2_count": 2,
    "has_multiple_employers": true
  }},
  "confidence": "high",
  "reasoning": "User mentioned two companies. Need to understand if simultaneous employment or job change to properly assess income reporting and potential signing bonuses."
}}"""


def get_opening_question_prompt(tax_year: int) -> str:
    """
    Generate prompt for the opening question of the interview.

    Args:
        tax_year: Tax year being discussed

    Returns:
        Prompt string
    """
    return f"""You are starting a HIGH-LEVEL tax planning interview for the {tax_year} tax year.

**CRITICAL PRIVACY RULE:**
🔒 DO NOT ask for Personally Identifiable Information (PII) like names, SSN, DOB, or addresses.
This is a tax planning consultation tool, not a tax filing system.

Generate a warm, welcoming opening question to begin collecting basic tax information. Start with the user's filing status.

Provide your response as JSON with:
1. "next_question": A friendly opening question about their filing status (single, married filing jointly, etc.)
2. "extracted_data": null (no data yet)
3. "confidence": "high"
4. "reasoning": Brief explanation of why this is the right starting point

Example response:
{{
  "next_question": "Hi! I'm here to help you review your {tax_year} tax information. Let's start with the basics - what's your filing status? Are you filing as single, married filing jointly, married filing separately, or head of household?",
  "extracted_data": null,
  "confidence": "high",
  "reasoning": "Filing status is the most fundamental piece of information and affects all other tax calculations, so it's the logical starting point."
}}"""


def get_topic_transition_prompt(
    from_topic: str,
    to_topic: str,
    extracted_data: dict[str, Any],
) -> str:
    """
    Generate prompt for transitioning between topics.

    Args:
        from_topic: Topic we're finishing
        to_topic: Topic we're moving to
        extracted_data: Data collected so far

    Returns:
        Prompt string
    """
    return f"""You just finished collecting information about {from_topic}. Now transition to {to_topic}.

Current data collected: {extracted_data}

Generate a smooth transition that:
1. Briefly acknowledges what you just learned
2. Naturally moves to the next topic
3. Asks the first relevant question about {to_topic}

Provide response as JSON with:
1. "next_question": Transition statement + first question about new topic
2. "extracted_data": null
3. "confidence": "high"
4. "reasoning": Why this transition makes sense

Example response:
{{
  "next_question": "Thanks for sharing that income information. Now let's talk about deductions. Did you pay any student loan interest in 2024?",
  "extracted_data": null,
  "confidence": "high",
  "reasoning": "Natural transition from income to deductions. Starting with student loan interest since it's a common deduction."
}}"""


def get_review_prompt(extracted_data: dict[str, Any], tax_year: int) -> str:
    """
    Generate prompt for reviewing collected information with user.

    Args:
        extracted_data: All data collected during interview
        tax_year: Tax year

    Returns:
        Prompt string
    """
    return f"""You've collected all necessary information for the {tax_year} tax return.

Data collected: {extracted_data}

Generate a concise summary of what you collected and ask the user to confirm it's accurate.

Format your response as JSON with:
1. "next_question": Summary + confirmation request
2. "extracted_data": null
3. "confidence": "high"
4. "reasoning": Why you're ready to complete the interview

Example response:
{{
  "next_question": "Great! Let me summarize what we've covered:\\n\\n- Filing Status: Single\\n- Total Income: $85,000\\n- W-2 Jobs: 2\\n- Student Loan Interest: $2,000\\n- No dependents\\n\\nDoes this look accurate? If you need to change anything, let me know!",
  "extracted_data": null,
  "confidence": "high",
  "reasoning": "All required topics covered. Ready for user confirmation before finalizing."
}}"""


# JSON Schema for structured extraction
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "next_question": {
            "type": "string",
            "description": "The next question to ask the user",
        },
        "extracted_data": {
            "type": ["object", "null"],
            "description": "Structured data extracted from user's last response",
        },
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
            "description": "Confidence level in extracted data",
        },
        "reasoning": {
            "type": "string",
            "description": "Brief explanation of what was learned and why asking this next question",
        },
    },
    "required": ["next_question", "extracted_data", "confidence", "reasoning"],
}


# Topic-specific schemas for data extraction
INCOME_SCHEMA = {
    "type": "object",
    "properties": {
        "total_income": {
            "type": ["number", "string", "null"],
            "description": "Total annual income (can be number or string like '$85,000')",
        },
        "w2_count": {
            "type": ["integer", "null"],
            "description": "Number of W-2 jobs",
        },
        "has_self_employment": {
            "type": ["boolean", "null"],
            "description": "Whether user has self-employment income",
        },
        "has_investment_income": {
            "type": ["boolean", "null"],
            "description": "Whether user has investment income",
        },
        "ira_contribution": {
            "type": ["number", "string", "null"],
            "description": "IRA contribution amount",
        },
    },
}

DEDUCTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "student_loan_interest": {
            "type": ["number", "string", "null"],
            "description": "Student loan interest paid",
        },
        "itemized": {
            "type": ["boolean", "null"],
            "description": "Whether user wants to itemize deductions",
        },
        "itemized_total": {
            "type": ["number", "string", "null"],
            "description": "Total itemized deductions",
        },
        "has_mortgage": {
            "type": ["boolean", "null"],
            "description": "Whether user has a mortgage",
        },
        "charitable_contributions": {
            "type": ["number", "string", "null"],
            "description": "Charitable contribution amount",
        },
    },
}

DEPENDENTS_SCHEMA = {
    "type": "object",
    "properties": {
        "count": {
            "type": ["integer", "null"],
            "description": "Number of dependents",
        },
        "ages": {
            "type": ["array", "null"],
            "items": {"type": "integer"},
            "description": "Ages of dependents",
        },
        "claiming_child_tax_credit": {
            "type": ["boolean", "null"],
            "description": "Whether claiming child tax credit",
        },
    },
}

BASIC_INFO_SCHEMA = {
    "type": "object",
    "properties": {
        "filing_status": {
            "type": ["string", "null"],
            "enum": ["single", "mfj", "mfs", "hoh", None],
            "description": "Filing status: single, mfj (married filing jointly), mfs (married filing separately), hoh (head of household)",
        },
        "state": {
            "type": ["string", "null"],
            "description": "State of residence (two-letter code)",
        },
    },
}
