import pytest
import os
import json

CONTRACT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../contracts/nexapact.py")
)


def test_agreement_lifecycle_and_adjudication(direct_vm, direct_deploy, direct_alice, direct_bob):
    """Test creating an agreement, adding milestones, adjudicating deliverable, and releasing funds."""
    direct_vm.sender = direct_alice
    direct_vm.value = 1000

    nexapact = direct_deploy(CONTRACT_PATH)

    # 1. Create agreement
    agreement_id = nexapact.create_agreement(direct_bob, "Build GenLayer Python SDK Wrapper")
    assert agreement_id == 0

    ag_info = nexapact.get_agreement(0)
    assert ag_info["client"] == direct_alice.lower()
    assert ag_info["contractor"] == direct_bob.lower()
    assert ag_info["total_locked"] == "1000"
    assert ag_info["remaining_balance"] == "1000"
    assert ag_info["is_active"] is True
    assert ag_info["milestone_count"] == 0

    # 2. Add milestone (500 GEN)
    m_idx = nexapact.add_milestone(
        0,
        "Implement core client with automatic RPC retries",
        "https://github.com/agent-tank/sdk/pull/1",
        500,
    )
    assert m_idx == 0

    m_info = nexapact.get_milestone(0, 0)
    assert m_info["status"] == "PENDING"
    assert m_info["payout_amount"] == "500"

    # 3. Contractor submits deliverable
    direct_vm.sender = direct_bob
    direct_vm.value = 0

    direct_vm.mock_web("github.com/agent-tank/sdk/pull/1", "PR #1: Completed client implementation, 12 unit tests pass.")
    direct_vm.mock_llm("SPECIFICATION", json.dumps({
        "functional": 92,
        "criteria": 95,
        "quality": 88,
        "defect_severity": "NONE",
        "summary": "Outstanding implementation, fully compliant with specifications."
    }))

    res = nexapact.submit_and_adjudicate_milestone(0, 0, "Ready for evaluation.")
    assert "APPROVED" in res

    # Verify state after approval
    m_after = nexapact.get_milestone(0, 0)
    assert m_after["status"] == "APPROVED"
    assert m_after["score_functional"] == 92
    assert m_after["score_criteria"] == 95

    ag_after = nexapact.get_agreement(0)
    assert ag_after["remaining_balance"] == "500"

    # Verify contractor reputation
    rep = nexapact.get_agent_profile(direct_bob)
    assert rep["completed_tasks"] == 1
    assert rep["reputation_score"] == 115  # Base 100 + 15


def test_milestone_rejection_on_defective_work(direct_vm, direct_deploy, direct_alice, direct_bob):
    """Test that deliverables failing quality criteria enter REVISION_REQUIRED."""
    direct_vm.sender = direct_alice
    direct_vm.value = 800

    nexapact = direct_deploy(CONTRACT_PATH)
    ag_id = nexapact.create_agreement(direct_bob, "Security Audit Task")

    nexapact.add_milestone(
        ag_id,
        "Fuzz testing suite with coverage report",
        "https://github.com/agent-tank/fuzzer/pull/5",
        400,
    )

    direct_vm.sender = direct_bob
    direct_vm.mock_web("github.com/agent-tank/fuzzer/pull/5", "Broken build, only 1 test passed.")
    direct_vm.mock_llm("SPECIFICATION", json.dumps({
        "functional": 45,
        "criteria": 50,
        "quality": 40,
        "defect_severity": "HIGH",
        "summary": "Fuzzing framework crashes on start. Incomplete."
    }))

    res = nexapact.submit_and_adjudicate_milestone(ag_id, 0, "Please review.")
    assert "REVISION_REQUIRED" in res

    m_info = nexapact.get_milestone(ag_id, 0)
    assert m_info["status"] == "REVISION_REQUIRED"
    assert m_info["defect_severity"] == "HIGH"

    # Balance was NOT released
    ag_info = nexapact.get_agreement(ag_id)
    assert ag_info["remaining_balance"] == "800"


def test_refund_unclaimed_funds(direct_vm, direct_deploy, direct_alice, direct_bob):
    """Test client refunding remaining balance when work is unfulfilled."""
    direct_vm.sender = direct_alice
    direct_vm.value = 600

    nexapact = direct_deploy(CONTRACT_PATH)
    ag_id = nexapact.create_agreement(direct_bob, "Design System Prototype")

    nexapact.add_milestone(ag_id, "Figma design specs", "https://figma.com/design", 300)

    # Client initiates refund
    refunded = nexapact.refund_remaining(ag_id)
    assert refunded == 600

    ag_info = nexapact.get_agreement(ag_id)
    assert ag_info["remaining_balance"] == "0"
    assert ag_info["is_active"] is False

    m_info = nexapact.get_milestone(ag_id, 0)
    assert m_info["status"] == "REFUNDED"


def test_unauthorized_access_reverts(direct_vm, direct_deploy, direct_alice, direct_bob):
    """Ensure strict role isolation: only client adds milestones, only contractor submits."""
    direct_vm.sender = direct_alice
    direct_vm.value = 500

    nexapact = direct_deploy(CONTRACT_PATH)
    ag_id = nexapact.create_agreement(direct_bob, "Contractor isolation test")

    # Bob (contractor) tries to add a milestone -> must revert
    direct_vm.sender = direct_bob
    with direct_vm.expect_revert("Only the client can add milestones"):
        nexapact.add_milestone(ag_id, "Attempt unauthorized milestone", "https://evil.com", 200)

    # Alice (client) adds milestone
    direct_vm.sender = direct_alice
    nexapact.add_milestone(ag_id, "Valid milestone", "https://valid.com", 200)

    # Alice (client) tries to submit milestone -> must revert
    with direct_vm.expect_revert("Only the assigned contractor can submit milestones"):
        nexapact.submit_and_adjudicate_milestone(ag_id, 0)


def test_milestone_allocation_overflow_reverts(direct_vm, direct_deploy, direct_alice, direct_bob):
    """Ensure total milestone allocations cannot exceed locked deposit."""
    direct_vm.sender = direct_alice
    direct_vm.value = 500

    nexapact = direct_deploy(CONTRACT_PATH)
    ag_id = nexapact.create_agreement(direct_bob, "Overflow test")

    nexapact.add_milestone(ag_id, "Milestone 1", "https://m1.com", 300)

    # Attempting to allocate 300 more when only 200 left -> must revert
    with direct_vm.expect_revert("exceed locked deposit"):
        nexapact.add_milestone(ag_id, "Milestone 2", "https://m2.com", 300)
