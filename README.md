# Tracking pension deductions

This project contains a Claude skill and a single-page tracker for Italian supplementary pension contributions. The tracker records voluntary payments and employee/employer contributions, compares them with the annual deduction limit, and estimates contributions through year-end.

## Using the skill

Ask Claude to set up, update, or review your contributions. You receive a report showing contributions to date, how much of the annual limit remains, and an estimate through year-end, together with an HTML Artifact that keeps your figures for future chats.

### Capabilities

- **Zucchetti payslips:** A script extracts the contribution amounts from the payslip, so no AI tokens are used to read it. Claude shows you the results for confirmation.
- **Other payslips:** Claude reads the contribution amounts from other payslips and asks you to confirm them before updating the tracker.

#### Privacy

The tracker stores contribution figures, not personal identifiers. Anyone with the Artifact link can view those figures, so share it only with people you trust.

## Download and install

1. **Download:** Get `tracking-pension-deductions-skill.zip` from the [latest release](https://github.com/cdemeo92/tracking-pension-deductions/releases).
2. **Enable file creation:** In Claude settings, open **Features** and turn on **Create and edit files**.
3. **Upload:** In Claude.ai, open [Customize → Skills](https://claude.ai/customize/skills), select **+ Add → Upload a skill**, and choose the ZIP.
4. **Activate:** Turn on the skill in your skills list.

See Anthropic's [user guide to using Skills](https://support.claude.com/en/articles/12512180-use-skills-in-claude) for specific instructions and troubleshooting.

## Project structure

```text
tracking-pension-deductions/
├── SKILL.md                # Claude workflow instructions and activation rules
├── assets/                 # HTML tracker and its TypeScript source
├── scripts/                # Python tracker and payslip tools
├── references/             # Tax rules and payslip guidance
├── evals/                  # Claude skill behavior scenarios
└── tests/                  # Automated unit and integration tests
```

- See [`scripts/README.md`](scripts/README.md) for the scripts.
- See [`assets/README.md`](assets/README.md) for the tracker source.

## Requirements

- Node.js 26 or later and npm
- Make and the `zip` utility to create the Claude skill archive
- Python 3.13 or later
- `uv` for the optional `pdfplumber` fallback; Poppler's `pdftotext` utility is recommended for PDF extraction.

Run `asdf install` to install those versions. If either plugin is missing, add it first:

```sh
asdf plugin add nodejs https://github.com/asdf-vm/asdf-nodejs.git
asdf plugin add python https://github.com/asdf-community/asdf-python.git
asdf install
```

On macOS, install the optional tools with `brew install uv poppler`.

## Install and build

```sh
npm ci
uv sync --extra pdf
npm run build
```

The build creates the standalone tracker at `dist/template.html`. The generated `dist/` directory is ignored by Git.

## Create the Claude skill ZIP manually

From the project root, run:

```sh
npm i
npm run build
make package-skill
```

`make package-skill` creates `dist/tracking-pension-deductions-skill.zip` from the existing `dist/template.html`. The ZIP contains the skill instructions, runtime Python scripts, references, and generated HTML in a top-level `tracking-pension-deductions/` folder.

## Run and modify

Use the skill in Claude.ai for the normal tracker workflow. For local development, start the Vite preview with:

```sh
npm run dev
```

To inspect the Python command-line options, run:

```sh
python3 scripts/state.py --help
python3 scripts/extract_zucchetti.py --help
```

## Test

```sh
npm test
```

This builds the page, runs strict TypeScript checks, runs the Vitest frontend suite, and runs the Python unit and integration tests. Use `npm run test:frontend` or `npm run test:python` to run one suite separately.
