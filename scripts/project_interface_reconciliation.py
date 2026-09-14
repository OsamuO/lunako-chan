#!/usr/bin/env python3
"""Minimal in-memory conflict reconciliation for the 6-role Project Interface.

The resolver deliberately does not semantically classify whole documents. A caller
that has identified a material conflict can pass the disputed source references to
this module. Reconciliation then uses already-resolved semantic role authority,
applicable scope, specificity within the same authority relationship, and an
independently established authorized supersession when present.

Human-readable authority/provenance text is never used as authority identity. A
specificity decision is allowed only when the same authority relationship is known
from a resolver-controlled convention or is supplied as an explicit opaque in-memory
relation identity with an independently trusted basis.

It never treats newness, persuasive wording, or a document's own authority claim as
sufficient grounds to override an applicable authority. When the available evidence
cannot establish a governing interpretation safely, the result is UNRESOLVED and an
existing ResolutionIssue is returned; no new global Harness status is introduced.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath

from project_interface_resolver import (
    ResolvedInterface,
    ResolvedReference,
    ResolutionIssue,
    Role,
)


class ReconciliationStatus(str, Enum):
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class AuthorizedSupersession:
    """Supersession authority established outside the disputed document itself."""

    source_ref: str
    authority_basis: str
    scope: str = "."


@dataclass(frozen=True)
class ConflictStatement:
    """A caller-identified material conflict among already-resolved references.

    ``authority_relation_id`` is an opaque in-memory identity for the authority
    relationship shared by the disputed candidates. It is optional because most
    conflicts should remain unresolved unless that relationship is independently
    known. ``authority_relation_basis`` records why the caller is entitled to assert
    the relation. Neither value may be inferred from the disputed documents' own
    wording.
    """

    disputed_role: Role
    source_refs: tuple[str, ...]
    scope: str = "."
    subject: str = "material conflict"
    authorized_supersession: AuthorizedSupersession | None = None
    authority_relation_id: str | None = None
    authority_relation_basis: str | None = None


@dataclass(frozen=True)
class ReconciliationDecision:
    subject: str
    disputed_role: Role
    scope: str
    governing_source_ref: str
    candidate_source_refs: tuple[str, ...]
    basis: str


@dataclass(frozen=True)
class ReconciliationResult:
    status: ReconciliationStatus
    decision: ReconciliationDecision | None
    issues: tuple[ResolutionIssue, ...] = ()


class ProjectInterfaceReconciler:
    """Reconcile one material conflict without mutating the resolved interface."""

    def reconcile(
        self,
        resolved: ResolvedInterface,
        conflict: ConflictStatement,
    ) -> ReconciliationResult:
        candidate_refs = tuple(dict.fromkeys(conflict.source_refs))
        if len(candidate_refs) < 2:
            return self._unresolved(
                conflict,
                "material conflict reconciliation requires at least two candidate sources",
            )

        indexed = self._index_references(resolved)
        missing = [source_ref for source_ref in candidate_refs if source_ref not in indexed]
        if missing:
            return self._unresolved(
                conflict,
                "conflict candidate is not already resolved: " + ", ".join(missing),
                source_ref=missing[0],
                code="CONFLICT_CANDIDATE_UNRESOLVED",
            )

        role_candidates = self._applicable_role_candidates(
            indexed,
            candidate_refs,
            conflict.disputed_role,
            conflict.scope,
        )

        supersession = conflict.authorized_supersession
        if supersession is not None:
            return self._apply_authorized_supersession(
                conflict,
                candidate_refs,
                role_candidates,
                supersession,
            )

        if len(role_candidates) == 1:
            winner = role_candidates[0]
            return self._resolved(
                conflict,
                candidate_refs,
                winner.source_ref,
                (
                    "only this candidate has established authority for the disputed "
                    f"{conflict.disputed_role.value} role in the applicable scope; "
                    "other candidate content cannot self-promote into that authority"
                ),
            )

        if not role_candidates:
            return self._unresolved(
                conflict,
                (
                    "no candidate has established authority for the disputed "
                    f"{conflict.disputed_role.value} role in scope {conflict.scope}"
                ),
            )

        specificity_winner, relation_basis = self._specificity_winner(
            role_candidates,
            conflict,
        )
        if specificity_winner is not None:
            return self._resolved(
                conflict,
                candidate_refs,
                specificity_winner.source_ref,
                (
                    "candidates share the same independently established authority "
                    "relationship; the governing source is the uniquely more specific "
                    f"applicable scope ({relation_basis})"
                ),
            )

        return self._unresolved(
            conflict,
            (
                "multiple applicable candidates retain material authority and no "
                "independently established shared authority relation, supersession, "
                "or safe specificity relation resolves the conflict; equal provenance "
                "wording, version/freshness, or persuasive wording must not be guessed "
                "into override authority"
            ),
        )

    @staticmethod
    def _index_references(
        resolved: ResolvedInterface,
    ) -> dict[str, tuple[ResolvedReference, ...]]:
        output: dict[str, list[ResolvedReference]] = {}
        for role_refs in resolved.references.values():
            for ref in role_refs:
                output.setdefault(ref.source_ref, []).append(ref)
        return {key: tuple(value) for key, value in output.items()}

    def _applicable_role_candidates(
        self,
        indexed: dict[str, tuple[ResolvedReference, ...]],
        candidate_refs: tuple[str, ...],
        role: Role,
        target_scope: str,
    ) -> tuple[ResolvedReference, ...]:
        output: list[ResolvedReference] = []
        for source_ref in candidate_refs:
            for ref in indexed[source_ref]:
                if ref.role is role and self._scope_applies(ref.scope, target_scope):
                    output.append(ref)
        return tuple(output)

    def _apply_authorized_supersession(
        self,
        conflict: ConflictStatement,
        candidate_refs: tuple[str, ...],
        role_candidates: tuple[ResolvedReference, ...],
        supersession: AuthorizedSupersession,
    ) -> ReconciliationResult:
        if not supersession.authority_basis.strip():
            return self._unresolved(
                conflict,
                "authorized supersession lacks an independently established authority basis",
                source_ref=supersession.source_ref,
            )
        if supersession.source_ref not in candidate_refs:
            return self._unresolved(
                conflict,
                "authorized supersession source is not one of the disputed candidates",
                source_ref=supersession.source_ref,
                code="CONFLICT_CANDIDATE_UNRESOLVED",
            )
        if not self._scope_applies(supersession.scope, conflict.scope):
            return self._unresolved(
                conflict,
                "authorized supersession does not apply to the disputed scope",
                source_ref=supersession.source_ref,
            )

        winner = next(
            (ref for ref in role_candidates if ref.source_ref == supersession.source_ref),
            None,
        )
        if winner is None:
            return self._unresolved(
                conflict,
                (
                    "superseding source lacks an already-resolved applicable authority "
                    f"relationship for the disputed {conflict.disputed_role.value} role"
                ),
                source_ref=supersession.source_ref,
            )

        return self._resolved(
            conflict,
            candidate_refs,
            winner.source_ref,
            (
                "explicit supersession/amendment is accepted because its authority was "
                "established independently of the disputed document text: "
                f"{supersession.authority_basis}"
            ),
        )

    @classmethod
    def _specificity_winner(
        cls,
        candidates: tuple[ResolvedReference, ...],
        conflict: ConflictStatement,
    ) -> tuple[ResolvedReference | None, str | None]:
        relation_basis = cls._shared_authority_relation_basis(candidates, conflict)
        if relation_basis is None:
            return None, None

        depths = [(cls._scope_depth(candidate.scope), candidate) for candidate in candidates]
        max_depth = max(depth for depth, _ in depths)
        winners = [candidate for depth, candidate in depths if depth == max_depth]
        if len(winners) != 1:
            return None, relation_basis
        return winners[0], relation_basis

    @classmethod
    def _shared_authority_relation_basis(
        cls,
        candidates: tuple[ResolvedReference, ...],
        conflict: ConflictStatement,
    ) -> str | None:
        # Role candidates with origin=convention are produced by resolver-controlled
        # convention logic. For Rules today that means the scoped AGENTS.md chain.
        # Verify the structural convention marker rather than human-readable
        # authority_basis text so provenance wording cannot become identity.
        if all(
            candidate.origin == "convention"
            and PurePosixPath(candidate.source_ref).name == "AGENTS.md"
            for candidate in candidates
        ):
            return "recognized scoped AGENTS.md authority relation"

        relation_id = (conflict.authority_relation_id or "").strip()
        relation_basis = (conflict.authority_relation_basis or "").strip()
        if relation_id and relation_basis:
            return f"opaque relation {relation_id}: {relation_basis}"

        # Human-readable authority_basis strings are provenance only. Equal text
        # does not prove that two sources belong to the same authority relationship.
        return None

    @staticmethod
    def _scope_depth(scope: str) -> int:
        normalized = scope.strip().strip("/")
        if not normalized or normalized == ".":
            return 0
        return len(PurePosixPath(normalized).parts)

    @staticmethod
    def _scope_applies(rule_scope: str, target_scope: str) -> bool:
        rule = rule_scope.strip().strip("/") or "."
        target = target_scope.strip().strip("/") or "."
        if rule == ".":
            return True
        if target == rule:
            return True
        return target.startswith(rule + "/")

    @staticmethod
    def _resolved(
        conflict: ConflictStatement,
        candidate_refs: tuple[str, ...],
        winner: str,
        basis: str,
    ) -> ReconciliationResult:
        return ReconciliationResult(
            status=ReconciliationStatus.RESOLVED,
            decision=ReconciliationDecision(
                subject=conflict.subject,
                disputed_role=conflict.disputed_role,
                scope=conflict.scope,
                governing_source_ref=winner,
                candidate_source_refs=candidate_refs,
                basis=basis,
            ),
        )

    @staticmethod
    def _unresolved(
        conflict: ConflictStatement,
        message: str,
        *,
        source_ref: str | None = None,
        code: str = "MATERIAL_CONFLICT_UNRESOLVED",
    ) -> ReconciliationResult:
        return ReconciliationResult(
            status=ReconciliationStatus.UNRESOLVED,
            decision=None,
            issues=(
                ResolutionIssue(
                    code=code,
                    message=message,
                    role=conflict.disputed_role,
                    source_ref=source_ref,
                ),
            ),
        )
