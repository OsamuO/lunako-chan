#!/usr/bin/env python3
"""Frozen N0 legacy installation-shape expectations for production detection.

Support authority is payload/ownership evidence only. source_repo/source_commit are
provenance and are deliberately excluded from shape matching.
"""
from __future__ import annotations

from typing import Any

LEGACY_BUNDLE_NAME = "lunatic-harnes-runtime"
LEGACY_AGENTS_BLOCK_SHA256 = "8d957907192ae655849b2f87c233c50c628560e9b9252c9b6ee4069c97afff05"
L1A_PUBLIC_COMMIT = "e06e5797a94fd4f76eaf436e8942614bf6cdc680"
L1B_D2_COMMIT = "61b1e77defb4425309801ff83677cd314e30c70d"

COMMON_L1B_L2_TARGET_SHA256 = {
    ".agents/project-interface/SPECIFICATION.md": "cb341d72759ec02194237feeb39738eb84047f477daac6829f57aed8ade452fe",
    ".agents/schemas/agent-result.schema.json": "49e380b4182ec42507f994b3548c4afd2728e5f22b3bc53f4feb352c48edefb2",
    ".agents/schemas/architecture-gates.schema.json": "58a7b1bb83aec536d220e166ec94b34099b29862b9444f36f9b2d99b101e44f8",
    ".agents/schemas/consistency-gate.schema.json": "7e51c3d4092432e34ae1d483d582286be3cc5ca3390d99f72b87c9be5b70e210",
    ".agents/schemas/context-capsule.schema.json": "354c59a9ddde9745b667869c6f95a7cb95ec6188e5c2fe05d36fd25cf3c4990b",
    ".agents/schemas/contract-impact.schema.json": "e2a6f43addbaef1e9ab73d61d7ba89149f5195c43be9bb11c021b17172a63d78",
    ".agents/schemas/dependency-graph.schema.json": "dd43fb26cbcd0accad5adb43d184bdee9a7c8d0f8480e5b5834de6aea75abac0",
    ".agents/schemas/domain-map.schema.json": "c4932cfa15f4d2e2599e5d7fe5769874daed5f59d4cb1630567ca7ff9fd5e8d6",
    ".agents/schemas/external-audit.schema.json": "de2a2ebb8eb8133e991932943058b03213ef504fa2e7c19f1b642c98539dfa4c",
    ".agents/schemas/impact-manifest.schema.json": "6d2ab628b46649088c409750bcbc43b02410816d585cf15d3909fd963e4e1dc7",
    ".agents/schemas/integration-waves.schema.json": "af58c30866ade52b6e998b09bec3f0b1360d1096e4973bffa73a38dca4dd332f",
    ".agents/schemas/packet-states.schema.json": "b7854c9b55067fd856c74df16bcbb38ab0daf95b70ad13e85759a22a7c82d99f",
    ".agents/schemas/quality-evidence.schema.json": "d303063427f15dac148a5c2bacbcd58f682794134e95cd060ef23776707a2d36",
    ".agents/schemas/routing-decision.schema.json": "00a9c9ef6ec3b05f189198b3b9842f84a0d3b9301c6110e5878842dad3c9dc2c",
    ".agents/schemas/run-record.schema.json": "cd593ab5e27b19b2196d872bca54ff0a735849954c7436fe9ebcbce8702ebfe3",
    ".agents/schemas/strict-agent-result.schema.json": "6be8b92f25cc53793ce817c4ee7bd7fd7672df9481bd5fdc875e06a519852c10",
    ".agents/schemas/strict-run-record.schema.json": "a7e87593a15dc7d5c9b277e632685d7d1e877d7b5313570601ad949375a833df",
    ".agents/schemas/worktrees.schema.json": "b2a1edab8a450bc61d7da521235ef771d771a15fe272452c03a2e2efe7cd98c2",
    ".agents/skills/design-feedback/SKILL.md": "da810c7203c99f3d1a38f9d0adb69b1142cbcecacc4fafb2a03d6c8f977f790c",
    ".agents/skills/design-feedback/agents/openai.yaml": "e84475526e7b0a56e047f7604cc89127027fee0cb725bb664c7e9348b3f3c13d",
    ".agents/skills/external-audit/SKILL.md": "9da308b4f603fbcf61b94a426130be5e452f71b961176b3b6d3d3e6556359166",
    ".agents/skills/integration/SKILL.md": "7f54fb40e5af0e16df96a23f433f16b4449ff6d29a1dc3eed649dc5a64c73baa",
    ".agents/skills/integration/agents/openai.yaml": "7bf9d1c9c56cbe29b7bfed05ba3919a91a007c16293597f3920da0341fc39559",
    ".agents/skills/low-token-mode/SKILL.md": "dcf3214c35ec140a5335e80dad1a74381ad746ad315d3775b30a700e794306fb",
    ".agents/skills/low-token-mode/agents/openai.yaml": "6db5cf75cf89d79326267187154148581ce95b1dd5fe336a0302d2907dcccee1",
    ".agents/skills/luna-harness/SKILL.md": "3c63c8c9caf7379c68c416d67041c36137614a6766e63810d1e9e085409e58cb",
    ".agents/skills/luna-harness/agents/openai.yaml": "d7b60fd55e8865b5f47230cf08cf105c70a29512ce9c6123064a1146191fe530",
    ".agents/skills/luna-harness/references/runtime-contracts.md": "4c10e7feeb0a93353762e7328f0a293176178dc88fe0129aac2e7e6b2c275d74",
    ".agents/skills/model-escalation/SKILL.md": "cc4ff25b03d0ff0db16d6825e84b5d0ae049e1c6f4e44d665bbcd09e7facc163",
    ".agents/skills/model-escalation/agents/openai.yaml": "67630df4fbea700d8d59da4c57004afa2a2340938ab686a34fd9aeef91581112",
    ".agents/skills/task-decomposition/SKILL.md": "e43144b6fd095e34b294f4c23abbe1b80f0ad6afdb7a2fa9b0894011dd63d64e",
    ".agents/skills/task-decomposition/agents/openai.yaml": "babee54fce508c3beb98467606902aa6ac06d0e4d8bdfe06351997eaa774cea7",
    ".agents/skills/verification/SKILL.md": "e65f794c615b460a42d81624bd2040a40fbd011b2b1beb59061b021069670491",
    ".agents/skills/verification/agents/openai.yaml": "32ebabc69b4840b57e562eab02b04f2a6368951a588553fea8102215d330c060",
    ".agents/skills/work-packet/SKILL.md": "a86d29e0e4654b4df79addb5cbdf26243cbf982c3b835dd9c997a7ec8f51c4d5",
    ".agents/skills/work-packet/agents/openai.yaml": "89c6a0285f2637aba94b221d4d205e0372d590abe9eda92915672dea6d831818",
    ".codex/agents/luna-decomposer.toml": "8fa9d40b8fd821e0568236926706b7c68bcca943cf39cd7d3d5289c7da830fbb",
    ".codex/agents/luna-integrator.toml": "54cb3c1153804cf7952a6f566bf698c758868d1082628ec4d5d4ac2f1d2ba9e4",
    ".codex/agents/luna-planner.toml": "3ebac8421ffd5f1ff3bd3a2bd8a27150010c5e25323dd05bd7c8e3de597675df",
    ".codex/agents/luna-verifier.toml": "d2bb4b3594c45dfdac3117b507c34d735f4e4a9d4aa920b2a8dc21686fd05fa7",
    ".codex/agents/luna-worker.toml": "12530a045cb5535a0c59c9ead1a43d342afa151c9fd7b0fabf240cdcc1770355",
    ".codex/agents/sol-architect.toml": "7a5ecbe083c259ea0ed88600c645e5d1e2c616bb015b7f3c3388aece335e6dc7",
    ".codex/agents/sol-decision-reviewer.toml": "f4b279f62b284129bb2383befe8a59d1951f6712115dd7dbe889aa52fa2bf7fa",
    ".codex/agents/sol-reviewer.toml": "0acb0a59fec95d5884fc6ea94963c9e426c3597e744ef68f4f47cb12ec95d81f",
    "scripts/check_assurance_done_gate.py": "d8c4736cd523bc37214653a5ebaee1c7ec3e1f37faa9b3b8b8b6869c16f8848a",
    "scripts/check_impact_closure.py": "cac3b029f8de42c3a272fff842769dedeacaa5f0196941b46a85daeda29a6d1a",
    "scripts/lunatic_permission_profile.py": "4b2cb38dfc5a73c3bd91eb2270b39a9cc948f0af79ed745731c149340022d733",
    "scripts/project_interface_reconciliation.py": "a3728299ebe349565a68d0a7b9d18092b2950f26376a4582fae80cc38a0555e5",
    "scripts/project_interface_resolver.py": "c7a2fa996372072fdade5a4f1ecbef4d92841fdee362949147ca76bc86ddb915",
}

L1A_TARGET_SHA256 = dict(COMMON_L1B_L2_TARGET_SHA256)
L1A_TARGET_SHA256[".codex/agents/luna-verifier.toml"] = "5ac5bf4847b5db2aed9df257d56de5135b337243e4f127ad76d8276bdd4ddf9c"

L1_MANIFEST_KEYS = frozenset({
    "schema_version", "source_repo", "source_commit", "bundle_name", "bundle_version",
    "managed_files", "managed_agents_block_sha256", "managed_agents_segment_sha256",
    "agents_binding_prefix", "agents_binding_suffix", "agents_file_created", "installed_at",
})
L2_MANIFEST_KEYS = L1_MANIFEST_KEYS | {"managed_regions"}
MANAGED_FILE_KEYS = frozenset({"source_path", "target_path", "installed_sha256"})
L2_REGION_KEYS = frozenset({
    "region_id", "target_path", "ownership", "placement", "begin_marker", "end_marker",
    "managed_region_sha256", "managed_segment_sha256", "segment_prefix", "segment_suffix",
    "target_file_created", "source_contract", "installed_registrations",
})
L2_REGION_SHA256 = "d3170577f075d83be2594f75db6e81359813b7c5724156bb95b092909c6a4fd1"
L2_EXPECTED_REGISTRATIONS = [
    {"role": "luna_planner", "config_file": "agents/luna-planner.toml"},
    {"role": "luna_decomposer", "config_file": "agents/luna-decomposer.toml"},
    {"role": "luna_worker", "config_file": "agents/luna-worker.toml"},
    {"role": "luna_verifier", "config_file": "agents/luna-verifier.toml"},
    {"role": "luna_integrator", "config_file": "agents/luna-integrator.toml"},
    {"role": "sol_architect", "config_file": "agents/sol-architect.toml"},
    {"role": "sol_reviewer", "config_file": "agents/sol-reviewer.toml"},
    {"role": "sol_decision_reviewer", "config_file": "agents/sol-decision-reviewer.toml"},
]


def _valid_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _common_ownership_problems(manifest: dict[str, Any], expected_keys: frozenset[str]) -> list[str]:
    problems: list[str] = []
    if set(manifest) != set(expected_keys):
        problems.append("legacy manifest ownership record shape differs from frozen N0 shape")
    if manifest.get("bundle_name") != LEGACY_BUNDLE_NAME:
        problems.append("legacy bundle identity differs from frozen N0 shape")
    if manifest.get("managed_agents_block_sha256") != LEGACY_AGENTS_BLOCK_SHA256:
        problems.append("legacy AGENTS managed block differs from frozen N0 payload")
    if not _valid_sha(manifest.get("managed_agents_segment_sha256")):
        problems.append("legacy AGENTS managed segment hash invalid")
    if not isinstance(manifest.get("agents_binding_prefix"), str) or not isinstance(manifest.get("agents_binding_suffix"), str):
        problems.append("legacy AGENTS affix ownership metadata invalid")
    if not isinstance(manifest.get("agents_file_created"), bool):
        problems.append("legacy agents_file_created ownership metadata invalid")
    for key in ("source_repo", "source_commit", "installed_at"):
        if not isinstance(manifest.get(key), str):
            problems.append(f"legacy provenance field invalid: {key}")
    return problems


def _managed_records(manifest: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    items = manifest.get("managed_files")
    if not isinstance(items, list):
        return {}, ["legacy managed_files missing"]
    records: dict[str, dict[str, Any]] = {}
    problems: list[str] = []
    for item in items:
        if not isinstance(item, dict) or set(item) != set(MANAGED_FILE_KEYS):
            problems.append("legacy managed_files record shape differs from frozen N0 shape")
            continue
        target = item.get("target_path")
        source = item.get("source_path")
        if not isinstance(target, str) or target in records:
            problems.append("legacy managed target invalid or duplicated")
            continue
        if source != target:
            problems.append(f"legacy source mapping differs from frozen N0 shape: {target}")
        records[target] = item
    return records, problems


def _payload_match(records: dict[str, dict[str, Any]], expected: dict[str, str]) -> bool:
    return set(records) == set(expected) and all(records[path].get("installed_sha256") == digest for path, digest in expected.items())


def _l2_region_problems(manifest: dict[str, Any]) -> list[str]:
    regions = manifest.get("managed_regions")
    if not isinstance(regions, list) or len(regions) != 1 or not isinstance(regions[0], dict):
        return ["legacy L2 managed region shape differs from frozen N0 shape"]
    r = regions[0]
    problems: list[str] = []
    if set(r) != set(L2_REGION_KEYS):
        problems.append("legacy L2 managed region record fields differ from frozen N0 shape")
    expected = {
        "region_id": "codex-project-role-registration",
        "target_path": ".codex/config.toml",
        "ownership": "managed-terminal-region",
        "placement": "terminal",
        "begin_marker": "# LUNATIC-HARNES:BEGIN PROJECT-ROLE-REGISTRATION",
        "end_marker": "# LUNATIC-HARNES:END PROJECT-ROLE-REGISTRATION",
        "source_contract": "project_role_registration",
        "managed_region_sha256": L2_REGION_SHA256,
    }
    for key, value in expected.items():
        if r.get(key) != value:
            problems.append(f"legacy L2 region differs from frozen N0 shape: {key}")
    if r.get("installed_registrations") != L2_EXPECTED_REGISTRATIONS:
        problems.append("legacy L2 registration snapshot differs from frozen N0 shape")
    if not _valid_sha(r.get("managed_segment_sha256")):
        problems.append("legacy L2 managed segment hash invalid")
    if not isinstance(r.get("segment_prefix"), str) or not isinstance(r.get("segment_suffix"), str):
        problems.append("legacy L2 region affix ownership metadata invalid")
    if not isinstance(r.get("target_file_created"), bool):
        problems.append("legacy L2 target_file_created ownership metadata invalid")
    return problems


def match_frozen_legacy_manifest(manifest: dict[str, Any]) -> tuple[str | None, list[str]]:
    """Return frozen payload family (L1A/L1B/L2) or fail-closed problems."""
    schema = manifest.get("schema_version")
    if schema == 1:
        problems = _common_ownership_problems(manifest, L1_MANIFEST_KEYS)
        if str(manifest.get("bundle_version")) != "1":
            problems.append("legacy L1 bundle version differs from frozen N0 shape")
        records, record_problems = _managed_records(manifest)
        problems.extend(record_problems)
        if _payload_match(records, L1A_TARGET_SHA256):
            family = "L1A"
        elif _payload_match(records, COMMON_L1B_L2_TARGET_SHA256):
            family = "L1B"
        else:
            family = None
            problems.append("legacy L1 managed payload differs from all frozen N0 payload families")
        return family, problems
    if schema == 2:
        problems = _common_ownership_problems(manifest, L2_MANIFEST_KEYS)
        if str(manifest.get("bundle_version")) != "2":
            problems.append("legacy L2 bundle version differs from frozen N0 shape")
        records, record_problems = _managed_records(manifest)
        problems.extend(record_problems)
        if not _payload_match(records, COMMON_L1B_L2_TARGET_SHA256):
            problems.append("legacy L2 managed payload differs from frozen N0 payload")
        problems.extend(_l2_region_problems(manifest))
        return "L2" if not problems else None, problems
    return None, [f"unsupported legacy manifest schema: {schema!r}"]


def diagnostic_subtype(family: str, manifest: dict[str, Any]) -> str:
    """Provenance only affects diagnostics, never the support decision."""
    source_commit = manifest.get("source_commit")
    if family == "L1A":
        return "L1A" if source_commit == L1A_PUBLIC_COMMIT else "L1A_EQUIVALENT"
    if family == "L1B":
        return "L1B" if source_commit == L1B_D2_COMMIT else "L1B_EQUIVALENT"
    return "L2"
