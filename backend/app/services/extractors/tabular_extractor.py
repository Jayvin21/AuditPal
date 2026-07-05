import os
import re
from typing import Any

import pandas as pd


COLUMN_ALIASES = {
    "document_id": [
        "invoice no", "invoice number", "inv no", "inv number", "bill no",
        "bill number", "voucher no", "voucher number", "document no",
        "document number", "ref no", "reference no", "reference number",
        "cheque no", "chq no", "transaction id", "utr", "utr no",
        "voucher no.",
        "vch no",
        "vch no.",
        "doc number",
        "assignment",
        "invoice reference",
        "supplier invoice no",
        "bill no.",
        "instrument no",
        "billing document",],
    "party_name": [
        "vendor", "vendor name", "supplier", "supplier name", "party",
        "party name", "customer", "customer name", "name", "ledger name",
        "beneficiary", "payee", "payer", "account name",
        "particulars",
        "name 1",
        "g/l account",
        "gl account",
        "cost center",
        "profit center",
        "trade/legal name",
        "legal name",],
    "transaction_date": [
        "date", "invoice date", "bill date", "voucher date", "posting date",
        "document date", "transaction date", "entry date", "value date"
    ],
    "amount": [
        "amount", "total", "total amount", "gross amount", "invoice amount",
        "bill amount", "net amount", "taxable value", "value", "grand total",
        "transaction amount",
        "gross total",
        "invoice value",
        "amount in local currency",
        "local currency amount",
        "inr amount",
        "debit/credit amount",],
    "debit_amount": [
        "debit", "debit amount", "withdrawal", "withdrawals", "dr", "paid",
        "payment", "payments", "amount debited",
        "paid amount",],
    "credit_amount": [
        "credit", "credit amount", "deposit", "deposits", "cr", "received",
        "receipt", "receipts", "amount credited",
        "received amount",],
    "gstin": [
        "gstin", "gst no", "gst number", "gstin/uin", "gstin uin",
        "supplier gstin", "vendor gstin", "gst",
        "party gstin",
        "gstin of supplier",],
    "description": [
        "description", "particulars", "narration", "details", "remarks",
        "item", "expense head", "transaction remarks",
        "text",
        "document header text",
        "voucher type",
        "supply type",
        "place of supply",
        "memo",],
}



EXTRA_COLUMN_ALIASES = {
    "supplier_gstin": [
        "supplier gstin", "gstin of supplier", "vendor gstin", "party gstin",
        "gstin/uin", "gstin uin",
    ],
    "customer_gstin": [
        "customer gstin", "recipient gstin", "buyer gstin",
    ],
    "taxable_value": [
        "taxable value", "taxable amount", "assessable value", "tax base",
    ],
    "invoice_value": [
        "invoice value", "gross total", "gross amount", "invoice amount",
        "bill amount", "total invoice value",
    ],
    "igst": ["igst", "igst amount", "integrated tax", "integrated tax amount"],
    "cgst": ["cgst", "cgst amount", "central tax", "central tax amount"],
    "sgst": ["sgst", "sgst amount", "state tax", "state tax amount"],
    "place_of_supply": ["place of supply", "pos", "state", "supply state"],
    "supply_type": ["supply type", "type of supply", "invoice type"],

    "pan": [
        "pan", "vendor pan", "supplier pan", "permanent account number",
        "pan no", "pan number",
    ],
    "tds_amount": [
        "tds amount", "tds deducted", "tax deducted", "withholding tax",
        "wht amount", "tds payable",
    ],
    "tds_section": [
        "tds section", "section", "tds nature", "withholding tax code",
        "wht code", "194c", "194j", "194a",
    ],
    "payment_nature": [
        "nature", "expense nature", "payment nature", "ledger name",
        "particulars",
    ],

    "asset_id": [
        "asset id", "asset code", "asset no", "asset number", "fa code",
        "tag no",
    ],
    "asset_category": [
        "asset category", "category", "block", "asset class", "class",
        "group",
    ],
    "asset_description": [
        "asset description", "description", "asset name", "particulars",
    ],
    "asset_cost": [
        "cost", "asset cost", "gross block", "original cost",
        "capitalized amount", "acquisition value", "purchase value",
    ],
    "depreciation": [
        "depreciation", "depreciation amount", "current year depreciation",
        "dep for the year", "accumulated depreciation", "accum dep",
    ],
    "depreciation_rate": [
        "depreciation rate", "dep rate", "rate", "useful life rate",
    ],
    "wdv": [
        "wdv", "net block", "carrying amount", "written down value",
        "net book value",
    ],
    "asset_status": ["status", "asset status", "disposal status"],

    "ledger_name": [
        "ledger name", "account name", "account", "particulars",
        "g/l account", "gl account", "ledger",
    ],
    "ledger_group": [
        "group", "primary group", "schedule", "fs group",
        "classification", "nature",
    ],
    "opening_balance": ["opening balance", "opening", "opening bal"],
    "debit_balance": ["debit", "debit balance", "dr", "dr balance"],
    "credit_balance": ["credit", "credit balance", "cr", "cr balance"],
    "closing_balance": [
        "closing balance", "balance", "closing", "net balance",
        "current year balance",
    ],

    "invoice_date": [
        "invoice date", "bill date", "document date", "posting date", "date",
    ],
    "due_date": ["due date", "payment due date", "net due date", "aging date", "due"],
    "days_overdue": ["days overdue", "overdue days", "age", "aging days", "days"],
    "outstanding_amount": [
        "outstanding", "outstanding amount", "balance", "closing balance",
        "open amount", "amount due", "net due", "amount",
    ],
    "aging_bucket": ["aging bucket", "bucket", "ageing bucket"],
    "party_type": ["party type", "customer vendor type", "type", "nature"],

    "ocr_confidence": [
        "ocr confidence", "confidence", "confidence score",
        "extraction confidence",
    ],
    "document_type": ["document type", "doc type", "invoice type", "bill type"],
    "extracted_text": ["ocr text", "extracted text", "text", "description"],
    "support_file_name": ["support file name", "file name", "filename", "source file"],

    "bank_reference": ["bank reference", "utr", "utr no", "transaction id", "reference no"],
    "cheque_no": ["cheque no", "chq no", "instrument no"],
    "value_date": ["value date", "bank date"],
}

for field, aliases in EXTRA_COLUMN_ALIASES.items():
    COLUMN_ALIASES[field] = aliases

STANDARD_FIELDS = [
    "document_id",
    "party_name",
    "transaction_date",
    "amount",
    "debit_amount",
    "credit_amount",
    "gstin",
    "description",
]

ALLOWED_MAPPING_FIELDS = set(STANDARD_FIELDS) | set(EXTRA_COLUMN_ALIASES.keys())

TEXT_EXTRA_FIELDS = {
    "supplier_gstin",
    "customer_gstin",
    "place_of_supply",
    "supply_type",
    "pan",
    "tds_section",
    "payment_nature",
    "asset_id",
    "asset_category",
    "asset_description",
    "asset_status",
    "ledger_name",
    "ledger_group",
    "aging_bucket",
    "party_type",
    "document_type",
    "extracted_text",
    "support_file_name",
    "bank_reference",
    "cheque_no",
}

DATE_EXTRA_FIELDS = {
    "invoice_date",
    "due_date",
    "value_date",
}

AMOUNT_EXTRA_FIELDS = set(EXTRA_COLUMN_ALIASES.keys()) - TEXT_EXTRA_FIELDS - DATE_EXTRA_FIELDS


def normalize_column_name(value: str) -> str:
    value = str(value).strip().lower()
    value = re.sub(r"[_\-/]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value


def find_header_row(df_preview: pd.DataFrame) -> int:
    best_index = 0
    best_score = -1

    keywords = set()
    for aliases in COLUMN_ALIASES.values():
        keywords.update(aliases)

    for idx, row in df_preview.iterrows():
        score = 0
        values = [normalize_column_name(cell) for cell in row.tolist() if str(cell).strip() != "nan"]

        for value in values:
            for keyword in keywords:
                if keyword == value or keyword in value:
                    score += 1

        if score > best_score:
            best_score = score
            best_index = idx

    return int(best_index)


def map_columns(columns: list[str]) -> dict[str, str]:
    normalized_lookup = {normalize_column_name(col): col for col in columns}
    mapping: dict[str, str] = {}

    for standard_field, aliases in COLUMN_ALIASES.items():
        for normalized_col, original_col in normalized_lookup.items():
            for alias in aliases:
                alias_norm = normalize_column_name(alias)
                if normalized_col == alias_norm or alias_norm in normalized_col:
                    mapping[standard_field] = original_col
                    break
            if standard_field in mapping:
                break

    return mapping


def clean_amount(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, (int, float)) and not pd.isna(value):
        return float(value)

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "-"}:
        return None

    text = text.replace(",", "")
    text = text.replace("₹", "")
    text = text.replace("rs.", "")
    text = text.replace("rs", "")
    text = re.sub(r"[^\d.\-]", "", text)

    if not text or text in {"-", ".", "-."}:
        return None

    try:
        return float(text)
    except ValueError:
        return None


def derive_amount(row: pd.Series, mapping: dict[str, str | None]) -> float | None:
    if mapping.get("amount"):
        return clean_amount(row[mapping["amount"]])

    debit = clean_amount(row[mapping["debit_amount"]]) if mapping.get("debit_amount") else None
    credit = clean_amount(row[mapping["credit_amount"]]) if mapping.get("credit_amount") else None

    debit = debit or 0
    credit = credit or 0

    if debit == 0 and credit == 0:
        return None

    return float(credit - debit)


def clean_text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None

    return text


def clean_date(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None

    try:
        parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
        if pd.isna(parsed):
            return clean_text(value)
        return parsed.date().isoformat()
    except Exception:
        return clean_text(value)


def row_is_empty(row: pd.Series) -> bool:
    non_empty = [
        value for value in row.tolist()
        if value is not None and not pd.isna(value) and str(value).strip() != ""
    ]
    return len(non_empty) == 0


def calculate_mapping_confidence(mapping: dict[str, str | None]) -> float:
    score = 0.0

    important_fields = {
        "document_id": 0.15,
        "party_name": 0.20,
        "amount": 0.25,
        "debit_amount": 0.125,
        "credit_amount": 0.125,
        "transaction_date": 0.15,
        "gstin": 0.10,
    }

    for field, weight in important_fields.items():
        if mapping.get(field):
            score += weight

    return round(min(score, 1.0), 2)


def load_tabular_data(file_path: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    extension = os.path.splitext(file_path)[1].lower()

    if extension in [".xlsx", ".xls"]:
        preview = pd.read_excel(file_path, header=None, nrows=20)
        header_row = find_header_row(preview)
        sheets = pd.read_excel(file_path, sheet_name=None, header=header_row)

        first_sheet_name = list(sheets.keys())[0]
        df = sheets[first_sheet_name]

        return df, {
            "file_type": extension,
            "header_row": header_row,
            "sheet_name": first_sheet_name,
        }

    if extension == ".csv":
        preview = pd.read_csv(file_path, header=None, nrows=20)
        header_row = find_header_row(preview)
        df = pd.read_csv(file_path, header=header_row)

        return df, {
            "file_type": extension,
            "header_row": header_row,
            "sheet_name": None,
        }

    raise ValueError(f"Unsupported tabular file type: {extension}")


def preview_tabular_file(file_path: str) -> dict[str, Any]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    df, metadata = load_tabular_data(file_path)
    df = df.dropna(how="all")

    columns = [str(col).strip() for col in df.columns]
    detected_mapping = map_columns(columns)

    preview_rows = []
    for _, row in df.head(8).iterrows():
        item = {}
        for col in df.columns:
            value = row[col]
            item[str(col)] = None if pd.isna(value) else str(value)
        preview_rows.append(item)

    return {
        "available_columns": columns,
        "detected_mapping": detected_mapping,
        "preview_rows": preview_rows,
        "metadata": metadata,
    }



def extract_extra_mapped_values(row: pd.Series, mapping: dict[str, str | None]) -> dict[str, Any]:
    extra_values: dict[str, Any] = {}

    for field in ALLOWED_MAPPING_FIELDS:
        if field in STANDARD_FIELDS:
            continue

        column = mapping.get(field)
        if not column or column not in row.index:
            continue

        if field in DATE_EXTRA_FIELDS:
            extra_values[field] = clean_date(row[column])
        elif field in AMOUNT_EXTRA_FIELDS:
            extra_values[field] = clean_amount(row[column])
        else:
            extra_values[field] = clean_text(row[column])

    return extra_values


def extract_records_from_dataframe(
    df: pd.DataFrame,
    file_id: int,
    workspace_id: int,
    record_type: str,
    sheet_name: str | None = None,
    user_mapping: dict[str, str | None] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    df = df.dropna(how="all")

    if df.empty:
        return [], {
            "sheet_name": sheet_name,
            "rows_seen": 0,
            "records_extracted": 0,
            "column_mapping": {},
            "warnings": ["Sheet is empty"],
        }

    columns = [str(col).strip() for col in df.columns]
    auto_mapping = map_columns(columns)

    if user_mapping:
        mapping = {
            field: col
            for field, col in user_mapping.items()
            if col and col in df.columns and field in ALLOWED_MAPPING_FIELDS
        }
    else:
        mapping = auto_mapping

    records: list[dict[str, Any]] = []
    warnings: list[str] = []

    has_amount = "amount" in mapping or "debit_amount" in mapping or "credit_amount" in mapping
    required_soft_fields = ["party_name"]
    if not has_amount:
        required_soft_fields.append("amount")

    missing_mapped_fields = [field for field in required_soft_fields if field not in mapping]

    if missing_mapped_fields:
        warnings.append(f"Could not map fields: {', '.join(missing_mapped_fields)}")

    for source_idx, row in df.iterrows():
        if row_is_empty(row):
            continue

        raw_data = {}
        for col in df.columns:
            value = row[col]
            raw_data[str(col)] = None if pd.isna(value) else str(value)

        extra_values = extract_extra_mapped_values(row, mapping)

        description_value = clean_text(row[mapping["description"]]) if "description" in mapping else None
        party_value = clean_text(row[mapping["party_name"]]) if "party_name" in mapping else description_value

        record = {
            "workspace_id": workspace_id,
            "file_id": file_id,
            "record_type": record_type,
            "source_row": int(source_idx) + 2,
            "document_id": clean_text(row[mapping["document_id"]]) if "document_id" in mapping else None,
            "party_name": party_value,
            "transaction_date": clean_date(row[mapping["transaction_date"]]) if "transaction_date" in mapping else None,
            "amount": derive_amount(row, mapping),
            "gstin": clean_text(row[mapping["gstin"]]) if "gstin" in mapping else None,
            "raw_data": {
                **raw_data,
                **extra_values,
                "sheet_name": sheet_name,
                "source_row_values": raw_data,
                "extra_mapped_values": extra_values,
                "column_mapping": mapping,
                "auto_mapping": auto_mapping,
                "mapping_source": "user" if user_mapping else "auto",
                "description": description_value,
            },
            "confidence": calculate_mapping_confidence(mapping),
        }

        records.append(record)

    metadata = {
        "sheet_name": sheet_name,
        "rows_seen": int(len(df)),
        "records_extracted": len(records),
        "column_mapping": mapping,
        "auto_mapping": auto_mapping,
        "mapping_source": "user" if user_mapping else "auto",
        "warnings": warnings,
    }

    return records, metadata


def extract_tabular_file(
    file_path: str,
    file_id: int,
    workspace_id: int,
    record_type: str,
    user_mapping: dict[str, str | None] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    df, metadata = load_tabular_data(file_path)

    records, extraction_metadata = extract_records_from_dataframe(
        df=df,
        file_id=file_id,
        workspace_id=workspace_id,
        record_type=record_type,
        sheet_name=metadata.get("sheet_name"),
        user_mapping=user_mapping,
    )

    return records, {
        "file_path": file_path,
        "record_type": record_type,
        "total_records_extracted": len(records),
        "file_metadata": metadata,
        "sheets": [extraction_metadata],
    }