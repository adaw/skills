# Config Normalization — fabric-init

## 0.1) Normalizuj config (autodetect `COMMANDS`)

Cíl: aby další fáze nemusely hádat test/lint/format příkazy a aby `fabric-test`/`fabric-close` mohly bezpečně enforce quality gates.

### Process

1. Načti YAML blok `COMMANDS` z `{WORK_ROOT}/config.md`.
2. Pokud je některá hodnota `TBD`, pokus se ji **deterministicky** doplnit podle repo signálů (viz níže).
3. Změny zapisuj **jen** pro klíče, které byly `TBD` (nepřepisuj uživatelské hodnoty).
4. Pokud auto-detekce selže:
   - pro `COMMANDS.test` nastav fail-fast placeholder: `echo "CONFIGURE COMMANDS.test" && exit 1`
   - pro `COMMANDS.lint` / `COMMANDS.format_check` nastav `""` (explicitně vypnuto) a vytvoř WARN intake item

### Detekce (v tomto pořadí)

#### A) **Makefile**

- pokud existuje `Makefile` a obsahuje target `test:` → `COMMANDS.test = "make test"`
- pokud existuje `lint:` → `COMMANDS.lint = "make lint"`
- pokud existuje `lint-fix:` / `lint_fix:` → `COMMANDS.lint_fix = "make <target>"`
- pokud existuje `format-check:` / `fmt-check:` / `format_check:` → `COMMANDS.format_check = "make <target>"`
- pokud existuje `format:` / `fmt:` → `COMMANDS.format = "make <target>"`

#### B) **Node.js (`package.json`)**

- vyber package manager podle lockfile (`pnpm-lock.yaml`→pnpm, `yarn.lock`→yarn, jinak npm)
- pokud `scripts.test` existuje → `COMMANDS.test = "<pm> test"`
- pokud `scripts.lint` existuje → `COMMANDS.lint = "<pm> run lint"`
- pokud `scripts.lint:fix` nebo `scripts.lint-fix` existuje → `COMMANDS.lint_fix = "<pm> run <script>"`
- pokud `scripts.format:check` nebo `scripts.format-check` existuje → `COMMANDS.format_check = "<pm> run <script>"`
- pokud `scripts.format` existuje → `COMMANDS.format = "<pm> run format"`

#### C) **Python**

- pokud existuje `pyproject.toml` nebo převaha `*.py` → `COMMANDS.test = "python -m pytest"`
- pokud v `pyproject.toml` najdeš `ruff`:
  - `COMMANDS.lint = "python -m ruff check ."`
  - `COMMANDS.lint_fix = "python -m ruff check --fix ."`
  - `COMMANDS.format_check = "python -m ruff format --check ."`
  - `COMMANDS.format = "python -m ruff format ."`
- jinak pokud najdeš `black`:
  - `COMMANDS.format_check = "python -m black --check ."`
  - `COMMANDS.format = "python -m black ."`

#### D) **Go / Rust**

**go.mod:**
- `COMMANDS.test = "go test ./..."`
- `COMMANDS.lint = "golangci-lint run"` (pokud `golangci-lint` dostupný; jinak `""`)
- `COMMANDS.lint_fix = "golangci-lint run --fix"` (pokud dostupný)
- `COMMANDS.format_check = "test -z \"$(gofmt -l .)\"`
- `COMMANDS.format = "gofmt -w ."`

**Cargo.toml:**
- `COMMANDS.test = "cargo test"`
- `COMMANDS.lint = "cargo clippy -- -D warnings"`
- `COMMANDS.lint_fix = "cargo clippy --fix --allow-dirty -- -D warnings"`
- `COMMANDS.format_check = "cargo fmt -- --check"`
- `COMMANDS.format = "cargo fmt"`

#### E) **Java / JVM**

**build.gradle / build.gradle.kts:**
- `COMMANDS.test = "gradle test"`
- `COMMANDS.lint = ""` (Java nemá standardní lint; nastav `""`)
- `COMMANDS.format_check = ""` (pokud `spotless` plugin → `gradle spotlessCheck`)
- `COMMANDS.format = ""` (pokud `spotless` → `gradle spotlessApply`)

**pom.xml:**
- `COMMANDS.test = "mvn test"`
- `COMMANDS.lint = ""` (pokud `checkstyle` plugin → `mvn checkstyle:check`)
- `COMMANDS.format_check = ""`
- `COMMANDS.format = ""`

#### F) **Ruby**

**Gemfile / Rakefile:**
- `COMMANDS.test = "bundle exec rake test"` (nebo `bundle exec rspec` pokud `.rspec` existuje)
- `COMMANDS.lint = "bundle exec rubocop"` (pokud `.rubocop.yml` existuje)
- `COMMANDS.lint_fix = "bundle exec rubocop -A"` (pokud rubocop dostupný)
- `COMMANDS.format_check = ""` (Ruby nemá standardní formátování mimo rubocop)
- `COMMANDS.format = ""`

#### G) **Fallback (žádný rozpoznaný projekt)**

Pokud žádný z výše uvedených signálů neodpovídá:
- `COMMANDS.test` → nastav fail-fast placeholder: `echo "CONFIGURE COMMANDS.test" && exit 1`
- Ostatní → `""` (vypnuto)
- Vytvoř intake item `intake/init-unknown-project-type.md` s doporučením ručně nakonfigurovat COMMANDS

### Evidence

Pokud jsi něco autodetekoval nebo vypnul:

- ujisti se, že existují `{WORK_ROOT}/reports/` a `{WORK_ROOT}/intake/` (pokud ne, vytvoř je `mkdir -p` ještě před zápisem)
- vytvoř `{WORK_ROOT}/reports/config-commands-{YYYY-MM-DD}.md` (co bylo `TBD`, co bylo nastaveno, confidence, proč)
- vytvoř intake item `{WORK_ROOT}/intake/config-commands-autodetected.md` (aby to bylo auditovatelné / přezkoumatelné)
