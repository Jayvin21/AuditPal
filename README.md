# AuditPal

AuditPal is an Agentic AI audit assistant designed for CA interns, audit teams, and Excel-heavy finance workflows.

It helps auditors upload financial records, compare them against supporting documents, detect mismatches, flag suspicious transactions, and review findings through a human-in-the-loop workflow.

## Core Idea

Small firms often use Excel, Tally exports, scanned bills, physical vouchers, and bank statements for audit work. AuditPal converts this manual verification process into a structured exception-review system.

## MVP Features

- Client audit workspaces
- Excel/CSV/PDF/image upload support
- File type tagging
- Audit coverage summary
- Risk-ranked findings
- Human review statuses
- Source-level evidence for every issue
- FastAPI backend
- Next.js frontend

## Planned Audit Modules

- Purchase audit
- Expense audit
- Bank reconciliation
- Ledger scrutiny
- Balance sheet review

## Tech Stack

- Frontend: Next.js, TypeScript, Tailwind CSS
- Backend: FastAPI, Python
- Data Processing: Pandas, OpenPyXL
- Database: SQLite with SQLAlchemy
- Matching: RapidFuzz
- Reports: ReportLab



