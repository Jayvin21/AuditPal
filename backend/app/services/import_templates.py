IMPORT_TEMPLATES = [
    {
        "key": "generic_purchase_register",
        "name": "Generic Purchase Register",
        "source": "Generic Excel / CSV",
        "file_type": "purchase_register",
        "supported_modules": ["Purchase Audit", "GST Review"],
        "expected_columns": [
            "Invoice No", "Invoice Date", "Vendor Name", "GSTIN",
            "Taxable Value", "GST Amount", "Total Amount"
        ],
        "mapping": {
            "document_id": ["Invoice No", "Bill No", "Voucher No"],
            "party_name": ["Vendor Name", "Supplier Name", "Party Name"],
            "transaction_date": ["Invoice Date", "Bill Date", "Voucher Date"],
            "amount": ["Total Amount", "Gross Amount", "Invoice Amount"],
            "gstin": ["GSTIN", "Supplier GSTIN", "Vendor GSTIN"],
            "description": ["Narration", "Description", "Particulars"]
        },
        "notes": "Use this for normal purchase registers exported from Excel, accounting tools, or manual books."
    },
    {
        "key": "tally_purchase_register",
        "name": "Tally Purchase Register",
        "source": "Tally Prime / Tally ERP Export",
        "file_type": "tally_purchase_register",
        "supported_modules": ["Purchase Audit", "GST Review"],
        "expected_columns": [
            "Date", "Particulars", "Voucher Type", "Voucher No.", "GSTIN/UIN",
            "Taxable Value", "Integrated Tax", "Central Tax", "State Tax", "Gross Total"
        ],
        "mapping": {
            "document_id": ["Voucher No.", "Voucher Number", "Bill No.", "Supplier Invoice No."],
            "party_name": ["Particulars", "Party Name", "Supplier", "Ledger Name"],
            "transaction_date": ["Date", "Voucher Date", "Invoice Date"],
            "amount": ["Gross Total", "Invoice Value", "Amount", "Total"],
            "gstin": ["GSTIN/UIN", "GSTIN", "Party GSTIN"],
            "description": ["Narration", "Particulars", "Voucher Type"]
        },
        "notes": "Export Purchase Register from Tally as Excel/CSV, then upload and verify mappings."
    },
    {
        "key": "tally_ledger_vouchers",
        "name": "Tally Ledger Vouchers",
        "source": "Tally Ledger Voucher Export",
        "file_type": "tally_ledger_vouchers",
        "supported_modules": ["Ledger Scrutiny", "Expense Audit", "Bank Reconciliation"],
        "expected_columns": [
            "Date", "Particulars", "Voucher Type", "Voucher No.", "Debit", "Credit", "Narration"
        ],
        "mapping": {
            "document_id": ["Voucher No.", "Voucher Number", "Ref No.", "Reference No."],
            "party_name": ["Particulars", "Ledger Name", "Party Name"],
            "transaction_date": ["Date", "Voucher Date"],
            "debit_amount": ["Debit", "Dr", "Debit Amount"],
            "credit_amount": ["Credit", "Cr", "Credit Amount"],
            "description": ["Narration", "Particulars", "Voucher Type"]
        },
        "notes": "Useful for expense ledgers, party ledgers, bank books, and ledger scrutiny."
    },
    {
        "key": "tally_bank_book",
        "name": "Tally Bank Book",
        "source": "Tally Bank Book Export",
        "file_type": "tally_bank_book",
        "supported_modules": ["Bank Reconciliation"],
        "expected_columns": [
            "Date", "Particulars", "Voucher No.", "Debit", "Credit", "Narration"
        ],
        "mapping": {
            "document_id": ["Voucher No.", "Cheque No.", "Instrument No.", "Reference No."],
            "party_name": ["Particulars", "Party Name", "Ledger Name"],
            "transaction_date": ["Date", "Voucher Date"],
            "debit_amount": ["Debit", "Payment", "Withdrawal"],
            "credit_amount": ["Credit", "Receipt", "Deposit"],
            "description": ["Narration", "Particulars"]
        },
        "notes": "Upload along with bank statement to run reconciliation."
    },
    {
        "key": "sap_vendor_line_items",
        "name": "SAP Vendor Line Items",
        "source": "SAP FBL1N Export",
        "file_type": "sap_vendor_line_items",
        "supported_modules": ["Purchase Audit", "Ledger Scrutiny", "TDS Review"],
        "expected_columns": [
            "Document Number", "Posting Date", "Document Date", "Vendor", "Name 1",
            "Reference", "Amount in Local Currency", "Text"
        ],
        "mapping": {
            "document_id": ["Document Number", "Reference", "Assignment", "Invoice Reference"],
            "party_name": ["Vendor", "Name 1", "Vendor Name", "Account"],
            "transaction_date": ["Posting Date", "Document Date", "Entry Date"],
            "amount": ["Amount in Local Currency", "Amount", "Local Currency Amount"],
            "description": ["Text", "Document Header Text", "Assignment"]
        },
        "notes": "Export SAP FBL1N to Excel/CSV and map vendor/payment columns."
    },
    {
        "key": "sap_gl_line_items",
        "name": "SAP G/L Line Items",
        "source": "SAP FBL3N Export",
        "file_type": "sap_gl_line_items",
        "supported_modules": ["Ledger Scrutiny", "Expense Audit", "Journal Entry Review"],
        "expected_columns": [
            "G/L Account", "Document Number", "Posting Date", "Document Date",
            "Amount in Local Currency", "Text", "Profit Center", "Cost Center"
        ],
        "mapping": {
            "document_id": ["Document Number", "Reference", "Assignment"],
            "party_name": ["G/L Account", "Account", "Cost Center", "Profit Center"],
            "transaction_date": ["Posting Date", "Document Date"],
            "amount": ["Amount in Local Currency", "Amount", "Local Currency Amount"],
            "description": ["Text", "Document Header Text", "Assignment"]
        },
        "notes": "Useful for expense ledgers, journal entries, and trial-balance drilldowns."
    },
    {
        "key": "sap_customer_line_items",
        "name": "SAP Customer Line Items",
        "source": "SAP FBL5N Export",
        "file_type": "sap_customer_line_items",
        "supported_modules": ["Sales Audit", "Receivables Review"],
        "expected_columns": [
            "Customer", "Name 1", "Document Number", "Posting Date",
            "Reference", "Amount in Local Currency", "Text"
        ],
        "mapping": {
            "document_id": ["Document Number", "Reference", "Assignment", "Billing Document"],
            "party_name": ["Customer", "Name 1", "Customer Name", "Account"],
            "transaction_date": ["Posting Date", "Document Date"],
            "amount": ["Amount in Local Currency", "Amount", "Local Currency Amount"],
            "description": ["Text", "Document Header Text", "Assignment"]
        },
        "notes": "Useful for sales audit and receivable testing."
    },
    {
        "key": "gstr_2b",
        "name": "GSTR-2B",
        "source": "GST Portal Export",
        "file_type": "gstr_2b",
        "supported_modules": ["GST Reconciliation"],
        "expected_columns": [
            "GSTIN of supplier", "Trade/Legal name", "Invoice number",
            "Invoice Date", "Taxable Value", "Integrated Tax", "Central Tax", "State/UT Tax"
        ],
        "mapping": {
            "document_id": ["Invoice number", "Invoice No", "Document Number"],
            "party_name": ["Trade/Legal name", "Supplier Name", "Legal Name"],
            "transaction_date": ["Invoice Date", "Document Date"],
            "amount": ["Taxable Value", "Invoice Value", "Total Taxable Value"],
            "gstin": ["GSTIN of supplier", "Supplier GSTIN", "GSTIN"],
            "description": ["Supply Type", "Place of Supply"]
        },
        "notes": "Later this will reconcile books ITC against GST portal 2B."
    },
]


def get_import_templates():
    return IMPORT_TEMPLATES


def get_import_template(key: str):
    for template in IMPORT_TEMPLATES:
        if template["key"] == key:
            return template
    return None
