# fabric-process References Index

Quick navigation guide to the split fabric-process documentation.

## Files Overview

### SKILL.md (Main Entry Point)
**Location:** `../SKILL.md` (333 lines)

Main skill document with all §1-§12 sections. Contains summaries and cross-references to detailed procedures.

### references/workflow.md (Detailed Procedures & Bash)
**Location:** `workflow.md` (287 lines)

Contains all detailed procedural bash scripts and implementations referenced from §7 (Postup).

**Key sections:**
- State validation & path traversal guards
- K2 fix: Process extraction counter
- FAST PATH detection scripts (route, service, CLI, model inventory)
- P1: External process anti-patterns + validation
- P2: Orphan classification algorithm (WQ5)
- P4: Test coverage & stub detection
- Quality Gate implementations

### references/examples.md (Templates & Schemas)
**Location:** `examples.md` (235 lines)

LLMem-specific examples, call chain diagrams, and reusable templates for all process documentation.

**Key sections:**
- P1: Complete LLMem external processes table (8 API, 6 CLI)
- P2: Internal process call chain ASCII diagram
- P2: Individual process file template (v1.2 with deprecation support)
- P3: Cross-layer mapping template & orphan categories
- P5: Process map master template
- Process ID naming conventions
- Significant process threshold (WQ5)

### references/preconditions.md (Configuration & Protocol)
**Location:** `preconditions.md` (138 lines)

Setup, configuration, and protocol logging procedures referenced from §2-§6.

**Key sections:**
- Protocol logging (START, END, ERROR events with bash)
- Precondition checks (1-5 with bash validation)
- Required & optional inputs
- Output artifacts (primary & secondary)
- Process map contract schema (YAML)
- FAST PATH index sync

### references/validation.md (Quality Gates & Reports)
**Location:** `validation.md` (190 lines)

Quality assurance procedures, report schemas, and downstream consumer contracts referenced from §8-§12.

**Key sections:**
- 3 Quality gates with pass/fail criteria & bash
- Self-check checklist (18 items, full)
- Report schema (fabric.report.v1)
- Failure handling matrix
- Metadata for fabric-loop orchestration
- Downstream consumers (fabric-gap, analyze, review, check, implement)

## Cross-Reference Map

### From SKILL.md to References

| SKILL.md Section | References |
|---|---|
| §2 Protokol | preconditions.md (Protocol Logging) |
| §3 Preconditions | preconditions.md (all checks) |
| §4-5 I/O | preconditions.md (Inputs/Outputs) |
| §6 FAST PATH | workflow.md (all scans) |
| §7 P1 Extract | examples.md (LLMem table) + workflow.md (anti-patterns) |
| §7 P2 Trace | examples.md (call chain, template) + workflow.md (algorithm) |
| §7 P3 Cross-map | examples.md (templates, categories) + workflow.md |
| §7 P4 Validate | workflow.md (test, stub coverage) |
| §7 P5 Update | examples.md (schemas) + validation.md (report) |
| §8 Quality Gates | validation.md (gates 1-3) |
| §9 Report | validation.md (schema + template) |
| §10 Self-check | validation.md (full checklist) |
| §11 Failure | validation.md (matrix) |
| §12 Metadata | validation.md (YAML structure) |

## How to Use These Files

### For Quick Start
1. Read `../SKILL.md` — understand the 5 phases (P1-P5)
2. Jump to reference file as needed (links provided in SKILL.md)
3. Copy/adapt templates from `examples.md`
4. Follow bash procedures from `workflow.md`

### For Process Extraction (P1)
1. Review SKILL.md §7 P1 summary
2. See `examples.md` for real LLMem process table
3. Run bash from `workflow.md` (anti-patterns A/B/C)
4. Validate count with bash from `workflow.md`

### For Process Tracing (P2)
1. Review SKILL.md §7 P2 summary
2. Check `examples.md` for call chain ASCII structure
3. Use individual process template from `examples.md`
4. Apply classification algorithm from `workflow.md` for orphans

### For Quality Validation (§8)
1. Review SKILL.md §8 (3 gates summary)
2. Run gate bash scripts from `validation.md`
3. Fix issues and re-run gates

### For Report Generation (§9)
1. Use report schema from `validation.md`
2. Populate metrics from process-map.md you created
3. Reference template from `validation.md`

### For Failure Recovery (§11)
1. Consult failure matrix in `validation.md`
2. Check if your error is listed
3. Follow recommended action
4. Log protocol event using bash from `preconditions.md`

## File Dependencies

```
SKILL.md (main entry point)
├── references/workflow.md (procedures & bash)
├── references/examples.md (templates & schemas)
├── references/preconditions.md (config & protocol)
└── references/validation.md (quality & reports)
```

All reference files are self-contained with complete bash scripts, schemas, and examples.
No cross-dependencies between reference files.

## Content Statistics

| File | Lines | Size | Purpose |
|---|---|---|---|
| SKILL.md | 333 | 16K | Navigation + summaries |
| workflow.md | 287 | 12K | Procedures & bash scripts |
| examples.md | 235 | 12K | Templates & real examples |
| validation.md | 190 | 8K | Quality gates & reports |
| preconditions.md | 138 | 4K | Config & protocol |
| **TOTAL** | **1183** | **52K** | Complete documentation |

Original SKILL.md was 948 lines; split with 24.7% content growth (from 37.6K to 52K total).

## Language & Format

- **Language:** Czech (Česky) — all instructions and summaries in Czech
- **Format:** Markdown with YAML frontmatter for schemas
- **Bash:** POSIX-compatible bash scripts, suitable for fabric-loop orchestration
- **Schemas:** fabric.* v1 schemas (process-map, process, report, intake_item)

## Updates & Maintenance

When updating fabric-process skill:

1. Update summaries in `../SKILL.md` first
2. Update detailed procedures in relevant reference file
3. Keep cross-references in sync (4-6 per section)
4. Maintain line count: SKILL.md ≤500, total ≥948
5. Never duplicate content (one source of truth per detail)

---

**Last Updated:** 2026-03-07
**Status:** Documentation complete, ready for deployment
