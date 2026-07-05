from pathlib import Path
import re

ROOT = Path(r"D:\1Workspace\AuditPal")

RUNNER = ROOT / "backend" / "app" / "services" / "audit_engine" / "runner.py"
AUDIT_RUNS = ROOT / "backend" / "app" / "api" / "routes" / "audit_runs.py"
CHECKS_DIR = ROOT / "backend" / "app" / "services" / "audit_engine" / "checks"
FRONTEND = ROOT / "frontend" / "src" / "app" / "workspaces" / "[id]" / "page.tsx"
SAMPLE_DIR = ROOT / "sample-data"

CHECKS_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------
# 1. Ledger scrutiny checks
# ----------------------------------------------------

(CHECKS_DIR / "ledger_scrutiny_checks.py").write_text(
r'''from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


SUSPENSE_KEYWORDS = ["suspense", "temporary", "dummy", "unclassified", "unknown"]
CASH_KEYWORDS = ["cash", "petty cash"]
LOAN_ADVANCE_KEYWORDS = ["loan", "advance", "deposit", "unsecured loan", "director loan"]
MANUAL_ENTRY_KEYWORDS = ["journal", "manual", "jv", "adjustment", "provision", "rectification"]


def _norm(value):
    if value is None:
        return ""
    return str(value).strip()


def _lower(value):
    return _norm(value).lower()


def _amount(value):
    if value is None:
        return None
    try:
        if isinstance(value, Decimal):
            return float(value)
        cleaned = str(value).replace(",", "").replace("₹", "").strip()
        if cleaned == "":
            return None
        return float(cleaned)
    except (ValueError, InvalidOperation):
        return None


def _date_string(value):
    if not value:
        return ""
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _is_year_end(value):
    text = _date_string(value)
    return any(marker in text for marker in ["03-31", "31-03", "31/03", "2025-03-31", "2026-03-31"])


def _raw(record, *keys):
    raw = getattr(record, "raw_data", None) or {}
    for key in keys:
        if key in raw and raw[key] not in [None, ""]:
            return raw[key]
    return None


def _description(record):
    return (
        _raw(record, "description", "narration", "Narration", "Description", "Particulars", "Text")
        or getattr(record, "description", None)
        or ""
    )


def _voucher_type(record):
    return _raw(record, "Voucher Type", "voucher_type", "Document Type", "document_type", "Entry Type") or ""


def _ledger_name(record):
    return (
        getattr(record, "party_name", None)
        or _raw(record, "Ledger Name", "G/L Account", "GL Account", "Account", "Particulars", "Cost Center")
        or ""
    )


def _money(value):
    amount = _amount(value)
    if amount is None:
        return ""
    return f"₹{amount:,.0f}"


def _title(base, record):
    bits = []
    doc = _norm(getattr(record, "document_id", None))
    ledger = _norm(_ledger_name(record))
    amount = _money(getattr(record, "amount", None))

    if doc:
        bits.append(doc)
    if ledger:
        bits.append(ledger)
    if amount:
        bits.append(amount)

    if not bits:
        return base

    return f"{base} — {' · '.join(bits[:3])}"


def _finding(record, finding_type, risk_level, title, description, extra=None):
    evidence = {
        "record_id": getattr(record, "id", None),
        "source_row": getattr(record, "source_row", None),
        "document_id": getattr(record, "document_id", None),
        "ledger_name": _ledger_name(record),
        "party_name": getattr(record, "party_name", None),
        "transaction_date": _date_string(getattr(record, "transaction_date", None)),
        "amount": getattr(record, "amount", None),
        "description": _description(record),
        "voucher_type": _voucher_type(record),
        "record_type": getattr(record, "record_type", None),
    }

    if extra:
        evidence.update(extra)

    return {
        "source_record_id": getattr(record, "id", None),
        "finding_type": finding_type,
        "risk_level": risk_level,
        "title": _title(title, record),
        "description": description,
        "evidence": evidence,
    }


def run_ledger_scrutiny_checks(records):
    findings = []
    voucher_index = defaultdict(list)
    ledger_amount_date_index = defaultdict(list)

    for record in records:
        document_id = _norm(getattr(record, "document_id", None))
        ledger_name = _norm(_ledger_name(record))
        ledger_lower = ledger_name.lower()
        description = _description(record)
        description_lower = description.lower()
        voucher_type = _voucher_type(record)
        voucher_type_lower = voucher_type.lower()
        amount = _amount(getattr(record, "amount", None))
        txn_date = getattr(record, "transaction_date", None)
        txn_date_text = _date_string(txn_date)

        combined_text = " ".join([ledger_lower, description_lower, voucher_type_lower])

        if document_id:
            voucher_index[document_id.lower()].append(record)

        if ledger_name and amount is not None and txn_date_text:
            ledger_amount_date_index[(ledger_lower, round(abs(amount), 2), txn_date_text)].append(record)

        if not document_id:
            findings.append(_finding(
                record,
                "missing_ledger_voucher_number",
                "medium",
                "Missing ledger voucher/reference number",
                "Ledger entry has no voucher, document, reference, or journal number.",
            ))

        if not ledger_name:
            findings.append(_finding(
                record,
                "missing_ledger_name",
                "medium",
                "Missing ledger/account name",
                "Ledger entry does not identify the ledger, account, party, cost center, or G/L account.",
            ))

        if amount is None:
            findings.append(_finding(
                record,
                "missing_ledger_amount",
                "high",
                "Missing ledger amount",
                "Ledger entry does not contain a usable amount.",
            ))
            continue

        if abs(amount) >= 100000:
            findings.append(_finding(
                record,
                "high_value_ledger_entry",
                "high",
                "High-value ledger entry",
                "Ledger entry is above ₹1,00,000 and should be verified with supporting documents and approval trail.",
                {"amount": amount},
            ))

        if abs(amount) >= 1000 and abs(amount) % 1000 == 0:
            findings.append(_finding(
                record,
                "round_number_ledger_entry",
                "low",
                "Round-number ledger entry",
                "Ledger entry has a round amount. This can be normal, but should be reviewed for manual or estimated postings.",
                {"amount": amount},
            ))

        if _is_year_end(txn_date):
            findings.append(_finding(
                record,
                "year_end_ledger_entry",
                "medium",
                "Year-end ledger entry",
                "Ledger entry was posted near financial year end. Review cut-off, provisioning, reversal, and supporting documents.",
                {"transaction_date": txn_date_text},
            ))

        if any(keyword in combined_text for keyword in SUSPENSE_KEYWORDS):
            findings.append(_finding(
                record,
                "suspense_or_temporary_account_activity",
                "high",
                "Suspense/temporary account activity",
                "Ledger entry appears to involve suspense, temporary, dummy, unknown, or unclassified accounts.",
                {"matched_text": combined_text},
            ))

        if any(keyword in combined_text for keyword in MANUAL_ENTRY_KEYWORDS):
            findings.append(_finding(
                record,
                "manual_or_journal_entry",
                "medium",
                "Manual/journal entry indicator",
                "Ledger entry appears to be a manual, journal, adjustment, provision, or rectification posting.",
                {"voucher_type": voucher_type, "description": description},
            ))

        if any(keyword in combined_text for keyword in CASH_KEYWORDS) and abs(amount) >= 10000:
            findings.append(_finding(
                record,
                "high_value_cash_ledger_activity",
                "high",
                "High-value cash ledger activity",
                "Cash or petty-cash ledger activity above ₹10,000 should be reviewed for tax/audit sensitivity and supporting documents.",
                {"amount": amount},
            ))

        if any(keyword in combined_text for keyword in LOAN_ADVANCE_KEYWORDS) and abs(amount) >= 50000:
            findings.append(_finding(
                record,
                "loan_or_advance_movement",
                "medium",
                "Loan/advance/deposit ledger movement",
                "Ledger entry appears to involve loans, advances, deposits, or unsecured loan movement. Verify agreement, confirmation, and classification.",
                {"amount": amount},
            ))

        if not description or len(description.strip()) < 4:
            findings.append(_finding(
                record,
                "missing_or_weak_ledger_narration",
                "low",
                "Missing or weak ledger narration",
                "Ledger entry has no meaningful narration, text, or description.",
            ))

    for voucher, duplicate_records in voucher_index.items():
        if len(duplicate_records) > 1:
            first = duplicate_records[0]
            findings.append(_finding(
                first,
                "duplicate_ledger_voucher_reference",
                "medium",
                "Duplicate ledger voucher/reference",
                "Same voucher/reference appears more than once in ledger data. Review whether this is valid multi-line accounting or duplicate posting.",
                {
                    "voucher": voucher,
                    "duplicate_count": len(duplicate_records),
                    "source_rows": [getattr(record, "source_row", None) for record in duplicate_records],
                    "record_ids": [getattr(record, "id", None) for record in duplicate_records],
                },
            ))

    for key, repeated_records in ledger_amount_date_index.items():
        if len(repeated_records) > 1:
            first = repeated_records[0]
            ledger_name, amount, txn_date = key
            findings.append(_finding(
                first,
                "repeated_ledger_pattern",
                "medium",
                "Repeated ledger amount/date pattern",
                "Same ledger, same amount, and same date appears multiple times. Review for duplicate posting or repeated adjustment.",
                {
                    "ledger_name": ledger_name,
                    "amount": amount,
                    "transaction_date": txn_date,
                    "duplicate_count": len(repeated_records),
                    "source_rows": [getattr(record, "source_row", None) for record in repeated_records],
                },
            ))

    return findings
''',
encoding="utf-8",
)

# ----------------------------------------------------
# 2. Patch runner.py
# ----------------------------------------------------

runner = RUNNER.read_text(encoding="utf-8")

if "from app.services.audit_engine.checks.ledger_scrutiny_checks import run_ledger_scrutiny_checks" not in runner:
    if "from app.services.audit_engine.checks.gst_reco_checks import run_gst_reconciliation_checks" in runner:
        runner = runner.replace(
            "from app.services.audit_engine.checks.gst_reco_checks import run_gst_reconciliation_checks",
            "from app.services.audit_engine.checks.gst_reco_checks import run_gst_reconciliation_checks\nfrom app.services.audit_engine.checks.ledger_scrutiny_checks import run_ledger_scrutiny_checks",
        )
    else:
        runner = runner.replace(
            "from app.services.audit_engine.checks.sales_checks import run_sales_checks",
            "from app.services.audit_engine.checks.sales_checks import run_sales_checks\nfrom app.services.audit_engine.checks.ledger_scrutiny_checks import run_ledger_scrutiny_checks",
        )

if "LEDGER_SCRUTINY_FILE_TYPES" not in runner:
    marker = '''LEDGER_FILE_TYPES = {
    "cash_bank_ledger",
    "bank_ledger",
    "ledger",
    "tally_bank_book",
}
'''
    addition = marker + '''

LEDGER_SCRUTINY_FILE_TYPES = {
    "ledger",
    "expense_ledger",
    "tally_ledger_vouchers",
    "sap_gl_line_items",
    "cash_bank_ledger",
    "bank_ledger",
    "trial_balance",
}
'''
    if marker in runner:
        runner = runner.replace(marker, addition)
    else:
        runner += '''

LEDGER_SCRUTINY_FILE_TYPES = {
    "ledger",
    "expense_ledger",
    "tally_ledger_vouchers",
    "sap_gl_line_items",
    "cash_bank_ledger",
    "bank_ledger",
    "trial_balance",
}
'''

if "def run_ledger_scrutiny" not in runner:
    ledger_function = r'''

def run_ledger_scrutiny(workspace_id: int, db: Session) -> dict:
    parse_summary = parse_workspace_files(workspace_id, db, force_reparse=False)

    records = (
        db.query(ExtractedRecord)
        .filter(ExtractedRecord.workspace_id == workspace_id)
        .all()
    )

    ledger_records = [
        record for record in records
        if record.record_type.lower() in LEDGER_SCRUTINY_FILE_TYPES
    ]

    clear_findings(workspace_id, db)

    if not ledger_records:
        audit_run = AuditRun(
            workspace_id=workspace_id,
            audit_type="ledger_scrutiny",
            status="completed_with_limitations",
            total_records=len(records),
            checked_records=0,
            issues_found=0,
            unchecked_records=len(records),
        )
        db.add(audit_run)
        db.commit()
        db.refresh(audit_run)

        return {
            "audit_run_id": audit_run.id,
            "status": audit_run.status,
            "message": "Ledger scrutiny needs ledger-style records such as Tally Ledger Vouchers, SAP G/L Line Items, Expense Ledger, or Trial Balance.",
            "parse_summary": parse_summary,
            "coverage": {
                "total_records": len(records),
                "ledger_records_checked": 0,
                "unchecked_records": len(records),
                "issues_found": 0,
            },
        }

    finding_payloads = run_ledger_scrutiny_checks(ledger_records)

    audit_run = AuditRun(
        workspace_id=workspace_id,
        audit_type="ledger_scrutiny",
        status="completed",
        total_records=len(ledger_records),
        checked_records=len(ledger_records),
        issues_found=len(finding_payloads),
        unchecked_records=max(0, len(records) - len(ledger_records)),
    )

    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)

    save_findings(workspace_id, audit_run.id, finding_payloads, db)

    return {
        "audit_run_id": audit_run.id,
        "status": audit_run.status,
        "message": "Ledger scrutiny completed using uploaded ledger records",
        "parse_summary": parse_summary,
        "coverage": {
            "total_records": len(records),
            "ledger_records_checked": len(ledger_records),
            "unchecked_records": audit_run.unchecked_records,
            "issues_found": len(finding_payloads),
            "risk_counts": risk_counts(finding_payloads),
        },
    }
'''
    if "\n\ndef run_gst_reconciliation" in runner:
        runner = runner.replace("\n\ndef run_gst_reconciliation", ledger_function + "\n\ndef run_gst_reconciliation")
    elif "\n\ndef run_bank_reconciliation" in runner:
        runner = runner.replace("\n\ndef run_bank_reconciliation", ledger_function + "\n\ndef run_bank_reconciliation")
    else:
        runner += ledger_function

RUNNER.write_text(runner, encoding="utf-8")

# ----------------------------------------------------
# 3. Patch audit_runs.py
# ----------------------------------------------------

routes = AUDIT_RUNS.read_text(encoding="utf-8")

if "run_ledger_scrutiny" not in routes:
    if "run_gst_reconciliation," in routes:
        routes = routes.replace(
            "run_gst_reconciliation,",
            "run_gst_reconciliation,\n    run_ledger_scrutiny,",
        )
    else:
        routes = routes.replace(
            "run_expense_audit,",
            "run_expense_audit,\n    run_ledger_scrutiny,",
        )

if 'run-ledger-scrutiny' not in routes:
    endpoint = r'''

@router.post("/{workspace_id}/run-ledger-scrutiny")
def run_real_ledger_scrutiny(workspace_id: int, db: Session = Depends(get_db)):
    try:
        return run_ledger_scrutiny(workspace_id=workspace_id, db=db)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Ledger scrutiny failed: {str(exc)}")
'''
    if '\n\n@router.post("/{workspace_id}/run-gst-reconciliation")' in routes:
        routes = routes.replace(
            '\n\n@router.post("/{workspace_id}/run-gst-reconciliation")',
            endpoint + '\n\n@router.post("/{workspace_id}/run-gst-reconciliation")',
        )
    else:
        routes = routes.replace(
            '\n\n@router.post("/{workspace_id}/run-bank-reconciliation")',
            endpoint + '\n\n@router.post("/{workspace_id}/run-bank-reconciliation")',
        )

AUDIT_RUNS.write_text(routes, encoding="utf-8")

# ----------------------------------------------------
# 4. Patch frontend
# ----------------------------------------------------

page = FRONTEND.read_text(encoding="utf-8")

if "ledger_records_checked?: number;" not in page:
    page = page.replace(
        "checked_records?: number;",
        "checked_records?: number;\n    ledger_records_checked?: number;",
    )

if "async function runLedgerScrutiny()" not in page:
    ledger_fn = r'''
  async function runLedgerScrutiny() {
    setBusy(true);
    setStatusMessage("Running ledger scrutiny...");

    try {
      const res = await api.post(`/audit-runs/${workspaceId}/run-ledger-scrutiny`);
      setAuditSummary(res.data);
      setSelectedAuditRunId(res.data.audit_run_id);
      setStatusMessage("Ledger scrutiny completed.");
      await refreshAll();
      setActiveSection("findings");
    } catch {
      setStatusMessage("Ledger scrutiny failed.");
    } finally {
      setBusy(false);
    }
  }

'''
    if "  async function runGstReconciliation()" in page:
        page = page.replace("  async function runGstReconciliation()", ledger_fn + "  async function runGstReconciliation()")
    else:
        page = page.replace("  async function runBankReconciliation()", ledger_fn + "  async function runBankReconciliation()")

if "runLedgerScrutiny={runLedgerScrutiny}" not in page:
    page = page.replace(
        "runExpenseAudit={runExpenseAudit}\n                runGstReconciliation={runGstReconciliation}",
        "runExpenseAudit={runExpenseAudit}\n                runLedgerScrutiny={runLedgerScrutiny}\n                runGstReconciliation={runGstReconciliation}",
    )
    page = page.replace(
        "runExpenseAudit={runExpenseAudit}\n                runBankReconciliation={runBankReconciliation}",
        "runExpenseAudit={runExpenseAudit}\n                runLedgerScrutiny={runLedgerScrutiny}\n                runBankReconciliation={runBankReconciliation}",
    )

if "runLedgerScrutiny," not in page:
    page = page.replace(
        "runExpenseAudit,\n  runGstReconciliation,",
        "runExpenseAudit,\n  runLedgerScrutiny,\n  runGstReconciliation,",
    )
    page = page.replace(
        "runExpenseAudit,\n  runBankReconciliation,",
        "runExpenseAudit,\n  runLedgerScrutiny,\n  runBankReconciliation,",
    )

if "runLedgerScrutiny: () => void;" not in page:
    page = page.replace(
        "runExpenseAudit: () => void;\n  runGstReconciliation: () => void;",
        "runExpenseAudit: () => void;\n  runLedgerScrutiny: () => void;\n  runGstReconciliation: () => void;",
    )
    page = page.replace(
        "runExpenseAudit: () => void;\n  runBankReconciliation: () => void;",
        "runExpenseAudit: () => void;\n  runLedgerScrutiny: () => void;\n  runBankReconciliation: () => void;",
    )

if 'key: "ledger"' not in page:
    expense_option = r'''    {
      key: "expense",
      label: "Expense Audit",
      description: "Checks expense ledgers for duplicate vouchers, high-value spends, cash expenses, weak narration, and discretionary spend.",
      run: runExpenseAudit,
    },'''
    ledger_option = expense_option + r'''
    {
      key: "ledger",
      label: "Ledger Scrutiny",
      description: "Reviews ledger-style exports for suspense accounts, manual journals, year-end entries, cash risks, loans/advances, and repeated posting patterns.",
      run: runLedgerScrutiny,
    },'''
    page = page.replace(expense_option, ledger_option)

if 'if (type === "ledger_scrutiny") return "Ledger Scrutiny";' not in page:
    page = page.replace(
        'if (type === "gst_reconciliation") return "GST Reconciliation";',
        'if (type === "ledger_scrutiny") return "Ledger Scrutiny";\n  if (type === "gst_reconciliation") return "GST Reconciliation";',
    )
    page = page.replace(
        'if (type === "bank_reconciliation") return "Bank Reconciliation";',
        'if (type === "ledger_scrutiny") return "Ledger Scrutiny";\n  if (type === "bank_reconciliation") return "Bank Reconciliation";',
    )

# checked records should understand ledger_records_checked
page = page.replace(
    "coverageSource?.expense_records_checked ??\n    0;",
    "coverageSource?.expense_records_checked ??\n    coverageSource?.ledger_records_checked ??\n    0;",
)

# Infer ledger module
page = re.sub(
    r"function inferRecommendedAuditModule\(files\?: UploadedFile\[\]\) \{[\s\S]*?\n\}",
    r'''function inferRecommendedAuditModule(files?: UploadedFile[]) {
  if (!files || !files.length) return "purchase";

  const candidates = files
    .filter((file) => file.status === "parsed" || file.status === "uploaded")
    .sort((a, b) => b.id - a.id);

  const latest = candidates[0] ?? files[files.length - 1];
  const type = latest?.file_type?.toLowerCase() ?? "";

  if (type.includes("gstr") || type.includes("gst_2b") || type.includes("gstr_2b")) return "gst";
  if (type.includes("sales") || type.includes("customer")) return "sales";
  if (type.includes("expense")) return "expense";
  if (type.includes("trial_balance") || type.includes("sap_gl") || type.includes("ledger_vouchers")) return "ledger";
  if (type.includes("bank") || type.includes("cash_bank") || type.includes("tally_bank")) return "bank";
  if (type.includes("purchase") || type.includes("vendor")) return "purchase";

  return "purchase";
}''',
    page,
)

FRONTEND.write_text(page, encoding="utf-8")

# ----------------------------------------------------
# 5. Sample ledger scrutiny data
# ----------------------------------------------------

(SAMPLE_DIR / "ledger_scrutiny_edge_cases.csv").write_text(
"""Voucher No,Date,Ledger Name,Narration,Debit,Credit,Voucher Type
JV-001,01-04-2025,Office Expense,Normal office expense,12000,0,Journal
JV-002,15-04-2025,Suspense Account,Temporary adjustment pending classification,50000,0,Journal
JV-003,20-04-2025,Petty Cash,Cash paid for repairs,25000,0,Payment
JV-004,31-03-2026,Provision for Expenses,Year end provision entry,150000,0,Journal
JV-005,31-03-2026,Director Loan,Unsecured loan movement,200000,0,Journal
JV-006,10-05-2025,,Missing ledger name,10000,0,Journal
,12-05-2025,Repairs,Missing voucher number,8000,0,Payment
JV-008,14-05-2025,Misc Expense,,3000,0,Journal
JV-009,20-05-2025,Unclassified Expense,Unknown classification entry,18000,0,Journal
JV-010,22-05-2025,Office Expense,Repeated entry pattern,7000,0,Journal
JV-011,22-05-2025,Office Expense,Repeated entry pattern,7000,0,Journal
JV-011,22-05-2025,Office Expense,Duplicate voucher reference,7000,0,Journal
""",
encoding="utf-8",
)

print("Ledger Scrutiny module applied.")
print("Updated:")
print(f"- {CHECKS_DIR / 'ledger_scrutiny_checks.py'}")
print(f"- {RUNNER}")
print(f"- {AUDIT_RUNS}")
print(f"- {FRONTEND}")
print(f"- {SAMPLE_DIR / 'ledger_scrutiny_edge_cases.csv'}")