# Tracking pension deductions

This project contains a Claude skill and a single-page tracker for Italian supplementary pension contributions. The tracker records voluntary payments and employee/employer contributions, compares them with the annual deduction limit, and estimates contributions through year-end.

## For users

Add the project as a skill in Claude.ai, including its bundled files. Ask Claude to create, check, update, or reset the tracker. The tracker is an HTML Artifact: its page contains the saved figures, so anyone who can open its link can see them. Do not store names, tax codes, employer details, or bank information in the page.

Zucchetti payslips can be processed automatically. Claude presents the extracted amounts for confirmation before adding them. Other payslip formats require manual extraction and confirmation. TFR is excluded. The tracker is an estimate, not tax advice.

## Download and install

Download `tracking-pension-deductions-skill.zip` from the [latest GitHub release](https://github.com/cdemeo92/tracking-pension-deductions/releases). In Claude.ai, enable **Code execution and file creation** under **Settings → Capabilities**, then open [Customize → Skills](https://claude.ai/customize/skills), select **+ → + Create skill → Upload a skill**, and upload the ZIP. Enable the skill from your skills list.

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
- Python 3.10 or later
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

`make package-skill` creates `dist/tracking-pension-deductions-skill.zip` from the existing `dist/template.html`. The ZIP contains the skill instructions, runtime Python scripts, references, license, and generated HTML in a top-level `tracking-pension-deductions/` folder.

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
