from pathlib import Path

ROOT = Path(r"D:\1Workspace\AuditPal")

RUNNER = ROOT / "backend" / "app" / "services" / "audit_engine" / "runner.py"
AUDIT_RUNS_ROUTE = ROOT / "backend" / "app" / "api" / "routes" / "audit_runs.py"
CHECKS_DIR = ROOT / "backend" / "app" / "services" / "audit_engine" / "checks"
FRONTEND_PAGE = ROOT / "frontend" / "src" / "app" / "workspaces" / "[id]" / "page.tsx"
SAMPLE_DIR = ROOT / "sample-data"

CHECKS_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------
# 1. Sales audit checks
# ----------------------------------------------------

(CHECKS_DIR / "sales_checks.py").write_text(
r'''from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


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


def _record_description(record):
    return (
        _raw(record, "description", "narration", "Narration", "Description", "Particulars", "Text")
        or getattr(record, "description", None)
        or ""
    )


def _gstin_valid(gstin):
    gstin = _norm(gstin).upper()
    if not gstin:
        return False
    if len(gstin) != 15:
        return False
    if not gstin[:2].isdigit():
        return False
    if not gstin[2:12].isalnum():
        return False
    return True


def _finding(record, finding_type, risk_level, title, description, extra=None):
    evidence = {
        "record_id": getattr(record, "id", None),
        "source_row": getattr(record, "source_row", None),
        "document_id": getattr(record, "document_id", None),
        "party_name": getattr(record, "party_name", None),
        "transaction_date": _date_string(getattr(record, "transaction_date", None)),
        "amount": getattr(record, "amount", None),
        "gstin": getattr(record, "gstin", None),
    }

    if extra:
        evidence.update(extra)

    return {
        "source_record_id": getattr(record, "id", None),
        "finding_type": finding_type,
        "risk_level": risk_level,
        "title": title,
        "description": description,
        "evidence": evidence,
    }


def run_sales_checks(records):
    findings = []

    invoice_index = defaultdict(list)
    customer_amount_date_index = defaultdict(list)

    for record in records:
        document_id = _norm(getattr(record, "document_id", None))
        party_name = _norm(getattr(record, "party_name", None))
        txn_date = getattr(record, "transaction_date", None)
        txn_date_text = _date_string(txn_date)
        amount = _amount(getattr(record, "amount", None))
        gstin = _norm(getattr(record, "gstin", None))
        description = _record_description(record)
        description_lower = _lower(description)

        if document_id:
            invoice_index[document_id.lower()].append(record)

        if party_name and amount is not None and txn_date_text:
            key = (party_name.lower(), round(abs(amount), 2), txn_date_text)
            customer_amount_date_index[key].append(record)

        if not document_id:
            findings.append(_finding(
                record,
                "missing_sales_invoice_number",
                "high",
                "Missing sales invoice number",
                "Sales entry does not have an invoice, bill, voucher, or reference number.",
            ))

        if not party_name:
            findings.append(_finding(
                record,
                "missing_customer_name",
                "medium",
                "Missing customer/party name",
                "Sales entry does not identify the customer or party.",
            ))

        if amount is None:
            findings.append(_finding(
                record,
                "missing_sales_amount",
                "high",
                "Missing sales amount",
                "Sales entry does not contain a usable amount.",
            ))
            continue

        if amount <= 0:
            findings.append(_finding(
                record,
                "non_positive_sales_amount",
                "high",
                "Zero or negative sales amount",
                "Sales entry has zero or negative value. Check for cancellation, credit note, or incorrect posting.",
                {"amount": amount},
            ))

        if abs(amount) >= 100000:
            findings.append(_finding(
                record,
                "high_value_sales_invoice",
                "medium",
                "High-value sales invoice",
                "Sales invoice is above ₹1,00,000 and should be verified for billing, GST, and collection trail.",
                {"amount": amount},
            ))

        if abs(amount) >= 1000 and abs(amount) % 1000 == 0:
            findings.append(_finding(
                record,
                "round_number_sales",
                "low",
                "Round-number sales invoice",
                "Sales amount is a round number. This is not necessarily wrong but should be reviewed for estimated/manual billing.",
                {"amount": amount},
            ))

        if not gstin:
            findings.append(_finding(
                record,
                "missing_customer_gstin",
                "medium",
                "Missing customer GSTIN",
                "Customer GSTIN is missing. This may be acceptable for B2C sales but should be reviewed for B2B invoices.",
            ))
        elif not _gstin_valid(gstin):
            findings.append(_finding(
                record,
                "invalid_customer_gstin",
                "high",
                "Invalid customer GSTIN format",
                "Customer GSTIN does not match the expected 15-character Indian GSTIN pattern.",
                {"gstin": gstin},
            ))

        if _is_year_end(txn_date):
            findings.append(_finding(
                record,
                "year_end_sales_invoice",
                "medium",
                "Year-end sales invoice",
                "Sales invoice was recorded near financial year end. Check cut-off, dispatch/service completion, and revenue recognition.",
                {"transaction_date": txn_date_text},
            ))

        if any(word in description_lower for word in ["cancel", "cancelled", "void"]):
            findings.append(_finding(
                record,
                "cancelled_sales_indicator",
                "medium",
                "Cancellation indicator in sales narration",
                "Sales narration suggests a cancelled or void invoice. Verify whether the entry should remain in revenue.",
                {"description": description},
            ))

        if any(word in description_lower for word in ["credit note", "sales return", "return"]):
            findings.append(_finding(
                record,
                "sales_return_or_credit_note_indicator",
                "medium",
                "Sales return / credit note indicator",
                "Narration suggests a sales return or credit note. Verify adjustment, GST impact, and linkage to original invoice.",
                {"description": description},
            ))

    for invoice, duplicate_records in invoice_index.items():
        if len(duplicate_records) > 1:
            for record in duplicate_records:
                findings.append(_finding(
                    record,
                    "duplicate_sales_invoice",
                    "high",
                    "Duplicate sales invoice number",
                    "Same sales invoice/reference number appears more than once.",
                    {"invoice": invoice, "duplicate_count": len(duplicate_records)},
                ))

    for key, repeated_records in customer_amount_date_index.items():
        if len(repeated_records) > 1:
            customer_name, amount, txn_date = key
            for record in repeated_records:
                findings.append(_finding(
                    record,
                    "repeated_sales_pattern",
                    "medium",
                    "Repeated same-customer same-amount sale",
                    "Same customer, same amount, and same date appears multiple times. Check for duplicate billing.",
                    {
                        "customer_name": customer_name,
                        "amount": amount,
                        "transaction_date": txn_date,
                        "duplicate_count": len(repeated_records),
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

if "from app.services.audit_engine.checks.sales_checks import run_sales_checks" not in runner:
    runner = runner.replace(
        "from app.services.audit_engine.checks.expense_checks import run_expense_checks",
        "from app.services.audit_engine.checks.expense_checks import run_expense_checks\nfrom app.services.audit_engine.checks.sales_checks import run_sales_checks",
    )

if "SALES_FILE_TYPES" not in runner:
    marker = '''EXPENSE_FILE_TYPES = {
    "expense_ledger",
    "expenses",
    "tally_ledger_vouchers",
    "sap_gl_line_items",
    "tally_purchase_register",
}
'''
    addition = marker + '''

SALES_FILE_TYPES = {
    "sales_register",
    "generic_sales_register",
    "sales",
    "sap_customer_line_items",
}
'''
    if marker in runner:
        runner = runner.replace(marker, addition)
    else:
        runner = runner.replace(
            "BANK_FILE_TYPES = {",
            'SALES_FILE_TYPES = {\n    "sales_register",\n    "generic_sales_register",\n    "sales",\n    "sap_customer_line_items",\n}\n\nBANK_FILE_TYPES = {',
        )

if "def run_sales_audit" not in runner:
    sales_function = r'''

def run_sales_audit(workspace_id: int, db: Session) -> dict:
    parse_summary = parse_workspace_files(workspace_id, db, force_reparse=False)

    records = (
        db.query(ExtractedRecord)
        .filter(ExtractedRecord.workspace_id == workspace_id)
        .all()
    )

    sales_records = [
        record for record in records
        if record.record_type.lower() in SALES_FILE_TYPES
    ]

    clear_findings(workspace_id, db)

    if not sales_records:
        audit_run = AuditRun(
            workspace_id=workspace_id,
            audit_type="sales_audit",
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
            "message": "No sales records found. Upload a file tagged as generic_sales_register or sap_customer_line_items.",
            "parse_summary": parse_summary,
            "coverage": {
                "total_records": len(records),
                "sales_records_checked": 0,
                "unchecked_records": len(records),
                "issues_found": 0,
            },
        }

    finding_payloads = run_sales_checks(sales_records)

    audit_run = AuditRun(
        workspace_id=workspace_id,
        audit_type="sales_audit",
        status="completed",
        total_records=len(sales_records),
        checked_records=len(sales_records),
        issues_found=len(finding_payloads),
        unchecked_records=max(0, len(records) - len(sales_records)),
    )

    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)

    save_findings(workspace_id, audit_run.id, finding_payloads, db)

    return {
        "audit_run_id": audit_run.id,
        "status": audit_run.status,
        "message": "Sales audit completed using uploaded sales records",
        "parse_summary": parse_summary,
        "coverage": {
            "total_records": len(records),
            "sales_records_checked": len(sales_records),
            "unchecked_records": audit_run.unchecked_records,
            "issues_found": len(finding_payloads),
            "risk_counts": risk_counts(finding_payloads),
        },
    }
'''
    if "\n\ndef run_expense_audit" in runner:
        runner = runner.replace("\n\ndef run_expense_audit", sales_function + "\n\ndef run_expense_audit")
    else:
        runner = runner.replace("\n\ndef run_bank_reconciliation", sales_function + "\n\ndef run_bank_reconciliation")

RUNNER.write_text(runner, encoding="utf-8")

# ----------------------------------------------------
# 3. Patch audit_runs.py
# ----------------------------------------------------

route = AUDIT_RUNS_ROUTE.read_text(encoding="utf-8")

if "run_sales_audit" not in route:
    route = route.replace(
        "from app.services.audit_engine.runner import run_bank_reconciliation, run_expense_audit, run_purchase_audit",
        "from app.services.audit_engine.runner import run_bank_reconciliation, run_expense_audit, run_purchase_audit, run_sales_audit",
    )
    route = route.replace(
        "from app.services.audit_engine.runner import run_bank_reconciliation, run_purchase_audit",
        "from app.services.audit_engine.runner import run_bank_reconciliation, run_expense_audit, run_purchase_audit, run_sales_audit",
    )

if 'run-sales-audit' not in route:
    endpoint = r'''

@router.post("/{workspace_id}/run-sales-audit")
def run_real_sales_audit(workspace_id: int, db: Session = Depends(get_db)):
    try:
        return run_sales_audit(workspace_id=workspace_id, db=db)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Sales audit failed: {str(exc)}")
'''
    route = route.replace("\n\n@router.post(\"/{workspace_id}/run-expense-audit\")", endpoint + "\n\n@router.post(\"/{workspace_id}/run-expense-audit\")")

AUDIT_RUNS_ROUTE.write_text(route, encoding="utf-8")

# ----------------------------------------------------
# 4. Patch frontend workspace page
# ----------------------------------------------------

page = FRONTEND_PAGE.read_text(encoding="utf-8")

if "async function runSalesAudit()" not in page:
    insertion = r'''
  async function runSalesAudit() {
    setBusy(true);
    setStatusMessage("Running sales audit...");

    try {
      const res = await api.post(`/audit-runs/${workspaceId}/run-sales-audit`);
      setAuditSummary(res.data);
      setStatusMessage("Sales audit completed.");
      await refreshAll();
      setActiveSection("findings");
    } catch {
      setStatusMessage("Sales audit failed.");
    } finally {
      setBusy(false);
    }
  }

'''
    page = page.replace("  async function runExpenseAudit()", insertion + "  async function runExpenseAudit()")

if "runSalesAudit={runSalesAudit}" not in page:
    page = page.replace(
        "runPurchaseAudit={runPurchaseAudit}\n                runExpenseAudit={runExpenseAudit}",
        "runPurchaseAudit={runPurchaseAudit}\n                runSalesAudit={runSalesAudit}\n                runExpenseAudit={runExpenseAudit}",
    )

if "runSalesAudit," not in page:
    page = page.replace(
        "runPurchaseAudit,\n  runExpenseAudit,",
        "runPurchaseAudit,\n  runSalesAudit,\n  runExpenseAudit,",
    )

if "runSalesAudit: () => void;" not in page:
    page = page.replace(
        "runPurchaseAudit: () => void;\n  runExpenseAudit: () => void;",
        "runPurchaseAudit: () => void;\n  runSalesAudit: () => void;\n  runExpenseAudit: () => void;",
    )

if "Run Sales Audit" not in page:
    page = page.replace(
        '''            <button
              onClick={runExpenseAudit}
              disabled={busy}
              className="w-full rounded-xl border border-[#B4D6C1] bg-white px-5 py-3 font-medium text-[#17352E] transition hover:bg-[#EDF6F0] disabled:opacity-50"
            >
              Run Expense Audit
            </button>''',
        '''            <button
              onClick={runSalesAudit}
              disabled={busy}
              className="w-full rounded-xl border border-[#B4D6C1] bg-white px-5 py-3 font-medium text-[#17352E] transition hover:bg-[#EDF6F0] disabled:opacity-50"
            >
              Run Sales Audit
            </button>

            <button
              onClick={runExpenseAudit}
              disabled={busy}
              className="w-full rounded-xl border border-[#B4D6C1] bg-white px-5 py-3 font-medium text-[#17352E] transition hover:bg-[#EDF6F0] disabled:opacity-50"
            >
              Run Expense Audit
            </button>''',
    )

FRONTEND_PAGE.write_text(page, encoding="utf-8")

# ----------------------------------------------------
# 5. Sample sales data
# ----------------------------------------------------

(SAMPLE_DIR / "sales_register_edge_cases.csv").write_text(
"""Invoice No,Date,Customer Name,GSTIN,Narration,Amount
S-001,01-04-2025,ABC Retailers,27ABCDE1234F1Z5,Regular B2B sale,11800
S-002,05-04-2025,Walk-in Customer,,B2C counter sale,5000
S-003,10-04-2025,XYZ Stores,INVALIDGSTIN,Invalid GSTIN example,25000
S-004,15-04-2025,Large Customer,27ABCDE1234F1Z5,High value sale,150000
S-004,15-04-2025,Large Customer,27ABCDE1234F1Z5,Duplicate invoice number,150000
,20-04-2025,No Invoice Customer,27ABCDE1234F1Z5,Missing invoice no,12000
S-006,31-03-2026,Year End Customer,27ABCDE1234F1Z5,Year end revenue invoice,90000
S-007,22-05-2025,Return Customer,27ABCDE1234F1Z5,Sales return / credit note adjustment,-8000
S-008,25-05-2025,Cancelled Customer,27ABCDE1234F1Z5,Cancelled invoice retained in sales,30000
S-009,28-05-2025,Repeat Customer,27ABCDE1234F1Z5,Repeated same amount sale,10000
S-010,28-05-2025,Repeat Customer,27ABCDE1234F1Z5,Repeated same amount sale,10000
""",
encoding="utf-8",
)

print("Sales Audit module update applied.")
print("Updated:")
print(f"- {CHECKS_DIR / 'sales_checks.py'}")
print(f"- {RUNNER}")
print(f"- {AUDIT_RUNS_ROUTE}")
print(f"- {FRONTEND_PAGE}")
print(f"- {SAMPLE_DIR / 'sales_register_edge_cases.csv'}")