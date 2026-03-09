#!/usr/bin/env python3
"""S4: Dependency symmetry check.

Ověřuje konzistenci depends_on ↔ feeds_into v §12 metadata
pro všechny fabric skills.

Sémantika:
- depends_on = strict ordering (co musí běžet přede mnou)
- feeds_into = data flow (kdo konzumuje můj output)

Tyto vztahy NEJSOU nutně symetrické. Proto check rozlišuje:
- LEVEL 1: depends_on→feeds_into (A depends B → B should feeds A)
  → WARN, protože B by měl vědět že A na něm závisí
- LEVEL 2: feeds_into→depends_on (A feeds B → B should depends A)
  → INFO only, B nemusí na A přímo záviset (může záviset na mezikroku)

Special: init, loop, checker, builder jsou vyloučeny z L1 kontroly
(init feeds do všeho, loop je orchestrátor).

Použití:
    python3 scripts/s4_symmetry_check.py
    python3 scripts/s4_symmetry_check.py --strict   # obě úrovně jako WARN
"""
import re
import os
import sys


def parse_deps(val: str) -> set[str]:
    """Parse '[fabric-x, fabric-y]' or '- fabric-x' into set."""
    if not val or val == '[]':
        return set()
    return set(re.findall(r'fabric-\w+', val))


def extract_metadata(skill_path: str) -> tuple[set[str], set[str]]:
    """Extrahuje depends_on a feeds_into z §12 metadata bloku.

    Hledá řádky začínající 'depends_on:' a 'feeds_into:'
    za posledním výskytem '## §12' v souboru.
    """
    text = open(skill_path).read()

    # Najdi §12 blok (poslední výskyt)
    s12_pos = text.rfind('## §12')
    if s12_pos == -1:
        return set(), set()

    s12_block = text[s12_pos:]

    dep_match = re.search(r'^depends_on:\s*(.+?)$', s12_block, re.MULTILINE)
    feed_match = re.search(r'^feeds_into:\s*(.+?)$', s12_block, re.MULTILINE)

    deps = parse_deps(dep_match.group(1)) if dep_match else set()
    feeds = parse_deps(feed_match.group(1)) if feed_match else set()

    return deps, feeds


def main():
    strict = "--strict" in sys.argv
    skills_dir = 'skills'
    dep_map: dict[str, set[str]] = {}
    feed_map: dict[str, set[str]] = {}

    # Meta/orchestration skills kde symetrie nemá smysl
    META_SKILLS = {'fabric-init', 'fabric-loop', 'fabric-checker', 'fabric-builder'}

    for d in sorted(os.listdir(skills_dir)):
        if not d.startswith('fabric-'):
            continue
        skill_path = os.path.join(skills_dir, d, 'SKILL.md')
        if not os.path.exists(skill_path):
            continue

        deps, feeds = extract_metadata(skill_path)
        dep_map[d] = deps
        feed_map[d] = feeds

    warnings = []
    infos = []

    # LEVEL 1: A depends_on B → B should feeds_into A
    # (pokud B není meta skill)
    for skill in sorted(dep_map):
        for source in dep_map[skill]:
            if source in META_SKILLS:
                continue
            if source not in feed_map:
                warnings.append(f"ERROR: {skill} depends_on {source}, but {source} not found")
            elif skill not in feed_map[source]:
                warnings.append(
                    f"L1-WARN: {skill} depends_on {source}, "
                    f"but {source} missing {skill} in feeds_into"
                )

    # LEVEL 2: A feeds_into B → B should depends_on A
    # (informational — B může záviset na jiném mezikroku)
    for skill in sorted(feed_map):
        if skill in META_SKILLS:
            continue
        for target in feed_map[skill]:
            if target in META_SKILLS:
                continue
            if target not in dep_map:
                warnings.append(f"ERROR: {skill} feeds_into {target}, but {target} not found")
            elif skill not in dep_map[target]:
                msg = (
                    f"L2-INFO: {skill} feeds_into {target}, "
                    f"but {target} doesn't depend on {skill} (may use intermediate)"
                )
                if strict:
                    warnings.append(msg)
                else:
                    infos.append(msg)

    total_deps = sum(len(v) for v in dep_map.values())
    total_feeds = sum(len(v) for v in feed_map.values())

    print(f"S4 Symmetry Check — {len(dep_map)} skills, "
          f"{total_deps} depends_on edges, {total_feeds} feeds_into edges")
    print(f"   (Meta skills excluded from L1: {', '.join(sorted(META_SKILLS))})")

    if warnings:
        for w in warnings:
            print(w)
        print(f"\nS4: FAIL ({len(warnings)} issues)")
    else:
        print("S4: PASS — dependency contracts consistent")

    if infos:
        print(f"\n--- Informational ({len(infos)}) ---")
        for i in infos:
            print(i)

    sys.exit(1 if warnings else 0)


if __name__ == '__main__':
    main()
