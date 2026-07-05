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
# 1. Fixed assets audit checks
# ----------------------------------------------------

(CHECKS_DIR / "fixed_asset_checks.py").write_text(
r'''from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


REPAIRS_KEYWORDS = ["repair", "repairs", "maintenance", "servicing", "service", "renovation", "painting"]
DISPOSAL_KEYWORDS = ["sold", "sale", "disposed", "scrapped", "discarded", "write off", "written off"]
LAND_KEYWORDS = ["land", "freehold land"]
VEHICLE_KEYWORDS = ["vehicle", "car", "truck", "bike", "motor"]
COMPUTER_KEYWORDS = ["computer", "laptop", "server", "printer", "it equipment"]
FURNITURE_KEYWORDS = ["furniture", "fixture", "office equipment"]
PLANT_KEYWORDS = ["plant", "machinery", "machine", "equipment"]


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
        _raw(record, "Description", "Asset Description", "Narration", "Particulars", "Asset Name", "Text")
        or getattr(record, "description", None)
        or ""
    )


def _asset_id(record):
    return (
        _raw(record, "Asset ID", "Asset Code", "Asset No", "Asset Number", "FA Code", "Tag No")
        or getattr(record, "document_id", None)
        or ""
    )


def _asset_category(record):
    return (
        _raw(record, "Asset Category", "Category", "Block", "Asset Class", "Class", "Group")
        or getattr(record, "party_name", None)
        or ""
    )


def _cost(record):
    return _amount(
        _raw(
            record,
            "Cost",
            "Asset Cost",
            "Gross Block",
            "Original Cost",
            "Capitalized Amount",
            "Acquisition Value",
            "Purchase Value",
        )
        or getattr(record, "amount", None)
    )


def _depreciation(record):
    return _amount(
        _raw(
            record,
            "Depreciation",
            "Depreciation Amount",
            "Current Year Depreciation",
            "Dep for the Year",
            "Accumulated Depreciation",
            "Accum Dep",
        )
    )


def _wdv(record):
    return _amount(_raw(record, "WDV", "Net Block", "Carrying Amount", "Written Down Value", "Net Book Value"))


def _status(record):
    return _raw(record, "Status", "Asset Status", "Disposal Status") or ""


def _rate(record):
    value = _raw(record, "Depreciation Rate", "Dep Rate", "Rate", "Useful Life Rate")
    if value is None:
        return None
    text = str(value).replace("%", "").strip()
    return _amount(text)


def _expected_rate_band(category_text):
    text = category_text.lower()

    if any(keyword in text for keyword in LAND_KEYWORDS):
        return (0, 0)
    if any(keyword in text for keyword in COMPUTER_KEYWORDS):
        return (20, 80)
    if any(keyword in text for keyword in VEHICLE_KEYWORDS):
        return (10, 40)
    if any(keyword in text for keyword in FURNITURE_KEYWORDS):
        return (5, 25)
    if any(keyword in text for keyword in PLANT_KEYWORDS):
        return (5, 30)

    return (0, 60)


def _title(base, record):
    bits = []
    asset_id = _norm(_asset_id(record))
    category = _norm(_asset_category(record))
    cost = _cost(record)

    if asset_id:
        bits.append(asset_id)
    if category:
        bits.append(category)
    if cost is not None:
        bits.append(f"₹{cost:,.0f}")

    if not bits:
        return base

    return f"{base} — {' · '.join(bits[:3])}"


def _finding(record, finding_type, risk_level, title, description, extra=None):
    evidence = {
        "record_id": getattr(record, "id", None),
        "source_row": getattr(record, "source_row", None),
        "asset_id": _asset_id(record),
        "document_id": getattr(record, "document_id", None),
        "asset_category": _asset_category(record),
        "asset_description": _description(record),
        "capitalization_date": _date_string(getattr(record, "transaction_date", None)),
        "cost": _cost(record),
        "depreciation": _depreciation(record),
        "wdv": _wdv(record),
        "depreciation_rate": _rate(record),
        "status": _status(record),
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


def run_fixed_asset_checks(records):
    findings = []
    asset_index = defaultdict(list)
    invoice_index = defaultdict(list)

    for record in records:
        asset_id = _norm(_asset_id(record))
        document_id = _norm(getattr(record, "document_id", None))
        category = _asset_category(record)
        category_lower = _lower(category)
        description = _description(record)
        description_lower = _lower(description)
        combined_text = " ".join([category_lower, description_lower, _lower(_status(record))])

        cost = _cost(record)
        dep = _depreciation(record)
        wdv = _wdv(record)
        dep_rate = _rate(record)
        cap_date = getattr(record, "transaction_date", None)

        if asset_id:
            asset_index[asset_id.lower()].append(record)

        if document_id:
            invoice_index[document_id.lower()].append(record)

        if not asset_id:
            findings.append(_finding(
                record,
                "missing_asset_id",
                "high",
                "Missing fixed asset ID/code",
                "Fixed asset record has no asset ID/code/tag. This weakens physical verification and register tracking.",
            ))

        if not category:
            findings.append(_finding(
                record,
                "missing_asset_category",
                "medium",
                "Missing asset category/class",
                "Fixed asset record has no asset category/class/block. Depreciation and classification cannot be reviewed reliably.",
            ))

        if not cap_date:
            findings.append(_finding(
                record,
                "missing_capitalization_date",
                "high",
                "Missing capitalization/acquisition date",
                "Fixed asset record does not have a capitalization/acquisition date.",
            ))

        if cost is None:
            findings.append(_finding(
                record,
                "missing_asset_cost",
                "high",
                "Missing fixed asset cost",
                "Fixed asset record does not have a usable cost/capitalized amount.",
            ))
            continue

        if cost <= 0:
            findings.append(_finding(
                record,
                "non_positive_asset_cost",
                "high",
                "Non-positive fixed asset cost",
                "Fixed asset record has zero or negative cost. Review classification and posting.",
                {"cost": cost},
            ))

        if cost >= 100000:
            findings.append(_finding(
                record,
                "high_value_asset_addition",
                "medium",
                "High-value fixed asset addition",
                "Asset addition is above ₹1,00,000. Verify invoice, approval, capitalization date, and physical existence.",
                {"cost": cost},
            ))

        if _is_year_end(cap_date):
            findings.append(_finding(
                record,
                "year_end_asset_capitalization",
                "medium",
                "Year-end asset capitalization",
                "Asset was capitalized near financial year end. Verify put-to-use date, invoice, and depreciation start date.",
            ))

        if any(keyword in combined_text for keyword in REPAIRS_KEYWORDS) and cost >= 10000:
            findings.append(_finding(
                record,
                "repairs_or_maintenance_capitalized",
                "medium",
                "Repairs/maintenance may be capitalized",
                "Asset description suggests repairs/maintenance/service expense. Verify whether capitalization is appropriate.",
                {"cost": cost, "description": description},
            ))

        if any(keyword in combined_text for keyword in DISPOSAL_KEYWORDS):
            findings.append(_finding(
                record,
                "asset_disposal_indicator",
                "medium",
                "Asset disposal/sale/write-off indicator",
                "Asset record suggests sale, disposal, scrap, or write-off. Verify sale proceeds, gain/loss, GST, and register removal.",
                {"status": _status(record), "description": description},
            ))

        if dep is None:
            if not any(keyword in category_lower for keyword in LAND_KEYWORDS):
                findings.append(_finding(
                    record,
                    "missing_depreciation",
                    "medium",
                    "Missing depreciation amount",
                    "Depreciable asset has no visible depreciation amount. Verify depreciation schedule.",
                    {"category": category},
                ))
        elif dep < 0:
            findings.append(_finding(
                record,
                "negative_depreciation",
                "high",
                "Negative depreciation amount",
                "Depreciation amount is negative. Review depreciation posting or reversal.",
                {"depreciation": dep},
            ))
        elif dep > cost:
            findings.append(_finding(
                record,
                "depreciation_exceeds_cost",
                "high",
                "Depreciation exceeds asset cost",
                "Depreciation amount is greater than asset cost. This is likely incorrect.",
                {"cost": cost, "depreciation": dep},
            ))

        if dep_rate is not None:
            low, high = _expected_rate_band(category)
            if dep_rate < low or dep_rate > high:
                findings.append(_finding(
                    record,
                    "unusual_depreciation_rate",
                    "medium",
                    "Unusual depreciation rate",
                    "Depreciation rate appears outside the expected broad range for this asset category.",
                    {
                        "category": category,
                        "depreciation_rate": dep_rate,
                        "expected_range": f"{low}% to {high}%",
                    },
                ))

        if wdv is not None:
            if wdv < 0:
                findings.append(_finding(
                    record,
                    "negative_wdv_or_net_block",
                    "high",
                    "Negative WDV/net block",
                    "Asset has negative written down value/net block. Review depreciation and disposal accounting.",
                    {"wdv": wdv},
                ))

            if wdv == 0 and not any(keyword in combined_text for keyword in DISPOSAL_KEYWORDS):
                findings.append(_finding(
                    record,
                    "fully_depreciated_asset_still_active",
                    "low",
                    "Fully depreciated asset still active",
                    "Asset has zero WDV but no visible disposal/write-off indicator. Consider physical verification and active-use status.",
                    {"wdv": wdv},
                ))

    for asset_id, asset_records in asset_index.items():
        if len(asset_records) > 1:
            first = asset_records[0]
            findings.append(_finding(
                first,
                "duplicate_asset_id",
                "high",
                "Duplicate fixed asset ID/code",
                "Same asset ID/code appears multiple times. Verify whether records are duplicate or represent valid componentization.",
                {
                    "asset_id": asset_id,
                    "duplicate_count": len(asset_records),
                    "source_rows": [getattr(record, "source_row", None) for record in asset_records],
                    "record_ids": [getattr(record, "id", None) for record in asset_records],
                },
            ))

    for invoice, invoice_records in invoice_index.items():
        if len(invoice_records) > 1:
            first = invoice_records[0]
            findings.append(_finding(
                first,
                "duplicate_asset_invoice_reference",
                "medium",
                "Duplicate asset invoice/reference",
                "Same invoice/reference appears across multiple asset records. Verify if this is valid split capitalization or duplicate booking.",
                {
                    "invoice": invoice,
                    "duplicate_count": len(invoice_records),
                    "source_rows": [getattr(record, "source_row", None) for record in invoice_records],
                    "record_ids": [getattr(record, "id", None) for record in invoice_records],
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

if "from app.services.audit_engine.checks.fixed_asset_checks import run_fixed_asset_checks" not in runner:
    if "from app.services.audit_engine.checks.tds_checks import run_tds_checks" in runner:
        runner = runner.replace(
            "from app.services.audit_engine.checks.tds_checks import run_tds_checks",
            "from app.services.audit_engine.checks.tds_checks import run_tds_checks\nfrom app.services.audit_engine.checks.fixed_asset_checks import run_fixed_asset_checks",
        )
    else:
        runner = runner.replace(
            "from app.services.audit_engine.checks.ledger_scrutiny_checks import run_ledger_scrutiny_checks",
            "from app.services.audit_engine.checks.ledger_scrutiny_checks import run_ledger_scrutiny_checks\nfrom app.services.audit_engine.checks.fixed_asset_checks import run_fixed_asset_checks",
        )

if "FIXED_ASSET_FILE_TYPES" not in runner:
    runner += '''

FIXED_ASSET_FILE_TYPES = {
    "fixed_asset_register",
    "fixed_assets",
    "asset_register",
    "depreciation_schedule",
    "sap_asset_register",
    "tally_fixed_assets",
}
'''

if "def run_fixed_asset_audit" not in runner:
    fixed_asset_function = r'''

def run_fixed_asset_audit(workspace_id: int, db: Session) -> dict:
    parse_summary = parse_workspace_files(workspace_id, db, force_reparse=False)

    records = (
        db.query(ExtractedRecord)
        .filter(ExtractedRecord.workspace_id == workspace_id)
        .all()
    )

    fixed_asset_records = [
        record for record in records
        if record.record_type.lower() in FIXED_ASSET_FILE_TYPES
    ]

    clear_findings(workspace_id, db)

    if not fixed_asset_records:
        audit_run = AuditRun(
            workspace_id=workspace_id,
            audit_type="fixed_asset_audit",
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
            "message": "Fixed asset audit needs a fixed asset register or depreciation schedule file.",
            "parse_summary": parse_summary,
            "coverage": {
                "total_records": len(records),
                "fixed_asset_records_checked": 0,
                "unchecked_records": len(records),
                "issues_found": 0,
            },
        }

    finding_payloads = run_fixed_asset_checks(fixed_asset_records)

    audit_run = AuditRun(
        workspace_id=workspace_id,
        audit_type="fixed_asset_audit",
        status="completed",
        total_records=len(fixed_asset_records),
        checked_records=len(fixed_asset_records),
        issues_found=len(finding_payloads),
        unchecked_records=max(0, len(records) - len(fixed_asset_records)),
    )

    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)

    save_findings(workspace_id, audit_run.id, finding_payloads, db)

    return {
        "audit_run_id": audit_run.id,
        "status": audit_run.status,
        "message": "Fixed asset audit completed using uploaded asset records",
        "parse_summary": parse_summary,
        "coverage": {
            "total_records": len(records),
            "fixed_asset_records_checked": len(fixed_asset_records),
            "unchecked_records": audit_run.unchecked_records,
            "issues_found": len(finding_payloads),
            "risk_counts": risk_counts(finding_payloads),
        },
    }
'''
    if "\n\ndef run_tds_review" in runner:
        runner = runner.replace("\n\ndef run_tds_review", fixed_asset_function + "\n\ndef run_tds_review")
    elif "\n\ndef run_ledger_scrutiny" in runner:
        runner = runner.replace("\n\ndef run_ledger_scrutiny", fixed_asset_function + "\n\ndef run_ledger_scrutiny")
    else:
        runner += fixed_asset_function

RUNNER.write_text(runner, encoding="utf-8")

# ----------------------------------------------------
# 3. Patch audit_runs.py
# ----------------------------------------------------

routes = AUDIT_RUNS.read_text(encoding="utf-8")

if "run_fixed_asset_audit" not in routes:
    if "run_tds_review," in routes:
        routes = routes.replace(
            "run_tds_review,",
            "run_tds_review,\n    run_fixed_asset_audit,",
        )
    else:
        routes = routes.replace(
            "run_ledger_scrutiny,",
            "run_ledger_scrutiny,\n    run_fixed_asset_audit,",
        )

if 'run-fixed-asset-audit' not in routes:
    endpoint = r'''

@router.post("/{workspace_id}/run-fixed-asset-audit")
def run_real_fixed_asset_audit(workspace_id: int, db: Session = Depends(get_db)):
    try:
        return run_fixed_asset_audit(workspace_id=workspace_id, db=db)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Fixed asset audit failed: {str(exc)}")
'''
    if '\n\n@router.post("/{workspace_id}/run-tds-review")' in routes:
        routes = routes.replace(
            '\n\n@router.post("/{workspace_id}/run-tds-review")',
            endpoint + '\n\n@router.post("/{workspace_id}/run-tds-review")',
        )
    elif '\n\n@router.post("/{workspace_id}/run-ledger-scrutiny")' in routes:
        routes = routes.replace(
            '\n\n@router.post("/{workspace_id}/run-ledger-scrutiny")',
            endpoint + '\n\n@router.post("/{workspace_id}/run-ledger-scrutiny")',
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

if "fixed_asset_records_checked?: number;" not in page:
    page = page.replace(
        "tds_records_checked?: number;",
        "tds_records_checked?: number;\n    fixed_asset_records_checked?: number;",
    )
    page = page.replace(
        "ledger_records_checked?: number;",
        "ledger_records_checked?: number;\n    fixed_asset_records_checked?: number;",
    )

# Add file type options
if '<option value="fixed_asset_register">Fixed Asset Register</option>' not in page:
    page = page.replace(
        '<option value="trial_balance">Trial Balance</option>',
        '''<option value="fixed_asset_register">Fixed Asset Register</option>
            <option value="depreciation_schedule">Depreciation Schedule</option>
            <option value="sap_asset_register">SAP Asset Register</option>
            <option value="tally_fixed_assets">Tally Fixed Assets</option>
            <option value="trial_balance">Trial Balance</option>''',
    )

# Add run function
if "async function runFixedAssetAudit()" not in page:
    fn = r'''
  async function runFixedAssetAudit() {
    setBusy(true);
    setStatusMessage("Running fixed asset audit...");

    try {
      const res = await api.post(`/audit-runs/${workspaceId}/run-fixed-asset-audit`);
      setAuditSummary(res.data);
      setSelectedAuditRunId(res.data.audit_run_id);
      setStatusMessage("Fixed asset audit completed.");
      await refreshAll();
      setActiveSection("findings");
    } catch {
      setStatusMessage("Fixed asset audit failed.");
    } finally {
      setBusy(false);
    }
  }

'''
    if "  async function runTdsReview()" in page:
        page = page.replace("  async function runTdsReview()", fn + "  async function runTdsReview()")
    else:
        page = page.replace("  async function runLedgerScrutiny()", fn + "  async function runLedgerScrutiny()")

# Pass prop into AuditSection call
if "runFixedAssetAudit={runFixedAssetAudit}" not in page:
    if "runTdsReview={runTdsReview}" in page:
        page = page.replace(
            "runExpenseAudit={runExpenseAudit}\n                runTdsReview={runTdsReview}",
            "runExpenseAudit={runExpenseAudit}\n                runFixedAssetAudit={runFixedAssetAudit}\n                runTdsReview={runTdsReview}",
        )
    else:
        page = page.replace(
            "runExpenseAudit={runExpenseAudit}\n                runLedgerScrutiny={runLedgerScrutiny}",
            "runExpenseAudit={runExpenseAudit}\n                runFixedAssetAudit={runFixedAssetAudit}\n                runLedgerScrutiny={runLedgerScrutiny}",
        )

# Add AuditSection destructuring prop
if "runFixedAssetAudit," not in page:
    if "runTdsReview," in page:
        page = page.replace(
            "runExpenseAudit,\n  runTdsReview,",
            "runExpenseAudit,\n  runFixedAssetAudit,\n  runTdsReview,",
        )
    else:
        page = page.replace(
            "runExpenseAudit,\n  runLedgerScrutiny,",
            "runExpenseAudit,\n  runFixedAssetAudit,\n  runLedgerScrutiny,",
        )

# Add AuditSection prop type
if "runFixedAssetAudit: () => void;" not in page:
    if "runTdsReview: () => void;" in page:
        page = page.replace(
            "runExpenseAudit: () => void;\n  runTdsReview: () => void;",
            "runExpenseAudit: () => void;\n  runFixedAssetAudit: () => void;\n  runTdsReview: () => void;",
        )
    else:
        page = page.replace(
            "runExpenseAudit: () => void;\n  runLedgerScrutiny: () => void;",
            "runExpenseAudit: () => void;\n  runFixedAssetAudit: () => void;\n  runLedgerScrutiny: () => void;",
        )

# Add module option
if 'key: "fixed_asset"' not in page:
    expense_option = r'''    {
      key: "expense",
      label: "Expense Audit",
      description: "Checks expense ledgers for duplicate vouchers, high-value spends, cash expenses, weak narration, and discretionary spend.",
      run: runExpenseAudit,
    },'''
    fixed_option = expense_option + r'''
    {
      key: "fixed_asset",
      label: "Fixed Asset Audit",
      description: "Reviews fixed asset registers for missing asset IDs, capitalization risk, depreciation issues, disposals, and duplicate asset references.",
      run: runFixedAssetAudit,
    },'''
    page = page.replace(expense_option, fixed_option)

# Format audit type
if 'if (type === "fixed_asset_audit") return "Fixed Asset Audit";' not in page:
    if 'if (type === "tds_review") return "TDS Review";' in page:
        page = page.replace(
            'if (type === "tds_review") return "TDS Review";',
            'if (type === "fixed_asset_audit") return "Fixed Asset Audit";\n  if (type === "tds_review") return "TDS Review";',
        )
    else:
        page = page.replace(
            'if (type === "ledger_scrutiny") return "Ledger Scrutiny";',
            'if (type === "fixed_asset_audit") return "Fixed Asset Audit";\n  if (type === "ledger_scrutiny") return "Ledger Scrutiny";',
        )

# Coverage checked records
page = page.replace(
    "coverageSource?.tds_records_checked ??\n    0;",
    "coverageSource?.tds_records_checked ??\n    coverageSource?.fixed_asset_records_checked ??\n    0;",
)

page = page.replace(
    "coverageSource?.ledger_records_checked ??\n    0;",
    "coverageSource?.ledger_records_checked ??\n    coverageSource?.fixed_asset_records_checked ??\n    0;",
)

# Infer fixed asset module
page = re.sub(
    r"function inferRecommendedAuditModule\(files\?: UploadedFile\[\]\) \{[\s\S]*?\n\}",
    r'''function inferRecommendedAuditModule(files?: UploadedFile[]) {
  if (!files || !files.length) return "purchase";

  const candidates = files
    .filter((file) => file.status === "parsed" || file.status === "uploaded")
    .sort((a, b) => b.id - a.id);

  const latest = candidates[0] ?? files[files.length - 1];
  const type = latest?.file_type?.toLowerCase() ?? "";

  if (type.includes("fixed_asset") || type.includes("asset_register") || type.includes("depreciation") || type.includes("sap_asset") || type.includes("tally_fixed")) return "fixed_asset";
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
# 5. Sample fixed asset data
# ----------------------------------------------------

(SAMPLE_DIR / "fixed_asset_register_edge_cases.csv").write_text(
"""Asset ID,Capitalization Date,Asset Category,Asset Description,Cost,Depreciation,Depreciation Rate,WDV,Status,Invoice No
FA-001,01-04-2025,Computer,Laptop for office,75000,30000,40,45000,Active,INV-FA-001
FA-002,31-03-2026,Plant and Machinery,Year end machine addition,250000,0,15,250000,Active,INV-FA-002
FA-003,15-04-2025,Land,Freehold land purchase,500000,10000,2,490000,Active,INV-FA-003
FA-004,20-04-2025,Vehicle,Company car,900000,120000,13.3,780000,Active,INV-FA-004
FA-005,25-04-2025,Repairs,Major repair capitalized as asset,60000,6000,10,54000,Active,INV-FA-005
FA-006,30-04-2025,Furniture,Office chairs,50000,,10,50000,Active,INV-FA-006
FA-007,05-05-2025,Computer,Old server,100000,100000,40,0,Active,INV-FA-007
FA-008,10-05-2025,Equipment,Scrapped equipment,80000,40000,15,40000,Scrapped,INV-FA-008
,12-05-2025,Computer,Missing asset id,45000,18000,40,27000,Active,INV-FA-009
FA-010,,Furniture,Missing capitalization date,30000,3000,10,27000,Active,INV-FA-010
FA-011,18-05-2025,,Missing asset category,35000,3500,10,31500,Active,INV-FA-011
FA-012,20-05-2025,Computer,Dep exceeds cost,50000,60000,120,-10000,Active,INV-FA-012
FA-012,20-05-2025,Computer,Duplicate asset id,50000,20000,40,30000,Active,INV-FA-013
FA-014,22-05-2025,Computer,Split invoice component,25000,10000,40,15000,Active,INV-SPLIT
FA-015,22-05-2025,Computer,Split invoice component duplicate,25000,10000,40,15000,Active,INV-SPLIT
""",
encoding="utf-8",
)

print("Fixed Asset Audit module applied.")
print("Updated:")
print(f"- {CHECKS_DIR / 'fixed_asset_checks.py'}")
print(f"- {RUNNER}")
print(f"- {AUDIT_RUNS}")
print(f"- {FRONTEND}")
print(f"- {SAMPLE_DIR / 'fixed_asset_register_edge_cases.csv'}")