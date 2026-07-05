from collections import defaultdict
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
