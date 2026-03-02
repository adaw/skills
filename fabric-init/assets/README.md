# fabric-init assets

Tento adresář je součást distribuce `skills/` a slouží jako **source-of-truth defaults** pro bootstrap.

- `templates/` — default šablony (kopírují se do `{WORK_ROOT}/templates/` jen pokud chybí)
- `config.template.md` — default config pro nový projekt (kopíruje se do `{WORK_ROOT}/config.md` jen pokud chybí)

Záměr:
- Po zkopírování pouze `skills/` do cizího projektu je možné spustit `skills/fabric-loop/SKILL.md`.
- Pokud workspace/config chybí, `fabric-init` si umí vytvořit minimální skeleton a vyžádat doplnění.
