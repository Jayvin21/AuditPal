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
# 1. Aging review checks
# ----------------------------------------------------

(CHECKS_DIR / "aging_checks.py").write_text(
r'''from datetime import date, datetime
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


def _parse_date(value):
    if not value:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value).strip()

    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d.%m.%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass

    return None


def _date_string(value):
    parsed = _parse_date(value)
    if parsed:
        return parsed.isoformat()
    return _norm(value)


def _party(record):
    return (
        getattr(record, "party_name", None)
        or _raw(record, "Party Name", "Customer Name", "Vendor Name", "Supplier Name", "Name 1", "Account")
        or ""
    )


def _invoice_date(record):
    return (
        getattr(record, "transaction_date", None)
        or _raw(record, "Invoice Date", "Bill Date", "Document Date", "Posting Date", "Date")
    )


def _due_date(record):
    return _raw(record, "Due Date", "Payment Due Date", "Net Due Date", "Aging Date", "Due") or ""


def _outstanding(record):
    return _amount(
        _raw(
            record,
            "Outstanding",
            "Outstanding Amount",
            "Balance",
            "Closing Balance",
            "Open Amount",
            "Amount Due",
            "Net Due",
            "Amount",
        )
        or getattr(record, "amount", None)
    )


def _days_overdue(record, as_of=None):
    if as_of is None:
        as_of = date.today()

    direct = _amount(_raw(record, "Days Overdue", "Overdue Days", "Age", "Aging Days", "Days"))
    if direct is not None:
        return int(direct)

    due = _parse_date(_due_date(record))
    if not due:
        return None

    return (as_of - due).days


def _bucket(days):
    if days is None:
        return "unknown"
    if days <= 0:
        return "not_due"
    if days <= 30:
        return "0_30"
    if days <= 60:
        return "31_60"
    if days <= 90:
        return "61_90"
    if days <= 180:
        return "91_180"
    return "180_plus"


def _is_receivable(record):
    typ = _lower(getattr(record, "record_type", ""))
    text = " ".join([
        typ,
        _lower(_raw(record, "Report Type", "Type", "Nature") or ""),
        _lower(_party(record)),
    ])
    return "receivable" in text or "debtor" in text or "customer" in text


def _is_payable(record):
    typ = _lower(getattr(record, "record_type", ""))
    text = " ".join([
        typ,
        _lower(_raw(record, "Report Type", "Type", "Nature") or ""),
        _lower(_party(record)),
    ])
    return "payable" in text or "creditor" in text or "vendor" in text or "supplier" in text


def _title(base, record):
    bits = []

    doc = _norm(getattr(record, "document_id", None))
    party = _norm(_party(record))
    outstanding = _outstanding(record)

    if doc:
        bits.append(doc)
    if party:
        bits.append(party)
    if outstanding is not None:
        bits.append(f"₹{abs(outstanding):,.0f}")

    if not bits:
        return base

    return f"{base} — {' · '.join(bits[:3])}"


def _finding(record, finding_type, risk_level, title, description, extra=None):
    days = _days_overdue(record)
    outstanding = _outstanding(record)

    evidence = {
        "record_id": getattr(record, "id", None),
        "source_row": getattr(record, "source_row", None),
        "document_id": getattr(record, "document_id", None),
        "party_name": _party(record),
        "invoice_date": _date_string(_invoice_date(record)),
        "due_date": _date_string(_due_date(record)),
        "days_overdue": days,
        "aging_bucket": _bucket(days),
        "outstanding_amount": outstanding,
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


def run_aging_checks(records):
    findings = []

    for record in records:
        document_id = _norm(getattr(record, "document_id", None))
        party = _norm(_party(record))
        outstanding = _outstanding(record)
        days = _days_overdue(record)
        due = _due_date(record)
        invoice_date = _invoice_date(record)

        is_receivable = _is_receivable(record)
        is_payable = _is_payable(record)

        if not document_id:
            findings.append(_finding(
                record,
                "missing_aging_invoice_reference",
                "medium",
                "Missing invoice/reference in aging report",
                "Aging row does not have invoice, bill, voucher, or reference number.",
            ))

        if not party:
            findings.append(_finding(
                record,
                "missing_aging_party",
                "high",
                "Missing customer/vendor name",
                "Aging row does not identify the customer/vendor/party.",
            ))

        if not invoice_date:
            findings.append(_finding(
                record,
                "missing_aging_invoice_date",
                "medium",
                "Missing invoice/document date",
                "Aging row does not have invoice/document date.",
            ))

        if not due:
            findings.append(_finding(
                record,
                "missing_due_date",
                "medium",
                "Missing due date",
                "Aging row does not contain a due date, so overdue status cannot be verified reliably.",
            ))

        if outstanding is None:
            findings.append(_finding(
                record,
                "missing_outstanding_amount",
                "high",
                "Missing outstanding amount",
                "Aging row does not contain a usable outstanding amount.",
            ))
            continue

        if outstanding == 0:
            findings.append(_finding(
                record,
                "zero_outstanding_in_aging",
                "low",
                "Zero outstanding in aging report",
                "Aging row has zero outstanding amount. Check if it should be excluded from open-item report.",
                {"outstanding_amount": outstanding},
            ))

        if outstanding < 0:
            findings.append(_finding(
                record,
                "negative_outstanding_amount",
                "medium",
                "Negative outstanding amount",
                "Aging row has negative outstanding amount. Review credit note, advance, overpayment, or classification.",
                {"outstanding_amount": outstanding},
            ))

        if abs(outstanding) >= 500000:
            findings.append(_finding(
                record,
                "high_value_outstanding_balance",
                "high",
                "High-value outstanding balance",
                "Outstanding balance is above ₹5,00,000 and should be prioritized for confirmation/recovery/payment review.",
                {"outstanding_amount": outstanding},
            ))

        if abs(outstanding) >= 10000 and abs(outstanding) % 1000 == 0:
            findings.append(_finding(
                record,
                "round_number_outstanding_balance",
                "low",
                "Round-number outstanding balance",
                "Outstanding amount is a round number. This can be normal but may indicate estimate/manual adjustment.",
                {"outstanding_amount": outstanding},
            ))

        if days is None:
            findings.append(_finding(
                record,
                "unknown_aging_bucket",
                "medium",
                "Unknown aging bucket",
                "Days overdue could not be calculated because due date or aging days are missing/invalid.",
            ))
            continue

        if days > 180:
            risk = "high" if is_receivable else "medium"
            findings.append(_finding(
                record,
                "over_180_days_outstanding",
                risk,
                "Outstanding over 180 days",
                "Open item is outstanding for more than 180 days. Review recoverability, provision, confirmation, dispute, or payment plan.",
                {"days_overdue": days},
            ))
        elif days > 90:
            findings.append(_finding(
                record,
                "over_90_days_outstanding",
                "medium",
                "Outstanding over 90 days",
                "Open item is outstanding for more than 90 days and should be reviewed for follow-up, confirmation, or settlement.",
                {"days_overdue": days},
            ))
        elif days > 60:
            findings.append(_finding(
                record,
                "over_60_days_outstanding",
                "low",
                "Outstanding over 60 days",
                "Open item is outstanding for more than 60 days.",
                {"days_overdue": days},
            ))

        if is_receivable and days > 90 and outstanding > 0:
            findings.append(_finding(
                record,
                "old_receivable_recoverability_review",
                "high",
                "Old receivable recoverability review",
                "Receivable is old and should be reviewed for recoverability, expected credit loss/provision, and balance confirmation.",
                {"days_overdue": days, "outstanding_amount": outstanding},
            ))

        if is_payable and days > 180 and outstanding > 0:
            findings.append(_finding(
                record,
                "old_payable_confirmation_review",
                "medium",
                "Old payable confirmation review",
                "Payable is old and should be reviewed for vendor confirmation, dispute, write-back, or settlement status.",
                {"days_overdue": days, "outstanding_amount": outstanding},
            ))

    return findings
''',
encoding="utf-8",
)

# ----------------------------------------------------
# 2. Patch runner.py
# ----------------------------------------------------

runner = RUNNER.read_text(encoding="utf-8")

if "from app.services.audit_engine.checks.aging_checks import run_aging_checks" not in runner:
    if "from app.services.audit_engine.checks.trial_balance_checks import run_trial_balance_checks" in runner:
        runner = runner.replace(
            "from app.services.audit_engine.checks.trial_balance_checks import run_trial_balance_checks",
            "from app.services.audit_engine.checks.trial_balance_checks import run_trial_balance_checks\nfrom app.services.audit_engine.checks.aging_checks import run_aging_checks",
        )
    else:
        runner = runner.replace(
            "from app.services.audit_engine.checks.fixed_asset_checks import run_fixed_asset_checks",
            "from app.services.audit_engine.checks.fixed_asset_checks import run_fixed_asset_checks\nfrom app.services.audit_engine.checks.aging_checks import run_aging_checks",
        )

if "AGING_FILE_TYPES" not in runner:
    runner += '''

AGING_FILE_TYPES = {
    "receivables_aging",
    "payables_aging",
    "outstanding_receivables",
    "outstanding_payables",
    "debtors_aging",
    "creditors_aging",
    "tally_outstanding_receivables",
    "tally_outstanding_payables",
    "sap_customer_open_items",
    "sap_vendor_open_items",
}
'''

if "def run_aging_review" not in runner:
    aging_function = r'''

def run_aging_review(workspace_id: int, db: Session) -> dict:
    parse_summary = parse_workspace_files(workspace_id, db, force_reparse=False)

    records = (
        db.query(ExtractedRecord)
        .filter(ExtractedRecord.workspace_id == workspace_id)
        .all()
    )

    aging_records = [
        record for record in records
        if record.record_type.lower() in AGING_FILE_TYPES
    ]

    clear_findings(workspace_id, db)

    if not aging_records:
        audit_run = AuditRun(
            workspace_id=workspace_id,
            audit_type="aging_review",
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
            "message": "Aging review needs receivables/payables aging or open-item files.",
            "parse_summary": parse_summary,
            "coverage": {
                "total_records": len(records),
                "aging_records_checked": 0,
                "unchecked_records": len(records),
                "issues_found": 0,
            },
        }

    finding_payloads = run_aging_checks(aging_records)

    audit_run = AuditRun(
        workspace_id=workspace_id,
        audit_type="aging_review",
        status="completed",
        total_records=len(aging_records),
        checked_records=len(aging_records),
        issues_found=len(finding_payloads),
        unchecked_records=max(0, len(records) - len(aging_records)),
    )

    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)

    save_findings(workspace_id, audit_run.id, finding_payloads, db)

    return {
        "audit_run_id": audit_run.id,
        "status": audit_run.status,
        "message": "Aging review completed using uploaded receivable/payable records",
        "parse_summary": parse_summary,
        "coverage": {
            "total_records": len(records),
            "aging_records_checked": len(aging_records),
            "unchecked_records": audit_run.unchecked_records,
            "issues_found": len(finding_payloads),
            "risk_counts": risk_counts(finding_payloads),
        },
    }
'''
    if "\n\ndef run_trial_balance_review" in runner:
        runner = runner.replace("\n\ndef run_trial_balance_review", aging_function + "\n\ndef run_trial_balance_review")
    elif "\n\ndef run_fixed_asset_audit" in runner:
        runner = runner.replace("\n\ndef run_fixed_asset_audit", aging_function + "\n\ndef run_fixed_asset_audit")
    else:
        runner += aging_function

RUNNER.write_text(runner, encoding="utf-8")

# ----------------------------------------------------
# 3. Patch audit_runs.py
# ----------------------------------------------------

routes = AUDIT_RUNS.read_text(encoding="utf-8")

if "run_aging_review" not in routes:
    if "run_trial_balance_review," in routes:
        routes = routes.replace(
            "run_trial_balance_review,",
            "run_trial_balance_review,\n    run_aging_review,",
        )
    elif "run_fixed_asset_audit," in routes:
        routes = routes.replace(
            "run_fixed_asset_audit,",
            "run_fixed_asset_audit,\n    run_aging_review,",
        )
    else:
        routes = routes.replace(
            "run_tds_review,",
            "run_tds_review,\n    run_aging_review,",
        )

if 'run-aging-review' not in routes:
    endpoint = r'''

@router.post("/{workspace_id}/run-aging-review")
def run_real_aging_review(workspace_id: int, db: Session = Depends(get_db)):
    try:
        return run_aging_review(workspace_id=workspace_id, db=db)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Aging review failed: {str(exc)}")
'''
    if '\n\n@router.post("/{workspace_id}/run-trial-balance-review")' in routes:
        routes = routes.replace(
            '\n\n@router.post("/{workspace_id}/run-trial-balance-review")',
            endpoint + '\n\n@router.post("/{workspace_id}/run-trial-balance-review")',
        )
    elif '\n\n@router.post("/{workspace_id}/run-fixed-asset-audit")' in routes:
        routes = routes.replace(
            '\n\n@router.post("/{workspace_id}/run-fixed-asset-audit")',
            endpoint + '\n\n@router.post("/{workspace_id}/run-fixed-asset-audit")',
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

if "aging_records_checked?: number;" not in page:
    page = page.replace(
        "trial_balance_records_checked?: number;",
        "trial_balance_records_checked?: number;\n    aging_records_checked?: number;",
    )
    page = page.replace(
        "fixed_asset_records_checked?: number;",
        "fixed_asset_records_checked?: number;\n    aging_records_checked?: number;",
    )

# Add file type options
if '<option value="receivables_aging">Receivables Aging</option>' not in page:
    page = page.replace(
        '<option value="trial_balance">Trial Balance</option>',
        '''<option value="receivables_aging">Receivables Aging</option>
            <option value="payables_aging">Payables Aging</option>
            <option value="outstanding_receivables">Outstanding Receivables</option>
            <option value="outstanding_payables">Outstanding Payables</option>
            <option value="tally_outstanding_receivables">Tally Outstanding Receivables</option>
            <option value="tally_outstanding_payables">Tally Outstanding Payables</option>
            <option value="sap_customer_open_items">SAP Customer Open Items</option>
            <option value="sap_vendor_open_items">SAP Vendor Open Items</option>
            <option value="trial_balance">Trial Balance</option>''',
    )

# Add run function
if "async function runAgingReview()" not in page:
    fn = r'''
  async function runAgingReview() {
    setBusy(true);
    setStatusMessage("Running receivables/payables aging review...");

    try {
      const res = await api.post(`/audit-runs/${workspaceId}/run-aging-review`);
      setAuditSummary(res.data);
      setSelectedAuditRunId(res.data.audit_run_id);
      setStatusMessage("Aging review completed.");
      await refreshAll();
      setActiveSection("findings");
    } catch {
      setStatusMessage("Aging review failed.");
    } finally {
      setBusy(false);
    }
  }

'''
    if "  async function runTrialBalanceReview()" in page:
        page = page.replace("  async function runTrialBalanceReview()", fn + "  async function runTrialBalanceReview()")
    elif "  async function runFixedAssetAudit()" in page:
        page = page.replace("  async function runFixedAssetAudit()", fn + "  async function runFixedAssetAudit()")
    else:
        page = page.replace("  async function runTdsReview()", fn + "  async function runTdsReview()")

# Pass prop
if "runAgingReview={runAgingReview}" not in page:
    if "runTrialBalanceReview={runTrialBalanceReview}" in page:
        page = page.replace(
            "runExpenseAudit={runExpenseAudit}\n                runTrialBalanceReview={runTrialBalanceReview}",
            "runExpenseAudit={runExpenseAudit}\n                runAgingReview={runAgingReview}\n                runTrialBalanceReview={runTrialBalanceReview}",
        )
    elif "runFixedAssetAudit={runFixedAssetAudit}" in page:
        page = page.replace(
            "runExpenseAudit={runExpenseAudit}\n                runFixedAssetAudit={runFixedAssetAudit}",
            "runExpenseAudit={runExpenseAudit}\n                runAgingReview={runAgingReview}\n                runFixedAssetAudit={runFixedAssetAudit}",
        )

# Destructure
if "runAgingReview," not in page:
    if "runTrialBalanceReview," in page:
        page = page.replace(
            "runExpenseAudit,\n  runTrialBalanceReview,",
            "runExpenseAudit,\n  runAgingReview,\n  runTrialBalanceReview,",
        )
    elif "runFixedAssetAudit," in page:
        page = page.replace(
            "runExpenseAudit,\n  runFixedAssetAudit,",
            "runExpenseAudit,\n  runAgingReview,\n  runFixedAssetAudit,",
        )

# Prop type
if "runAgingReview: () => void;" not in page:
    if "runTrialBalanceReview: () => void;" in page:
        page = page.replace(
            "runExpenseAudit: () => void;\n  runTrialBalanceReview: () => void;",
            "runExpenseAudit: () => void;\n  runAgingReview: () => void;\n  runTrialBalanceReview: () => void;",
        )
    elif "runFixedAssetAudit: () => void;" in page:
        page = page.replace(
            "runExpenseAudit: () => void;\n  runFixedAssetAudit: () => void;",
            "runExpenseAudit: () => void;\n  runAgingReview: () => void;\n  runFixedAssetAudit: () => void;",
        )

# Module option
if 'key: "aging"' not in page:
    expense_option = r'''    {
      key: "expense",
      label: "Expense Audit",
      description: "Checks expense ledgers for duplicate vouchers, high-value spends, cash expenses, weak narration, and discretionary spend.",
      run: runExpenseAudit,
    },'''
    aging_option = expense_option + r'''
    {
      key: "aging",
      label: "Receivables/Payables Aging",
      description: "Reviews debtor/creditor aging and open-item reports for overdue balances, missing due dates, old receivables, and payable confirmation risks.",
      run: runAgingReview,
    },'''
    page = page.replace(expense_option, aging_option)

# Format audit type
if 'if (type === "aging_review") return "Receivables/Payables Aging";' not in page:
    if 'if (type === "trial_balance_review") return "Trial Balance Review";' in page:
        page = page.replace(
            'if (type === "trial_balance_review") return "Trial Balance Review";',
            'if (type === "aging_review") return "Receivables/Payables Aging";\n  if (type === "trial_balance_review") return "Trial Balance Review";',
        )
    elif 'if (type === "fixed_asset_audit") return "Fixed Asset Audit";' in page:
        page = page.replace(
            'if (type === "fixed_asset_audit") return "Fixed Asset Audit";',
            'if (type === "aging_review") return "Receivables/Payables Aging";\n  if (type === "fixed_asset_audit") return "Fixed Asset Audit";',
        )

# Coverage checked records
page = page.replace(
    "coverageSource?.trial_balance_records_checked ??\n    0;",
    "coverageSource?.trial_balance_records_checked ??\n    coverageSource?.aging_records_checked ??\n    0;",
)

page = page.replace(
    "coverageSource?.fixed_asset_records_checked ??\n    0;",
    "coverageSource?.fixed_asset_records_checked ??\n    coverageSource?.aging_records_checked ??\n    0;",
)

# Infer module
page = re.sub(
    r"function inferRecommendedAuditModule\(files\?: UploadedFile\[\]\) \{[\s\S]*?\n\}",
    r'''function inferRecommendedAuditModule(files?: UploadedFile[]) {
  if (!files || !files.length) return "purchase";

  const candidates = files
    .filter((file) => file.status === "parsed" || file.status === "uploaded")
    .sort((a, b) => b.id - a.id);

  const latest = candidates[0] ?? files[files.length - 1];
  const type = latest?.file_type?.toLowerCase() ?? "";

  if (type.includes("aging") || type.includes("receivable") || type.includes("payable") || type.includes("outstanding") || type.includes("open_items")) return "aging";
  if (type.includes("trial_balance") || type.includes("financial_statement") || type.includes("fs_trial")) return "trial_balance";
  if (type.includes("fixed_asset") || type.includes("asset_register") || type.includes("depreciation") || type.includes("sap_asset") || type.includes("tally_fixed")) return "fixed_asset";
  if (type.includes("tds")) return "tds";
  if (type.includes("gstr") || type.includes("gst_2b") || type.includes("gstr_2b")) return "gst";
  if (type.includes("sales") || type.includes("customer")) return "sales";
  if (type.includes("expense")) return "expense";
  if (type.includes("sap_gl") || type.includes("ledger_vouchers")) return "ledger";
  if (type.includes("bank") || type.includes("cash_bank") || type.includes("tally_bank")) return "bank";
  if (type.includes("purchase") || type.includes("vendor")) return "purchase";

  return "purchase";
}''',
    page,
)

FRONTEND.write_text(page, encoding="utf-8")

# ----------------------------------------------------
# 5. Sample aging data
# ----------------------------------------------------

(SAMPLE_DIR / "receivables_aging_edge_cases.csv").write_text(
"""Invoice No,Invoice Date,Due Date,Customer Name,Outstanding Amount,Days Overdue,Narration
AR-001,01-04-2025,30-04-2025,Good Customer,25000,20,Normal receivable
AR-002,01-01-2025,31-01-2025,Old Customer,150000,120,Old receivable over 90 days
AR-003,01-09-2024,30-09-2024,Very Old Customer,650000,240,Very old high-value receivable
AR-004,10-03-2025,,No Due Date Customer,50000,,Missing due date
,15-03-2025,15-04-2025,No Invoice Customer,30000,80,Missing invoice reference
AR-006,20-03-2025,20-04-2025,,40000,70,Missing party
AR-007,01-04-2025,30-04-2025,Credit Balance Customer,-12000,30,Negative outstanding
AR-008,01-04-2025,30-04-2025,Zero Balance Customer,0,10,Zero outstanding
AR-009,01-02-2025,28-02-2025,Round Balance Customer,100000,100,Round old balance
""",
encoding="utf-8",
)

(SAMPLE_DIR / "payables_aging_edge_cases.csv").write_text(
"""Bill No,Bill Date,Due Date,Vendor Name,Outstanding Amount,Days Overdue,Narration
AP-001,01-04-2025,30-04-2025,Normal Vendor,40000,20,Normal payable
AP-002,01-10-2024,31-10-2024,Old Vendor,250000,210,Old payable over 180 days
AP-003,01-01-2025,31-01-2025,High Value Vendor,700000,120,High-value payable
AP-004,10-03-2025,,No Due Date Vendor,50000,,Missing due date
,15-03-2025,15-04-2025,No Bill Vendor,30000,80,Missing reference
AP-006,20-03-2025,20-04-2025,,40000,70,Missing vendor
AP-007,01-04-2025,30-04-2025,Debit Balance Vendor,-15000,30,Negative payable
AP-008,01-04-2025,30-04-2025,Round Vendor,100000,95,Round payable
""",
encoding="utf-8",
)

print("Receivables/Payables Aging module applied.")
print("Updated:")
print(f"- {CHECKS_DIR / 'aging_checks.py'}")
print(f"- {RUNNER}")
print(f"- {AUDIT_RUNS}")
print(f"- {FRONTEND}")
print(f"- {SAMPLE_DIR / 'receivables_aging_edge_cases.csv'}")
print(f"- {SAMPLE_DIR / 'payables_aging_edge_cases.csv'}")