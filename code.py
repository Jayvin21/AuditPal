from pathlib import Path
import re

ROOT = Path(r"D:\1Workspace\AuditPal")

FRONTEND_PAGE = ROOT / "frontend" / "src" / "app" / "workspaces" / "[id]" / "page.tsx"
MAIN_PY = ROOT / "backend" / "app" / "main.py"
ROUTES_DIR = ROOT / "backend" / "app" / "api" / "routes"
SERVICES_DIR = ROOT / "backend" / "app" / "services"
EXTRACTOR = ROOT / "backend" / "app" / "services" / "extractors" / "tabular_extractor.py"

ROUTES_DIR.mkdir(parents=True, exist_ok=True)
SERVICES_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------
# 1. Backend import templates
# -----------------------------

(SERVICES_DIR / "import_templates.py").write_text(
r'''IMPORT_TEMPLATES = [
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
''',
encoding="utf-8"
)

(ROUTES_DIR / "import_templates.py").write_text(
r'''from fastapi import APIRouter, HTTPException
from app.services.import_templates import get_import_template, get_import_templates

router = APIRouter(prefix="/import-templates", tags=["import-templates"])


@router.get("")
def list_import_templates():
    return get_import_templates()


@router.get("/{template_key}")
def read_import_template(template_key: str):
    template = get_import_template(template_key)
    if not template:
        raise HTTPException(status_code=404, detail="Import template not found")
    return template
''',
encoding="utf-8"
)


# -----------------------------
# 2. Patch backend main.py
# -----------------------------

main = MAIN_PY.read_text(encoding="utf-8")

if "import_templates" not in main:
    main = main.replace(
        "reports,",
        "reports, import_templates,",
    )

if "app.include_router(import_templates.router)" not in main:
    main = main.replace(
        "app.include_router(reports.router)",
        "app.include_router(reports.router)\napp.include_router(import_templates.router)",
    )

MAIN_PY.write_text(main, encoding="utf-8")


# -----------------------------
# 3. Patch extractor aliases
# -----------------------------

if EXTRACTOR.exists():
    text = EXTRACTOR.read_text(encoding="utf-8")

    additions = {
        "document_id": [
            "voucher no", "voucher no.", "voucher number", "vch no", "vch no.",
            "document number", "doc number", "reference", "reference no",
            "ref no", "assignment", "invoice reference", "supplier invoice no",
            "bill no", "bill no.", "cheque no", "instrument no", "utr", "utr no",
            "billing document"
        ],
        "party_name": [
            "particulars", "ledger name", "party name", "supplier", "supplier name",
            "vendor", "vendor name", "name 1", "customer", "customer name",
            "account", "g/l account", "gl account", "cost center", "profit center",
            "trade/legal name", "legal name"
        ],
        "transaction_date": [
            "date", "voucher date", "invoice date", "bill date", "posting date",
            "document date", "entry date", "transaction date", "value date"
        ],
        "amount": [
            "amount", "total", "gross total", "invoice value", "invoice amount",
            "gross amount", "taxable value", "total amount",
            "amount in local currency", "local currency amount", "inr amount",
            "debit/credit amount"
        ],
        "debit_amount": [
            "debit", "dr", "debit amount", "withdrawal", "withdrawals",
            "payment", "payments", "paid amount"
        ],
        "credit_amount": [
            "credit", "cr", "credit amount", "deposit", "deposits",
            "receipt", "receipts", "received amount"
        ],
        "gstin": [
            "gstin", "gstin/uin", "party gstin", "supplier gstin", "vendor gstin",
            "gstin of supplier", "gst no", "gst number"
        ],
        "description": [
            "narration", "description", "particulars", "text", "document header text",
            "voucher type", "supply type", "place of supply", "remarks", "memo"
        ],
    }

    def patch_alias_list(src: str, key: str, new_aliases: list[str]) -> str:
        # Works for common Python dict style:
        # "document_id": [...]
        pattern = rf'("{re.escape(key)}"\s*:\s*\[)(.*?)(\])'
        match = re.search(pattern, src, flags=re.S)

        quote = '"'
        if not match:
            pattern = rf"('{re.escape(key)}'\s*:\s*\[)(.*?)(\])"
            match = re.search(pattern, src, flags=re.S)
            quote = "'"

        if not match:
            return src

        existing_block = match.group(2)
        existing_lower = existing_block.lower()

        to_add = []
        for alias in new_aliases:
            if alias.lower() not in existing_lower:
                to_add.append(alias)

        if not to_add:
            return src

        insertion = "".join([f"\n        {quote}{alias}{quote}," for alias in to_add])
        return src[:match.end(2)] + insertion + src[match.end(2):]

    for key, aliases in additions.items():
        text = patch_alias_list(text, key, aliases)

    EXTRACTOR.write_text(text, encoding="utf-8")
else:
    print(f"Extractor not found, skipped alias patch: {EXTRACTOR}")


# -----------------------------
# 4. Patch frontend workspace page
# -----------------------------

page = FRONTEND_PAGE.read_text(encoding="utf-8")

# Add Import Templates section in sidebar.
if '{ key: "templates", label: "Import Templates"' not in page:
    page = page.replace(
        '{ key: "files", label: "Files", icon: Upload },',
        '{ key: "files", label: "Files", icon: Upload },\n  { key: "templates", label: "Import Templates", icon: FileSearch },',
    )

# Add template data const before sections.
if "const importTemplates = [" not in page:
    page = page.replace(
        "const sections = [",
r'''const importTemplates = [
  {
    name: "Tally Purchase Register",
    source: "Tally Prime / ERP",
    fileType: "tally_purchase_register",
    modules: "Purchase Audit, GST Review",
    columns: "Date, Particulars, Voucher No., GSTIN/UIN, Taxable Value, Gross Total",
  },
  {
    name: "Tally Ledger Vouchers",
    source: "Tally Ledger Export",
    fileType: "tally_ledger_vouchers",
    modules: "Ledger Scrutiny, Expense Audit, Bank Reconciliation",
    columns: "Date, Particulars, Voucher Type, Voucher No., Debit, Credit, Narration",
  },
  {
    name: "Tally Bank Book",
    source: "Tally Bank Book",
    fileType: "tally_bank_book",
    modules: "Bank Reconciliation",
    columns: "Date, Particulars, Voucher No., Debit, Credit, Narration",
  },
  {
    name: "SAP Vendor Line Items",
    source: "SAP FBL1N",
    fileType: "sap_vendor_line_items",
    modules: "Purchase Audit, Ledger Scrutiny, TDS Review",
    columns: "Document Number, Posting Date, Vendor, Name 1, Amount in Local Currency, Text",
  },
  {
    name: "SAP G/L Line Items",
    source: "SAP FBL3N",
    fileType: "sap_gl_line_items",
    modules: "Ledger Scrutiny, Expense Audit, Journal Entry Review",
    columns: "G/L Account, Document Number, Posting Date, Amount in Local Currency, Text",
  },
  {
    name: "SAP Customer Line Items",
    source: "SAP FBL5N",
    fileType: "sap_customer_line_items",
    modules: "Sales Audit, Receivables Review",
    columns: "Customer, Name 1, Document Number, Posting Date, Reference, Amount, Text",
  },
  {
    name: "GSTR-2B",
    source: "GST Portal",
    fileType: "gstr_2b",
    modules: "GST Reconciliation",
    columns: "GSTIN of supplier, Trade/Legal name, Invoice number, Invoice Date, Taxable Value",
  },
];

const sections = [''',
    )

# Expand file-type dropdown.
old_options = r'''            <option value="purchase_register">Purchase Register</option>
            <option value="expense_ledger">Expense Ledger</option>
            <option value="bank_statement">Bank Statement</option>
            <option value="cash_bank_ledger">Cash / Bank Ledger</option>
            <option value="bank_ledger">Bank Ledger</option>
            <option value="tally_bank_book">Tally Bank Book</option>'''

new_options = r'''            <option value="purchase_register">Purchase Register</option>
            <option value="tally_purchase_register">Tally Purchase Register</option>
            <option value="generic_sales_register">Sales Register</option>
            <option value="expense_ledger">Expense Ledger</option>
            <option value="tally_ledger_vouchers">Tally Ledger Vouchers</option>
            <option value="bank_statement">Bank Statement</option>
            <option value="cash_bank_ledger">Cash / Bank Ledger</option>
            <option value="bank_ledger">Bank Ledger</option>
            <option value="tally_bank_book">Tally Bank Book</option>
            <option value="sap_vendor_line_items">SAP Vendor Line Items - FBL1N</option>
            <option value="sap_gl_line_items">SAP G/L Line Items - FBL3N</option>
            <option value="sap_customer_line_items">SAP Customer Line Items - FBL5N</option>
            <option value="gstr_2b">GSTR-2B</option>
            <option value="trial_balance">Trial Balance</option>'''

if old_options in page:
    page = page.replace(old_options, new_options)

# Add active templates section before files section.
if 'activeSection === "templates"' not in page:
    page = page.replace(
        '            {activeSection === "files" && (',
r'''            {activeSection === "templates" && (
              <ImportTemplatesSection />
            )}

            {activeSection === "files" && (''',
    )

# Add ImportTemplatesSection function before FilesSection.
if "function ImportTemplatesSection()" not in page:
    page = page.replace(
        "function FilesSection({",
r'''function ImportTemplatesSection() {
  return (
    <SectionShell
      title="Import Templates"
      subtitle="Supported Excel/CSV export layouts for Tally, SAP, GST portal, banks, and manual books."
    >
      <div className="grid gap-4 lg:grid-cols-2">
        {importTemplates.map((template) => (
          <Card key={template.fileType}>
            <div className="mb-3 flex items-start justify-between gap-4">
              <div>
                <h2 className="font-semibold text-[#17352E]">{template.name}</h2>
                <p className="mt-1 text-sm text-[#5F7D70]">{template.source}</p>
              </div>
              <span className="rounded-full bg-[#EAF4EE] px-3 py-1 text-xs font-medium text-[#2F7866]">
                {template.fileType}
              </span>
            </div>

            <div className="mt-4 rounded-2xl border border-[#D6E6DD] bg-[#F6FBF8] p-4">
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-[#6B8E7F]">
                Expected columns
              </p>
              <p className="mt-2 text-sm leading-6 text-[#42685B]">
                {template.columns}
              </p>
            </div>

            <div className="mt-4 rounded-2xl border border-[#D6E6DD] bg-white p-4">
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-[#6B8E7F]">
                Supported modules
              </p>
              <p className="mt-2 text-sm leading-6 text-[#42685B]">
                {template.modules}
              </p>
            </div>
          </Card>
        ))}
      </div>
    </SectionShell>
  );
}

function FilesSection({''',
    )

FRONTEND_PAGE.write_text(page, encoding="utf-8")


# -----------------------------
# 5. Add sample template CSVs
# -----------------------------

sample_dir = ROOT / "sample-data" / "import-templates"
sample_dir.mkdir(parents=True, exist_ok=True)

(sample_dir / "tally_purchase_register_template.csv").write_text(
"""Date,Particulars,Voucher Type,Voucher No.,GSTIN/UIN,Taxable Value,Integrated Tax,Central Tax,State Tax,Gross Total,Narration
01-04-2025,ABC Traders,Purchase,PV-001,27ABCDE1234F1Z5,10000,0,900,900,11800,Sample Tally purchase
""",
encoding="utf-8"
)

(sample_dir / "tally_ledger_vouchers_template.csv").write_text(
"""Date,Particulars,Voucher Type,Voucher No.,Debit,Credit,Narration
01-04-2025,Office Expenses,Payment,PMT-001,2500,0,Sample expense payment
02-04-2025,HDFC Bank,Receipt,RCP-001,0,5000,Sample receipt
""",
encoding="utf-8"
)

(sample_dir / "sap_vendor_line_items_template.csv").write_text(
"""Document Number,Posting Date,Document Date,Vendor,Name 1,Reference,Amount in Local Currency,Text
510000001,01-04-2025,31-03-2025,100045,ABC Suppliers,INV-1001,11800,Sample SAP vendor invoice
""",
encoding="utf-8"
)

(sample_dir / "sap_gl_line_items_template.csv").write_text(
"""G/L Account,Document Number,Posting Date,Document Date,Amount in Local Currency,Text,Profit Center,Cost Center
500100,190000001,01-04-2025,31-03-2025,2500,Office expense posting,PC01,CC01
""",
encoding="utf-8"
)

print("Tally/SAP import-template update applied.")
print("Updated:")
print(f"- {SERVICES_DIR / 'import_templates.py'}")
print(f"- {ROUTES_DIR / 'import_templates.py'}")
print(f"- {MAIN_PY}")
print(f"- {EXTRACTOR}")
print(f"- {FRONTEND_PAGE}")
print(f"- {sample_dir}")