import pytest
import json


def test_initial_state(direct_deploy):
    contract = direct_deploy("contracts/prompt_pedagogy_grader.py", sdk_version="v0.2.16")
    assert contract.get_total_records() == 0


def test_input_validation(direct_deploy, direct_vm):
    contract = direct_deploy("contracts/prompt_pedagogy_grader.py", sdk_version="v0.2.16")

    # Empty image_prompt
    with pytest.raises(Exception) as excinfo:
        contract.evaluate_prompt("", "Grade 4 students")
    assert "image_prompt must not be empty" in str(excinfo.value)

    # Empty target_audience
    with pytest.raises(Exception) as excinfo:
        contract.evaluate_prompt("A 3D cartoon of a friendly map", "")
    assert "target_audience must not be empty" in str(excinfo.value)


def test_evaluate_prompt_approved(direct_deploy, direct_vm):
    contract = direct_deploy("contracts/prompt_pedagogy_grader.py", sdk_version="v0.2.16")

    direct_vm.mock_llm(
        r".*",
        '{"verdict": "APPROVED", "confidence": 97, "rationale": "Prompt is safe, educational, and age-appropriate for Grade 4 students."}'
    )

    contract.evaluate_prompt(
        image_prompt="A cute 3D cartoon illustration of King Ngo Quyen planting wooden stakes on the Bach Dang River, bright colors, no violence or blood, child-friendly style.",
        target_audience="Grade 4 students aged 9-10"
    )

    assert contract.get_total_records() == 1

    record_json = contract.get_record("0")
    record = json.loads(record_json)

    assert record["id"] == "0"
    assert record["verdict"] == "APPROVED"
    assert record["confidence"] == 97
    assert "safe" in record["rationale"].lower() or "appropriate" in record["rationale"].lower()
