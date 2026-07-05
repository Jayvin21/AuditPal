from pathlib import Path

ROOT = Path(r"D:\1Workspace\AuditPal")
README = ROOT / "README.md"

readme = r"""# AuditPal — Agentic Audit Automation Platform

AuditPal is a full-stack audit automation platform built for Excel-heavy audit workflows. It helps auditors upload accounting exports, map messy columns, extract normalized records, run domain-specific audit checks, review risk-ranked findings, use an audit workspace assistant, and export audit reports.

Built by **Jayvin Parmar**.

---

## Preview

![AuditPal Landing Page](screenshots/01_landing_page.png)

---

## Workflow

AuditPal follows a practical audit workflow:

```txt
Upload Files → Map Columns → Extract Records → Run Audit Modules → Review Findings → Audit Chat → Export Reports

Why AuditPal?

Traditional audit review often depends on manually checking Excel files, Tally exports, SAP line items, bank statements, GST reports, support documents, and ledger data.

AuditPal converts that process into a structured exception-review workflow.

Auditors can:

Upload CSV/XLSX audit files
Label files by audit source/type
Map messy real-world columns into normalized audit fields
Extract records into a database
Run deterministic audit modules
Review risk-ranked findings
Save reviewer decisions and notes
Use Audit Chat to summarize, retrieve, and act on workspace data
Export findings as CSV/PDF reports
Screenshots
File Upload and Source Classification

Module-Specific Column Mapping

Mapping Preview

Audit Module Selector

Audit Run History

Findings Review

Findings Search and Filters

Evidence Panel

Extracted Records

Reports Export

Audit Chat Summary

Audit Chat Agent Action

Core Features
Workspace-Based Audit Flow

Each client audit is managed inside a workspace with its own files, records, audit runs, findings, and reports.

File Upload

AuditPal supports multiple accounting and audit file types:

Purchase registers
Sales registers
Expense ledgers
Tally exports
SAP exports
Bank statements
GSTR-2B files
Fixed asset registers
Aging reports
Trial balances
Support document / OCR extract files
Column Mapping

Real audit files rarely follow the same column structure. AuditPal includes a column mapping layer for messy CSV/XLSX files.

The mapping system supports module-specific fields such as:

GSTIN, taxable value, invoice value, IGST, CGST, SGST
PAN, TDS amount, TDS section
Asset ID, asset cost, depreciation, WDV
Ledger name, debit balance, credit balance, closing balance
Due date, days overdue, outstanding amount, aging bucket
OCR confidence, document type, extracted text
Audit Modules

AuditPal includes 11 audit/review modules:

Module	Purpose
Purchase Audit	Detects duplicate invoices, missing fields, high-value purchases, round amounts, GSTIN issues, and year-end risks
Sales Audit	Reviews sales invoices for missing customer data, duplicates, cancellations, returns, and high-value sales
Expense Audit	Flags high-value expenses, cash expenses, weak narration, duplicate vouchers, and sensitive spend
Bank Reconciliation	Matches bank statement entries against books-side bank/cash ledgers
GST Reconciliation	Compares books-side purchase data with GSTR-2B records
Ledger Scrutiny	Reviews ledger entries for suspense accounts, journal indicators, cash activity, and weak narration
TDS Review	Checks possible TDS applicability, missing PAN, missing TDS section, and payment nature issues
Fixed Asset Audit	Reviews asset capitalization, depreciation, WDV, disposals, and duplicate asset references
Trial Balance Review	Checks suspense balances, abnormal debit/credit balances, high-value ledgers, and imbalance
Aging Review	Reviews receivables/payables aging, old balances, overdue items, and high-value outstandings
Document Matching	Matches book entries against structured OCR/support document extracts
Findings Review Workflow

Findings are risk-ranked and human-reviewable.

Supported review statuses:

Needs Review
Confirmed Issue
False Positive
Needs Client Clarification
Resolved

Users can:

Search findings
Filter by risk/status/type
Sort findings
Inspect evidence
Save reviewer notes
Update finding status
Export reports
Audit Chat Assistant

AuditPal includes an agentic workspace assistant that can inspect the current audit workspace, retrieve relevant records/findings, summarize risk, draft clarification lists, prepare export links, and run existing audit modules through deterministic backend tools.

Example prompts:

Summarize this workspace
Show high-risk findings
Which vendors have the most findings?
Draft client clarification list
Run fixed asset audit
Export PDF and CSV
Extract records again

Current Audit Chat scope:

Retrieves relevant findings and records
Summarizes workspace risk
Groups findings by vendor/party
Drafts client clarification lists
Runs existing audit modules
Runs record extraction
Prepares export links

It does not require a paid LLM API for the local demo.

Tech Stack
Frontend
Next.js
React
TypeScript
Tailwind CSS
Lucide React
Axios
Backend
FastAPI
Python
SQLAlchemy
SQLite
Pandas
OpenPyXL
CSV export
PDF report generation
Architecture
AuditPal/
├── frontend/          # Next.js frontend
├── backend/           # FastAPI backend
├── sample-data/       # Sample audit CSV/XLSX files
├── screenshots/       # README screenshots
├── docs/
└── README.md
Backend Capabilities
Workspace creation and deletion
File upload and deletion
CSV/XLSX parsing
Column detection
Saved column mappings
Record extraction
Audit run creation
Rule-based audit modules
Findings persistence
Review status updates
Reviewer notes
CSV/PDF report generation
Audit Chat tool execution
Getting Started
1. Clone the repository
git clone https://github.com/Jayvin21/AuditPal.git
cd AuditPal
2. Start the backend
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

Backend:

http://localhost:8000

API docs:

http://localhost:8000/docs
3. Start the frontend

Open a second terminal:

cd frontend
npm install
npm run dev

Frontend:

http://localhost:3000
Demo Workflow
1. Create workspace
2. Upload CSV/XLSX file
3. Choose file type
4. Map columns
5. Extract records
6. Run relevant audit module
7. Review findings
8. Save reviewer status/notes
9. Ask Audit Chat for summary or clarification list
10. Export CSV/PDF report
Example Audit Checks

AuditPal can detect issues such as:

Missing invoice number
Missing vendor/customer name
Missing GSTIN
Invalid GSTIN format
Duplicate invoice numbers
Repeated same-party same-amount transactions
High-value purchases/sales/expenses
Round-number transactions
Year-end transactions
Possible TDS not deducted
Missing PAN for TDS-sensitive payments
Suspense ledger balances
Abnormal trial balance signs
Overdue receivables/payables
Old outstanding balances
Depreciation exceeding asset cost
Negative WDV
Fully depreciated active assets
Books entries missing support documents
Support documents not booked
Books vs support amount mismatch
GST books vs GSTR-2B mismatch
Current Limitations
Document Matching currently works with structured OCR/support document extracts, not direct raw image/PDF OCR.
The audit engine is rule-based and deterministic; it is designed for exception detection, not final audit judgment.
Results require human review.
SQLite is used for local demo storage.
Report exports are workspace-level in the current version.
Future Improvements
Gemini/OpenAI intent planner for Audit Chat
Direct PDF/image OCR for invoice and voucher extraction
Selected audit-run-specific PDF/CSV exports
User authentication
Organization/team roles
Cloud database deployment
Background jobs for large files
Configurable materiality thresholds
LLM-generated audit memos and client query letters
Portfolio Positioning

AuditPal demonstrates:

Full-stack product development
Audit-domain workflow design
Data extraction and normalization
Rule-based automation
RAG-style workspace retrieval
Agentic assistant patterns
Human-in-the-loop review
Report generation
Realistic business process automation
Author

Jayvin Parmar

Computer Engineering graduate building full-stack AI, automation, RAG, and data workflow systems.

GitHub: Jayvin21

"""

README.write_text(readme, encoding="utf-8")

print("README.md created successfully.")
print(README)