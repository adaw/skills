---
# Intake Item — Raw Finding
# Slouží pro zaznamenání nových myšlenek, poznatků z kontrol, nebo dalších vstupů
# Tento formulář se vyplňuje před triáží a klasifikací

id: INTAKE-{YYYY}-{NNN}
schema: fabric.intake_item.v1
title: "{TITLE}"
# Zdroj zjištění: manual (ruční zadání), review (code review), check (kontrola), gap (detekce mezery), generate (generováno agentem)
source: "{SOURCE_TYPE}"
date: "{YYYY-MM-DD}"
created_by: "{AUTHOR_NAME_OR_AGENT}"

# Kategoriae guess — předběžný odhad typu (upřesní se během design fáze)
# Možné hodnoty: Epic, Story, Task, Bug, Chore, Spike
initial_type: "{SUGGESTED_TYPE}"

# Surová priorita před aplikací PRIO vzorce (1-10)
raw_priority: "{RAW_PRIORITY}"  # string-safe; triage nástroj může převést na int

# Volitelně: Propojení s cílem viditelným v long-term plánu
linked_vision_goal: "{VISION_GOAL_REF_OR_EMPTY}"
---

## Popis

{DETAILED_DESCRIPTION}

## Kontext

{BACKGROUND_AND_DISCOVERY_CONTEXT}

## Doporučená akce

{RECOMMENDED_NEXT_STEPS}

## Přílohy

- Zdroj/odkaz: {SOURCE_URL_OR_REFERENCE}
- Poznámky: {ADDITIONAL_NOTES}
