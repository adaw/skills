# H6: Backlog + Docs Update — Detailní procedura

## Cíl
Aktualizuj backlog item na DONE, regeneruj index.

## Postup

### 1. Backlog update
```bash
SHA=$(git rev-parse HEAD)
python skills/fabric-init/tools/fabric.py backlog-set --id "${TASK_ID}" \
  --fields-json '{"status": "DONE", "merge_commit": "'"$SHA"'", "updated": "'"$(date +%Y-%m-%d)"'", "branch": null}'
```

### 2. Regeneruj backlog index
```bash
python skills/fabric-init/tools/fabric.py backlog-index
```

### 3. Docs update (pokud se týká)
- Aktualizuj relevantní `docs/` soubory pokud hotfix mění veřejné chování
- Přidej changelog záznam pokud existuje `CHANGELOG.md`

## Minimum (výstup)
- Backlog item má `status: DONE` a `merge_commit`
- Backlog index regenerován

## Anti-patterns (zakázáno)

### Bez evidence
- Nastavit `status: DONE` bez `merge_commit` — DONE bez evidence není DONE

### Stale branch
- Nechat `branch:` vyplněné po merge — smaž (nastavit `null`), jinak příští sprint uvidí stale branch

### Index drift
- Zapomenout regenerovat backlog index — `backlog.md` bude nekonzistentní se soubory

### Docs drift
- Přeskočit docs update když hotfix mění veřejné API — drift mezi kódem a dokumentací
