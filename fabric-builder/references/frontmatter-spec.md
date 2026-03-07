# Frontmatter Specification (B3)

## Supported Attributes

**Claude Code + Agent Skills standard frontmatter attributes:**

| Atribut | Povinný | Popis |
|---------|---------|-------|
| `name` | Ne (default = dirname) | max **64 znaků**, jen lowercase, čísla, pomlčky |
| `description` | Doporučený | max **1024 znaků**, non-empty, bez XML tagů. 3. osoba. CO dělá + KDY použít |
| `disable-model-invocation` | Ne | `true` = jen manuální `/name` invokace |
| `user-invocable` | Ne | `false` = skrytý z `/` menu, jen Claude invokuje |
| `allowed-tools` | Ne | Povolené nástroje bez per-use potvrzení |
| `argument-hint` | Ne | Nápověda pro autocomplete: `[issue-number]` |
| `model` | Ne | Model pro tento skill |
| `context` | Ne | `fork` pro subagent |
| `agent` | Ne | Typ subagenta (`Explore`, `Plan`, ...) |
| `hooks` | Ne | Hooks pro lifecycle |
| `compatibility` | Ne | Platformová kompatibilita (Agent Skills standard) |
| `license` | Ne | Licence (Agent Skills standard) |
| `metadata` | Ne | Custom metadata (Agent Skills standard) |

## Fabric Skills Rules

- **`name`**: MUSÍ odpovídat názvu adresáře (`fabric-{name}`)
- **`description`**: MUSÍ říct CO dělá + KDY to použít. Claude ho používá k rozhodování, zda skill aktivovat
- **`<!-- built from: builder-template -->`**: VŽDY na řádku ZA uzavíracím `---`, NIKDY uvnitř frontmatteru
- Závislosti (upstream/downstream) se dokumentují v **§12 Metadata** uvnitř skill body, NE ve frontmatteru

## Anti-patterns

❌ Nepodporované atributy:
- `title`, `type`, `schema`, `version`, `tags`, `depends_on`, `feeds_into`

❌ Nepodporované popisy:
- Description v první osobě ("I process...") nebo druhé ("You can use...")
- Vágní description ("Helps with stuff", "Processes data")
- Builder tag uvnitř YAML bloku `---` (musí být za uzavřením)
