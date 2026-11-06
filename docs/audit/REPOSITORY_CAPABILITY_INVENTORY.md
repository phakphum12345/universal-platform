> **Historical audit notice (2026-11-06):** This file contains an earlier targeted audit and must not be treated as the current repository baseline. It predates the executable engineering-core, mechanism, CAD mesh/STL, and hardware schematic increments. Use [Repository Audit post-PR #82](REPOSITORY_AUDIT_2026-11-06_POST_PR82.md) and the Implementation Status ledger for the current pinned baseline.

# Repository Capability Inventory — UEIC and 3D Engineering

**Audit date:** 2026-11-06  
**Repository:** phakphum12345/universal-platform  
**Audited branch:** docs/phase-0-complete-requirements  
**Baseline commit:** 2d6ea99578cb0ac577e9644c59b22b4400a64fe9  
**Default branch:** main  
**Audit status:** PARTIAL — external source located; full source-tree and runtime verification still open  
**Scope:** documentation and repository metadata only; no code changed

## 1. Executive finding

The audited branch contains a substantial documentation baseline for multidisciplinary engineering, UEIC, hardware intelligence, 3D design, simulation, manufacturing preparation, safety and traceability. The comparison against main reports 39 commits ahead and 0 behind. The reported changed-file set is documentation-focused: README plus architecture, engineering, design-3d, hardware, governance, integration, laboratory, requirements, roadmap and traceability documents.

No implementation capability is confirmed by the presence of these specifications. Targeted checks for common source/build entry points returned 404: pyproject.toml, package.json, Cargo.toml, go.mod, requirements.txt, src/main.py and src/index.ts. Guessed directory-content checks for core/, engine/, domains/, tests/, tools/ and schemas/ did not produce a usable directory listing; those directory states remain UNKNOWN rather than proven absent.

The Universal Platform repository remains a documentation baseline in the inspected set. The owner then supplied `phakphum12345/research_os_efi_platform` as a candidate source repository. Targeted source inspection confirms hardware discovery and an EFI/OpenCore candidate builder there. It does not yet confirm a general-purpose driver generator for arbitrary devices and operating systems. The source-tree audit is targeted, not exhaustive.

## 2. Repository metadata evidence

| Check | Result | Evidence |
|---|---|---|
| Repository | phakphum12345/universal-platform | GitHub repository metadata |
| Visibility | Public | Repository metadata |
| Default branch | main | Repository metadata |
| Working branch | docs/phase-0-complete-requirements | Branch search |
| Branch comparison | 39 ahead / 0 behind | compare main...working branch |
| Compared file changes | 35 paths reported | Compare response; documentation-oriented |
| Known working-branch commit | 2d6ea99578cb0ac577e9644c59b22b4400a64fe9 | Hardware design verification commit |
| CI combined status for that SHA | No statuses returned | Status query; this is not a passing CI result |
| Main README | Describes documentation/proposals, implementation not started | README content |
| Working README | Links the engineering and 3D specification set | README content |

## 3. Capability inventory

| Capability | Documentation evidence | Source/runtime evidence | Classification | Next action |
|---|---|---|---|---|
| UEIC shared core | UNIVERSAL_ENGINEERING_INTELLIGENCE_CORE.md | Not found in audited source set | SPECIFIED / NOT VERIFIED | Design contracts; implementation later |
| Discipline registry/modules | MULTIDISCIPLINARY_KNOWLEDGE_MODULES.md | Not found | SPECIFIED / NOT VERIFIED | Define schema and module lifecycle |
| Physics models | PHYSICS_AND_FIRST_PRINCIPLES.md | Not found | SPECIFIED / NOT VERIFIED | Build reference-case plan |
| Calculation/solver integration | UNIVERSAL_CALCULATION_ENGINE.md; ENGINEERING_SOLVER_AND_MODEL_CONTRACT.md | Not found | SPECIFIED / NOT VERIFIED | Inventory existing calculation tools externally |
| Units/provenance/uncertainty | ENGINEERING_UNITS_UNCERTAINTY_AND_PROVENANCE.md | Not found | SPECIFIED / NOT VERIFIED | Define typed data and validation tests |
| Cross-domain constraints | CROSS_DOMAIN_CONSTRAINT_SOLVING.md | Not found | SPECIFIED / NOT VERIFIED | Specify conflict and infeasibility cases |
| 3D CAD design | 3D_DESIGN_INTELLIGENCE.md | No CAD source/kernel integration verified | SPECIFIED / NOT VERIFIED | Evaluate CAD candidates after requirements freeze |
| 3D tool generation | 3D_TOOL_GENERATION_ENGINE.md | No runtime evidence | SPECIFIED / NOT VERIFIED | Reuse templates only after source audit |
| Assembly/kinematics | 3D_ASSEMBLY_AND_KINEMATICS.md | No runtime evidence | SPECIFIED / NOT VERIFIED | Define joints/DOF reference cases |
| 3D simulation | 3D_ENGINEERING_SIMULATION.md | No solver integration verified | SPECIFIED / NOT VERIFIED | Evaluate validated solver adapters |
| Structural/civil design | STRUCTURAL_AND_CIVIL_DESIGN.md | No runtime evidence | SPECIFIED / NOT VERIFIED | Require jurisdiction and professional review |
| CAD manufacturing pipeline | CAD_TO_MANUFACTURING_PIPELINE.md | No export pipeline verified | SPECIFIED / NOT VERIFIED | Define format round-trip tests |
| Model verification | 3D_MODEL_VALIDATION.md | No test runner/results verified | SPECIFIED / NOT VERIFIED | Create geometry and assembly fixtures |
| Hardware/device intelligence | DEVICE_INTELLIGENCE.md; schematic/hardware docs | No runtime evidence in audited set | SPECIFIED / NOT VERIFIED | Locate parsers and hardware source |
| Hardware discovery | Candidate source `research_os_efi_platform` | Windows/Linux/macOS discovery modules and normalized HardwareSnapshot source inspected | EXISTING SOURCE / NOT RUNTIME-VERIFIED | Reuse behind a versioned discovery adapter after tests and contract review |
| EFI/OpenCore candidate generation | Candidate source `research_os_efi_platform` | `backend/builder/efi_builder.py`, `kext_resolver.py`, `compatibility.py`, `config_gen.py` inspected | EXISTING SOURCE / EFI-SPECIFIC | Reuse only for EFI research; do not label it universal driver generation |
| Universal Driver Generation | Owner says Driver Generation already exists | The inspected resolver selects a short list of macOS kext names from profile flags; no general compiler/package/install workflow confirmed | PARTIAL / GENERAL CAPABILITY UNKNOWN | Do not duplicate; determine whether this is the intended existing Driver Generation or locate its canonical source separately |
| Virtual laboratory | VIRTUAL_LAB_AND_SIMULATION.md | No execution/runtime evidence | SPECIFIED / NOT VERIFIED | Inventory external simulators and isolation |
| Safety/governance | ENGINEERING_SAFETY_AND_APPROVAL.md | Policy document only | SPECIFIED / NOT IMPLEMENTED | Carry controls into every implementation gate |

## 4. Targeted source checks

The following exact file paths were requested from the audited branch and returned HTTP 404:
- pyproject.toml
- package.json
- Cargo.toml
- go.mod
- requirements.txt
- src/main.py
- src/index.ts

Directory-like requests for core/, engine/, domains/, tests/, tools/ and schemas/ returned an unusable response. Their contents are UNKNOWN. Do not interpret those results as a complete repository tree.

## 5. Driver Generation reuse boundary

The owner explicitly clarified that Driver Generation has already been created. Therefore:
- Do not create another Driver Generator as part of UEIC.
- Treat Driver Generation as an external/existing capability until its canonical repository, branch, commit SHA, entry point, API, tests, license and maintainer are identified.
- UEIC may consume a versioned Driver Generation contract through an adapter after compatibility and safety review.
- Driver refactoring remains a separate, human-approved capability.
- No physical hardware operations are enabled by this integration.

Required missing evidence: canonical source URL/path, exact baseline SHA, build/test instructions, supported hardware/OS matrix, interface contract, and current known limitations.

## 6. External candidate source audit — research_os_efi_platform

**Repository:** `phakphum12345/research_os_efi_platform`  
**Inspected ref:** `main` (the exact ref SHA was not reliably pinned by the connector during this targeted pass; individual content blob SHAs are recorded below).  
**License:** Apache-2.0 (`LICENSE`, blob `261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64`).

| Capability/file | Observed source | Blob SHA | Finding |
|---|---|---|---|
| EFI builder | `backend/builder/efi_builder.py` | `92df9f5c975d78333587e78f55ac7c9f971a25a2` | Compatibility gate, EFI structure, config and integrity manifest |
| Candidate entry | `backend/platform/candidate.py` | `770d3a8c11c6686f00ab339397bb7959fff966ca` | Calls `build_efi`, adds evidence manifest |
| Kext resolver | `backend/builder/kext_resolver.py` | `81014e26d478e33cadad35450cf84f4ffb166034` | Selects Lilu, VirtualSMC, WhateverGreen, AppleALC and WiFi from evidence flags; this is macOS kext selection, not generic driver compilation |
| Compatibility | `backend/builder/compatibility.py` | `7d1b8e48121dcadce0efed51e0a9e849233659d4` | Profile-specific checks including Intel UHD, VMD, audio, Wi-Fi and touchpad evidence |
| Config generation | `backend/builder/config_gen.py` | `7152e14d35001fb0cc5c5d51d53386187303f59d` | OpenCore-shaped plist starting point; source comments disclaim bootability |
| Candidate validator | `backend/platform/validator.py` | `a06bd9c07217d4bd1e21a1e41208b75b4b70f923` | Directory/plist/report structural validation; absent config is intentionally non-bootable warning |
| Hardware model | `backend/platform/universal/models.py` | `9497e4875594a45b2d408bcead9eee71a9d018e2` | ProductIdentity, HardwareComponent and HardwareSnapshot; component includes driver string |
| Windows discovery | `backend/platform/universal/discovery/windows.py` | `5dd4ff457712da82449c433e82157ed5ff62740a` | Read-only CIM/PnP inventory across computer, board, BIOS, CPU, GPU, storage, network and audio |
| Linux discovery | `backend/platform/universal/discovery/linux.py` | `a50e4608da0472d271c91840978b30629047813e` | Read-only sysfs/procfs/lspci/lsusb discovery |
| macOS discovery | `backend/platform/universal/discovery/macos.py` | `c9b4d9aeb4811c1c80ae11ba5a623dd8e8e6f73d` | system_profiler-based discovery |
| Normalization | `backend/platform/universal/normalize.py` | `c50a9f7a09d15889b1155d0633ec1dd676572e6d` | PCI/USB ID and snapshot normalization |
| Identity | `backend/platform/universal/identity.py` | `9a209608a37b6fc2658ef9151aa93136ee8378ca` | Deterministic SHA-256 product/hardware/discovery identity |
| Runtime manager | `backend/platform/universal/runtime/manager.py` | `9e337527faba172df96541996fc33d6e8a45e84c` | OS-specific adapter registry and local-host platform guard |
| Runtime adapters | Windows/Linux/macOS modules | `a3cbd7581ef073031aacb854b101b9cbc5cf866a`; `9151113b08b0cad7ac862a52fae3e0e7b9c98803`; `5ee03877e7105fed6193a586167aa9e6725a1012` | Fixed OS-owned observation commands; no general driver build API demonstrated |
| Live discovery test | `tests/test_live_discovery.py` | `6163166fcc4c62e0482c6f9c78b15da2e6945363` | Unit tests for read-only evidence, UNKNOWN/PARTIAL states and JSON writer; not executed in this audit |

`requirements.txt` includes torch, fastapi, uvicorn, redis and numpy (blob `8e7fecf09e05901987c797fdff0612851044ba91`). Dependency necessity, versions, license transitivity, security and reproducibility remain unreviewed. README states the repository is standalone and that Research OS is a separate project with no shared runtime/data dependency. The `research_bridge.py` file records provenance references only.

**Verification:** combined status returned an empty `statuses` list; workflow-run query returned no runs. CI = UNKNOWN, not PASS. No tests were executed. No source was copied or changed. Exact full-tree enumeration remains outstanding.

## 7. Evidence and status rules

- CONFIRMED: owner-confirmed scope or directly observed repository metadata.
- SPECIFIED: represented in documentation only.
- EXISTING: source and behavior demonstrated by inspectable code/test evidence.
- PARTIAL: some source or tests exist, but acceptance is incomplete.
- MISSING: an exact expected path or artifact was checked and not found.
- UNKNOWN: evidence is insufficient or the query did not reliably establish state.
- BLOCKED: a required input or prerequisite prevents a valid audit.

A documentation file is not implementation evidence. A missing guessed path is not proof that a capability does not exist in another repository. No CI status returned is not PASS.

## 8. Audit exit criteria

Phase 1 may be marked PASS only when:
- [ ] The full repository tree at a pinned commit has been enumerated.
- [ ] All source, test, schema, build and configuration files are inventoried.
- [ ] Existing Driver Generation source is located and inspected.
- [ ] Calculation, simulation, CAD and hardware adapters are located or explicitly marked absent with complete tree evidence.
- [ ] Tests and workflows are enumerated with actual results.
- [ ] Reuse/extend/create decisions are recorded per capability.
- [ ] Licenses, dependencies, platform support and security boundaries are reviewed.

Until then: **Phase 1 = PARTIAL / BLOCKED**.

## 9. Next actions

1. Obtain a complete tree listing or repository archive for the exact branch SHA.
2. Identify the canonical Driver Generation repository/path supplied by the owner.
3. Audit existing source and tests before any implementation proposal.
4. Finalize the Master File Plan and vertical-slice acceptance tests.
5. Only after the plan is reviewed, prepare a minimal implementation diff on a separate feature branch.
