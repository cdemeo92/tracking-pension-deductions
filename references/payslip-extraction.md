# Extracting pension contributions from payslips

Zucchetti payslips are read by `scripts/extract_zucchetti.py`, so this file is only for payslips the script cannot handle: its `unrecognized` files, and `problems` where the split between employee and employer is missing. Read it only then.

## What to extract, per payslip month

Three amounts in EUR:

- **employee**: pension contributions paid by the worker, plus any membership fee charged to the worker.
- **employer**: pension contributions paid by the employer, plus any membership fee paid by the employer.
- **control_total**: the deductible supplementary-pension amount printed on the payslip. Omit it only when the payslip prints none.

Exclude TFR, health funds, bilateral-body contributions and INPS. Do not add, compare or round anything yourself: write the three amounts as printed and let `scripts/state.py apply` check them against the total. It rejects a month whose employee + employer differs from `control_total`, which is how a misread line is caught before it reaches the page.

## Finding the right lines

Payslip software varies, so look for meaning rather than fixed positions: the line stating the deductible pension amount, and the lines carrying the fund's name (words like "contributo fondo pensione", "previdenza complementare", "fondo negoziale", "dedotto").

- The employee amount is in the deductions column. The employer amount is in the earnings column, often in parentheses or marked as company-paid.
- Arrears (a tag such as "05/26" on a line) belong to the month of the payslip that contains them. The printed total already includes them.
- Pension lines can be on a different page from the header. Group pages by the pay period in the header.
- If the payslip belongs to a different year from the page, do not add it. `apply` rejects it when you pass `"year"`.

## Write the changes file

Use the same format as in SKILL.md, adding `"year": YEAR` and one entry per month:

```json
{"year": 2026, "months": {"9": {"employee": 23.57, "employer": 66.43, "control_total": 90.00}}}
```

## Confirm before writing

Show the user the amounts you extracted (month, employee, employer, payslip total) and wait for a yes. A misreading looks identical to correct data once it is in the page, and only the user can compare it with the paper payslip. If a payslip is unreadable, write nothing for it, say which one, and offer manual entry. Never guess an amount.

## Privacy

Keep only month and amounts. Do not copy the worker's name, tax code, employee number, employer name or bank details into the page or your replies.
