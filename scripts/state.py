#!/usr/bin/env python3
"""Read, validate, update and summarise the state block of the pension tracker page.

The page keeps its data in one line:
  <script type="application/json" id="state">{...}</script>
This script is the only thing that should edit that line, so that every change is
validated and the page is never left with a broken state.

Commands (all print JSON on stdout, errors as JSON on stderr):
    init  PAGE --year Y --limit L          create PAGE from the built template (run npm run build first)
  show  PAGE                             print the current state
  recap PAGE [--format markdown --lang it|en]
                                         print computed totals and the year-end estimate;
                                         with --format markdown, a ready-to-send table
  apply PAGE CHANGES.json [--lang it|en] validate and apply changes, then print the recap

Exit codes: 0 ok, 1 invalid input, 2 file or state problem, 3 needs user confirmation.
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fmt  # noqa: E402

STATE_RE = re.compile(r'(<script type="application/json" id="state">)(.*?)(</script>)', re.S)
TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "template.html"
PUBLISHED_TEMPLATE = Path(__file__).resolve().parent.parent / "dist" / "template.html"
CENT_TOLERANCE = 0.02  # largest accepted gap between employee + employer and the payslip total
PARAM_KEYS = ("year", "limit", "rate", "base", "bonus13", "bonus14")
BONUS_MONTHS = {6: "bonus14", 12: "bonus13"}  # month number -> state key added to the base pay
EXIT_INVALID, EXIT_FILE, EXIT_CONFIRM = 1, 2, 3


class Failure(Exception):
    def __init__(self, message, code=EXIT_INVALID, details=None):
        super().__init__(message)
        self.code, self.details = code, details


def r2(n):
    return round(float(n) + 0.0, 2)


def read_state(path):
    p = Path(path)
    if not p.is_file():
        raise Failure(f"File not found: {path}", EXIT_FILE)
    html = p.read_text(encoding="utf-8")
    m = STATE_RE.search(html)
    if not m:
        raise Failure("State block not found. Is this the tracker page?", EXIT_FILE)
    try:
        state = json.loads(m.group(2))
    except json.JSONDecodeError as e:
        raise Failure(f"State block is not valid JSON: {e}", EXIT_FILE)
    return html, state


def write_state(path, html, state):
    validate(state)
    text = json.dumps(state, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    new_html = STATE_RE.sub(lambda m: m.group(1) + text + m.group(3), html, count=1)
    Path(path).write_text(new_html, encoding="utf-8")


def number(value, name, low=0, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise Failure(f"{name} must be a number, got {value!r}")
    if value < low or (high is not None and value > high):
        raise Failure(f"{name} is out of range: {value}")
    return r2(value)


def validate(state):
    for key in PARAM_KEYS + ("months", "voluntary"):
        if key not in state:
            raise Failure(f"State is missing '{key}'", EXIT_FILE)
    if not (isinstance(state["year"], int) and 2000 <= state["year"] <= 2100):
        raise Failure(f"year is out of range: {state['year']}")
    number(state["limit"], "limit", low=0.01)
    number(state["rate"], "rate", high=100)
    for key in ("base", "bonus13", "bonus14"):
        number(state[key], key)
    for month, value in state["months"].items():
        if not (month.isdigit() and 1 <= int(month) <= 12):
            raise Failure(f"Month key must be 1-12, got {month!r}")
        number(value.get("employee"), f"employee[{month}]")
        number(value.get("employer"), f"employer[{month}]")
    for i, v in enumerate(state["voluntary"]):
        number(v.get("amount"), f"voluntary[{i}].amount")


def recap(state):
    months = {int(m): v for m, v in state["months"].items()}
    employee = r2(sum(v["employee"] for v in months.values()))
    employer = r2(sum(v["employer"] for v in months.values()))
    voluntary = r2(sum(v["amount"] for v in state["voluntary"]))
    total = r2(employee + employer + voluntary)
    remaining = r2(state["limit"] - total)
    last = max(months) if months else 0
    missing_inputs = [k for k in ("rate", "base") if not state[k]]
    estimates = {}
    if last and not missing_inputs:
        for m in range(last + 1, 13):
            extra = state[BONUS_MONTHS[m]] if m in BONUS_MONTHS else 0
            estimates[str(m)] = r2((state["base"] + extra) * state["rate"] / 100)
    estimate_total = r2(sum(estimates.values()))
    return {
        "year": state["year"],
        "months_entered": sorted(months),
        "months_count": len(months),
        "voluntary_count": len(state["voluntary"]),
        "voluntary": voluntary,
        "employee": employee,
        "employer": employer,
        "total_deductible": total,
        "limit": state["limit"],
        "remaining_today": remaining,
        "over_limit_today": remaining < 0,
        "estimates": estimates,
        "estimate_total": estimate_total,
        "estimate_available": bool(estimates),
        "estimate_missing_inputs": missing_inputs if last else [],
        "remaining_year_end": r2(remaining - estimate_total),
    }


def recap_markdown(r, lang):
    L = fmt.labels(lang)
    m = lambda v: fmt.money(v, lang)
    rows = [(L["voluntary"], m(r["voluntary"])), (L["employee"], m(r["employee"])), (L["employer"], m(r["employer"])),
            (f"**{L['total']}**", f"**{m(r['total_deductible'])}**"), (L["limit"], m(r["limit"]))]
    rem = r["remaining_today"]
    rows.append((f"**{L['excess'] if rem < 0 else L['remaining']}**", f"**{m(abs(rem))}**"))
    if r["estimate_available"]:
        end = r["remaining_year_end"]
        rows.append((L["estimate"], m(r["estimate_total"])))
        rows.append((f"**{L['excess_end'] if end < 0 else L['remaining_end']}**", f"**{m(abs(end))}**"))
    text = fmt.table([L["item"], L["amount"]], rows)
    notes = []
    if r["over_limit_today"] or (r["estimate_available"] and r["remaining_year_end"] < 0):
        notes.append(L["over_note"])
    if r["estimate_missing_inputs"]:
        notes.append(L["need_inputs"])
    return text + ("\n\n" + " ".join(notes) if notes else "")


def cmd_init(args):
    if Path(args.page).exists():
        raise Failure(f"{args.page} already exists; refusing to overwrite", EXIT_FILE)
    if not PUBLISHED_TEMPLATE.is_file():
        raise Failure("Built tracker template not found. Run `npm run build` first.", EXIT_FILE)
    Path(args.page).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PUBLISHED_TEMPLATE, args.page)
    html, state = read_state(args.page)
    state.update(year=args.year, limit=number(args.limit, "limit", low=0.01))
    write_state(args.page, html, state)
    return {"created": args.page, "state": state}


def apply_changes(state, changes):
    """Mutate state according to changes; return a log. Raise Failure(EXIT_CONFIRM) on unconfirmed conflicts."""
    log, conflicts = [], []
    confirmed = bool(changes.get("confirmed"))

    declared_year = changes.get("year")
    if declared_year is not None and declared_year != state["year"] and not (changes.get("reset") or {}).get("year"):
        raise Failure(
            f"These payslips are for {declared_year} but the page is set to {state['year']}. Reset the page to the new year first. Nothing was written.")

    reset = changes.get("reset")
    if reset and reset.get("year") is not None and reset["year"] != state["year"]:
        if not (reset.get("months") and reset.get("voluntary") and "limit" in reset):
            raise Failure("Changing the year requires a new limit and clearing months and voluntary payments. Nothing was written.")

    if reset:
        if reset.get("months"):
            state["months"] = {}
            log.append("Removed all months")
        if reset.get("voluntary"):
            state["voluntary"] = []
            log.append("Removed all voluntary payments")
        for key in ("year", "limit"):
            if key in reset:
                state[key] = reset[key]
                log.append(f"Set {key} to {reset[key]}")

    for key, value in (changes.get("params") or {}).items():
        if key not in PARAM_KEYS:
            raise Failure(f"Unknown parameter {key!r}")
        if key == "year" and value != state[key]:
            raise Failure("Change the year through reset.year, not params.year. Nothing was written.")
        if state[key] != value:
            log.append(f"Set {key}: {state[key]} -> {value}")
            state[key] = value

    for month, new in (changes.get("months") or {}).items():
        if not (str(month).isdigit() and 1 <= int(month) <= 12):
            raise Failure(f"Month key must be 1-12, got {month!r}")
        employee = number(new.get("employee"), f"employee[{month}]")
        employer = number(new.get("employer"), f"employer[{month}]")
        control = new.get("control_total")
        if control is not None and abs(employee + employer - control) > CENT_TOLERANCE:
            raise Failure(
                f"Month {month}: employee + employer = {r2(employee + employer)} but the payslip total is {control}. Nothing was written.")
        old = state["months"].get(str(month))
        if old and (old["employee"], old["employer"]) == (employee, employer):
            log.append(f"Month {month}: unchanged")
            continue
        if old and not confirmed:
            conflicts.append({"month": int(month), "current": old, "new": {"employee": employee, "employer": employer}})
            continue
        state["months"][str(month)] = {"employee": employee, "employer": employer}
        log.append(f"Month {month}: {'replaced' if old else 'added'} ({employee} + {employer})")

    for item in changes.get("voluntary_add") or []:
        amount, date = number(item.get("amount"), "voluntary amount"), item.get("date", "")
        duplicate = any(v["amount"] == amount and v.get("date", "") == date for v in state["voluntary"])
        if duplicate and not confirmed:
            conflicts.append({"voluntary_duplicate": {"date": date, "amount": amount}})
            continue
        state["voluntary"].append({"date": date, "amount": amount})
        log.append(f"Voluntary payment added: {amount} {date}".strip())

    if conflicts:
        raise Failure("Confirmation needed before overwriting or duplicating. Nothing was written.", EXIT_CONFIRM, conflicts)
    return log


def cmd_apply(args):
    html, state = read_state(args.page)
    try:
        changes = json.loads(Path(args.changes).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise Failure(f"Cannot read changes file: {e}", EXIT_FILE)
    log = apply_changes(state, changes)
    write_state(args.page, html, state)
    r = recap(state)
    return {"changes": log or ["No changes"], "recap": r, "recap_markdown": recap_markdown(r, args.lang)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("page")
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--limit", type=float, required=True)
    sub.add_parser("show").add_argument("page")
    p = sub.add_parser("recap")
    p.add_argument("page")
    p.add_argument("--format", choices=("json", "markdown"), default="json")
    p.add_argument("--lang", default="en")
    p = sub.add_parser("apply")
    p.add_argument("page")
    p.add_argument("changes")
    p.add_argument("--lang", default="en")
    args = ap.parse_args()
    try:
        if args.cmd == "init":
            out = cmd_init(args)
        elif args.cmd == "show":
            out = read_state(args.page)[1]
        elif args.cmd == "recap":
            out = recap(read_state(args.page)[1])
            if args.format == "markdown":
                print(recap_markdown(out, args.lang))
                return
        else:
            out = cmd_apply(args)
    except Failure as e:
        print(json.dumps({"error": str(e), "details": e.details}, ensure_ascii=False), file=sys.stderr)
        sys.exit(e.code)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
