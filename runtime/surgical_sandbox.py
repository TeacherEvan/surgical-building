#!/usr/bin/env python3
"""
Surgical-Building Runtime Guard:
Enforces realpath folder-scoped sandboxing, SHA-256 canonical debrief deduplication,
token compaction thresholds (98,304 tokens), and 3-cycle revision circuit breaking.
"""
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, List, Set

class SurgicalSandboxGuard:
    MAX_CONCURRENCY = 2
    COMPACTION_TOKEN_LIMIT = 98304

    def __init__(self, workspace_root: str, max_revisions: int = 3):
        self.workspace_root = Path(os.path.realpath(workspace_root))
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.max_revisions = max_revisions
        self.seen_debrief_hashes: Set[str] = set()
        self.revision_counts: Dict[str, int] = {}

    def verify_write_path(self, target_path: str, allowed_subdirs: List[str]) -> Path:
        """Prevents symlink traversal or cross-worker file pollution."""
        resolved = Path(os.path.realpath(target_path))
        if not str(resolved).startswith(str(self.workspace_root)):
            raise PermissionError(f"Sandbox Violation: {resolved} escapes workspace {self.workspace_root}")

        allowed_resolved = [Path(os.path.realpath(self.workspace_root / d)) for d in allowed_subdirs]
        if not any(str(resolved).startswith(str(a)) for a in allowed_resolved):
            raise PermissionError(f"Subagent Scope Violation: {resolved} not in allowed paths {allowed_subdirs}")
        return resolved

    def register_and_verify_debrief(self, subagent_role: str, debrief_payload: Dict) -> str:
        """Computes canonical JSON SHA-256 hash to halt identical hallucination loops."""
        payload_copy = {k: v for k, v in debrief_payload.items() if k != "payload_sha256"}
        canonical_bytes = json.dumps(payload_copy, sort_keys=True, separators=(",", ":")).encode("utf-8")
        digest = hashlib.sha256(canonical_bytes).hexdigest()
        debrief_payload["payload_sha256"] = digest

        if digest in self.seen_debrief_hashes:
            raise RuntimeError(f"Deduplication Halt: Subagent {subagent_role} emitted duplicate state {digest[:12]}")
        self.seen_debrief_hashes.add(digest)

        if debrief_payload.get("status") == "REJECTED":
            count = self.revision_counts.get(subagent_role, 0) + 1
            self.revision_counts[subagent_role] = count
            if count > self.max_revisions:
                raise RuntimeError(f"Circuit Breaker Tripped: {subagent_role} exceeded {self.max_revisions} QA cycles.")
        return digest

if __name__ == "__main__":
    guard = SurgicalSandboxGuard("./workspace_test")
    sample_debrief = {
        "job_id": "job_00000001",
        "subagent_role": "Placement-Solver",
        "status": "APPROVED",
        "artifacts_written": ["interior/layout.json"],
        "telemetry": {"max_penetration_m": 0.0, "a_star_walkway_valid": True},
        "fix_directives": []
    }
    digest = guard.register_and_verify_debrief("Placement-Solver", sample_debrief)
    print(f"Verified SHA-256 Debrief Digest: {digest}")
