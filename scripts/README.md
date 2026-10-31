# Scripts

These scripts hold the tracker's calculations, validation, and supported payslip extraction. Keeping this work in code makes results repeatable and avoids asking Claude to redo arithmetic in conversation.

Run the commands below from the repository root.

## `state.py`

`state.py` reads and updates the JSON state embedded in the tracker HTML. It validates inputs before writing and produces the totals and recap. It is the only script that should modify the tracker's state block.

Build the single-file tracker before initializing a new page:

```sh
npm run build
python3 scripts/state.py init /tmp/tracker.html --year 2026 --limit 5300
```

Available operations:

```sh
python3 scripts/state.py --help
python3 scripts/state.py show /tmp/tracker.html
python3 scripts/state.py recap /tmp/tracker.html
python3 scripts/state.py recap /tmp/tracker.html --format markdown --lang it
python3 scripts/state.py apply /tmp/tracker.html changes.json --lang it
```

`apply` accepts a JSON changes file. It rejects invalid amounts, a payslip total that does not match the employee/employer split, and year changes that do not reset yearly contributions. Replacing an existing month or adding a duplicate voluntary payment requires explicit confirmation. Exit codes are `0` for success, `1` for invalid input, `2` for a file/state problem, and `3` when confirmation is required.

## `extract_zucchetti.py`

This script extracts pension contribution amounts from supported Zucchetti PDFs. It compares the employee and employer amounts with the deductible total printed on the payslip, accepting a difference of at most two cents. Mismatches, missing totals, other tax years, and unsupported files are reported and are not included in the proposed changes.

```sh
python3 scripts/extract_zucchetti.py --help
python3 scripts/extract_zucchetti.py --year 2026 --lang it path/to/payslip.pdf
```

The JSON output includes `changes`, a confirmation `table`, `problems`, `no_pension`, and `unrecognized`. Review the table against the payslip before applying its changes. `pdftotext` from Poppler is the preferred PDF text extractor; `pdfplumber` is the fallback enabled by `uv sync --extra pdf`.

## `fmt.py`

`fmt.py` provides shared Italian and English labels, currency formatting, and Markdown table formatting for the Python scripts.

## Tests

Python tests are under `tests/unit/` and `tests/integration/`. Run an individual module's tests with:

```sh
python3 -m unittest tests.unit.test_fmt -v
python3 -m unittest tests.unit.test_state -v
python3 -m unittest tests.unit.test_extract_zucchetti -v
python3 -m unittest tests.integration.test_workflow -v
```

The state CLI and workflow integration tests initialize pages from `dist/template.html`, so build it first:

```sh
npm run build
python3 -m unittest tests.unit.test_state -v
python3 -m unittest tests.integration.test_workflow -v
```

Run the complete Python suite with `python3 -m unittest discover -v`, or run all project checks with `npm test`.
