from pathlib import Path
import re

ROOT = Path(r"D:\1Workspace\AuditPal")
PAGE = ROOT / "frontend" / "src" / "app" / "workspaces" / "[id]" / "page.tsx"

page = PAGE.read_text(encoding="utf-8")

# ----------------------------------------------------
# 1. Remove wrongly inserted audit-run props from FilesSection call
# ----------------------------------------------------

wrong_files_props = '''                files={files}
                auditRuns={auditRuns}
                selectedAuditRunId={selectedAuditRunId}
                setSelectedAuditRunId={setSelectedAuditRunId}
                deleteAuditRun={deleteAuditRun}
                busy={busy}'''

correct_files_props = '''                files={files}
                busy={busy}'''

page = page.replace(wrong_files_props, correct_files_props)

# ----------------------------------------------------
# 2. Add correct audit-run props to AuditSection call
# ----------------------------------------------------

old_audit_call = '''              <AuditSection
                busy={busy}
                auditSummary={auditSummary}
                parseFiles={parseFiles}
                runPurchaseAudit={runPurchaseAudit}
                runSalesAudit={runSalesAudit}
                runExpenseAudit={runExpenseAudit}
                runBankReconciliation={runBankReconciliation}
              />'''

new_audit_call = '''              <AuditSection
                files={files}
                auditRuns={auditRuns}
                selectedAuditRunId={selectedAuditRunId}
                setSelectedAuditRunId={setSelectedAuditRunId}
                deleteAuditRun={deleteAuditRun}
                busy={busy}
                auditSummary={auditSummary}
                parseFiles={parseFiles}
                runPurchaseAudit={runPurchaseAudit}
                runSalesAudit={runSalesAudit}
                runExpenseAudit={runExpenseAudit}
                runBankReconciliation={runBankReconciliation}
              />'''

if old_audit_call not in page:
    raise RuntimeError("Could not find the old AuditSection call. Paste the AuditSection call block if this fails.")

page = page.replace(old_audit_call, new_audit_call)

# ----------------------------------------------------
# 3. Make FilesSection files prop non-optional again
# ----------------------------------------------------

page = page.replace(
    "files?: UploadedFile[];",
    "files: UploadedFile[];",
)

# ----------------------------------------------------
# 4. Make AuditSection props safe but real
# ----------------------------------------------------

# Keep auditRuns optional defensively, but it should now be passed correctly.
page = page.replace(
    "auditRuns: AuditRunItem[];",
    "auditRuns?: AuditRunItem[];",
)

# ----------------------------------------------------
# 5. Improve auto-select logic for Audit module
# ----------------------------------------------------

page = re.sub(
    r"function inferRecommendedAuditModule\(files\?: UploadedFile\[\]\) \{[\s\S]*?\n\}",
    r'''function inferRecommendedAuditModule(files?: UploadedFile[]) {
  if (!files || !files.length) return "purchase";

  const candidates = files
    .filter((file) => file.status === "parsed" || file.status === "uploaded")
    .sort((a, b) => b.id - a.id);

  const latest = candidates[0] ?? files[files.length - 1];
  const type = latest?.file_type?.toLowerCase() ?? "";

  if (type.includes("sales") || type.includes("customer")) return "sales";
  if (type.includes("expense") || type.includes("gl") || type.includes("ledger_vouchers")) return "expense";
  if (type.includes("bank") || type.includes("cash_bank") || type.includes("tally_bank")) return "bank";
  if (type.includes("purchase") || type.includes("vendor")) return "purchase";

  return "purchase";
}''',
    page,
)

# ----------------------------------------------------
# 6. Fix mojibake from previous clipboard/paste corruption
# ----------------------------------------------------

replacements = {
    "â€”": "—",
    "Â·": "·",
    "â€¢": "•",
    "â†’": "→",
    "â‚¹": "₹",
    "â€œ": "“",
    "â€": "”",
    "â€": "”",
}

for bad, good in replacements.items():
    page = page.replace(bad, good)

PAGE.write_text(page, encoding="utf-8")
print("Fixed AuditSection props, FilesSection props, audit auto-select, and mojibake text.")