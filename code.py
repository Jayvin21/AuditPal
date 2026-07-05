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
# 1. Trial balance / financial statement checks
# ----------------------------------------------------

(CHECKS_DIR / "trial_balance_checks.py").write_text(
r'''from decimal import Decimal, InvalidOperation


ASSET_KEYWORDS = [
    "cash", "bank", "debtor", "receivable", "asset", "fixed asset", "inventory",
    "stock", "advance", "deposit", "loan given", "prepaid"
]

LIABILITY_KEYWORDS = [
    "creditor", "payable", "liability", "loan", "unsecured loan", "secured loan",
    "capital", "provision", "duties", "tax payable", "gst payable", "tds payable"
]

INCOME_KEYWORDS = [
    "sales", "revenue", "income", "interest received", "commission received"
]

EXPENSE_KEYWORDS = [
    "expense", "purchase", "salary", "wages", "rent", "professional fees",
    "repairs", "maintenance", "depreciation", "travelling", "office"
]

SUSPENSE_KEYWORDS = ["suspense", "temporary", "dummy", "unknown", "unclassified"]
CASH_BANK_KEYWORDS = ["cash", "bank"]
LOAN_ADVANCE_KEYWORDS = ["loan", "advance", "deposit"]


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


def _ledger_name(record):
    return (
        getattr(record, "party_name", None)
        or _raw(record, "Ledger Name", "Account Name", "Account", "Particulars", "G/L Account", "GL Account", "Ledger")
        or ""
    )


def _group(record):
    return _raw(record, "Group", "Primary Group", "Schedule", "FS Group", "Classification", "Nature") or ""


def _debit(record):
    return _amount(_raw(record, "Debit", "Debit Balance", "Dr", "Dr Balance"))


def _credit(record):
    return _amount(_raw(record, "Credit", "Credit Balance", "Cr", "Cr Balance"))


def _closing_balance(record):
    direct = _amount(
        _raw(
            record,
            "Closing Balance",
            "Balance",
            "Amount",
            "Closing",
            "Net Balance",
            "Current Year Balance",
        )
    )

    if direct is not None:
        return direct

    debit = _debit(record)
    credit = _credit(record)

    if debit is not None or credit is not None:
        return (debit or 0) - (credit or 0)

    return _amount(getattr(record, "amount", None))


def _balance_side(balance):
    if balance is None:
        return ""
    if balance > 0:
        return "debit"
    if balance < 0:
        return "credit"
    return "zero"


def _classification_text(record):
    return " ".join([
        _lower(_ledger_name(record)),
        _lower(_group(record)),
        _lower(_raw(record, "Description", "Narration", "Text") or ""),
    ])


def _expected_nature(text):
    if any(keyword in text for keyword in ASSET_KEYWORDS):
        return "asset"
    if any(keyword in text for keyword in LIABILITY_KEYWORDS):
        return "liability"
    if any(keyword in text for keyword in INCOME_KEYWORDS):
        return "income"
    if any(keyword in text for keyword in EXPENSE_KEYWORDS):
        return "expense"
    return "unknown"


def _title(base, record):
    ledger = _ledger_name(record)
    balance = _closing_balance(record)
    bits = []

    if ledger:
        bits.append(ledger)
    if balance is not None:
        bits.append(f"₹{abs(balance):,.0f} { _balance_side(balance) }")

    if not bits:
        return base

    return f"{base} — {' · '.join(bits[:2])}"


def _finding(record, finding_type, risk_level, title, description, extra=None):
    balance = _closing_balance(record)

    evidence = {
        "record_id": getattr(record, "id", None),
        "source_row": getattr(record, "source_row", None),
        "ledger_name": _ledger_name(record),
        "group": _group(record),
        "closing_balance": balance,
        "balance_side": _balance_side(balance),
        "debit": _debit(record),
        "credit": _credit(record),
        "document_id": getattr(record, "document_id", None),
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


def run_trial_balance_checks(records):
    findings = []

    total_debit_balance = 0
    total_credit_balance = 0

    for record in records:
        ledger = _ledger_name(record)
        text = _classification_text(record)
        expected = _expected_nature(text)
        balance = _closing_balance(record)
        side = _balance_side(balance)

        if not ledger:
            findings.append(_finding(
                record,
                "missing_ledger_name_trial_balance",
                "high",
                "Missing ledger/account name",
                "Trial balance row does not contain a usable ledger/account name.",
            ))

        if balance is None:
            findings.append(_finding(
                record,
                "missing_trial_balance_amount",
                "high",
                "Missing trial balance amount",
                "Trial balance row does not contain debit, credit, or closing balance amount.",
            ))
            continue

        if balance > 0:
            total_debit_balance += balance
        elif balance < 0:
            total_credit_balance += abs(balance)

        if any(keyword in text for keyword in SUSPENSE_KEYWORDS) and abs(balance) > 0:
            findings.append(_finding(
                record,
                "suspense_balance_present",
                "high",
                "Suspense/temporary account has balance",
                "Suspense, temporary, dummy, unknown, or unclassified ledger has a non-zero balance.",
                {"classification_text": text},
            ))

        if any(keyword in text for keyword in CASH_BANK_KEYWORDS) and balance < 0:
            findings.append(_finding(
                record,
                "negative_cash_or_bank_balance",
                "high",
                "Negative cash/bank balance",
                "Cash or bank ledger has credit/negative balance. Review overdraft classification, bank reconciliation, or posting error.",
                {"classification_text": text},
            ))

        if expected == "asset" and side == "credit":
            findings.append(_finding(
                record,
                "asset_ledger_credit_balance",
                "medium",
                "Asset ledger has credit balance",
                "Ledger appears to be an asset but has a credit balance. Review classification and postings.",
                {"expected_nature": expected},
            ))

        if expected == "liability" and side == "debit":
            findings.append(_finding(
                record,
                "liability_ledger_debit_balance",
                "medium",
                "Liability ledger has debit balance",
                "Ledger appears to be a liability but has a debit balance. Review classification, advances, or reversal postings.",
                {"expected_nature": expected},
            ))

        if expected == "income" and side == "debit":
            findings.append(_finding(
                record,
                "income_ledger_debit_balance",
                "medium",
                "Income ledger has debit balance",
                "Ledger appears to be income/revenue but has a debit balance. Review returns, reversals, or classification.",
                {"expected_nature": expected},
            ))

        if expected == "expense" and side == "credit":
            findings.append(_finding(
                record,
                "expense_ledger_credit_balance",
                "medium",
                "Expense ledger has credit balance",
                "Ledger appears to be expense but has a credit balance. Review reversals, provisions, or classification.",
                {"expected_nature": expected},
            ))

        if abs(balance) >= 500000:
            findings.append(_finding(
                record,
                "high_value_trial_balance_ledger",
                "medium",
                "High-value trial balance ledger",
                "Ledger balance is above ₹5,00,000. Consider materiality, variance, and supporting schedule review.",
                {"balance": balance},
            ))

        if abs(balance) >= 10000 and abs(balance) % 1000 == 0:
            findings.append(_finding(
                record,
                "round_number_trial_balance_ledger",
                "low",
                "Round-number ledger balance",
                "Ledger balance is a round number. This can be normal but may indicate manual estimate or provision.",
                {"balance": balance},
            ))

        if any(keyword in text for keyword in LOAN_ADVANCE_KEYWORDS) and abs(balance) >= 100000:
            findings.append(_finding(
                record,
                "loan_advance_deposit_balance_review",
                "medium",
                "Loan/advance/deposit balance review",
                "Ledger appears to involve loan, advance, or deposit balance. Verify confirmation, classification, and recoverability.",
                {"classification_text": text, "balance": balance},
            ))

    difference = round(abs(total_debit_balance - total_credit_balance), 2)

    if difference > 1:
        pseudo_record = records[0] if records else None
        if pseudo_record:
            findings.append(_finding(
                pseudo_record,
                "trial_balance_not_balanced",
                "high",
                "Trial balance debit/credit totals do not match",
                "Total debit balances and total credit balances do not agree. Review export format, missing rows, or mapping.",
                {
                    "total_debit_balance": round(total_debit_balance, 2),
                    "total_credit_balance": round(total_credit_balance, 2),
                    "difference": difference,
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

if "from app.services.audit_engine.checks.trial_balance_checks import run_trial_balance_checks" not in runner:
    if "from app.services.audit_engine.checks.fixed_asset_checks import run_fixed_asset_checks" in runner:
        runner = runner.replace(
            "from app.services.audit_engine.checks.fixed_asset_checks import run_fixed_asset_checks",
            "from app.services.audit_engine.checks.fixed_asset_checks import run_fixed_asset_checks\nfrom app.services.audit_engine.checks.trial_balance_checks import run_trial_balance_checks",
        )
    else:
        runner = runner.replace(
            "from app.services.audit_engine.checks.ledger_scrutiny_checks import run_ledger_scrutiny_checks",
            "from app.services.audit_engine.checks.ledger_scrutiny_checks import run_ledger_scrutiny_checks\nfrom app.services.audit_engine.checks.trial_balance_checks import run_trial_balance_checks",
        )

if "TRIAL_BALANCE_FILE_TYPES" not in runner:
    runner += '''

TRIAL_BALANCE_FILE_TYPES = {
    "trial_balance",
    "tally_trial_balance",
    "sap_trial_balance",
    "financial_statement",
    "fs_trial_balance",
}
'''

if "def run_trial_balance_review" not in runner:
    tb_function = r'''

def run_trial_balance_review(workspace_id: int, db: Session) -> dict:
    parse_summary = parse_workspace_files(workspace_id, db, force_reparse=False)

    records = (
        db.query(ExtractedRecord)
        .filter(ExtractedRecord.workspace_id == workspace_id)
        .all()
    )

    trial_balance_records = [
        record for record in records
        if record.record_type.lower() in TRIAL_BALANCE_FILE_TYPES
    ]

    clear_findings(workspace_id, db)

    if not trial_balance_records:
        audit_run = AuditRun(
            workspace_id=workspace_id,
            audit_type="trial_balance_review",
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
            "message": "Trial balance review needs a trial_balance, Tally trial balance, SAP trial balance, or financial statement file.",
            "parse_summary": parse_summary,
            "coverage": {
                "total_records": len(records),
                "trial_balance_records_checked": 0,
                "unchecked_records": len(records),
                "issues_found": 0,
            },
        }

    finding_payloads = run_trial_balance_checks(trial_balance_records)

    audit_run = AuditRun(
        workspace_id=workspace_id,
        audit_type="trial_balance_review",
        status="completed",
        total_records=len(trial_balance_records),
        checked_records=len(trial_balance_records),
        issues_found=len(finding_payloads),
        unchecked_records=max(0, len(records) - len(trial_balance_records)),
    )

    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)

    save_findings(workspace_id, audit_run.id, finding_payloads, db)

    return {
        "audit_run_id": audit_run.id,
        "status": audit_run.status,
        "message": "Trial balance review completed using uploaded trial balance records",
        "parse_summary": parse_summary,
        "coverage": {
            "total_records": len(records),
            "trial_balance_records_checked": len(trial_balance_records),
            "unchecked_records": audit_run.unchecked_records,
            "issues_found": len(finding_payloads),
            "risk_counts": risk_counts(finding_payloads),
        },
    }
'''
    if "\n\ndef run_fixed_asset_audit" in runner:
        runner = runner.replace("\n\ndef run_fixed_asset_audit", tb_function + "\n\ndef run_fixed_asset_audit")
    elif "\n\ndef run_tds_review" in runner:
        runner = runner.replace("\n\ndef run_tds_review", tb_function + "\n\ndef run_tds_review")
    else:
        runner += tb_function

RUNNER.write_text(runner, encoding="utf-8")

# ----------------------------------------------------
# 3. Patch audit_runs.py
# ----------------------------------------------------

routes = AUDIT_RUNS.read_text(encoding="utf-8")

if "run_trial_balance_review" not in routes:
    if "run_fixed_asset_audit," in routes:
        routes = routes.replace(
            "run_fixed_asset_audit,",
            "run_fixed_asset_audit,\n    run_trial_balance_review,",
        )
    else:
        routes = routes.replace(
            "run_tds_review,",
            "run_tds_review,\n    run_trial_balance_review,",
        )

if 'run-trial-balance-review' not in routes:
    endpoint = r'''

@router.post("/{workspace_id}/run-trial-balance-review")
def run_real_trial_balance_review(workspace_id: int, db: Session = Depends(get_db)):
    try:
        return run_trial_balance_review(workspace_id=workspace_id, db=db)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Trial balance review failed: {str(exc)}")
'''
    if '\n\n@router.post("/{workspace_id}/run-fixed-asset-audit")' in routes:
        routes = routes.replace(
            '\n\n@router.post("/{workspace_id}/run-fixed-asset-audit")',
            endpoint + '\n\n@router.post("/{workspace_id}/run-fixed-asset-audit")',
        )
    elif '\n\n@router.post("/{workspace_id}/run-tds-review")' in routes:
        routes = routes.replace(
            '\n\n@router.post("/{workspace_id}/run-tds-review")',
            endpoint + '\n\n@router.post("/{workspace_id}/run-tds-review")',
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

if "trial_balance_records_checked?: number;" not in page:
    page = page.replace(
        "fixed_asset_records_checked?: number;",
        "fixed_asset_records_checked?: number;\n    trial_balance_records_checked?: number;",
    )

# Add Tally/SAP trial balance options
if '<option value="tally_trial_balance">Tally Trial Balance</option>' not in page:
    page = page.replace(
        '<option value="trial_balance">Trial Balance</option>',
        '''<option value="tally_trial_balance">Tally Trial Balance</option>
            <option value="sap_trial_balance">SAP Trial Balance</option>
            <option value="financial_statement">Financial Statement</option>
            <option value="trial_balance">Trial Balance</option>''',
    )

# Add run function
if "async function runTrialBalanceReview()" not in page:
    fn = r'''
  async function runTrialBalanceReview() {
    setBusy(true);
    setStatusMessage("Running trial balance review...");

    try {
      const res = await api.post(`/audit-runs/${workspaceId}/run-trial-balance-review`);
      setAuditSummary(res.data);
      setSelectedAuditRunId(res.data.audit_run_id);
      setStatusMessage("Trial balance review completed.");
      await refreshAll();
      setActiveSection("findings");
    } catch {
      setStatusMessage("Trial balance review failed.");
    } finally {
      setBusy(false);
    }
  }

'''
    if "  async function runFixedAssetAudit()" in page:
        page = page.replace("  async function runFixedAssetAudit()", fn + "  async function runFixedAssetAudit()")
    else:
        page = page.replace("  async function runTdsReview()", fn + "  async function runTdsReview()")

# Pass prop
if "runTrialBalanceReview={runTrialBalanceReview}" not in page:
    if "runFixedAssetAudit={runFixedAssetAudit}" in page:
        page = page.replace(
            "runExpenseAudit={runExpenseAudit}\n                runFixedAssetAudit={runFixedAssetAudit}",
            "runExpenseAudit={runExpenseAudit}\n                runTrialBalanceReview={runTrialBalanceReview}\n                runFixedAssetAudit={runFixedAssetAudit}",
        )
    else:
        page = page.replace(
            "runExpenseAudit={runExpenseAudit}\n                runTdsReview={runTdsReview}",
            "runExpenseAudit={runExpenseAudit}\n                runTrialBalanceReview={runTrialBalanceReview}\n                runTdsReview={runTdsReview}",
        )

# Destructure prop
if "runTrialBalanceReview," not in page:
    if "runFixedAssetAudit," in page:
        page = page.replace(
            "runExpenseAudit,\n  runFixedAssetAudit,",
            "runExpenseAudit,\n  runTrialBalanceReview,\n  runFixedAssetAudit,",
        )
    else:
        page = page.replace(
            "runExpenseAudit,\n  runTdsReview,",
            "runExpenseAudit,\n  runTrialBalanceReview,\n  runTdsReview,",
        )

# Prop type
if "runTrialBalanceReview: () => void;" not in page:
    if "runFixedAssetAudit: () => void;" in page:
        page = page.replace(
            "runExpenseAudit: () => void;\n  runFixedAssetAudit: () => void;",
            "runExpenseAudit: () => void;\n  runTrialBalanceReview: () => void;\n  runFixedAssetAudit: () => void;",
        )
    else:
        page = page.replace(
            "runExpenseAudit: () => void;\n  runTdsReview: () => void;",
            "runExpenseAudit: () => void;\n  runTrialBalanceReview: () => void;\n  runTdsReview: () => void;",
        )

# Module option
if 'key: "trial_balance"' not in page:
    expense_option = r'''    {
      key: "expense",
      label: "Expense Audit",
      description: "Checks expense ledgers for duplicate vouchers, high-value spends, cash expenses, weak narration, and discretionary spend.",
      run: runExpenseAudit,
    },'''
    tb_option = expense_option + r'''
    {
      key: "trial_balance",
      label: "Trial Balance Review",
      description: "Reviews trial balance and financial statement ledgers for classification issues, abnormal balances, suspense accounts, and material balances.",
      run: runTrialBalanceReview,
    },'''
    page = page.replace(expense_option, tb_option)

# Format audit type
if 'if (type === "trial_balance_review") return "Trial Balance Review";' not in page:
    if 'if (type === "fixed_asset_audit") return "Fixed Asset Audit";' in page:
        page = page.replace(
            'if (type === "fixed_asset_audit") return "Fixed Asset Audit";',
            'if (type === "trial_balance_review") return "Trial Balance Review";\n  if (type === "fixed_asset_audit") return "Fixed Asset Audit";',
        )
    else:
        page = page.replace(
            'if (type === "tds_review") return "TDS Review";',
            'if (type === "trial_balance_review") return "Trial Balance Review";\n  if (type === "tds_review") return "TDS Review";',
        )

# Coverage checked records
page = page.replace(
    "coverageSource?.fixed_asset_records_checked ??\n    0;",
    "coverageSource?.fixed_asset_records_checked ??\n    coverageSource?.trial_balance_records_checked ??\n    0;",
)

page = page.replace(
    "coverageSource?.tds_records_checked ??\n    0;",
    "coverageSource?.tds_records_checked ??\n    coverageSource?.trial_balance_records_checked ??\n    0;",
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
# 5. Sample trial balance data
# ----------------------------------------------------

(SAMPLE_DIR / "trial_balance_edge_cases.csv").write_text(
"""Ledger Name,Group,Debit,Credit,Narration
Cash in Hand,Current Assets,0,25000,Negative cash balance
HDFC Bank,Current Assets,100000,0,Normal bank balance
Trade Debtors,Current Assets,350000,0,Receivables balance
Trade Creditors,Current Liabilities,50000,0,Debit balance in liability ledger
Sales Revenue,Income,25000,0,Income ledger debit balance
Rent Expense,Expenses,0,10000,Expense ledger credit balance
Suspense Account,Suspense,75000,0,Suspense balance open
Unsecured Loan,Loans,200000,0,Loan ledger debit balance
Fixed Assets,Fixed Assets,750000,0,Material asset balance
Provision for Expenses,Current Liabilities,0,300000,Provision balance
Round Balance Expense,Expenses,100000,0,Round number balance
,Current Assets,20000,0,Missing ledger name
Inventory Stock,Current Assets,0,5000,Credit balance in asset ledger
GST Payable,Current Liabilities,0,90000,Normal payable
Misc Income,Income,0,15000,Normal income credit
""",
encoding="utf-8",
)

print("Trial Balance Review module applied.")
print("Updated:")
print(f"- {CHECKS_DIR / 'trial_balance_checks.py'}")
print(f"- {RUNNER}")
print(f"- {AUDIT_RUNS}")
print(f"- {FRONTEND}")
print(f"- {SAMPLE_DIR / 'trial_balance_edge_cases.csv'}")