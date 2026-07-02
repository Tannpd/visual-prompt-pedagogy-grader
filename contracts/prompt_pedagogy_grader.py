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


class Contract(gl.Contract):
    records: TreeMap[str, PromptEvaluationRecord]
    next_id: bigint

    def __init__(self):
        self.next_id = bigint(0)

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
