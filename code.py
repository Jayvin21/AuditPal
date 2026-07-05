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
# 1. GST reconciliation checks
# ----------------------------------------------------

(CHECKS_DIR / "gst_reco_checks.py").write_text(
r'''from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def _norm(value):
    if value is None:
        return ""
    return str(value).strip()


def _clean_id(value):
    return _norm(value).replace(" ", "").replace("-", "").replace("/", "").lower()


def _clean_gstin(value):
    return _norm(value).upper().replace(" ", "")


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


def _key(record):
    doc = _clean_id(getattr(record, "document_id", None))
    gstin = _clean_gstin(getattr(record, "gstin", None))
    return (doc, gstin)


def _display(record):
    return {
        "record_id": getattr(record, "id", None),
        "source_row": getattr(record, "source_row", None),
        "document_id": getattr(record, "document_id", None),
        "party_name": getattr(record, "party_name", None),
        "transaction_date": _date_string(getattr(record, "transaction_date", None)),
        "amount": getattr(record, "amount", None),
        "gstin": getattr(record, "gstin", None),
        "record_type": getattr(record, "record_type", None),
    }


def _title(base, record):
    bits = []
    doc = _norm(getattr(record, "document_id", None))
    party = _norm(getattr(record, "party_name", None))
    gstin = _norm(getattr(record, "gstin", None))

    if doc:
        bits.append(doc)
    if party:
        bits.append(party)
    if gstin:
        bits.append(gstin)

    if not bits:
        return base

    return f"{base} — {' · '.join(bits[:3])}"


def _finding(record, finding_type, risk_level, title, description, extra=None):
    evidence = _display(record)
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


def _group_finding(records, finding_type, risk_level, title, description, extra=None):
    first = records[0]
    evidence = {
        "duplicate_count": len(records),
        "records": [_display(record) for record in records],
        "document_id": getattr(first, "document_id", None),
        "party_name": getattr(first, "party_name", None),
        "gstin": getattr(first, "gstin", None),
        "source_rows": [getattr(record, "source_row", None) for record in records],
    }

    if extra:
        evidence.update(extra)

    return {
        "source_record_id": getattr(first, "id", None),
        "finding_type": finding_type,
        "risk_level": risk_level,
        "title": _title(title, first),
        "description": description,
        "evidence": evidence,
    }


def run_gst_reconciliation_checks(book_records, gstr_2b_records, amount_tolerance=5.0):
    findings = []

    book_index = defaultdict(list)
    portal_index = defaultdict(list)

    for record in book_records:
        document_id = _norm(getattr(record, "document_id", None))
        gstin = _norm(getattr(record, "gstin", None))
        amount = _amount(getattr(record, "amount", None))

        if not document_id:
            findings.append(_finding(
                record,
                "books_missing_invoice_number",
                "high",
                "Books invoice missing invoice number",
                "Books purchase/ITC entry does not have a usable invoice number, so it cannot be reliably matched with GSTR-2B.",
            ))

        if not gstin:
            findings.append(_finding(
                record,
                "books_missing_supplier_gstin",
                "high",
                "Books invoice missing supplier GSTIN",
                "Books purchase/ITC entry does not have supplier GSTIN, so GST reconciliation is weak.",
            ))

        if amount is None:
            findings.append(_finding(
                record,
                "books_missing_taxable_or_invoice_amount",
                "medium",
                "Books invoice missing amount",
                "Books purchase/ITC entry does not have a usable amount for GST reconciliation.",
            ))

        key = _key(record)
        if key != ("", ""):
            book_index[key].append(record)

    for record in gstr_2b_records:
        document_id = _norm(getattr(record, "document_id", None))
        gstin = _norm(getattr(record, "gstin", None))
        amount = _amount(getattr(record, "amount", None))

        if not document_id:
            findings.append(_finding(
                record,
                "gstr_2b_missing_invoice_number",
                "medium",
                "GSTR-2B row missing invoice number",
                "GSTR-2B row does not have a usable invoice number.",
            ))

        if not gstin:
            findings.append(_finding(
                record,
                "gstr_2b_missing_supplier_gstin",
                "medium",
                "GSTR-2B row missing supplier GSTIN",
                "GSTR-2B row does not have a usable supplier GSTIN.",
            ))

        if amount is None:
            findings.append(_finding(
                record,
                "gstr_2b_missing_taxable_or_invoice_amount",
                "medium",
                "GSTR-2B row missing amount",
                "GSTR-2B row does not have a usable taxable/invoice amount.",
            ))

        key = _key(record)
        if key != ("", ""):
            portal_index[key].append(record)

    for key, records in book_index.items():
        if len(records) > 1:
            findings.append(_group_finding(
                records,
                "duplicate_invoice_in_books",
                "high",
                "Duplicate GST invoice in books",
                "Same invoice number and supplier GSTIN appears multiple times in books. Check duplicate ITC booking.",
                {"match_key": key},
            ))

    for key, records in portal_index.items():
        if len(records) > 1:
            findings.append(_group_finding(
                records,
                "duplicate_invoice_in_gstr_2b",
                "medium",
                "Duplicate GST invoice in GSTR-2B",
                "Same invoice number and supplier GSTIN appears multiple times in GSTR-2B export.",
                {"match_key": key},
            ))

    for key, books in book_index.items():
        if key not in portal_index:
            for record in books:
                findings.append(_finding(
                    record,
                    "itc_in_books_not_in_gstr_2b",
                    "high",
                    "ITC in books not found in GSTR-2B",
                    "Purchase/ITC entry exists in books but matching supplier GSTIN and invoice number was not found in GSTR-2B.",
                    {"match_key": key},
                ))
            continue

        portal_records = portal_index[key]

        for book_record in books:
            book_amount = _amount(getattr(book_record, "amount", None))
            if book_amount is None:
                continue

            closest_portal = None
            closest_diff = None

            for portal_record in portal_records:
                portal_amount = _amount(getattr(portal_record, "amount", None))
                if portal_amount is None:
                    continue

                diff = abs(abs(book_amount) - abs(portal_amount))

                if closest_diff is None or diff < closest_diff:
                    closest_diff = diff
                    closest_portal = portal_record

            if closest_portal is not None and closest_diff is not None and closest_diff > amount_tolerance:
                findings.append(_finding(
                    book_record,
                    "gst_amount_mismatch_books_vs_2b",
                    "medium",
                    "GST reconciliation amount mismatch",
                    "Invoice exists in both books and GSTR-2B, but amount differs beyond tolerance.",
                    {
                        "match_key": key,
                        "books_amount": book_amount,
                        "gstr_2b_amount": _amount(getattr(closest_portal, "amount", None)),
                        "difference": round(closest_diff, 2),
                        "gstr_2b_record": _display(closest_portal),
                    },
                ))

    for key, portal_records in portal_index.items():
        if key not in book_index:
            for record in portal_records:
                findings.append(_finding(
                    record,
                    "gstr_2b_invoice_not_booked",
                    "medium",
                    "GSTR-2B invoice not found in books",
                    "Invoice exists in GSTR-2B but matching books entry was not found. Check if purchase/ITC was missed or intentionally not booked.",
                    {"match_key": key},
                ))

    return findings
''',
encoding="utf-8",
)

# ----------------------------------------------------
# 2. Patch runner.py
# ----------------------------------------------------

runner = RUNNER.read_text(encoding="utf-8")

if "from app.services.audit_engine.checks.gst_reco_checks import run_gst_reconciliation_checks" not in runner:
    runner = runner.replace(
        "from app.services.audit_engine.checks.sales_checks import run_sales_checks",
        "from app.services.audit_engine.checks.sales_checks import run_sales_checks\nfrom app.services.audit_engine.checks.gst_reco_checks import run_gst_reconciliation_checks",
    )

if "GST_BOOK_FILE_TYPES" not in runner:
    insert_after = '''SALES_FILE_TYPES = {
    "sales_register",
    "generic_sales_register",
    "sales",
    "sap_customer_line_items",
}
'''
    gst_types = insert_after + '''

GST_BOOK_FILE_TYPES = {
    "purchase_register",
    "purchase",
    "purchase_ledger",
    "tally_purchase_register",
    "sap_vendor_line_items",
}

GSTR_2B_FILE_TYPES = {
    "gstr_2b",
    "gst_2b",
    "gstr2b",
}
'''
    if insert_after in runner:
        runner = runner.replace(insert_after, gst_types)
    else:
        runner = runner.replace(
            "BANK_FILE_TYPES = {",
            '''GST_BOOK_FILE_TYPES = {
    "purchase_register",
    "purchase",
    "purchase_ledger",
    "tally_purchase_register",
    "sap_vendor_line_items",
}

GSTR_2B_FILE_TYPES = {
    "gstr_2b",
    "gst_2b",
    "gstr2b",
}

BANK_FILE_TYPES = {''',
        )

if "def run_gst_reconciliation" not in runner:
    gst_function = r'''

def run_gst_reconciliation(workspace_id: int, db: Session) -> dict:
    parse_summary = parse_workspace_files(workspace_id, db, force_reparse=False)

    records = (
        db.query(ExtractedRecord)
        .filter(ExtractedRecord.workspace_id == workspace_id)
        .all()
    )

    book_records = [
        record for record in records
        if record.record_type.lower() in GST_BOOK_FILE_TYPES
    ]

    gstr_2b_records = [
        record for record in records
        if record.record_type.lower() in GSTR_2B_FILE_TYPES
    ]

    clear_findings(workspace_id, db)

    if not book_records or not gstr_2b_records:
        audit_run = AuditRun(
            workspace_id=workspace_id,
            audit_type="gst_reconciliation",
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
            "message": "GST reconciliation needs one books purchase file and one GSTR-2B file.",
            "parse_summary": parse_summary,
            "coverage": {
                "total_records": len(records),
                "book_records": len(book_records),
                "gstr_2b_records": len(gstr_2b_records),
                "checked_records": 0,
                "unchecked_records": len(records),
                "issues_found": 0,
            },
        }

    finding_payloads = run_gst_reconciliation_checks(book_records, gstr_2b_records)
    checked_records = len(book_records) + len(gstr_2b_records)

    audit_run = AuditRun(
        workspace_id=workspace_id,
        audit_type="gst_reconciliation",
        status="completed",
        total_records=checked_records,
        checked_records=checked_records,
        issues_found=len(finding_payloads),
        unchecked_records=max(0, len(records) - checked_records),
    )

    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)

    save_findings(workspace_id, audit_run.id, finding_payloads, db)

    return {
        "audit_run_id": audit_run.id,
        "status": audit_run.status,
        "message": "GST reconciliation completed using books and GSTR-2B records",
        "parse_summary": parse_summary,
        "coverage": {
            "total_records": len(records),
            "book_records": len(book_records),
            "gstr_2b_records": len(gstr_2b_records),
            "checked_records": checked_records,
            "unchecked_records": audit_run.unchecked_records,
            "issues_found": len(finding_payloads),
            "risk_counts": risk_counts(finding_payloads),
        },
    }
'''
    if "\n\ndef run_bank_reconciliation" in runner:
        runner = runner.replace("\n\ndef run_bank_reconciliation", gst_function + "\n\ndef run_bank_reconciliation")
    else:
        runner += gst_function

RUNNER.write_text(runner, encoding="utf-8")

# ----------------------------------------------------
# 3. Patch audit_runs.py
# ----------------------------------------------------

routes = AUDIT_RUNS.read_text(encoding="utf-8")

if "run_gst_reconciliation" not in routes:
    routes = routes.replace(
        "run_expense_audit,",
        "run_expense_audit,\n    run_gst_reconciliation,",
    )

if 'run-gst-reconciliation' not in routes:
    endpoint = r'''

@router.post("/{workspace_id}/run-gst-reconciliation")
def run_real_gst_reconciliation(workspace_id: int, db: Session = Depends(get_db)):
    try:
        return run_gst_reconciliation(workspace_id=workspace_id, db=db)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"GST reconciliation failed: {str(exc)}")
'''
    routes = routes.replace(
        '\n\n@router.post("/{workspace_id}/run-bank-reconciliation")',
        endpoint + '\n\n@router.post("/{workspace_id}/run-bank-reconciliation")',
    )

AUDIT_RUNS.write_text(routes, encoding="utf-8")

# ----------------------------------------------------
# 4. Patch frontend
# ----------------------------------------------------

page = FRONTEND.read_text(encoding="utf-8")

# Add coverage type hints
if "gstr_2b_records?: number;" not in page:
    page = page.replace(
        "ledger_records?: number;",
        "ledger_records?: number;\n    book_records?: number;\n    gstr_2b_records?: number;",
    )

# Add runGstReconciliation function before bank reconciliation
if "async function runGstReconciliation()" not in page:
    gst_fn = r'''
  async function runGstReconciliation() {
    setBusy(true);
    setStatusMessage("Running GST reconciliation...");

    try {
      const res = await api.post(`/audit-runs/${workspaceId}/run-gst-reconciliation`);
      setAuditSummary(res.data);
      setSelectedAuditRunId(res.data.audit_run_id);
      setStatusMessage("GST reconciliation completed.");
      await refreshAll();
      setActiveSection("findings");
    } catch {
      setStatusMessage("GST reconciliation failed.");
    } finally {
      setBusy(false);
    }
  }

'''
    page = page.replace("  async function runBankReconciliation()", gst_fn + "  async function runBankReconciliation()")

# Pass prop into AuditSection call
if "runGstReconciliation={runGstReconciliation}" not in page:
    page = page.replace(
        "runExpenseAudit={runExpenseAudit}\n                runBankReconciliation={runBankReconciliation}",
        "runExpenseAudit={runExpenseAudit}\n                runGstReconciliation={runGstReconciliation}\n                runBankReconciliation={runBankReconciliation}",
    )

# Add AuditSection destructuring prop
if "runGstReconciliation," not in page:
    page = page.replace(
        "runExpenseAudit,\n  runBankReconciliation,",
        "runExpenseAudit,\n  runGstReconciliation,\n  runBankReconciliation,",
    )

# Add AuditSection prop type
if "runGstReconciliation: () => void;" not in page:
    page = page.replace(
        "runExpenseAudit: () => void;\n  runBankReconciliation: () => void;",
        "runExpenseAudit: () => void;\n  runGstReconciliation: () => void;\n  runBankReconciliation: () => void;",
    )

# Add module option after expense
if 'key: "gst"' not in page:
    expense_option = r'''    {
      key: "expense",
      label: "Expense Audit",
      description: "Checks expense ledgers for duplicate vouchers, high-value spends, cash expenses, weak narration, and discretionary spend.",
      run: runExpenseAudit,
    },'''
    gst_option = expense_option + r'''
    {
      key: "gst",
      label: "GST Reconciliation",
      description: "Compares books purchase/ITC entries with GSTR-2B and flags missing invoices, amount mismatches, and duplicate ITC risk.",
      run: runGstReconciliation,
    },'''
    page = page.replace(expense_option, gst_option)

# Format audit type
if 'if (type === "gst_reconciliation") return "GST Reconciliation";' not in page:
    page = page.replace(
        'if (type === "bank_reconciliation") return "Bank Reconciliation";',
        'if (type === "gst_reconciliation") return "GST Reconciliation";\n  if (type === "bank_reconciliation") return "Bank Reconciliation";',
    )

# Infer GST module
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
  if (type.includes("expense") || type.includes("gl") || type.includes("ledger_vouchers")) return "expense";
  if (type.includes("bank") || type.includes("cash_bank") || type.includes("tally_bank")) return "bank";
  if (type.includes("purchase") || type.includes("vendor")) return "purchase";

  return "purchase";
}''',
    page,
)

FRONTEND.write_text(page, encoding="utf-8")

# ----------------------------------------------------
# 5. Sample files
# ----------------------------------------------------

(SAMPLE_DIR / "gst_books_purchase_edge_cases.csv").write_text(
"""Invoice No,Invoice Date,Vendor Name,GSTIN,Taxable Value,Narration
PB-001,01-04-2025,ABC Suppliers,27ABCDE1234F1Z5,10000,Matched invoice
PB-002,03-04-2025,Missing In 2B Vendor,27ABCDE1234F1Z5,25000,Books ITC not in 2B
PB-003,05-04-2025,Amount Mismatch Vendor,27ABCDE1234F1Z5,50000,Amount differs from 2B
PB-004,07-04-2025,Duplicate Vendor,27ABCDE1234F1Z5,12000,Duplicate in books
PB-004,07-04-2025,Duplicate Vendor,27ABCDE1234F1Z5,12000,Duplicate in books again
,08-04-2025,No Invoice Vendor,27ABCDE1234F1Z5,8000,Missing invoice number
PB-006,09-04-2025,No GSTIN Vendor,,15000,Missing supplier GSTIN
""",
encoding="utf-8",
)

(SAMPLE_DIR / "gstr_2b_edge_cases.csv").write_text(
"""Invoice number,Invoice Date,Trade/Legal name,GSTIN of supplier,Taxable Value,Supply Type
PB-001,01-04-2025,ABC Suppliers,27ABCDE1234F1Z5,10000,Regular
PB-003,05-04-2025,Amount Mismatch Vendor,27ABCDE1234F1Z5,48000,Regular
PB-005,10-04-2025,Only In 2B Vendor,27ABCDE1234F1Z5,30000,Regular
PB-007,11-04-2025,Duplicate 2B Vendor,27ABCDE1234F1Z5,9000,Regular
PB-007,11-04-2025,Duplicate 2B Vendor,27ABCDE1234F1Z5,9000,Regular duplicate
""",
encoding="utf-8",
)

print("GST Reconciliation module applied.")
print("Updated:")
print(f"- {CHECKS_DIR / 'gst_reco_checks.py'}")
print(f"- {RUNNER}")
print(f"- {AUDIT_RUNS}")
print(f"- {FRONTEND}")
print(f"- {SAMPLE_DIR / 'gst_books_purchase_edge_cases.csv'}")
print(f"- {SAMPLE_DIR / 'gstr_2b_edge_cases.csv'}")