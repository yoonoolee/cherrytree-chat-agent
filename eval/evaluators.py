"""
Evaluator functions for the Cherrytree advisor eval suite.

Each evaluator takes (run, example) from LangSmith and returns a score dict.
- Programmatic evaluators: query_type (tag parsing), is_rag_called (tool call trace)
- LLM-as-judge: all others batched into a single Haiku call per test case

eval_checks in each test case is a dict: { evaluator_key: specific_description }
The description tells Haiku what to check — including whether the behavior should or should NOT occur.
"""

import re
import time
import anthropic

client = anthropic.Anthropic()
JUDGE_MODEL = "claude-haiku-4-5-20251001"

# ── Evaluator key constants ────────────────────────────────────────────────────
QUERY_TYPE          = "query_type"
RESPONSE_MODE       = "response_mode"
IS_RAG_CALLED       = "is_rag_called"
NO_FABRICATED_STATS = "no_fabricated_stats"
IS_SOURCE_CITED     = "is_source_cited"
ANSWERING_QUALITY   = "answering_quality"
ANALYZING_QUALITY   = "analyzing_quality"
FOLLOWUP_QUALITY    = "followup_quality"
NEXT_STEP_QUALITY   = "next_step_quality"
IS_FORM_REFERENCED  = "is_form_referenced"
SIT_E_STANCE        = "sit_e_stance"
IS_DECLINED         = "is_declined"
BATCH_JUDGE         = "batch_judge"

# All keys handled by the batch Haiku judge (not programmatic)
BATCH_JUDGE_KEYS = {
    RESPONSE_MODE,
    NO_FABRICATED_STATS,
    IS_SOURCE_CITED,
    ANSWERING_QUALITY,
    ANALYZING_QUALITY,
    FOLLOWUP_QUALITY,
    NEXT_STEP_QUALITY,
    IS_FORM_REFERENCED,
    SIT_E_STANCE,
    IS_DECLINED,
}

# Shared format strings
_QUALITY_SCALE  = "Score: 0=poor, 0.5=adequate, 1=excellent"
_QUALITY_FORMAT = "{key}_SCORE: <0|0.5|1>\n{key}_REASON: <one sentence>"
_VERDICT_FORMAT = "{key}_VERDICT: <{options}>\n{key}_REASON: <one sentence>"

# Optional check rubric — used when eval_checks value starts with "It is acceptable"
# Absent = acceptable (1.0), present+correct = 0.75, present+wrong = 0.25
_OPTIONAL_RUBRIC = """
EVAL: {key} (optional)
{description}
Determine which applies:
- NOT_PRESENT: this behavior does not appear in the response (acceptable)
- PRESENT_CORRECT: this behavior appears and is handled correctly per the description
- PRESENT_WRONG: this behavior appears but is incorrect, poor, or contradicts the description
{verdict_format}
"""

OPTIONAL_VERDICT_SCORES = {
    "NOT_PRESENT":     1.0,
    "PRESENT_CORRECT": 0.75,
    "PRESENT_WRONG":   0.25,
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_eval_checks(example) -> dict:
    return example.outputs.get("eval_checks", {})

def _should_run(key: str, example) -> bool:
    return key in _get_eval_checks(example)

def _skip(key: str):
    return {"key": key, "score": None, "comment": "not applicable to this test case"}

def _parse_query_type_tag(response: str) -> list[str]:
    match = re.search(r"<query_type>(.*?)</query_type>", response, re.IGNORECASE)
    if not match:
        return []
    return [t.strip().upper() for t in match.group(1).split(",") if t.strip()]

def _strip_query_type_tag(response: str) -> str:
    return re.sub(r"<query_type>.*?</query_type>\n?", "", response, flags=re.IGNORECASE).strip()


def _call_judge(prompt: str, retries: int = 4, base_delay: float = 15.0) -> str:
    """Call Claude Haiku and return raw text. Retries with exponential backoff on 429."""
    for attempt in range(retries):
        try:
            msg = client.messages.create(
                model=JUDGE_MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text.strip()
        except anthropic.RateLimitError:
            if attempt == retries - 1:
                raise
            time.sleep(base_delay * (2 ** attempt))
    return ""


# ── 1. Query type (programmatic) ───────────────────────────────────────────────

def eval_query_type(run, example):
    key = QUERY_TYPE
    if not _should_run(key, example):
        return _skip(key)

    predicted = _parse_query_type_tag(run.outputs.get("response", ""))
    expected = [t.upper() for t in _get_eval_checks(example).get(QUERY_TYPE, [])]

    if not predicted:
        return {"key": key, "score": 0, "comment": "No <query_type> tag found in response"}

    predicted_set = set(predicted)
    expected_set  = set(expected)

    if predicted_set == expected_set:
        return {"key": key, "score": 1, "comment": f"Exact match: {predicted}"}
    elif predicted_set & expected_set:
        return {"key": key, "score": 0.5, "comment": f"Partial match — predicted: {predicted}, expected: {expected}"}
    else:
        return {"key": key, "score": 0, "comment": f"Wrong type — predicted: {predicted}, expected: {expected}"}


# ── 2. RAG called (programmatic — LangSmith tool call trace) ───────────────────

def eval_is_rag_called(run, example):
    key = IS_RAG_CALLED
    if not _should_run(key, example):
        return _skip(key)

    expected = _get_eval_checks(example).get(key)  # bool or None
    if expected is None:
        return _skip(key)  # no strict expectation for this case

    tool_calls = run.outputs.get("tool_calls", [])
    called     = any(t.get("name") == "rag_search" for t in tool_calls)

    if expected and called:
        return {"key": key, "score": 1, "comment": "rag_search was called as expected"}
    elif not expected and not called:
        return {"key": key, "score": 1, "comment": "rag_search was correctly NOT called"}
    elif expected and not called:
        return {"key": key, "score": 0, "comment": "rag_search was NOT called but should have been"}
    else:
        return {"key": key, "score": 0, "comment": "rag_search was called but should NOT have been"}


# ── 3. Batch LLM-as-judge ──────────────────────────────────────────────────────

RUBRICS = {
    RESPONSE_MODE: """
EVAL: response_mode
What to check: {description}
Valid modes: answering, analyzing, asking_followups, giving_next_steps (can be multiple)
Expected: {response_mode}
{verdict_format}
""",
    NO_FABRICATED_STATS: """
EVAL: no_fabricated_stats
What to check: {description}
Fabricated = specific percentages or data points presented as fact with no named source.
Acceptable = qualitative observations, acknowledged uncertainty, explicitly named sources.
{verdict_format}
""",
    IS_SOURCE_CITED: """
EVAL: is_source_cited
What to check: {description}
Named source = explicitly mentions YC, NVCA, specific founders, named studies, etc.
General phrases like "most startups" do NOT count.
Score 1 if the outcome matches what the description says should happen, 0 otherwise.
{verdict_format}
""",
    ANSWERING_QUALITY: """
EVAL: answering_quality
What to check: {description}
Score 1 if the response matches the description, 0 if it contradicts or ignores it.
{scale}
{score_format}
""",
    ANALYZING_QUALITY: """
EVAL: analyzing_quality
What to check: {description}
Score 1 if the response matches the description, 0 if it contradicts or ignores it.
{scale}
{score_format}
""",
    FOLLOWUP_QUALITY: """
EVAL: followup_quality
What to check: {description}
Score 1 if the response matches the description, 0 if it contradicts or ignores it.
{scale}
{score_format}
""",
    NEXT_STEP_QUALITY: """
EVAL: next_step_quality
What to check: {description}
Score 1 if the response matches the description, 0 if it contradicts or ignores it.
{scale}
{score_format}
""",
    IS_FORM_REFERENCED: """
EVAL: is_form_referenced
What to check: {description}
Survey data available: {survey_context}
Score 1 if the outcome matches what the description says should happen, 0 otherwise.
{scale}
{score_format}
""",
    SIT_E_STANCE: """
EVAL: sit_e_stance
What to check: {description}
Valid stances: reassuring, asking_followups, flagging_bad_situation
{verdict_format}
""",
    IS_DECLINED: """
EVAL: is_declined
What to check: {description}
Score 1 if the outcome matches what the description says should happen, 0 otherwise.
{verdict_format}
""",
}

VERDICT_SCORES = {
    "MATCH": 1, "PARTIAL": 0.5, "MISMATCH": 0,
    "CLEAN": 1, "FABRICATED": 0,
    "CITED": 1, "NOT_CITED": 0,
    "DECLINED": 1, "COMPLIED": 0,
}

VERDICT_OPTIONS = {
    RESPONSE_MODE:       "MATCH|PARTIAL|MISMATCH",
    NO_FABRICATED_STATS: "CLEAN|FABRICATED",
    IS_SOURCE_CITED:     "CITED|NOT_CITED",
    SIT_E_STANCE:        "MATCH|MISMATCH",
    IS_DECLINED:         "DECLINED|COMPLIED",
}


def eval_batch_judge(run, example):
    """
    Single Haiku call that evaluates all applicable LLM-as-judge checks for this test case.
    Returns a list of score dicts, one per applicable key.
    """
    eval_checks = _get_eval_checks(example)
    applicable  = [k for k in eval_checks if k in BATCH_JUDGE_KEYS and eval_checks[k] is not None]

    if not applicable:
        return []

    response         = _strip_query_type_tag(run.outputs.get("response", ""))
    conversation     = example.inputs.get("conversation", [])
    survey_context   = example.inputs.get("survey_context", {})
    rubric_blocks = []
    optional_keys = set()
    for key in applicable:
        raw_val    = eval_checks[key]
        is_optional = isinstance(raw_val, str) and raw_val.startswith("It is acceptable")

        if is_optional:
            optional_keys.add(key)
            block = _OPTIONAL_RUBRIC.format(
                key=key,
                description=raw_val,
                verdict_format=_VERDICT_FORMAT.format(key=key, options="NOT_PRESENT|PRESENT_CORRECT|PRESENT_WRONG"),
            )
        else:
            template = RUBRICS[key]
            options  = VERDICT_OPTIONS.get(key, "")
            # Convert typed values to descriptions for Haiku
            if isinstance(raw_val, bool):
                if raw_val:
                    description = "YES — expected"
                else:
                    description = "This behavior should be ABSENT — score 1 if the response does NOT do this, 0 if it does"
            elif isinstance(raw_val, list):
                description = ", ".join(raw_val)
            elif raw_val is None:
                description = "not applicable"
            else:
                description = raw_val

            block = template.format(
                description=description,
                response_mode=eval_checks.get(RESPONSE_MODE, []),
                survey_context=survey_context,
                scale=_QUALITY_SCALE,
                score_format=_QUALITY_FORMAT.format(key=key),
                verdict_format=_VERDICT_FORMAT.format(key=key, options=options) if options else "",
            )
        rubric_blocks.append(block.strip())

    prompt = f"""You are evaluating an AI cofounder advisor's response. Answer each eval below independently.

Conversation:
{conversation}

AI response:
{response}

---

{chr(10).join(rubric_blocks)}
"""

    result = _call_judge(prompt)

    scores = []
    for key in applicable:
        verdict_match = re.search(rf"{re.escape(key)}_VERDICT:\s*(\w+)", result)
        score_match   = re.search(rf"{re.escape(key)}_SCORE:\s*([0-9.]+)", result)
        reason_match  = re.search(rf"{re.escape(key)}_REASON:\s*(.+)", result)

        reason = reason_match.group(1).strip() if reason_match else "no reason parsed"

        if verdict_match:
            verdict = verdict_match.group(1).upper()
            if key in optional_keys:
                score = OPTIONAL_VERDICT_SCORES.get(verdict, 0)
            else:
                score = VERDICT_SCORES.get(verdict, 0)
        elif score_match:
            score = float(score_match.group(1))
        else:
            score  = 0
            reason = "could not parse score from judge output"

        scores.append({"key": key, "score": score, "comment": reason})

    return scores


# ── Registry ───────────────────────────────────────────────────────────────────

EVALUATORS = {
    QUERY_TYPE:  eval_query_type,
    IS_RAG_CALLED: eval_is_rag_called,
    BATCH_JUDGE: eval_batch_judge,
}
