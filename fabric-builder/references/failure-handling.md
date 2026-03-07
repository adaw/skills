# Failure Handling — fabric-builder

## Overview

Failure handling ensures that builder errors are logged, reported, and tracked without breaking the fabric workflow. The builder is designed to fail-fast on critical issues (e.g., invalid skill structure, parse errors) but to warn and continue on non-critical issues (e.g., optional templates missing).

---

## Failure Table

| Fáze | Chyba | Akce |
|------|-------|------|
| Preconditions | Assets (builder-template.md, config.md) chybí | STOP + protokol error log + jasná zpráva |
| BUILD mode | Nelze vytvořit adresář skillu | STOP + protokol error log |
| BUILD mode | Template parsing selže | STOP + protokol error log |
| FIX mode | Checker report neexistuje | STOP + protokol error log |
| FIX mode | Skill v no-fix seznamu je vybrán | SKIP skill + WARN do reportu |
| MIGRATE mode | Legacy skill neparsovatelný | STOP + protokol error log |
| MIGRATE mode | Nelze mapovat existující obsah na §1–§12 | WARN + pokračuj s best-effort mapováním |
| Size check | SKILL.md > 500 řádků | WARN + pokud > 500 → split povinný |
| Self-check | Chybí frontmatter nebo sekce | WARN + intake item s popisem |
| Overall | Skill je vytvořen ale checker report signalizuje P0 | Report WARN + doporučení spustit checker |

---

## General Rules

**Fail-fast (STOP):** Chybí povinné artefakty (template, config, skill soubor) nebo nelze parsovat YAML.

**Fail-open (WARN + continue):** Chybí volitelné sekcí (např. referenční workflow) nebo template má menší drift.

**Fail-safe:** Pokud builder selže v UPDATE režimu, **NIKDY** nepřepisuj skill soubor částečně. Buď kompletní update, nebo žádný.

---

## Anti-patterns (DO NOT)

1. **Частичное обновление** — Pokud fix/migrate selže, nepisuj HALF-FIXED skill. Vrať se do čistého stavu.
2. **Přepis bez validace** — Před Save buď ověř schemata, frontmatter, syntaxi.
3. **Ignoruj template evolution** — Pokud se změní builder-template.md, seber aktuální verzi (ne cached).
4. **Automatické normalizace** — Nepřepisuj uživatelské sekcí bez explicitní permise.
