"""Shared text formatting for the tracker scripts: money, month names and table labels.

Italian (it) and English (en) are built in. For any other language the scripts use English
and the agent translates the labels, so no calculation or layout is left to the agent.
"""

LABELS = {
    "en": {
        "item": "Item", "amount": "Amount",
        "voluntary": "Voluntary payments", "employee": "Via payslip, employee", "employer": "Via payslip, employer",
        "total": "Total already deductible", "limit": "Annual limit",
        "remaining": "Still missing today", "excess": "Excess today",
        "estimate": "Estimated payslip contributions to year end",
        "remaining_end": "Estimated missing at year end", "excess_end": "Estimated excess at year end",
        "need_inputs": "Set the contribution rate and the monthly pay in the page to see the year-end estimate.",
        "over_note": "Contributions above the limit are not deductible.",
        "month": "Month", "payslip_total": "Payslip total", "check": "Check", "matches": "matches",
        "months": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    },
    "it": {
        "item": "Voce", "amount": "Importo",
        "voluntary": "Versamenti volontari", "employee": "Da busta paga, tuo", "employer": "Da busta paga, datore di lavoro",
        "total": "Totale già deducibile", "limit": "Limite annuo",
        "remaining": "Ti manca oggi", "excess": "Eccedenza oggi",
        "estimate": "Stima contributi in busta fino a dicembre",
        "remaining_end": "Stima mancante a fine anno", "excess_end": "Stima eccedenza a fine anno",
        "need_inputs": "Imposta aliquota e retribuzione mensile nella pagina per vedere la stima a fine anno.",
        "over_note": "I contributi oltre il limite non sono deducibili.",
        "month": "Mese", "payslip_total": "Totale in busta", "check": "Controllo", "matches": "quadra",
        "months": ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"],
    },
}


def labels(lang):
    return LABELS.get((lang or "en").lower()[:2], LABELS["en"])


def money(value, lang):
    if (lang or "en").lower().startswith("it"):
        s = f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{'-' if value < 0 else ''}{s} €"
    return f"{'-' if value < 0 else ''}€{abs(value):,.2f}"


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)
