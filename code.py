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
# 1. TDS review checks
# ----------------------------------------------------

(CHECKS_DIR / "tds_checks.py").write_text(
r'''from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


TDS_SENSITIVE_KEYWORDS = {
    "professional": ["professional", "consultancy", "consultant", "technical fees", "legal fees", "audit fees", "ca fees"],
    "contractor": ["contractor", "contract", "labour", "job work", "works contract"],
    "rent": ["rent", "lease", "premises"],
    "commission": ["commission", "brokerage"],
    "interest": ["interest"],
    "royalty": ["royalty"],
}


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
    lowered = {str(k).strip().lower(): v for k, v in raw.items()}

    for key in keys:
        if key in raw and raw[key] not in [None, ""]:
            return raw[key]

        lowered_key = key.strip().lower()
        if lowered_key in lowered and lowered[lowered_key] not in [None, ""]:
            return lowered[lowered_key]

    return None


def _description(record):
    return (
        _raw(record, "description", "narration", "Narration", "Description", "Particulars", "Text", "Nature")
        or getattr(record, "description", None)
        or ""
    )


def _party(record):
    return (
        getattr(record, "party_name", None)
        or _raw(record, "Party Name", "Vendor Name", "Supplier Name", "Name 1", "Particulars")
        or ""
    )


def _pan(record):
    return _raw(record, "PAN", "Vendor PAN", "Supplier PAN", "Permanent Account Number", "PAN No", "PAN Number") or ""


def _tds_amount(record):
    return _amount(
        _raw(
            record,
            "TDS Deducted",
            "TDS Amount",
            "Tax Deducted",
            "TDS",
            "Withholding Tax",
            "WHT Amount",
            "TDS Payable",
        )
    )


def _tds_section(record):
    return _raw(record, "TDS Section", "Section", "TDS Nature", "194C/194J", "Withholding Tax Code", "WHT Code") or ""


def _nature(record):
    return (
        _raw(record, "Nature", "Expense Nature", "Payment Nature", "Ledger Name", "G/L Account", "GL Account")
        or _description(record)
        or _party(record)
    )


def _tds_category(text):
    text = text.lower()
    for category, keywords in TDS_SENSITIVE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    return ""


def _money(value):
    amount = _amount(value)
    if amount is None:
        return ""
    return f"₹{amount:,.0f}"


def _title(base, record):
    bits = []

    doc = _norm(getattr(record, "document_id", None))
    party = _norm(_party(record))
    amount = _money(getattr(record, "amount", None))

    if doc:
        bits.append(doc)
    if party:
        bits.append(party)
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
        "party_name": _party(record),
        "transaction_date": _date_string(getattr(record, "transaction_date", None)),
        "amount": getattr(record, "amount", None),
        "pan": _pan(record),
        "tds_amount": _tds_amount(record),
        "tds_section": _tds_section(record),
        "nature": _nature(record),
        "description": _description(record),
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


def run_tds_checks(records):
    findings = []
    voucher_index = defaultdict(list)
    party_amount_date_index = defaultdict(list)

    for record in records:
        document_id = _norm(getattr(record, "document_id", None))
        party = _party(record)
        amount = _amount(getattr(record, "amount", None))
        txn_date = getattr(record, "transaction_date", None)
        txn_date_text = _date_string(txn_date)
        description = _description(record)
        nature = _nature(record)
        combined_text = " ".join([_lower(party), _lower(description), _lower(nature)])

        pan = _norm(_pan(record)).upper()
        tds_amount = _tds_amount(record)
        tds_section = _norm(_tds_section(record))
        category = _tds_category(combined_text)

        if document_id:
            voucher_index[document_id.lower()].append(record)

        if party and amount is not None and txn_date_text:
            party_amount_date_index[(party.lower(), round(abs(amount), 2), txn_date_text)].append(record)

        if amount is None:
            findings.append(_finding(
                record,
                "tds_review_missing_payment_amount",
                "medium",
                "Missing payment amount for TDS review",
                "Entry does not contain a usable payment/expense amount, so TDS applicability cannot be assessed reliably.",
            ))
            continue

        if category:
            if amount >= 30000 and (tds_amount is None or tds_amount <= 0):
                findings.append(_finding(
                    record,
                    "possible_tds_not_deducted",
                    "high",
                    "Possible TDS not deducted",
                    "Payment appears TDS-sensitive and exceeds review threshold, but no TDS deducted amount is visible.",
                    {
                        "tds_category": category,
                        "amount": amount,
                        "tds_amount": tds_amount,
                    },
                ))

            if not pan:
                findings.append(_finding(
                    record,
                    "missing_vendor_pan_for_tds",
                    "high",
                    "Missing vendor PAN for TDS-sensitive payment",
                    "Payment appears TDS-sensitive but vendor PAN is missing. This affects TDS compliance and reporting.",
                    {
                        "tds_category": category,
                        "amount": amount,
                    },
                ))

            if tds_amount is not None and tds_amount > 0 and not tds_section:
                findings.append(_finding(
                    record,
                    "tds_deducted_section_missing",
                    "medium",
                    "TDS deducted but section/code missing",
                    "TDS amount is present but TDS section or withholding tax code is missing.",
                    {
                        "tds_amount": tds_amount,
                    },
                ))

            if amount >= 100000:
                findings.append(_finding(
                    record,
                    "high_value_tds_sensitive_payment",
                    "medium",
                    "High-value TDS-sensitive payment",
                    "High-value payment appears to fall under a TDS-sensitive category. Verify PAN, section, rate, deduction, and challan trail.",
                    {
                        "tds_category": category,
                        "amount": amount,
                    },
                ))

            if amount >= 1000 and amount % 1000 == 0:
                findings.append(_finding(
                    record,
                    "round_number_tds_sensitive_payment",
                    "low",
                    "Round-number TDS-sensitive payment",
                    "TDS-sensitive payment has a round amount. This can be normal but should be reviewed for estimate/manual booking.",
                    {
                        "tds_category": category,
                        "amount": amount,
                    },
                ))

            if _is_year_end(txn_date):
                findings.append(_finding(
                    record,
                    "year_end_tds_sensitive_payment",
                    "medium",
                    "Year-end TDS-sensitive payment",
                    "TDS-sensitive payment was booked near financial year end. Verify deduction timing, provision, and payment compliance.",
                    {
                        "tds_category": category,
                        "transaction_date": txn_date_text,
                    },
                ))

        elif tds_amount is not None and tds_amount > 0:
            findings.append(_finding(
                record,
                "tds_deducted_on_uncategorized_payment",
                "low",
                "TDS deducted on uncategorized payment",
                "TDS amount is present, but payment nature was not clearly classified by the rule engine.",
                {
                    "tds_amount": tds_amount,
                    "nature": nature,
                },
            ))

    for voucher, duplicate_records in voucher_index.items():
        if len(duplicate_records) > 1:
            first = duplicate_records[0]
            findings.append(_finding(
                first,
                "duplicate_tds_payment_voucher",
                "medium",
                "Duplicate TDS/payment voucher reference",
                "Same voucher/reference appears more than once in TDS-review data. Review whether this is valid multi-line accounting or duplicate booking.",
                {
                    "voucher": voucher,
                    "duplicate_count": len(duplicate_records),
                    "source_rows": [getattr(record, "source_row", None) for record in duplicate_records],
                    "record_ids": [getattr(record, "id", None) for record in duplicate_records],
                },
            ))

    for key, repeated_records in party_amount_date_index.items():
        if len(repeated_records) > 1:
            first = repeated_records[0]
            party, amount, txn_date = key
            findings.append(_finding(
                first,
                "repeated_tds_payment_pattern",
                "medium",
                "Repeated party/date/amount payment pattern",
                "Same party, same amount, and same date appears multiple times. Review for duplicate payment or split booking.",
                {
                    "party_name": party,
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

if "from app.services.audit_engine.checks.tds_checks import run_tds_checks" not in runner:
    if "from app.services.audit_engine.checks.ledger_scrutiny_checks import run_ledger_scrutiny_checks" in runner:
        runner = runner.replace(
            "from app.services.audit_engine.checks.ledger_scrutiny_checks import run_ledger_scrutiny_checks",
            "from app.services.audit_engine.checks.ledger_scrutiny_checks import run_ledger_scrutiny_checks\nfrom app.services.audit_engine.checks.tds_checks import run_tds_checks",
        )
    else:
        runner = runner.replace(
            "from app.services.audit_engine.checks.expense_checks import run_expense_checks",
            "from app.services.audit_engine.checks.expense_checks import run_expense_checks\nfrom app.services.audit_engine.checks.tds_checks import run_tds_checks",
        )

if "TDS_FILE_TYPES" not in runner:
    marker = '''LEDGER_SCRUTINY_FILE_TYPES = {
    "ledger",
    "expense_ledger",
    "tally_ledger_vouchers",
    "sap_gl_line_items",
    "cash_bank_ledger",
    "bank_ledger",
    "trial_balance",
}
'''
    addition = marker + '''

TDS_FILE_TYPES = {
    "tds_ledger",
    "expense_ledger",
    "tally_ledger_vouchers",
    "sap_gl_line_items",
    "sap_vendor_line_items",
    "purchase_register",
    "tally_purchase_register",
}
'''
    if marker in runner:
        runner = runner.replace(marker, addition)
    else:
        runner += '''

TDS_FILE_TYPES = {
    "tds_ledger",
    "expense_ledger",
    "tally_ledger_vouchers",
    "sap_gl_line_items",
    "sap_vendor_line_items",
    "purchase_register",
    "tally_purchase_register",
}
'''

if "def run_tds_review" not in runner:
    tds_function = r'''

def run_tds_review(workspace_id: int, db: Session) -> dict:
    parse_summary = parse_workspace_files(workspace_id, db, force_reparse=False)

    records = (
        db.query(ExtractedRecord)
        .filter(ExtractedRecord.workspace_id == workspace_id)
        .all()
    )

    tds_records = [
        record for record in records
        if record.record_type.lower() in TDS_FILE_TYPES
    ]

    clear_findings(workspace_id, db)

    if not tds_records:
        audit_run = AuditRun(
            workspace_id=workspace_id,
            audit_type="tds_review",
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
            "message": "TDS review needs expense/vendor/ledger records such as Tally Ledger Vouchers, SAP Vendor Line Items, or Expense Ledger.",
            "parse_summary": parse_summary,
            "coverage": {
                "total_records": len(records),
                "tds_records_checked": 0,
                "unchecked_records": len(records),
                "issues_found": 0,
            },
        }

    finding_payloads = run_tds_checks(tds_records)

    audit_run = AuditRun(
        workspace_id=workspace_id,
        audit_type="tds_review",
        status="completed",
        total_records=len(tds_records),
        checked_records=len(tds_records),
        issues_found=len(finding_payloads),
        unchecked_records=max(0, len(records) - len(tds_records)),
    )

    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)

    save_findings(workspace_id, audit_run.id, finding_payloads, db)

    return {
        "audit_run_id": audit_run.id,
        "status": audit_run.status,
        "message": "TDS review completed using uploaded records",
        "parse_summary": parse_summary,
        "coverage": {
            "total_records": len(records),
            "tds_records_checked": len(tds_records),
            "unchecked_records": audit_run.unchecked_records,
            "issues_found": len(finding_payloads),
            "risk_counts": risk_counts(finding_payloads),
        },
    }
'''
    if "\n\ndef run_ledger_scrutiny" in runner:
        runner = runner.replace("\n\ndef run_ledger_scrutiny", tds_function + "\n\ndef run_ledger_scrutiny")
    elif "\n\ndef run_gst_reconciliation" in runner:
        runner = runner.replace("\n\ndef run_gst_reconciliation", tds_function + "\n\ndef run_gst_reconciliation")
    else:
        runner += tds_function

RUNNER.write_text(runner, encoding="utf-8")

# ----------------------------------------------------
# 3. Patch audit_runs.py
# ----------------------------------------------------

routes = AUDIT_RUNS.read_text(encoding="utf-8")

if "run_tds_review" not in routes:
    if "run_ledger_scrutiny," in routes:
        routes = routes.replace(
            "run_ledger_scrutiny,",
            "run_ledger_scrutiny,\n    run_tds_review,",
        )
    else:
        routes = routes.replace(
            "run_expense_audit,",
            "run_expense_audit,\n    run_tds_review,",
        )

if 'run-tds-review' not in routes:
    endpoint = r'''

@router.post("/{workspace_id}/run-tds-review")
def run_real_tds_review(workspace_id: int, db: Session = Depends(get_db)):
    try:
        return run_tds_review(workspace_id=workspace_id, db=db)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"TDS review failed: {str(exc)}")
'''
    if '\n\n@router.post("/{workspace_id}/run-ledger-scrutiny")' in routes:
        routes = routes.replace(
            '\n\n@router.post("/{workspace_id}/run-ledger-scrutiny")',
            endpoint + '\n\n@router.post("/{workspace_id}/run-ledger-scrutiny")',
        )
    elif '\n\n@router.post("/{workspace_id}/run-gst-reconciliation")' in routes:
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

if "tds_records_checked?: number;" not in page:
    page = page.replace(
        "ledger_records_checked?: number;",
        "ledger_records_checked?: number;\n    tds_records_checked?: number;",
    )

# Add TDS file type option
if '<option value="tds_ledger">TDS Ledger</option>' not in page:
    page = page.replace(
        '<option value="expense_ledger">Expense Ledger</option>',
        '<option value="expense_ledger">Expense Ledger</option>\n            <option value="tds_ledger">TDS Ledger</option>',
    )

# Add runTdsReview function
if "async function runTdsReview()" not in page:
    tds_fn = r'''
  async function runTdsReview() {
    setBusy(true);
    setStatusMessage("Running TDS review...");

    try {
      const res = await api.post(`/audit-runs/${workspaceId}/run-tds-review`);
      setAuditSummary(res.data);
      setSelectedAuditRunId(res.data.audit_run_id);
      setStatusMessage("TDS review completed.");
      await refreshAll();
      setActiveSection("findings");
    } catch {
      setStatusMessage("TDS review failed.");
    } finally {
      setBusy(false);
    }
  }

'''
    if "  async function runLedgerScrutiny()" in page:
        page = page.replace("  async function runLedgerScrutiny()", tds_fn + "  async function runLedgerScrutiny()")
    else:
        page = page.replace("  async function runExpenseAudit()", tds_fn + "  async function runExpenseAudit()")

# Pass prop into AuditSection call
if "runTdsReview={runTdsReview}" not in page:
    if "runLedgerScrutiny={runLedgerScrutiny}" in page:
        page = page.replace(
            "runExpenseAudit={runExpenseAudit}\n                runLedgerScrutiny={runLedgerScrutiny}",
            "runExpenseAudit={runExpenseAudit}\n                runTdsReview={runTdsReview}\n                runLedgerScrutiny={runLedgerScrutiny}",
        )
    else:
        page = page.replace(
            "runExpenseAudit={runExpenseAudit}\n                runGstReconciliation={runGstReconciliation}",
            "runExpenseAudit={runExpenseAudit}\n                runTdsReview={runTdsReview}\n                runGstReconciliation={runGstReconciliation}",
        )

# Add AuditSection prop destructuring
if "runTdsReview," not in page:
    if "runLedgerScrutiny," in page:
        page = page.replace(
            "runExpenseAudit,\n  runLedgerScrutiny,",
            "runExpenseAudit,\n  runTdsReview,\n  runLedgerScrutiny,",
        )
    else:
        page = page.replace(
            "runExpenseAudit,\n  runGstReconciliation,",
            "runExpenseAudit,\n  runTdsReview,\n  runGstReconciliation,",
        )

# Add AuditSection prop type
if "runTdsReview: () => void;" not in page:
    if "runLedgerScrutiny: () => void;" in page:
        page = page.replace(
            "runExpenseAudit: () => void;\n  runLedgerScrutiny: () => void;",
            "runExpenseAudit: () => void;\n  runTdsReview: () => void;\n  runLedgerScrutiny: () => void;",
        )
    else:
        page = page.replace(
            "runExpenseAudit: () => void;\n  runGstReconciliation: () => void;",
            "runExpenseAudit: () => void;\n  runTdsReview: () => void;\n  runGstReconciliation: () => void;",
        )

# Add TDS module option after expense
if 'key: "tds"' not in page:
    expense_option = r'''    {
      key: "expense",
      label: "Expense Audit",
      description: "Checks expense ledgers for duplicate vouchers, high-value spends, cash expenses, weak narration, and discretionary spend.",
      run: runExpenseAudit,
    },'''
    tds_option = expense_option + r'''
    {
      key: "tds",
      label: "TDS Review",
      description: "Reviews vendor/expense payments for possible TDS non-deduction, missing PAN, missing section, high-value payments, and duplicate vouchers.",
      run: runTdsReview,
    },'''
    page = page.replace(expense_option, tds_option)

# Format audit type
if 'if (type === "tds_review") return "TDS Review";' not in page:
    if 'if (type === "ledger_scrutiny") return "Ledger Scrutiny";' in page:
        page = page.replace(
            'if (type === "ledger_scrutiny") return "Ledger Scrutiny";',
            'if (type === "tds_review") return "TDS Review";\n  if (type === "ledger_scrutiny") return "Ledger Scrutiny";',
        )
    else:
        page = page.replace(
            'if (type === "gst_reconciliation") return "GST Reconciliation";',
            'if (type === "tds_review") return "TDS Review";\n  if (type === "gst_reconciliation") return "GST Reconciliation";',
        )

# Coverage checked records
page = page.replace(
    "coverageSource?.ledger_records_checked ??\n    0;",
    "coverageSource?.ledger_records_checked ??\n    coverageSource?.tds_records_checked ??\n    0;",
)

# Infer TDS module
page = re.sub(
    r"function inferRecommendedAuditModule\(files\?: UploadedFile\[\]\) \{[\s\S]*?\n\}",
    r'''function inferRecommendedAuditModule(files?: UploadedFile[]) {
  if (!files || !files.length) return "purchase";

  const candidates = files
    .filter((file) => file.status === "parsed" || file.status === "uploaded")
    .sort((a, b) => b.id - a.id);

  const latest = candidates[0] ?? files[files.length - 1];
  const type = latest?.file_type?.toLowerCase() ?? "";

  if (type.includes("tds")) return "tds";
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
# 5. Sample TDS data
# ----------------------------------------------------

(SAMPLE_DIR / "tds_review_edge_cases.csv").write_text(
"""Voucher No,Date,Party Name,PAN,Nature,Amount,TDS Deducted,TDS Section,Narration
TDS-001,01-04-2025,ABC Consultants,ABCDE1234F,Professional Fees,50000,5000,194J,Proper TDS deducted
TDS-002,05-04-2025,No TDS Consultant,BCDEF2345G,Consultancy Charges,75000,0,,Possible TDS not deducted
TDS-003,10-04-2025,No PAN Contractor,,Contractor Payment,90000,0,,Missing PAN and TDS
TDS-004,15-04-2025,Rent Owner,CDEFG3456H,Rent,120000,12000,,TDS deducted but section missing
TDS-005,31-03-2026,Year End Legal Firm,DEFGH4567I,Legal Fees,150000,0,,Year-end professional payment
TDS-006,20-05-2025,Commission Agent,EFGHI5678J,Commission,30000,0,,Threshold payment no TDS
TDS-007,22-05-2025,Interest Party,FGHIJ6789K,Interest,60000,6000,194A,TDS deducted
TDS-008,24-05-2025,Regular Supplier,GHIJK7890L,Purchase of goods,40000,0,,Non-TDS normal purchase
TDS-009,26-05-2025,Duplicate Consultant,HIJKL8901M,Professional Fees,50000,0,,Repeated same amount
TDS-010,26-05-2025,Duplicate Consultant,HIJKL8901M,Professional Fees,50000,0,,Repeated same amount
TDS-010,26-05-2025,Duplicate Consultant,HIJKL8901M,Professional Fees,50000,0,,Duplicate voucher
""",
encoding="utf-8",
)

print("TDS Review module applied.")
print("Updated:")
print(f"- {CHECKS_DIR / 'tds_checks.py'}")
print(f"- {RUNNER}")
print(f"- {AUDIT_RUNS}")
print(f"- {FRONTEND}")
print(f"- {SAMPLE_DIR / 'tds_review_edge_cases.csv'}")