You are a policy enforcement engineer for the Noesis Agent Stack platform.

## Current Task
Enhance `agents/main-hermes/scripts/lib/approval.py` to satisfy spec requirements:

1. **Operator Override**
   - Add `operator_override: bool = False` field to the ApprovalRequest dataclass/model
   - When `operator_override` is true, bypass automatic rejection heuristics and require an explicit `approved_by` string
   - Log every override with reason and operator identity

2. **Category Tags**
   - Add `category: Optional[str]` to ApprovalRequest
   - Supported categories: `research`, `build`, `release`, `ops`, `treasury`
   - Log the category in approval decisions
   - Gate `treasury` and `release` categories to always require explicit approval (no auto-approve)

3. **Speculative-Finding Blocker**
   - Add a check: if the request payload contains a `confidence` field with value < 0.7, auto-reject with reason `speculative_finding_below_threshold`
   - If `evidence_count` is present and < 2, also auto-reject with reason `insufficient_evidence`
   - These checks run BEFORE operator override (override can still force approval, but must be logged)

4. **Decision Log Structure**
   - Ensure the decision log entry includes:
     - `decision_id: str` (UUID)
     - `category: str`
     - `outcome_ref: str` (reference to job_id or handoff_id)
     - `timestamp: str`
     - `reason: str`
     - `approved_by: Optional[str]`

## Rules
- Read approval.py before editing.
- Match existing style and patterns.
- Do NOT break existing approval flows.
- After edits, run `python -m py_compile`.
- Report exact changes and any behavioral changes.
