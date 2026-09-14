#!/usr/bin/env python3
"""Minimal in-memory resolver for the frozen 6-role Project Interface.

This module intentionally avoids a persistent mapping schema, repository-wide
semantic classification, and automatic external retrieval. It resolves trusted
project-native references and leaves content loading as a separate projection
step.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


class Role(str, Enum):
    RULES = "Rules"
    TASK = "Task"
    STATE = "State"
    ACCEPTANCE = "Acceptance"
    SOURCES = "Sources"
    DELIVERABLES = "Deliverables"


@dataclass(frozen=True)
class ExplicitBinding:
    role: Role
    source_ref: str
    scope: str = "."
    authority_basis: str = "explicit authorized mapping"
    projection_kind: str = "direct"
    allow_external: bool = True


@dataclass(frozen=True)
class ReferenceHint:
    """A bounded reference discovered from an already-resolved trusted source."""

    from_source_ref: str
    target_ref: str
    target_role: Role | None = None
    role_relationship_established: bool = False
    scope: str = "."
    authority_basis: str = "reference from resolved trusted context"
    allow_external: bool = False


@dataclass(frozen=True)
class ResolverRequest:
    current_task: str
    task_resolved: bool = True
    explicit_bindings: tuple[ExplicitBinding, ...] = ()
    scope_hints: tuple[str, ...] = ()
    reference_hints: tuple[ReferenceHint, ...] = ()

    def for_scope(self, *scope_hints: str) -> "ResolverRequest":
        """Return the same request re-targeted to a materially changed scope."""
        return replace(self, scope_hints=tuple(scope_hints))


@dataclass(frozen=True)
class ResolvedReference:
    role: Role
    source_ref: str
    scope: str
    origin: str
    authority_basis: str
    projection_kind: str = "direct"
    external: bool = False


@dataclass(frozen=True)
class ResolutionIssue:
    code: str
    message: str
    role: Role | None = None
    source_ref: str | None = None


@dataclass(frozen=True)
class ResolvedInterface:
    project_root: str
    task_text: str
    scope_hints: tuple[str, ...]
    references: dict[Role, tuple[ResolvedReference, ...]]
    issues: tuple[ResolutionIssue, ...] = ()

    @property
    def executable(self) -> bool:
        return not any(issue.code == "TASK_UNRESOLVED" for issue in self.issues)

    def for_role(self, role: Role) -> tuple[ResolvedReference, ...]:
        return self.references.get(role, ())


@dataclass(frozen=True)
class ProjectedInterface:
    """A bounded role/reference projection. Source contents remain unloaded."""

    task_text: str
    references: dict[Role, tuple[ResolvedReference, ...]]
    issues: tuple[ResolutionIssue, ...] = ()


class ResolverError(ValueError):
    pass


class ProjectBoundaryError(ResolverError):
    pass


class ProjectInterfaceResolver:
    """Resolve the six logical roles without creating a second source of truth."""

    _HARNESS_SOURCE_CONVENTIONS = (
        ".agents/project-state/ARCHITECTURE.md",
        ".agents/project-state/CONTRACTS.md",
        ".agents/project-state/CONSISTENCY_SPINE.md",
    )

    def __init__(self, project_root: str | Path):
        root = Path(project_root).expanduser()
        if not root.exists() or not root.is_dir():
            raise ResolverError(f"trusted project root is not a directory: {root}")
        self.root = root.resolve()

    def resolve(self, request: ResolverRequest) -> ResolvedInterface:
        refs: dict[Role, list[ResolvedReference]] = {role: [] for role in Role}
        issues: list[ResolutionIssue] = []

        task_text = request.current_task.strip()
        if task_text:
            refs[Role.TASK].append(
                ResolvedReference(
                    role=Role.TASK,
                    source_ref="invocation://current-task",
                    scope=".",
                    origin="explicit",
                    authority_basis="trusted current invocation",
                    projection_kind="direct",
                    external=False,
                )
            )
        if not task_text or not request.task_resolved:
            issues.append(
                ResolutionIssue(
                    code="TASK_UNRESOLVED",
                    message=(
                        "current Task meaning is not sufficiently resolved to identify "
                        "executable work"
                    ),
                    role=Role.TASK,
                    source_ref="invocation://current-task" if task_text else None,
                )
            )

        scope_hints = request.scope_hints or (".",)
        for scope in scope_hints:
            try:
                self._add_scoped_rules(refs[Role.RULES], scope)
            except ProjectBoundaryError as exc:
                issues.append(
                    ResolutionIssue(
                        code="SCOPE_OUTSIDE_PROJECT",
                        message=str(exc),
                        role=Role.RULES,
                        source_ref=scope,
                    )
                )

        self._add_harness_native_conventions(refs)

        for binding in request.explicit_bindings:
            try:
                source_ref, external = self._resolve_source_ref(
                    binding.source_ref,
                    allow_external=binding.allow_external,
                    require_existing=binding.role is not Role.DELIVERABLES,
                )
            except ResolverError as exc:
                issues.append(
                    ResolutionIssue(
                        code="EXPLICIT_BINDING_UNRESOLVED",
                        message=str(exc),
                        role=binding.role,
                        source_ref=binding.source_ref,
                    )
                )
                continue
            refs[binding.role].append(
                ResolvedReference(
                    role=binding.role,
                    source_ref=source_ref,
                    scope=binding.scope,
                    origin="explicit",
                    authority_basis=binding.authority_basis,
                    projection_kind=binding.projection_kind,
                    external=external,
                )
            )

        known_sources = {
            ref.source_ref
            for role_refs in refs.values()
            for ref in role_refs
        }
        for hint in request.reference_hints:
            if hint.from_source_ref not in known_sources:
                issues.append(
                    ResolutionIssue(
                        code="REFERENCE_ORIGIN_UNRESOLVED",
                        message=(
                            "reference-led inference requires an already-resolved "
                            f"referring source: {hint.from_source_ref}"
                        ),
                        source_ref=hint.from_source_ref,
                    )
                )
                continue

            role = (
                hint.target_role
                if hint.target_role is not None and hint.role_relationship_established
                else Role.SOURCES
            )
            try:
                target_ref, external = self._resolve_source_ref(
                    hint.target_ref,
                    allow_external=hint.allow_external,
                    require_existing=True,
                )
            except ResolverError as exc:
                issues.append(
                    ResolutionIssue(
                        code="REFERENCE_TARGET_UNRESOLVED",
                        message=str(exc),
                        role=role,
                        source_ref=hint.target_ref,
                    )
                )
                continue

            authority_basis = hint.authority_basis
            if hint.target_role is not None and not hint.role_relationship_established:
                authority_basis += "; target role not established, retained as Source"

            refs[role].append(
                ResolvedReference(
                    role=role,
                    source_ref=target_ref,
                    scope=hint.scope,
                    origin="inferred",
                    authority_basis=authority_basis,
                    projection_kind="direct",
                    external=external,
                )
            )
            known_sources.add(target_ref)

        frozen_refs = {
            role: tuple(self._dedupe(role_refs))
            for role, role_refs in refs.items()
        }
        return ResolvedInterface(
            project_root=self.root.as_posix(),
            task_text=task_text,
            scope_hints=tuple(scope_hints),
            references=frozen_refs,
            issues=tuple(issues),
        )

    def project(
        self,
        resolved: ResolvedInterface,
        roles: Iterable[Role],
        *,
        source_refs: Iterable[str] | None = None,
    ) -> ProjectedInterface:
        """Select bounded role/reference slices without loading source contents."""
        selected_roles = tuple(dict.fromkeys(roles))
        selected_refs = set(source_refs or ())
        output: dict[Role, tuple[ResolvedReference, ...]] = {}
        for role in selected_roles:
            candidates = resolved.for_role(role)
            if selected_refs:
                candidates = tuple(
                    ref for ref in candidates if ref.source_ref in selected_refs
                )
            output[role] = candidates
        return ProjectedInterface(
            task_text=resolved.task_text,
            references=output,
            issues=resolved.issues,
        )

    def load_local_text(self, source_ref: str, *, encoding: str = "utf-8") -> str:
        """Load one explicitly requested local source after resolution/projection."""
        parsed = urlparse(source_ref)
        if parsed.scheme:
            raise ResolverError(
                "automatic content loading is local-only; opaque/external ref: "
                f"{source_ref}"
            )
        path = self._safe_local_path(source_ref, require_existing=True)
        if not path.is_file():
            raise ResolverError(f"resolved source is not a file: {source_ref}")
        return path.read_text(encoding=encoding)

    def _add_scoped_rules(
        self,
        output: list[ResolvedReference],
        scope_hint: str,
    ) -> None:
        target_dir = self._scope_directory(scope_hint)
        ancestors = [target_dir]
        while ancestors[-1] != self.root:
            parent = ancestors[-1].parent
            if parent == ancestors[-1]:
                raise ProjectBoundaryError(
                    f"scope does not belong to trusted project root: {scope_hint}"
                )
            ancestors.append(parent)
        ancestors.reverse()

        for directory in ancestors:
            candidate = directory / "AGENTS.md"
            if not candidate.is_file():
                continue
            resolved = candidate.resolve()
            self._assert_inside_root(resolved)
            relative_scope = directory.relative_to(self.root).as_posix()
            output.append(
                ResolvedReference(
                    role=Role.RULES,
                    source_ref=resolved.relative_to(self.root).as_posix(),
                    scope=relative_scope if relative_scope != "." else ".",
                    origin="convention",
                    authority_basis="recognized scoped AGENTS.md convention",
                    projection_kind="direct",
                    external=False,
                )
            )

    def _add_harness_native_conventions(
        self,
        refs: dict[Role, list[ResolvedReference]],
    ) -> None:
        state = self.root / ".agents/project-state/CURRENT_STATE.md"
        if state.is_file():
            resolved = state.resolve()
            self._assert_inside_root(resolved)
            refs[Role.STATE].append(
                ResolvedReference(
                    role=Role.STATE,
                    source_ref=resolved.relative_to(self.root).as_posix(),
                    scope=".",
                    origin="convention",
                    authority_basis=(
                        "recognized Harness CURRENT_STATE checkpoint convention"
                    ),
                    external=False,
                )
            )

        for relative in self._HARNESS_SOURCE_CONVENTIONS:
            path = self.root / relative
            if not path.is_file():
                continue
            resolved = path.resolve()
            self._assert_inside_root(resolved)
            refs[Role.SOURCES].append(
                ResolvedReference(
                    role=Role.SOURCES,
                    source_ref=resolved.relative_to(self.root).as_posix(),
                    scope=".",
                    origin="convention",
                    authority_basis=(
                        "recognized Harness project-state source convention"
                    ),
                    external=False,
                )
            )

    def _scope_directory(self, scope_hint: str) -> Path:
        if not scope_hint.strip():
            scope_hint = "."
        raw = Path(scope_hint).expanduser()
        candidate = raw if raw.is_absolute() else self.root / raw

        if candidate.exists():
            resolved = candidate.resolve()
            self._assert_inside_root(resolved)
            return resolved if resolved.is_dir() else resolved.parent

        candidate = Path(os.path.abspath(candidate))
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ProjectBoundaryError(
                f"scope escapes trusted project root: {scope_hint}"
            ) from exc

        parent = candidate.parent
        while not parent.exists():
            if parent == parent.parent:
                raise ProjectBoundaryError(
                    f"cannot establish project-bounded scope for: {scope_hint}"
                )
            parent = parent.parent
        self._assert_inside_root(parent.resolve())

        # A non-existing path can still be a valid future deliverable scope as
        # long as its nearest existing ancestor remains inside the trusted root.
        return candidate.parent if candidate.suffix else candidate

    def _resolve_source_ref(
        self,
        source_ref: str,
        *,
        allow_external: bool,
        require_existing: bool,
    ) -> tuple[str, bool]:
        source_ref = source_ref.strip()
        if not source_ref:
            raise ResolverError("empty source reference")

        parsed = urlparse(source_ref)
        if parsed.scheme:
            if not allow_external:
                raise ProjectBoundaryError(
                    "automatic discovery will not follow external/opaque reference: "
                    f"{source_ref}"
                )
            # Record explicit caller-authorized opaque references without fetching.
            return source_ref, True

        path = self._safe_local_path(
            source_ref,
            require_existing=require_existing,
        )
        try:
            relative = path.relative_to(self.root)
        except ValueError as exc:
            raise ProjectBoundaryError(
                f"source escapes trusted project root: {source_ref}"
            ) from exc
        return relative.as_posix(), False

    def _safe_local_path(self, source_ref: str, *, require_existing: bool) -> Path:
        raw = Path(source_ref).expanduser()
        candidate = raw if raw.is_absolute() else self.root / raw

        if candidate.exists():
            resolved = candidate.resolve()
            self._assert_inside_root(resolved)
            return resolved

        if require_existing:
            raise ResolverError(f"local source does not exist: {source_ref}")

        # For a future deliverable path, validate both lexical containment and
        # the resolved nearest existing ancestor so a symlinked parent cannot escape.
        candidate = Path(os.path.abspath(candidate))
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ProjectBoundaryError(
                f"local path escapes trusted project root: {source_ref}"
            ) from exc

        parent = candidate.parent
        while not parent.exists():
            if parent == parent.parent:
                raise ProjectBoundaryError(
                    f"cannot establish safe parent for local path: {source_ref}"
                )
            parent = parent.parent
        self._assert_inside_root(parent.resolve())
        return candidate

    def _assert_inside_root(self, path: Path) -> None:
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise ProjectBoundaryError(
                f"path escapes trusted project root: {path}"
            ) from exc

    @staticmethod
    def _dedupe(
        references: Iterable[ResolvedReference],
    ) -> list[ResolvedReference]:
        output: list[ResolvedReference] = []
        seen: set[tuple[object, ...]] = set()
        for ref in references:
            key = (
                ref.role,
                ref.source_ref,
                ref.scope,
                ref.origin,
                ref.authority_basis,
                ref.projection_kind,
                ref.external,
            )
            if key in seen:
                continue
            seen.add(key)
            output.append(ref)
        return output
