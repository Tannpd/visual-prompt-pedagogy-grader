# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *

import json
import typing
from dataclasses import dataclass


@allow_storage
@dataclass
class PromptEvaluationRecord:
    image_prompt: str
    target_audience: str
    verdict: str  # APPROVED | NEEDS_REVISION | REJECTED
    confidence: bigint
    rationale: str


def _normalize_verdict(verdict: str) -> str:
    v = str(verdict or "").strip().upper()
    if "APPROVED" in v and "NEEDS" not in v:
        return "APPROVED"
    if "NEEDS" in v or "REVISION" in v:
        return "NEEDS_REVISION"
    if "REJECT" in v or "DENIED" in v or "REFUSE" in v:
        return "REJECTED"
    return "NEEDS_REVISION"


def _normalize_confidence(conf_val: typing.Any) -> int:
    try:
        c = int(conf_val)
    except Exception:
        c = 0
    return max(0, min(100, c))


class Contract(gl.Contract):
    records: TreeMap[str, PromptEvaluationRecord]
    next_id: bigint

    def __init__(self):
        self.next_id = bigint(0)

    @gl.public.write
    def evaluate_prompt(self, image_prompt: str, target_audience: str) -> None:
        if not image_prompt or not image_prompt.strip():
            raise gl.vm.UserError("image_prompt must not be empty")
        if not target_audience or not target_audience.strip():
            raise gl.vm.UserError("target_audience must not be empty")

        prompt_clean = image_prompt.strip()
        audience_clean = target_audience.strip()

        def leader_fn() -> str:
            eval_prompt = f"""You are a strict primary school administrator and ethics compliance officer.
Your task is to evaluate whether an AI image generation prompt is safe, appropriate,
and pedagogically sound for the given target audience.

TARGET AUDIENCE:
---
{audience_clean}
---

AI IMAGE GENERATION PROMPT TO EVALUATE:
---
{prompt_clean}
---

Evaluation criteria:
- Assign "APPROVED" if the prompt is clearly educational, age-appropriate, free from
  any violent, sexual, biased, or otherwise inappropriate elements, and serves a
  genuine pedagogical purpose (e.g., historical figures, geographic maps, math
  visualizations, scientific concepts shown in a safe and friendly style).
- Assign "NEEDS_REVISION" if the prompt has educational intent but contains elements
  that are mildly inappropriate, ambiguous, potentially biased, or could be improved
  with minor modifications (e.g., "a battle scene" without explicit violence, or an
  oversimplified cultural stereotype that needs more nuance).
- Assign "REJECTED" if the prompt contains violent, gory, sexually suggestive,
  discriminatory, or otherwise clearly age-inappropriate content that cannot be
  salvaged by minor edits. Safety of the children is the highest priority.
- Assign a confidence score from 0 to 100 representing how certain you are of this verdict.
- Provide a concise rationale (maximum 250 characters) explaining your decision.

Respond ONLY with a valid JSON object matching this structure:
{{
  "verdict": "APPROVED" | "NEEDS_REVISION" | "REJECTED",
  "confidence": <integer 0-100>,
  "rationale": "rationale string"
}}"""
            res = gl.nondet.exec_prompt(eval_prompt, response_format="json")
            if not isinstance(res, dict):
                res = {}

            verdict = _normalize_verdict(res.get("verdict", "NEEDS_REVISION"))
            confidence = _normalize_confidence(res.get("confidence", 0))
            rationale = str(res.get("rationale", "")).strip()[:250]
            if not rationale:
                rationale = "No rationale provided."

            return json.dumps({
                "verdict": verdict,
                "confidence": confidence,
                "rationale": rationale
            }, sort_keys=True)

        def validator_fn(leader_res: typing.Any) -> bool:
            if not isinstance(leader_res, gl.vm.Return):
                return False
            try:
                leader_data = json.loads(leader_res.calldata)
            except Exception:
                return False

            leader_verdict = _normalize_verdict(leader_data.get("verdict"))
            leader_confidence = _normalize_confidence(leader_data.get("confidence"))

            try:
                mine_json = leader_fn()
                mine_data = json.loads(mine_json)
            except Exception:
                return False

            mine_verdict = _normalize_verdict(mine_data.get("verdict"))
            mine_confidence = _normalize_confidence(mine_data.get("confidence"))

            if leader_verdict != mine_verdict:
                return False

            if abs(leader_confidence - mine_confidence) > 15:
                return False

            return True

        raw_result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        payload = json.loads(raw_result)

        rid = str(self.next_id)
        self.records[rid] = PromptEvaluationRecord(
            image_prompt=prompt_clean,
            target_audience=audience_clean,
            verdict=_normalize_verdict(payload.get("verdict")),
            confidence=bigint(_normalize_confidence(payload.get("confidence"))),
            rationale=str(payload.get("rationale", "")).strip()[:250]
        )
        self.next_id = self.next_id + bigint(1)

    @gl.public.view
    def get_record(self, record_id: str) -> str:
        if record_id not in self.records:
            raise gl.vm.UserError("Evaluation record not found")

        record = self.records[record_id]
        return json.dumps({
            "id": record_id,
            "image_prompt": record.image_prompt,
            "target_audience": record.target_audience,
            "verdict": record.verdict,
            "confidence": int(record.confidence),
            "rationale": record.rationale
        })

    @gl.public.view
    def get_total_records(self) -> int:
        return int(self.next_id)
