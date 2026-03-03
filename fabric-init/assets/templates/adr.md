---
# Architecture Decision Record (ADR)
# Zaznamenává rozhodnutí o architektuře a důvody za nimi
# Statusy: proposed (návrh), accepted (přijatý), deprecated (zastaralý), superseded (nahrazený)

id: "ADR-{NNN}"
schema: fabric.adr.v1
title: "{DECISION_TITLE}"
date: "{YYYY-MM-DD}"
created_at: "{YYYY-MM-DDTHH:MM:SSZ}"
kind: "adr"
step: "adr"
run_id: "{RUN_ID}"

# Stav ADR: proposed, accepted, deprecated, superseded
status: "{proposed_OR_accepted_OR_deprecated_OR_superseded}"

# Pokud je superseded, odkaz na ADR který jej nahrazuje
superseded_by: "{ADR-NNN_OR_EMPTY}"

created_by: "{AUTHOR_NAME}"
reviewed_by: "{REVIEWER_NAME_OR_EMPTY}"
---

## Kontext

{CONTEXT_AND_BACKGROUND}

### Problém

{PROBLEM_STATEMENT_AND_CONSTRAINTS}

### Dostupné možnosti

{OUTLINE_OF_CONSIDERED_ALTERNATIVES}

## Rozhodnutí

{DECISION_STATEMENT}

## Důsledky

### Pozitivní důsledky
- {POSITIVE_CONSEQUENCE_1}
- {POSITIVE_CONSEQUENCE_2}
- {POSITIVE_CONSEQUENCE_3}

### Negativní důsledky
- {NEGATIVE_CONSEQUENCE_1}
- {NEGATIVE_CONSEQUENCE_2}

### Rizika
- {RISK_1}: {MITIGATION_STRATEGY}
- {RISK_2}: {MITIGATION_STRATEGY}

## Zvažované alternativy

### Alternativa 1: {ALTERNATIVE_NAME}
**Výhody**: {ADVANTAGES}
**Nevýhody**: {DISADVANTAGES}
**Proč jsme ji zamítli**: {REASON_FOR_REJECTION}

### Alternativa 2: {ALTERNATIVE_NAME}
**Výhody**: {ADVANTAGES}
**Nevýhody**: {DISADVANTAGES}
**Proč jsme ji zamítli**: {REASON_FOR_REJECTION}

## Implementace

Toto rozhodnutí se promítá do:

- Architektury v: `{ARCHITECTURE_FILES}`
- Kódu v: `{CODE_FILES}`
- Dokumentace v: `{DOCUMENTATION_FILES}`

### Reference v kódu
- Commit: {COMMIT_HASH}
- Pull Request: {PR_NUMBER}
- Task: TASK-{YYYY}-{NNN}

## Diskuse a schválení

Diskutováno v:
- Meeting: {MEETING_DATE_AND_NOTES}
- Code Review: {REVIEW_ID}

Schváleno:
- Architektem: {ARCHITECT_NAME}
- Tech Lead: {TECH_LEAD_NAME}

## Poznámky

{ADDITIONAL_NOTES_AND_CONTEXT}

## Zdroje

- {REFERENCE_1}
- {REFERENCE_2}
- {DOCUMENTATION_LINK}
