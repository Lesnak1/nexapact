# { "Depends": "py-genlayer:test" }
"""
NexaPact Protocol: Decentralized Agent Labor & Multi-Milestone Escrow on GenLayer.

Enables autonomous AI agents and human contributors to discover, contract, and settle
complex tasks. Milestone completion is adjudicated via decentralized multi-validator
LLM consensus grounded on live web evidence (GitHub PRs, test reports, and API endpoints).
"""

import genlayer as gl
from genlayer import *
from dataclasses import dataclass
import json


@gl.storage.allow
@dataclass
class Milestone:
    description: str
    evidence_url: str
    payout_amount: u256
    status: str  # "PENDING", "SUBMITTED", "APPROVED", "REVISION_REQUIRED", "REFUNDED"
    score_functional: u32
    score_criteria: u32
    score_quality: u32
    defect_severity: str  # "NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"
    adjudication_summary: str


@gl.storage.allow
@dataclass
class EscrowAgreement:
    client: Address
    contractor: Address
    total_locked: u256
    remaining_balance: u256
    is_active: bool
    milestone_count: u32
    title: str


@gl.storage.allow
@dataclass
class AgentProfile:
    reputation_score: u32
    completed_tasks: u32
    slashed_tasks: u32
    metadata_uri: str


class NexaPact(gl.contract.Contract):
    """Decentralized Agent Labor & AI-Adjudicated Milestone Escrow on GenLayer."""

    agreements: gl.storage.TreeMap[u256, EscrowAgreement]
    milestones: gl.storage.TreeMap[str, Milestone]  # Key: f"{agreement_id}_{milestone_idx}"
    agents: gl.storage.TreeMap[Address, AgentProfile]
    agreement_counter: u256

    def __init__(self):
        self.agreement_counter = u256(0)

    @gl.public.write.payable
    def create_agreement(self, contractor: str, title: str = "Agent Labor Agreement") -> u256:
        """Create a new escrow agreement and lock GEN funds deposited with this call."""
        deposit_val = gl.message.value
        if deposit_val == u256(0):
            raise gl.vm.UserError("Escrow agreement requires a non-zero GEN deposit.")

        contractor_addr = Address(contractor)
        if contractor_addr == gl.message.sender_address:
            raise gl.vm.UserError("Client and contractor cannot be the same address.")

        agreement_id = self.agreement_counter
        self.agreement_counter = self.agreement_counter + u256(1)

        self.agreements[agreement_id] = EscrowAgreement(
            client=gl.message.sender_address,
            contractor=contractor_addr,
            total_locked=deposit_val,
            remaining_balance=deposit_val,
            is_active=True,
            milestone_count=u32(0),
            title=title,
        )

        # Initialize profile if not present
        if contractor_addr not in self.agents:
            self.agents[contractor_addr] = AgentProfile(
                reputation_score=u32(100),
                completed_tasks=u32(0),
                slashed_tasks=u32(0),
                metadata_uri="",
            )

        return agreement_id

    @gl.public.write
    def add_milestone(
        self,
        agreement_id: u256,
        description: str,
        evidence_url: str,
        payout_amount: u256,
    ) -> u32:
        """Client configures a milestone with specification, evidence URL, and payout."""
        if agreement_id not in self.agreements:
            raise gl.vm.UserError("Agreement does not exist.")

        agreement = self.agreements[agreement_id]
        if gl.message.sender_address != agreement.client:
            raise gl.vm.UserError("Only the client can add milestones.")

        if not agreement.is_active:
            raise gl.vm.UserError("Agreement is not active.")

        if payout_amount == u256(0):
            raise gl.vm.UserError("Milestone payout must be greater than zero.")

        # Calculate currently allocated payout across existing milestones
        allocated = u256(0)
        for i in range(int(agreement.milestone_count)):
            m_key = f"{agreement_id}_{i}"
            if m_key in self.milestones:
                allocated = allocated + self.milestones[m_key].payout_amount

        if allocated + payout_amount > agreement.total_locked:
            raise gl.vm.UserError(
                f"Total milestone allocations ({allocated + payout_amount}) exceed locked deposit ({agreement.total_locked})."
            )

        milestone_idx = agreement.milestone_count
        agreement.milestone_count = milestone_idx + u32(1)
        self.agreements[agreement_id] = agreement

        key = f"{agreement_id}_{milestone_idx}"
        self.milestones[key] = Milestone(
            description=description,
            evidence_url=evidence_url,
            payout_amount=payout_amount,
            status="PENDING",
            score_functional=u32(0),
            score_criteria=u32(0),
            score_quality=u32(0),
            defect_severity="NONE",
            adjudication_summary="Milestone created. Awaiting deliverable submission.",
        )
        return milestone_idx

    @gl.public.write
    def submit_and_adjudicate_milestone(
        self,
        agreement_id: u256,
        milestone_idx: u32,
        submission_notes: str = "",
    ) -> str:
        """
        Contractor submits deliverable. GenLayer validators independently fetch web evidence,
        run neural multi-axis evaluation, reach consensus under Equivalence Principle,
        and release funds if criteria are fulfilled.
        """
        if agreement_id not in self.agreements:
            raise gl.vm.UserError("Agreement does not exist.")

        agreement = self.agreements[agreement_id]
        if gl.message.sender_address != agreement.contractor:
            raise gl.vm.UserError("Only the assigned contractor can submit milestones.")

        if not agreement.is_active:
            raise gl.vm.UserError("Agreement is closed.")

        m_key = f"{agreement_id}_{milestone_idx}"
        if m_key not in self.milestones:
            raise gl.vm.UserError("Milestone index out of bounds.")

        milestone = self.milestones[m_key]
        if milestone.status not in ["PENDING", "REVISION_REQUIRED"]:
            raise gl.vm.UserError(f"Milestone cannot be adjudicated from status: {milestone.status}")

        milestone.status = "SUBMITTED"
        self.milestones[m_key] = milestone

        # Execution of non-deterministic web retrieval and neural adjudication
        evidence_url = milestone.evidence_url
        spec_desc = milestone.description

        def run_adjudication_pipeline() -> dict:
            # 1. Fetch live off-chain evidence
            try:
                evidence_text = gl.nondet.web.get(evidence_url)
                if len(evidence_text) > 8000:
                    evidence_text = evidence_text[:8000]
            except Exception as e:
                evidence_text = f"EVIDENCE_FETCH_ERROR: Could not retrieve {evidence_url}. Error: {str(e)}"

            # 2. Multi-axis neural prompt evaluation
            eval_prompt = f"""
            You are an impartial GenLayer Validator adjudicating a contractual milestone.
            
            SPECIFICATION / ACCEPTANCE CRITERIA:
            \"\"\"{spec_desc}\"\"\"

            SUBMISSION EVIDENCE (Retrieved from {evidence_url}):
            \"\"\"{evidence_text}\"\"\"

            CONTRACTOR NOTES:
            \"\"\"{submission_notes}\"\"\"

            Evaluate the evidence against the specification strictly and impartially.
            Provide scores (0-100) for:
            1. functional: Did it achieve the stated objective?
            2. criteria: Were all explicit criteria fulfilled?
            3. quality: Code/deliverable quality, completeness, and documentation.
            4. defect_severity: NONE, LOW, MEDIUM, HIGH, or CRITICAL.
            5. summary: 1-2 sentence rationale for the decision.

            Format your response STRICTLY as valid JSON with no markdown wrapping:
            {{"functional": 85, "criteria": 90, "quality": 80, "defect_severity": "NONE", "summary": "Deliverable successfully satisfies all criteria."}}
            """

            raw_resp = gl.nondet.exec_prompt(eval_prompt)
            # Clean possible markdown fences
            cleaned = raw_resp.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            try:
                data = json.loads(cleaned)
                func = int(data.get("functional", 0))
                crit = int(data.get("criteria", 0))
                qual = int(data.get("quality", 0))
                severity = str(data.get("defect_severity", "CRITICAL")).upper()
                if severity not in ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]:
                    severity = "CRITICAL"
                summary = str(data.get("summary", "Adjudication completed."))[:300]
            except Exception:
                func, crit, qual = 0, 0, 0
                severity = "CRITICAL"
                summary = "Failed to parse validator adjudication JSON response."

            return {
                "functional": func,
                "criteria": crit,
                "quality": qual,
                "defect_severity": severity,
                "summary": summary,
            }

        def validator_comparator(leader_res: dict, validator_res: dict) -> bool:
            """Equivalence Principle: Ensure consensus across multi-axis evaluations."""
            # 1. Defect severity must be in equivalent danger tier
            critical_tiers = ["HIGH", "CRITICAL"]
            lead_is_crit = leader_res["defect_severity"] in critical_tiers
            val_is_crit = validator_res["defect_severity"] in critical_tiers
            if lead_is_crit != val_is_crit:
                return False

            # 2. Tolerances on numerical scores (within 8 points)
            for axis in ["functional", "criteria", "quality"]:
                diff = abs(leader_res[axis] - validator_res[axis])
                if diff > 8:
                    return False

            return True

        adjudication = gl.vm.run_nondet_unsafe(
            run_adjudication_pipeline,
            validator_comparator,
        )

        func_score = u32(max(0, min(100, adjudication["functional"])))
        crit_score = u32(max(0, min(100, adjudication["criteria"])))
        qual_score = u32(max(0, min(100, adjudication["quality"])))
        severity = adjudication["defect_severity"]
        summary = adjudication["summary"]

        milestone.score_functional = func_score
        milestone.score_criteria = crit_score
        milestone.score_quality = qual_score
        milestone.defect_severity = severity
        milestone.adjudication_summary = summary

        # Passing threshold: All scores >= 70 and no HIGH/CRITICAL defect
        passed = (
            func_score >= u32(70)
            and crit_score >= u32(70)
            and qual_score >= u32(70)
            and severity not in ["HIGH", "CRITICAL"]
        )

        contractor_profile = self.agents.get(
            agreement.contractor,
            AgentProfile(u32(100), u32(0), u32(0), ""),
        )

        if passed:
            milestone.status = "APPROVED"
            payout = milestone.payout_amount
            if payout > agreement.remaining_balance:
                payout = agreement.remaining_balance

            agreement.remaining_balance = agreement.remaining_balance - payout
            self.agreements[agreement_id] = agreement
            self.milestones[m_key] = milestone

            # Update contractor reputation
            contractor_profile.completed_tasks = contractor_profile.completed_tasks + u32(1)
            contractor_profile.reputation_score = min(
                u32(1000),
                contractor_profile.reputation_score + u32(15),
            )
            self.agents[agreement.contractor] = contractor_profile

            # Transfer payout to contractor
            gl.message.sender_address = gl.current_address
            gl.emit_transfer(agreement.contractor, payout)
            return f"APPROVED: Payout of {payout} GEN released to contractor. Score: F={func_score}, C={crit_score}, Q={qual_score}"
        else:
            milestone.status = "REVISION_REQUIRED"
            self.milestones[m_key] = milestone

            # Slight reputation decay on defective submission
            contractor_profile.reputation_score = max(
                u32(0),
                contractor_profile.reputation_score - u32(5),
            )
            self.agents[agreement.contractor] = contractor_profile
            return f"REVISION_REQUIRED: Deficiencies detected. Defect: {severity}, Scores: F={func_score}, C={crit_score}, Q={qual_score}. Summary: {summary}"

    @gl.public.write
    def refund_remaining(self, agreement_id: u256) -> u256:
        """Client can reclaim unreleased funds if milestones are incomplete or cancelled."""
        if agreement_id not in self.agreements:
            raise gl.vm.UserError("Agreement does not exist.")

        agreement = self.agreements[agreement_id]
        if gl.message.sender_address != agreement.client:
            raise gl.vm.UserError("Only the client can trigger refund.")

        if not agreement.is_active:
            raise gl.vm.UserError("Agreement is already closed.")

        # Ensure no milestone is currently in SUBMITTED state pending resolution
        for i in range(int(agreement.milestone_count)):
            m_key = f"{agreement_id}_{i}"
            if m_key in self.milestones:
                if self.milestones[m_key].status == "SUBMITTED":
                    raise gl.vm.UserError("Cannot refund while milestone is undergoing adjudication.")

        refund_amount = agreement.remaining_balance
        if refund_amount == u256(0):
            raise gl.vm.UserError("No remaining balance to refund.")

        agreement.remaining_balance = u256(0)
        agreement.is_active = False
        self.agreements[agreement_id] = agreement

        # Mark any non-approved milestones as REFUNDED
        for i in range(int(agreement.milestone_count)):
            m_key = f"{agreement_id}_{i}"
            if m_key in self.milestones:
                m = self.milestones[m_key]
                if m.status != "APPROVED":
                    m.status = "REFUNDED"
                    self.milestones[m_key] = m

        gl.message.sender_address = gl.current_address
        gl.emit_transfer(agreement.client, refund_amount)
        return refund_amount

    @gl.public.view
    def get_agreement(self, agreement_id: u256) -> dict:
        """View agreement details."""
        if agreement_id not in self.agreements:
            raise gl.vm.UserError("Agreement does not exist.")
        a = self.agreements[agreement_id]
        return {
            "client": str(a.client),
            "contractor": str(a.contractor),
            "total_locked": str(a.total_locked),
            "remaining_balance": str(a.remaining_balance),
            "is_active": a.is_active,
            "milestone_count": int(a.milestone_count),
            "title": a.title,
        }

    @gl.public.view
    def get_milestone(self, agreement_id: u256, milestone_idx: u32) -> dict:
        """View milestone details."""
        m_key = f"{agreement_id}_{milestone_idx}"
        if m_key not in self.milestones:
            raise gl.vm.UserError("Milestone not found.")
        m = self.milestones[m_key]
        return {
            "description": m.description,
            "evidence_url": m.evidence_url,
            "payout_amount": str(m.payout_amount),
            "status": m.status,
            "score_functional": int(m.score_functional),
            "score_criteria": int(m.score_criteria),
            "score_quality": int(m.score_quality),
            "defect_severity": m.defect_severity,
            "adjudication_summary": m.adjudication_summary,
        }

    @gl.public.view
    def get_agent_profile(self, agent_address: str) -> dict:
        """View agent reputation and performance history."""
        addr = Address(agent_address)
        if addr not in self.agents:
            return {
                "reputation_score": 100,
                "completed_tasks": 0,
                "slashed_tasks": 0,
                "metadata_uri": "",
            }
        p = self.agents[addr]
        return {
            "reputation_score": int(p.reputation_score),
            "completed_tasks": int(p.completed_tasks),
            "slashed_tasks": int(p.slashed_tasks),
            "metadata_uri": p.metadata_uri,
        }
