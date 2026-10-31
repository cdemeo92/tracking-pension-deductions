#!/usr/bin/env python3
"""Extract pension contributions from Zucchetti payslip PDFs, with no judgement needed from the agent.

Usage: extract_zucchetti.py --year YEAR [--lang it|en] FILE.pdf [FILE.pdf ...]

Prints JSON:
  changes       ready to pass to `state.py apply` (months with a verified control_total)
  table         markdown confirmation table to show the user
  problems      payslips read but not trustworthy (total missing, mismatch, other year, conflicting duplicates)
  no_pension    months with no pension lines (nothing to add)
  unrecognized  files that are not Zucchetti payslips or could not be read: the agent must extract these

A month goes into `changes` only when employee + employer equals the payslip total (F01998)
within two cents, so a misread line never reaches the page.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fmt  # noqa: E402

CENT_TOLERANCE = 0.02
IT_MONTHS = fmt.LABELS["it"]["months"]
PERIOD_RE = re.compile(r"\b(" + "|".join(IT_MONTHS) + r")\s+(20\d\d)\b", re.I)
NUMBER_RE = re.compile(r"\d{1,3}(?:\.\d{3})*,\d{2}(?!\d)")
TOTAL_RE = re.compile(r"\bF01998\b")
FUND_RE = re.compile(r"\b(Z20000|Z20006)\b")  # contribution and membership-fee rows of the pension fund
EMPLOYER_MARK = "C/Ditta"


def to_number(text):
    return float(text.replace(".", "").replace(",", "."))


def last_number(line):
    found = NUMBER_RE.findall(line)
    return to_number(found[-1]) if found else None


def read_pages(path):
    """Return the text of each page, keeping rows intact."""
    try:
        out = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, check=True).stdout
        return out.split("\f")
    except (OSError, subprocess.CalledProcessError):
        pass
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return [(p.extract_text(layout=True) or "") for p in pdf.pages]
    except Exception:
        return None


def parse_file(path):
    """Return {(year, month): {...}} for one file, or None when it is not a readable Zucchetti payslip."""
    pages = read_pages(path)
    if not pages or not any("zucchetti" in p.lower() for p in pages):
        return None
    result = {}
    for text in pages:
        period = PERIOD_RE.search(text)
        if not period:
            continue
        key = (int(period.group(2)), [m.lower() for m in IT_MONTHS].index(period.group(1).lower()) + 1)
        entry = result.setdefault(key, {"total": None, "employee": 0.0, "employer": 0.0, "rows": 0})
        for line in text.splitlines():
            if TOTAL_RE.search(line):
                n = last_number(line)
                if n is not None:
                    entry["total"] = round((entry["total"] or 0) + n, 2)
            elif FUND_RE.search(line):
                n = last_number(line)
                if n is not None:
                    entry["rows"] += 1
                    entry["employer" if EMPLOYER_MARK in line else "employee"] += n
    return result or None


def extract_files(files, target_year, lang="en"):
    L = fmt.labels(lang)
    changes, problems, no_pension, unrecognized, seen, conflicted = {}, [], [], [], {}, set()
    for f in files:
        parsed = parse_file(f)
        if parsed is None:
            unrecognized.append(Path(f).name)
            continue
        for (year, month), e in sorted(parsed.items()):
            name = f"{L['months'][month - 1]} {year}"
            if year != target_year:
                problems.append({"payslip": name, "file": Path(f).name, "issue": "other_year", "page_year": target_year})
                continue
            employee, employer = round(e["employee"], 2), round(e["employer"], 2)
            if e["total"] is None and e["rows"] == 0:
                no_pension.append(name)
                continue
            if e["total"] is None:
                problems.append({"payslip": name, "file": Path(f).name, "issue": "total_missing", "employee": employee, "employer": employer})
                continue
            if e["rows"] == 0:
                problems.append({"payslip": name, "file": Path(f).name, "issue": "split_missing", "control_total": e["total"]})
                continue
            if abs(employee + employer - e["total"]) > CENT_TOLERANCE:
                problems.append({"payslip": name, "file": Path(f).name, "issue": "mismatch", "employee": employee, "employer": employer, "control_total": e["total"]})
                continue
            value = {"employee": employee, "employer": employer, "control_total": e["total"]}
            if month in conflicted:
                continue
            if month in seen and seen[month] != value:
                problems.append({"payslip": name, "file": Path(f).name, "issue": "conflicting_duplicate"})
                changes.pop(str(month), None)
                conflicted.add(month)
                continue
            seen[month] = value
            changes[str(month)] = value

    rows = [(L["months"][int(m) - 1], fmt.money(v["employee"], lang), fmt.money(v["employer"], lang),
             fmt.money(v["control_total"], lang), L["matches"]) for m, v in sorted(changes.items(), key=lambda kv: int(kv[0]))]
    table = fmt.table([L["month"], L["employee"].replace("Via payslip, ", "").replace("Da busta paga, ", "").capitalize(),
                       L["employer"].replace("Via payslip, ", "").replace("Da busta paga, ", "").capitalize(),
                       L["payslip_total"], L["check"]], rows) if rows else ""
    return {
        "changes": {"year": target_year, "months": changes} if changes else {},
        "table": table, "problems": problems, "no_pension": no_pension, "unrecognized": unrecognized,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int, required=True, help="year the page is set to")
    ap.add_argument("--lang", default="en")
    ap.add_argument("files", nargs="+")
    args = ap.parse_args()
    result = extract_files(args.files, args.year, args.lang)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
