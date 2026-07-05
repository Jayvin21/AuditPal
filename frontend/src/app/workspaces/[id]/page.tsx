"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ChangeEvent, ReactNode, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import AmbientBackground from "@/components/AmbientBackground";
import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  ClipboardList,
  Columns3,
  Download,
  FileSearch,
  FileSpreadsheet,
  Filter,
  LayoutDashboard,
  MessageSquare,
  Play,
  Save,
  Upload,
} from "lucide-react";

type Workspace = {
  id: number;
  client_name: string;
  audit_period: string;
  audit_type: string;
  status: string;
};

type UploadedFile = {
  id: number;
  original_filename: string;
  file_type: string;
  status: string;
};

type RecordRow = {
  id: number;
  source_row: number;
  document_id: string | null;
  party_name: string | null;
  transaction_date: string | null;
  amount: number | null;
  gstin: string | null;
  confidence: number;
};

type Finding = {
  id: number;
  audit_run_id: number | null;
  finding_type: string;
  risk_level: string;
  title: string;
  description: string;
  evidence: Record<string, unknown> | null;
  status: string;
  reviewer_note?: string | null;
};

type AuditRunResponse = {
  audit_run_id: number;
  status: string;
  message: string;
  coverage: {
    total_records: number;
    purchase_records_checked?: number;
    bank_records?: number;
    ledger_records?: number;
    book_records?: number;
    gstr_2b_records?: number;
    checked_records?: number;
    ledger_records_checked?: number;
    tds_records_checked?: number;
    fixed_asset_records_checked?: number;
    trial_balance_records_checked?: number;
    aging_records_checked?: number;
    document_match_records_checked?: number;
    unchecked_records: number;
    issues_found: number;
    risk_counts?: Record<string, number>;
  };
};

type AuditRunItem = {
  id: number;
  workspace_id: number;
  audit_type: string;
  status: string;
  total_records: number;
  checked_records: number;
  issues_found: number;
  unchecked_records: number;
  created_at: string;
  status_counts?: Record<string, number>;
  risk_counts?: Record<string, number>;
};

type ColumnMappingResponse = {
  file_id: number;
  workspace_id: number;
  available_columns: string[];
  detected_mapping: Record<string, string>;
  saved_mapping: Record<string, string | null> | null;
  preview_rows: Record<string, unknown>[];
};

const standardFields = [
  { key: "document_id", label: "Invoice / Bill / Voucher / UTR No" },
  { key: "party_name", label: "Vendor / Party / Payee Name" },
  { key: "transaction_date", label: "Transaction Date" },
  { key: "amount", label: "Amount" },
  { key: "debit_amount", label: "Debit / Withdrawal / Payment" },
  { key: "credit_amount", label: "Credit / Deposit / Receipt" },
  { key: "gstin", label: "GSTIN" },
  { key: "description", label: "Description / Narration" },
];

type SearchableOption = {
  value: string;
  label: string;
  description?: string;
  group?: string;
};


const fileTypeOptions: SearchableOption[] = [
  { value: "purchase_register", label: "Purchase Register", group: "Core books", description: "Generic purchase register or vendor invoice listing." },
  { value: "tally_purchase_register", label: "Tally Purchase Register", group: "Tally", description: "Purchase export from Tally Prime / ERP." },
  { value: "generic_sales_register", label: "Sales Register", group: "Core books", description: "Sales invoice register or customer billing export." },
  { value: "expense_ledger", label: "Expense Ledger", group: "Core books", description: "Expense ledger, overhead ledger, or payment expense file." },
  { value: "tds_ledger", label: "TDS Ledger", group: "Tax", description: "TDS deduction/payment review file." },
  { value: "tally_ledger_vouchers", label: "Tally Ledger Vouchers", group: "Tally", description: "Ledger voucher export from Tally." },
  { value: "bank_statement", label: "Bank Statement", group: "Banking", description: "Bank statement downloaded from bank portal." },
  { value: "cash_bank_ledger", label: "Cash / Bank Ledger", group: "Banking", description: "Books-side cash or bank ledger." },
  { value: "bank_ledger", label: "Bank Ledger", group: "Banking", description: "Books-side bank ledger." },
  { value: "tally_bank_book", label: "Tally Bank Book", group: "Tally", description: "Tally bank book export." },
  { value: "sap_vendor_line_items", label: "SAP Vendor Line Items - FBL1N", group: "SAP", description: "SAP vendor open/cleared line item export." },
  { value: "sap_gl_line_items", label: "SAP G/L Line Items - FBL3N", group: "SAP", description: "SAP general ledger line item export." },
  { value: "sap_customer_line_items", label: "SAP Customer Line Items - FBL5N", group: "SAP", description: "SAP customer line item export." },
  { value: "gstr_2b", label: "GSTR-2B", group: "GST", description: "GST portal GSTR-2B purchase/ITC file." },
  { value: "fixed_asset_register", label: "Fixed Asset Register", group: "Fixed assets", description: "Asset register with cost, WDV, depreciation, and status." },
  { value: "depreciation_schedule", label: "Depreciation Schedule", group: "Fixed assets", description: "Depreciation computation or schedule." },
  { value: "sap_asset_register", label: "SAP Asset Register", group: "SAP", description: "SAP fixed asset register/export." },
  { value: "tally_fixed_assets", label: "Tally Fixed Assets", group: "Tally", description: "Tally fixed asset ledger/export." },
  { value: "tally_trial_balance", label: "Tally Trial Balance", group: "Trial balance", description: "Trial balance exported from Tally." },
  { value: "sap_trial_balance", label: "SAP Trial Balance", group: "Trial balance", description: "Trial balance exported from SAP." },
  { value: "financial_statement", label: "Financial Statement", group: "Trial balance", description: "Financial statement or schedule extract." },
  { value: "trial_balance", label: "Trial Balance", group: "Trial balance", description: "Generic trial balance file." },
  { value: "receivables_aging", label: "Receivables Aging", group: "Aging", description: "Debtors/customer aging report." },
  { value: "payables_aging", label: "Payables Aging", group: "Aging", description: "Creditors/vendor aging report." },
  { value: "outstanding_receivables", label: "Outstanding Receivables", group: "Aging", description: "Open receivable items." },
  { value: "outstanding_payables", label: "Outstanding Payables", group: "Aging", description: "Open payable items." },
  { value: "tally_outstanding_receivables", label: "Tally Outstanding Receivables", group: "Tally", description: "Tally customer outstanding export." },
  { value: "tally_outstanding_payables", label: "Tally Outstanding Payables", group: "Tally", description: "Tally vendor outstanding export." },
  { value: "sap_customer_open_items", label: "SAP Customer Open Items", group: "SAP", description: "SAP customer open item report." },
  { value: "sap_vendor_open_items", label: "SAP Vendor Open Items", group: "SAP", description: "SAP vendor open item report." },
  { value: "support_documents", label: "Support Documents / OCR Extract", group: "Support docs", description: "Structured OCR/support document extract." },
  { value: "ocr_extract", label: "OCR Extract", group: "Support docs", description: "OCR-extracted document data." },
  { value: "document_extract", label: "Document Extract", group: "Support docs", description: "Structured document extraction output." },
  { value: "voucher_support", label: "Voucher Support", group: "Support docs", description: "Supporting voucher extract." },
  { value: "invoice_ocr", label: "Invoice OCR", group: "Support docs", description: "OCR output from invoice images/PDFs." },
  { value: "bill_ocr", label: "Bill OCR", group: "Support docs", description: "OCR output from bill images/PDFs." },
];

const importTemplates = [
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

const sections = [
  { key: "overview", label: "Overview", icon: LayoutDashboard },
  { key: "files", label: "Files", icon: Upload },
  { key: "templates", label: "Import Templates", icon: FileSearch },
  { key: "mapping", label: "Column Mapping", icon: Columns3 },
  { key: "audit", label: "Audit Runs", icon: Play },
  { key: "findings", label: "Findings", icon: ClipboardList },
  { key: "records", label: "Records", icon: FileSpreadsheet },
  { key: "reports", label: "Reports", icon: Download },
  { key: "chat", label: "Audit Chat", icon: MessageSquare },
];

export default function WorkspaceDetailPage() {
  const params = useParams<{ id: string }>();
  const workspaceId = Number(params.id);

  const [activeSection, setActiveSection] = useState("overview");

  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileType, setFileType] = useState("purchase_register");

  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [records, setRecords] = useState<RecordRow[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [auditSummary, setAuditSummary] = useState<AuditRunResponse | null>(null);
  const [auditRuns, setAuditRuns] = useState<AuditRunItem[]>([]);
  const [selectedAuditRunId, setSelectedAuditRunId] = useState<number | null>(null);

  const [selectedMappingFileId, setSelectedMappingFileId] = useState<number | null>(null);
  const [mappingPreview, setMappingPreview] = useState<ColumnMappingResponse | null>(null);
  const [mappingDraft, setMappingDraft] = useState<Record<string, string | null>>({});

  const [riskFilter, setRiskFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("needs_review");

  const [noteDrafts, setNoteDrafts] = useState<Record<number, string>>({});
  const [statusMessage, setStatusMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [updatingFindingId, setUpdatingFindingId] = useState<number | null>(null);

  async function refreshAll() {
    const [workspaceRes, filesRes, recordsRes, findingsRes, auditRunsRes] = await Promise.all([
      api.get(`/workspaces/${workspaceId}`),
      api.get(`/records/files/${workspaceId}`),
      api.get(`/records/workspace/${workspaceId}`),
      api.get(`/findings/${workspaceId}`),
      api.get(`/audit-runs/${workspaceId}`),
    ]);

    setWorkspace(workspaceRes.data);
    setFiles(filesRes.data);
    setRecords(recordsRes.data);
    setFindings(findingsRes.data);
    setAuditRuns(auditRunsRes.data);

    if (!selectedAuditRunId && auditRunsRes.data.length > 0) {
      setSelectedAuditRunId(auditRunsRes.data[0].id);
    }

    setNoteDrafts((prev) => {
      const next = { ...prev };
      for (const finding of findingsRes.data) {
        if (!(finding.id in next)) {
          next[finding.id] = finding.reviewer_note ?? "";
        }
      }
      return next;
    });
  }

  useEffect(() => {
    if (workspaceId) {
      refreshAll();
    }
  }, [workspaceId]);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setSelectedFile(event.target.files?.[0] ?? null);
  }


  async function deleteUploadedFile(fileId: number) {
    const confirmed = window.confirm(
      "Delete this file? This will also clear extracted records, findings, and audit runs for this workspace."
    );

    if (!confirmed) return;

    setBusy(true);
    setStatusMessage("Deleting file and dependent audit data...");

    try {
      await api.delete(`/uploads/${fileId}`);

      if (selectedMappingFileId === fileId) {
        setSelectedMappingFileId(null);
        setMappingPreview(null);
        setMappingDraft({});
      }

      setAuditSummary(null);
      setStatusMessage("File deleted. Extracted records, findings, and audit runs were cleared to prevent stale audit results.");
      await refreshAll();
      setActiveSection("files");
    } catch {
      setStatusMessage("File delete failed.");
    } finally {
      setBusy(false);
    }
  }

  async function uploadFile() {
    if (!selectedFile) {
      setStatusMessage("Select a file first.");
      return;
    }

    setBusy(true);
    setStatusMessage("Uploading file...");

    try {
      const formData = new FormData();
      formData.append("workspace_id", String(workspaceId));
      formData.append("file_type", fileType);
      formData.append("file", selectedFile);

      const res = await api.post("/uploads", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setSelectedFile(null);
      setStatusMessage("File uploaded. Review column mapping before extracting records.");
      await refreshAll();

      if (res.data?.id) {
        await openMapping(res.data.id);
        setActiveSection("mapping");
      }
    } catch {
      setStatusMessage("Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  async function openMapping(fileId: number) {
    setSelectedMappingFileId(fileId);
    setStatusMessage("Loading column mapping...");

    try {
      const res = await api.get(`/column-mappings/file/${fileId}`);
      const data: ColumnMappingResponse = res.data;

      setMappingPreview(data);

      const initialMapping: Record<string, string | null> = {};
      for (const field of standardFields) {
        initialMapping[field.key] =
          data.saved_mapping?.[field.key] ??
          data.detected_mapping?.[field.key] ??
          null;
      }

      setMappingDraft(initialMapping);
      setStatusMessage("Column mapping loaded.");
    } catch {
      setStatusMessage("Could not load column mapping.");
    }
  }

  async function saveMapping() {
    if (!selectedMappingFileId) return;

    setBusy(true);
    setStatusMessage("Saving column mapping...");

    try {
      await api.post(`/column-mappings/file/${selectedMappingFileId}`, {
        mapping: mappingDraft,
      });

      setStatusMessage("Column mapping saved. Apply mapping to extract records.");
      await refreshAll();
      await openMapping(selectedMappingFileId);
    } catch {
      setStatusMessage("Could not save column mapping.");
    } finally {
      setBusy(false);
    }
  }

  async function parseFiles() {
    setBusy(true);
    setStatusMessage("Extracting records using saved mappings...");

    try {
      await api.post(`/records/parse-workspace/${workspaceId}?force_reparse=true`);
      setStatusMessage("Records extracted using latest mappings.");
      await refreshAll();
      setActiveSection("audit");
    } catch {
      setStatusMessage("Record extraction failed.");
    } finally {
      setBusy(false);
    }
  }

  async function runPurchaseAudit() {
    setBusy(true);
    setStatusMessage("Running purchase audit...");

    try {
      const res = await api.post(`/audit-runs/${workspaceId}/run-purchase-audit`);
      setAuditSummary(res.data);
      setSelectedAuditRunId(res.data.audit_run_id);
      setStatusMessage("Purchase audit completed.");
      await refreshAll();
      setActiveSection("findings");
    } catch {
      setStatusMessage("Purchase audit failed.");
    } finally {
      setBusy(false);
    }
  }



  async function runSalesAudit() {
    setBusy(true);
    setStatusMessage("Running sales audit...");

    try {
      const res = await api.post(`/audit-runs/${workspaceId}/run-sales-audit`);
      setAuditSummary(res.data);
      setSelectedAuditRunId(res.data.audit_run_id);
      setStatusMessage("Sales audit completed.");
      await refreshAll();
      setActiveSection("findings");
    } catch {
      setStatusMessage("Sales audit failed.");
    } finally {
      setBusy(false);
    }
  }

  async function runExpenseAudit() {
    setBusy(true);
    setStatusMessage("Running expense audit...");

    try {
      const res = await api.post(`/audit-runs/${workspaceId}/run-expense-audit`);
      setAuditSummary(res.data);
      setSelectedAuditRunId(res.data.audit_run_id);
      setStatusMessage("Expense audit completed.");
      await refreshAll();
      setActiveSection("findings");
    } catch {
      setStatusMessage("Expense audit failed.");
    } finally {
      setBusy(false);
    }
  }








  async function runDocumentMatching() {
    setBusy(true);
    setStatusMessage("Running support document matching...");

    try {
      const res = await api.post(`/audit-runs/${workspaceId}/run-document-matching`);
      setAuditSummary(res.data);
      setSelectedAuditRunId(res.data.audit_run_id);
      setStatusMessage("Document matching completed.");
      await refreshAll();
      setActiveSection("findings");
    } catch {
      setStatusMessage("Document matching failed.");
    } finally {
      setBusy(false);
    }
  }

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

  async function runTdsReview() {
    setBusy(true);
    setStatusMessage("Running TDS review...");

    try {
      const res = await api.post(`/audit-runs/${workspaceId}/run-tds-review`);
      setAuditSummary(res.data);
      setSelectedAuditRunId(res.data.audit_run_id);
      setStatusMessage("TDS review completed.");
      await refreshAll();
      setActiveSection("findings");
    } catch {
      setStatusMessage("TDS review failed.");
    } finally {
      setBusy(false);
    }
  }

  async function runLedgerScrutiny() {
    setBusy(true);
    setStatusMessage("Running ledger scrutiny...");

    try {
      const res = await api.post(`/audit-runs/${workspaceId}/run-ledger-scrutiny`);
      setAuditSummary(res.data);
      setSelectedAuditRunId(res.data.audit_run_id);
      setStatusMessage("Ledger scrutiny completed.");
      await refreshAll();
      setActiveSection("findings");
    } catch {
      setStatusMessage("Ledger scrutiny failed.");
    } finally {
      setBusy(false);
    }
  }

  async function runGstReconciliation() {
    setBusy(true);
    setStatusMessage("Running GST reconciliation...");

    try {
      const res = await api.post(`/audit-runs/${workspaceId}/run-gst-reconciliation`);
      setAuditSummary(res.data);
      setSelectedAuditRunId(res.data.audit_run_id);
      setStatusMessage("GST reconciliation completed.");
      await refreshAll();
      setActiveSection("findings");
    } catch {
      setStatusMessage("GST reconciliation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function runBankReconciliation() {
    setBusy(true);
    setStatusMessage("Running bank reconciliation...");

    try {
      const res = await api.post(`/audit-runs/${workspaceId}/run-bank-reconciliation`);
      setAuditSummary(res.data);
      setSelectedAuditRunId(res.data.audit_run_id);
      setStatusMessage("Bank reconciliation completed.");
      await refreshAll();
      setActiveSection("findings");
    } catch {
      setStatusMessage("Bank reconciliation failed.");
    } finally {
      setBusy(false);
    }
  }

  function exportCsv() {
    window.open(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/reports/${workspaceId}/findings.csv`,
      "_blank"
    );
  }

  function exportPdf() {
    window.open(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/reports/${workspaceId}/audit-report.pdf`,
      "_blank"
    );
  }


  async function deleteAuditRun(auditRunId: number) {
    const confirmed = window.confirm(
      "Delete this audit run? This will delete only this run and its findings/review notes."
    );

    if (!confirmed) return;

    setBusy(true);
    setStatusMessage("Deleting audit run...");

    try {
      await api.delete(`/audit-runs/${auditRunId}`);

      if (selectedAuditRunId === auditRunId) {
        setSelectedAuditRunId(null);
      }

      setAuditSummary(null);
      setStatusMessage("Audit run deleted.");
      await refreshAll();
    } catch {
      setStatusMessage("Could not delete audit run.");
    } finally {
      setBusy(false);
    }
  }

  async function updateFindingStatus(findingId: number, status: string) {
    setUpdatingFindingId(findingId);
    try {
      await api.patch(`/findings/${findingId}`, { status });
      await refreshAll();
    } finally {
      setUpdatingFindingId(null);
    }
  }

  async function saveReviewerNote(findingId: number) {
    setUpdatingFindingId(findingId);
    try {
      await api.patch(`/findings/${findingId}`, {
        reviewer_note: noteDrafts[findingId] ?? "",
      });
      await refreshAll();
    } finally {
      setUpdatingFindingId(null);
    }
  }

  const visibleFindings = selectedAuditRunId
    ? findings.filter((finding) => finding.audit_run_id === selectedAuditRunId)
    : findings;

  const high = visibleFindings.filter((f) => f.risk_level === "high").length;
  const medium = visibleFindings.filter((f) => f.risk_level === "medium").length;
  const low = visibleFindings.filter((f) => f.risk_level === "low").length;

  const mappedFiles = files.filter((file) => file.status === "mapped" || file.status === "parsed").length;
  const parsedFiles = files.filter((file) => file.status === "parsed").length;
  const needsReview = visibleFindings.filter((finding) => finding.status === "needs_review").length;
  const confirmedIssues = visibleFindings.filter((finding) => finding.status === "confirmed_issue").length;
  const falsePositive = visibleFindings.filter((finding) => finding.status === "false_positive").length;
  const needsClarification = visibleFindings.filter((finding) => finding.status === "needs_client_clarification").length;
  const resolved = visibleFindings.filter((finding) => finding.status === "resolved").length;

  const findingTypes = useMemo(
    () => Array.from(new Set(visibleFindings.map((f) => f.finding_type))).sort(),
    [visibleFindings]
  );

  const filteredFindings = visibleFindings.filter((finding) => {
    const riskMatch = riskFilter === "all" || finding.risk_level === riskFilter;
    const typeMatch = typeFilter === "all" || finding.finding_type === typeFilter;
    const statusMatch = statusFilter === "all" || finding.status === statusFilter;
    return riskMatch && typeMatch && statusMatch;
  });

  const nextAction = getNextAction({
    files: files.length,
    mappedFiles,
    records: records.length,
    findings: findings.length,
    needsReview,
  });

  return (
    <main className="relative min-h-screen bg-[#F6FBF8] text-[#17352E]">
      <AmbientBackground />

      <div className="flex min-h-screen flex-col">
        <TopNav />

        <div className="mx-auto grid w-full max-w-7xl flex-1 gap-6 px-6 py-6 lg:grid-cols-[260px_1fr]">
          <aside className="hidden lg:block">
            <div className="sticky top-6 rounded-3xl border border-[#C8DDD0] bg-white/88 p-4 shadow-sm backdrop-blur">
              <div className="border-b border-[#D6E6DD] pb-4">
                <p className="text-xs font-medium uppercase tracking-[0.2em] text-[#6B8E7F]">
                  Workspace
                </p>
                <h2 className="mt-2 text-lg font-semibold text-[#17352E]">
                  {workspace?.client_name ?? `Workspace #${workspaceId}`}
                </h2>
                <p className="mt-1 text-sm text-[#5F7D70]">
                  {workspace?.audit_period ?? "—"}
                </p>
              </div>

              <nav className="mt-4 space-y-1">
                {sections.map((section) => {
                  const Icon = section.icon;
                  const active = activeSection === section.key;

                  return (
                    <button
                      key={section.key}
                      onClick={() => setActiveSection(section.key)}
                      className={
                        active
                          ? "flex w-full items-center gap-3 rounded-2xl bg-[#358873] px-4 py-3 text-left text-sm font-medium text-white shadow-sm"
                          : "flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-left text-sm font-medium text-[#5F7D70] transition hover:bg-[#EDF6F0] hover:text-[#17352E]"
                      }
                    >
                      <Icon size={17} />
                      {section.label}
                    </button>
                  );
                })}
              </nav>
            </div>
          </aside>

          <section className="min-w-0">
            <MobileSectionNav activeSection={activeSection} setActiveSection={setActiveSection} />

            <header className="mb-5 rounded-3xl border border-[#C8DDD0] bg-white/88 p-5 shadow-sm backdrop-blur">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <Link
                    href="/workspaces"
                    className="inline-flex items-center gap-2 text-sm text-[#5F7D70] hover:text-[#17352E]"
                  >
                    <ArrowLeft size={15} />
                    All workspaces
                  </Link>

                  <h1 className="mt-3 text-3xl font-semibold tracking-tight text-[#17352E]">
                    {workspace?.client_name ?? `Workspace #${workspaceId}`}
                  </h1>

                  <p className="mt-2 text-[#5F7D70]">
                    {workspace?.audit_period ?? "—"} · {workspace?.audit_type ?? "—"} · {workspace?.status ?? "—"}
                  </p>
                </div>

                <div className="rounded-2xl border border-[#D6E6DD] bg-[#F6FBF8] px-4 py-3 text-sm text-[#42685B]">
                  Upload → Map → Extract → Audit → Review → Export
                </div>
              </div>
            </header>

            <section className="mb-5 grid gap-4 md:grid-cols-4">
              <Metric label="Files" value={String(files.length)} />
              <Metric label="Records" value={String(records.length)} />
              <Metric label="High Risk" value={String(high)} />
              <Metric label="Findings" value={String(findings.length)} />
            </section>

            {statusMessage && (
              <div className="mb-5 rounded-2xl border border-[#C8DDD0] bg-white/88 p-4 text-sm text-[#5F7D70] shadow-sm backdrop-blur">
                {statusMessage}
              </div>
            )}

            {activeSection === "overview" && (
              <OverviewSection
                nextAction={nextAction}
                files={files.length}
                mappedFiles={mappedFiles}
                parsedFiles={parsedFiles}
                records={records.length}
                findings={findings.length}
                high={high}
                medium={medium}
                low={low}
                needsReview={needsReview}
                confirmedIssues={confirmedIssues}
                setActiveSection={setActiveSection}
              />
            )}

            {activeSection === "templates" && (
              <ImportTemplatesSection />
            )}

            {activeSection === "files" && (
              <FilesSection
                selectedFile={selectedFile}
                fileType={fileType}
                files={files}
                busy={busy}
                setFileType={setFileType}
                handleFileChange={handleFileChange}
                uploadFile={uploadFile}
                deleteUploadedFile={deleteUploadedFile}
                openMapping={openMapping}
                setActiveSection={setActiveSection}
              />
            )}

            {activeSection === "mapping" && (
              <MappingSection
                busy={busy}
                mappingPreview={mappingPreview}
                mappingDraft={mappingDraft}
                setMappingDraft={setMappingDraft}
                saveMapping={saveMapping}
                parseFiles={parseFiles}
              />
            )}

            {activeSection === "audit" && (
              <AuditSection
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
                runDocumentMatching={runDocumentMatching}
                runAgingReview={runAgingReview}
                runTrialBalanceReview={runTrialBalanceReview}
                runFixedAssetAudit={runFixedAssetAudit}
                runTdsReview={runTdsReview}
                runLedgerScrutiny={runLedgerScrutiny}
                runGstReconciliation={runGstReconciliation}
                runBankReconciliation={runBankReconciliation}
              />
            )}

            {activeSection === "findings" && (
              <FindingsSection
                findings={findings}
                filteredFindings={filteredFindings}
                findingTypes={findingTypes}
                high={high}
                medium={medium}
                low={low}
                needsReview={needsReview}
                confirmedIssues={confirmedIssues}
                falsePositive={falsePositive}
                needsClarification={needsClarification}
                resolved={resolved}
                riskFilter={riskFilter}
                typeFilter={typeFilter}
                statusFilter={statusFilter}
                noteDrafts={noteDrafts}
                updatingFindingId={updatingFindingId}
                setRiskFilter={setRiskFilter}
                setTypeFilter={setTypeFilter}
                setStatusFilter={setStatusFilter}
                setNoteDrafts={setNoteDrafts}
                updateFindingStatus={updateFindingStatus}
                saveReviewerNote={saveReviewerNote}
                exportCsv={exportCsv}
                exportPdf={exportPdf}
              />
            )}

            {activeSection === "records" && (
              <RecordsSection records={records} />
            )}

            {activeSection === "reports" && (
              <ReportsSection
                findings={findings.length}
                exportCsv={exportCsv}
                exportPdf={exportPdf}
              />
            )}

            {activeSection === "chat" && (
              <ChatPlaceholder />
            )}
          </section>
        </div>
      </div>
    </main>
  );
}

function TopNav() {
  return (
    <div className="border-b border-[#C8DDD0] bg-white/78 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <Link href="/" className="text-xl font-semibold tracking-tight text-[#17352E]">
          AuditPal
        </Link>

        <div className="flex items-center gap-4 text-sm">
          <Link href="/workspaces" className="text-[#5F7D70] hover:text-[#17352E]">
            Workspaces
          </Link>
          <span className="hidden text-[#B0C9BA] md:inline">•</span>
          <span className="hidden text-[#5F7D70] md:inline">
            Human-in-the-loop audit assistant
          </span>
        </div>
      </div>
    </div>
  );
}

function MobileSectionNav({
  activeSection,
  setActiveSection,
}: {
  activeSection: string;
  setActiveSection: (section: string) => void;
}) {
  return (
    <div className="mb-5 overflow-x-auto lg:hidden">
      <div className="flex min-w-max gap-2 rounded-2xl border border-[#C8DDD0] bg-white/88 p-2 shadow-sm backdrop-blur">
        {sections.map((section) => (
          <button
            key={section.key}
            onClick={() => setActiveSection(section.key)}
            className={
              activeSection === section.key
                ? "rounded-xl bg-[#358873] px-4 py-2 text-sm font-medium text-white"
                : "rounded-xl px-4 py-2 text-sm font-medium text-[#5F7D70]"
            }
          >
            {section.label}
          </button>
        ))}
      </div>
    </div>
  );
}


function SearchableSelect({
  value,
  onChange,
  options,
  placeholder = "Search...",
  emptyText = "No matches",
}: {
  value: string;
  onChange: (value: string) => void;
  options: SearchableOption[];
  placeholder?: string;
  emptyText?: string;
}) {
  const selected = options.find((option) => option.value === value) ?? null;
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);

  const filteredOptions = options.filter((option) => {
    const haystack = `${option.label} ${option.value} ${option.description ?? ""} ${option.group ?? ""}`.toLowerCase();
    return haystack.includes(query.toLowerCase().trim());
  });

  return (
    <div className="relative">
      <input
        value={open ? query : selected?.label ?? ""}
        onFocus={() => {
          setOpen(true);
          setQuery("");
        }}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
        }}
        onBlur={() => {
          window.setTimeout(() => setOpen(false), 120);
        }}
        placeholder={placeholder}
        className="w-full rounded-xl border border-[#C8DDD0] bg-[#F6FBF8] px-4 py-3 text-sm outline-none focus:border-[#4E9C81]"
      />

      {selected && !open && (
        <p className="mt-2 text-xs text-[#6B8E7F]">
          Selected: <span className="font-medium text-[#42685B]">{selected.label}</span>
          {selected.group ? ` · ${selected.group}` : ""}
        </p>
      )}

      {open && (
        <div className="absolute z-30 mt-2 max-h-72 w-full overflow-auto rounded-2xl border border-[#C8DDD0] bg-white p-2 shadow-lg">
          {filteredOptions.length === 0 ? (
            <div className="px-3 py-3 text-sm text-[#6B8E7F]">{emptyText}</div>
          ) : (
            filteredOptions.map((option) => {
              const active = option.value === value;

              return (
                <button
                  key={option.value}
                  type="button"
                  onMouseDown={(event) => {
                    event.preventDefault();
                    onChange(option.value);
                    setQuery("");
                    setOpen(false);
                  }}
                  className={
                    active
                      ? "block w-full rounded-xl bg-[#358873] px-3 py-3 text-left text-sm text-white"
                      : "block w-full rounded-xl px-3 py-3 text-left text-sm text-[#17352E] hover:bg-[#EDF6F0]"
                  }
                >
                  <span className="block font-medium">{option.label}</span>
                  <span className={active ? "mt-1 block text-xs text-white/80" : "mt-1 block text-xs text-[#6B8E7F]"}>
                    {option.group ? `${option.group} · ` : ""}
                    {option.description ?? option.value}
                  </span>
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}

function OverviewSection({
  nextAction,
  files,
  mappedFiles,
  parsedFiles,
  records,
  findings,
  high,
  medium,
  low,
  needsReview,
  confirmedIssues,
  setActiveSection,
}: {
  nextAction: { title: string; description: string; section: string };
  files: number;
  mappedFiles: number;
  parsedFiles: number;
  records: number;
  findings: number;
  high: number;
  medium: number;
  low: number;
  needsReview: number;
  confirmedIssues: number;
  setActiveSection: (section: string) => void;
}) {
  return (
    <div className="space-y-6">
      <Card>
        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.18em] text-[#6B8E7F]">
              Recommended next action
            </p>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-[#17352E]">
              {nextAction.title}
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[#5F7D70]">
              {nextAction.description}
            </p>
            <button
              onClick={() => setActiveSection(nextAction.section)}
              className="mt-5 rounded-xl bg-[#358873] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#2F7866]"
            >
              Continue
            </button>
          </div>

          <div className="rounded-2xl border border-[#D6E6DD] bg-[#F6FBF8] p-4">
            <h3 className="font-medium text-[#17352E]">Audit readiness</h3>
            <div className="mt-4 space-y-3">
              <ReadinessRow label="Files uploaded" value={files} done={files > 0} />
              <ReadinessRow label="Files mapped" value={mappedFiles} done={mappedFiles > 0} />
              <ReadinessRow label="Files parsed" value={parsedFiles} done={records > 0} />
              <ReadinessRow label="Findings generated" value={findings} done={findings > 0} />
            </div>
          </div>
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-4">
        <Metric label="Needs Review" value={String(needsReview)} />
        <Metric label="Confirmed Issues" value={String(confirmedIssues)} />
        <Metric label="Medium Risk" value={String(medium)} />
        <Metric label="Low Risk" value={String(low)} />
      </div>

      <Card>
        <div className="mb-4 flex items-center gap-2">
          <BarChart3 size={18} className="text-[#358873]" />
          <h2 className="font-medium">Risk distribution</h2>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <RiskBox label="High Risk" value={high} tone="high" />
          <RiskBox label="Medium Risk" value={medium} tone="medium" />
          <RiskBox label="Low Risk" value={low} tone="low" />
        </div>
      </Card>
    </div>
  );
}

function ImportTemplatesSection() {
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

function FilesSection({
  selectedFile,
  fileType,
  files,
  busy,
  setFileType,
  handleFileChange,
  uploadFile,
  deleteUploadedFile,
  openMapping,
  setActiveSection,
}: {
  selectedFile: File | null;
  fileType: string;
  files: UploadedFile[];
  busy: boolean;
  setFileType: (value: string) => void;
  handleFileChange: (event: ChangeEvent<HTMLInputElement>) => void;
  uploadFile: () => void;
  deleteUploadedFile: (fileId: number) => void;
  openMapping: (fileId: number) => void;
  setActiveSection: (section: string) => void;
}) {
  const [fileSearch, setFileSearch] = useState("");

  const selectedType = fileTypeOptions.find((option) => option.value === fileType);
  const visibleFiles = files.filter((file) => {
    const query = fileSearch.toLowerCase().trim();
    if (!query) return true;

    return `${file.original_filename} ${file.file_type} ${file.status}`.toLowerCase().includes(query);
  });

  return (
    <SectionShell
      title="Files"
      subtitle="Upload source files and label them correctly before column mapping."
    >
      <div className="grid items-start gap-6 lg:grid-cols-[0.78fr_1.22fr]">
        <div className="h-fit">
          <Card>
            <div className="mb-5 flex items-center gap-2">
              <Upload size={18} className="text-[#358873]" />
              <h2 className="font-medium">Upload audit file</h2>
            </div>

            <label className="mb-2 block text-sm text-[#5F7D70]">File type</label>
            <SearchableSelect
              value={fileType}
              onChange={setFileType}
              options={fileTypeOptions}
              placeholder="Search file type, module, source..."
            />

            {selectedType?.description && (
              <div className="my-4 rounded-2xl border border-[#D6E6DD] bg-[#F6FBF8] p-4 text-sm leading-6 text-[#5F7D70]">
                <p className="font-medium text-[#17352E]">{selectedType.label}</p>
                <p className="mt-1">{selectedType.description}</p>
              </div>
            )}

            <input
              type="file"
              accept=".xlsx,.xls,.csv"
              onChange={handleFileChange}
              className="mb-4 mt-4 w-full rounded-xl border border-[#C8DDD0] bg-[#F6FBF8] px-4 py-3 text-sm text-[#17352E]"
            />

            {selectedFile && (
              <p className="mb-4 rounded-xl border border-[#D6E6DD] bg-[#F6FBF8] p-3 text-sm text-[#5F7D70]">
                Selected: {selectedFile.name}
              </p>
            )}

            <button
              onClick={uploadFile}
              disabled={busy}
              className="w-full rounded-xl bg-[#358873] px-5 py-3 font-medium text-white transition hover:bg-[#2F7866] disabled:opacity-50"
            >
              Upload File
            </button>
          </Card>
        </div>

        <Card>
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <FileSpreadsheet size={18} className="text-[#358873]" />
              <h2 className="font-medium">Uploaded files</h2>
            </div>

            <span className="rounded-full bg-[#EAF4EE] px-3 py-1 text-xs font-medium text-[#2F7866]">
              {visibleFiles.length} / {files.length}
            </span>
          </div>

          {files.length > 0 && (
            <input
              value={fileSearch}
              onChange={(event) => setFileSearch(event.target.value)}
              placeholder="Search uploaded files, type, status..."
              className="mb-4 w-full rounded-xl border border-[#C8DDD0] bg-[#F6FBF8] px-4 py-3 text-sm outline-none focus:border-[#4E9C81]"
            />
          )}

          {files.length === 0 ? (
            <EmptyState text="No files uploaded yet. Upload a purchase register, bank statement, or ledger file." />
          ) : visibleFiles.length === 0 ? (
            <EmptyState text="No uploaded files match the search." />
          ) : (
            <div className="max-h-[720px] space-y-3 overflow-auto pr-1">
              {visibleFiles.map((file) => (
                <div
                  key={file.id}
                  className="rounded-xl border border-[#D6E6DD] bg-[#F6FBF8] p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="break-all font-medium text-[#17352E]">{file.original_filename}</p>
                      <p className="mt-1 text-sm text-[#5F7D70]">
                        {formatFileType(file.file_type)} · {file.status}
                      </p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => {
                          openMapping(file.id);
                          setActiveSection("mapping");
                        }}
                        className="rounded-lg border border-[#BFD8CB] bg-white px-3 py-2 text-xs font-medium text-[#17352E] transition hover:bg-[#EDF6F0]"
                      >
                        Map Columns
                      </button>

                      <button
                        onClick={() => deleteUploadedFile(file.id)}
                        disabled={busy}
                        className="rounded-lg border border-[#F3CACA] bg-white px-3 py-2 text-xs font-medium text-[#B42318] transition hover:bg-[#FDE8E8] disabled:opacity-50"
                      >
                        Delete File
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </SectionShell>
  );
}

function MappingSection({
  busy,
  mappingPreview,
  mappingDraft,
  setMappingDraft,
  saveMapping,
  parseFiles,
}: {
  busy: boolean;
  mappingPreview: ColumnMappingResponse | null;
  mappingDraft: Record<string, string | null>;
  setMappingDraft: React.Dispatch<React.SetStateAction<Record<string, string | null>>>;
  saveMapping: () => void;
  parseFiles: () => void;
}) {
  return (
    <SectionShell
      title="Column Mapping"
      subtitle="Map messy Excel, Tally, SAP, or bank statement columns into AuditPal fields."
    >
      <Card>
        {!mappingPreview ? (
          <EmptyState text="Select Map Columns from the Files section to start mapping an uploaded file." />
        ) : (
          <div className="grid gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
            <div>
              <div className="mb-5 flex items-center gap-2">
                <Columns3 size={18} className="text-[#358873]" />
                <h2 className="font-medium">File #{mappingPreview.file_id}</h2>
              </div>

              <div className="space-y-4">
                {standardFields.map((field) => (
                  <div key={field.key}>
                    <label className="mb-2 block text-sm text-[#5F7D70]">
                      {field.label}
                    </label>
                    <select
                      value={mappingDraft[field.key] ?? ""}
                      onChange={(e) =>
                        setMappingDraft((prev) => ({
                          ...prev,
                          [field.key]: e.target.value || null,
                        }))
                      }
                      className="w-full rounded-xl border border-[#C8DDD0] bg-[#F6FBF8] px-4 py-3 text-sm outline-none focus:border-[#4E9C81]"
                    >
                      <option value="">Not mapped</option>
                      {mappingPreview.available_columns.map((column) => (
                        <option key={column} value={column}>
                          {column}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}

                <div className="grid gap-3">
                  <button
                    onClick={saveMapping}
                    disabled={busy}
                    className="rounded-xl bg-[#358873] px-5 py-3 font-medium text-white transition hover:bg-[#2F7866] disabled:opacity-50"
                  >
                    Save Mapping
                  </button>

                  <button
                    onClick={parseFiles}
                    disabled={busy}
                    className="rounded-xl border border-[#B4D6C1] bg-white px-5 py-3 font-medium text-[#17352E] transition hover:bg-[#EDF6F0] disabled:opacity-50"
                  >
                    Extract Records
                  </button>
                </div>
              </div>
            </div>

            <div className="min-w-0">
              <h3 className="mb-3 font-medium">Preview Rows</h3>
              <div className="max-h-[560px] overflow-auto rounded-xl border border-[#D6E6DD]">
                <table className="w-full text-left text-xs">
                  <thead className="sticky top-0 bg-[#EDF6F0] text-[#5F7D70]">
                    <tr>
                      {mappingPreview.available_columns.map((column) => (
                        <th key={column} className="whitespace-nowrap px-3 py-2">
                          {column}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {mappingPreview.preview_rows.map((row, index) => (
                      <tr key={index} className="border-t border-[#D6E6DD] bg-white/70">
                        {mappingPreview.available_columns.map((column) => (
                          <td key={column} className="whitespace-nowrap px-3 py-2 text-[#42685B]">
                            {String(row[column] ?? "-")}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </Card>
    </SectionShell>
  );
}

function AuditSection({
  files,
  auditRuns,
  selectedAuditRunId,
  setSelectedAuditRunId,
  deleteAuditRun,
  busy,
  auditSummary,
  parseFiles,
  runPurchaseAudit,
  runSalesAudit,
  runExpenseAudit,
  runDocumentMatching,
  runAgingReview,
  runTrialBalanceReview,
  runFixedAssetAudit,
  runTdsReview,
  runLedgerScrutiny,
  runGstReconciliation,
  runBankReconciliation,
}: {
  files: UploadedFile[];
  auditRuns?: AuditRunItem[];
  selectedAuditRunId: number | null;
  setSelectedAuditRunId: (id: number | null) => void;
  deleteAuditRun: (id: number) => void;
  busy: boolean;
  auditSummary: AuditRunResponse | null;
  parseFiles: () => void;
  runPurchaseAudit: () => void;
  runSalesAudit: () => void;
  runExpenseAudit: () => void;
  runDocumentMatching: () => void;
  runAgingReview: () => void;
  runTrialBalanceReview: () => void;
  runFixedAssetAudit: () => void;
  runTdsReview: () => void;
  runLedgerScrutiny: () => void;
  runGstReconciliation: () => void;
  runBankReconciliation: () => void;
}) {
  const runHistory = auditRuns ?? [];
  const recommendedModule = inferRecommendedAuditModule(files);
  const [selectedModule, setSelectedModule] = useState(recommendedModule);
  const [runSearch, setRunSearch] = useState("");
  const [runTypeFilter, setRunTypeFilter] = useState("all");
  const [showAllRuns, setShowAllRuns] = useState(false);

  useEffect(() => {
    setSelectedModule(recommendedModule);
  }, [recommendedModule]);

  const selectedRun = runHistory.find((run) => run.id === selectedAuditRunId) ?? runHistory[0] ?? null;

  const moduleOptions = [
    {
      key: "purchase",
      label: "Purchase Audit",
      description: "Checks purchase registers for missing fields, GSTIN issues, duplicates, high-value entries, and year-end risks.",
      run: runPurchaseAudit,
    },
    {
      key: "sales",
      label: "Sales Audit",
      description: "Checks sales registers for duplicate invoices, GSTIN issues, cancellations, returns, high-value invoices, and cut-off risk.",
      run: runSalesAudit,
    },
    {
      key: "expense",
      label: "Expense Audit",
      description: "Checks expense ledgers for duplicate vouchers, high-value spends, cash expenses, weak narration, and discretionary spend.",
      run: runExpenseAudit,
    },
    {
      key: "document_match",
      label: "Document Matching",
      description: "Matches books entries against OCR/support document extracts and flags missing support, mismatched amounts, party mismatches, and low confidence OCR.",
      run: runDocumentMatching,
    },
    {
      key: "aging",
      label: "Receivables/Payables Aging",
      description: "Reviews debtor/creditor aging and open-item reports for overdue balances, missing due dates, old receivables, and payable confirmation risks.",
      run: runAgingReview,
    },
    {
      key: "trial_balance",
      label: "Trial Balance Review",
      description: "Reviews trial balance and financial statement ledgers for classification issues, abnormal balances, suspense accounts, and material balances.",
      run: runTrialBalanceReview,
    },
    {
      key: "fixed_asset",
      label: "Fixed Asset Audit",
      description: "Reviews fixed asset registers for missing asset IDs, capitalization risk, depreciation issues, disposals, and duplicate asset references.",
      run: runFixedAssetAudit,
    },
    {
      key: "tds",
      label: "TDS Review",
      description: "Reviews vendor/expense payments for possible TDS non-deduction, missing PAN, missing section, high-value payments, and duplicate vouchers.",
      run: runTdsReview,
    },
    {
      key: "ledger",
      label: "Ledger Scrutiny",
      description: "Reviews ledger-style exports for suspense accounts, manual journals, year-end entries, cash risks, loans/advances, and repeated posting patterns.",
      run: runLedgerScrutiny,
    },
    {
      key: "gst",
      label: "GST Reconciliation",
      description: "Compares books purchase/ITC entries with GSTR-2B and flags missing invoices, amount mismatches, and duplicate ITC risk.",
      run: runGstReconciliation,
    },
    {
      key: "bank",
      label: "Bank Reconciliation",
      description: "Compares bank statements with cash/bank ledgers and flags unmatched or repeated entries.",
      run: runBankReconciliation,
    },
  ];

  const moduleSelectOptions: SearchableOption[] = moduleOptions.map((module) => ({
    value: module.key,
    label: module.label,
    description: module.description,
    group: "Audit module",
  }));

  const selected = moduleOptions.find((module) => module.key === selectedModule) ?? moduleOptions[0];

  const runTypeOptions: SearchableOption[] = [
    { value: "all", label: "All audit types", group: "History filter" },
    ...Array.from(new Set(runHistory.map((run) => run.audit_type))).sort().map((type) => ({
      value: type,
      label: formatAuditType(type),
      group: "Audit type",
      description: type,
    })),
  ];

  const filteredRunHistory = runHistory.filter((run) => {
    const query = runSearch.toLowerCase().trim();
    const typeMatch = runTypeFilter === "all" || run.audit_type === runTypeFilter;
    const searchMatch =
      !query ||
      `${formatAuditType(run.audit_type)} ${run.audit_type} ${run.id} ${run.status}`.toLowerCase().includes(query);

    return typeMatch && searchMatch;
  });

  const visibleRunHistory = showAllRuns ? filteredRunHistory : filteredRunHistory.slice(0, 5);

  const coverageSource =
    auditSummary && auditSummary.audit_run_id === selectedAuditRunId
      ? auditSummary.coverage
      : selectedRun
        ? {
            total_records: selectedRun.total_records,
            checked_records: selectedRun.checked_records,
            unchecked_records: selectedRun.unchecked_records,
            issues_found: selectedRun.issues_found,
          }
        : null;

  const checkedRecords =
    coverageSource?.checked_records ??
    coverageSource?.purchase_records_checked ??
    coverageSource?.sales_records_checked ??
    coverageSource?.expense_records_checked ??
    coverageSource?.ledger_records_checked ??
    coverageSource?.tds_records_checked ??
    coverageSource?.fixed_asset_records_checked ??
    coverageSource?.trial_balance_records_checked ??
    coverageSource?.aging_records_checked ??
    coverageSource?.document_match_records_checked ??
    0;

  return (
    <SectionShell
      title="Audit Runs"
      subtitle="Run audit modules, revisit previous runs, and continue review where you left off."
    >
      <div className="grid items-start gap-6 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="h-fit">
          <Card>
            <div className="mb-5 flex items-center gap-2">
              <Play size={18} className="text-[#358873]" />
              <h2 className="font-medium">Run audit module</h2>
            </div>

            <label className="mb-2 block text-sm text-[#5F7D70]">
              Audit module
            </label>

            <SearchableSelect
              value={selectedModule}
              onChange={setSelectedModule}
              options={moduleSelectOptions}
              placeholder="Search audit module..."
            />

            <div className="my-4 rounded-2xl border border-[#D6E6DD] bg-[#F6FBF8] p-4 text-sm leading-6 text-[#5F7D70]">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <p className="font-medium text-[#17352E]">{selected.label}</p>
                {selected.key === recommendedModule && (
                  <span className="rounded-full bg-[#EAF4EE] px-2 py-1 text-[11px] font-medium text-[#2F7866]">
                    Recommended
                  </span>
                )}
              </div>
              <p>{selected.description}</p>
            </div>

            <div className="space-y-3">
              <button
                onClick={parseFiles}
                disabled={busy}
                className="w-full rounded-xl border border-[#B4D6C1] bg-white px-5 py-3 font-medium text-[#17352E] transition hover:bg-[#EDF6F0] disabled:opacity-50"
              >
                Apply Mapping & Extract Records
              </button>

              <button
                onClick={selected.run}
                disabled={busy}
                className="w-full rounded-xl bg-[#358873] px-5 py-3 font-medium text-white transition hover:bg-[#2F7866] disabled:opacity-50"
              >
                Run {selected.label}
              </button>
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <div className="mb-4 flex items-center gap-2">
              <CheckCircle2 size={18} className="text-[#358873]" />
              <h2 className="font-medium">Selected audit coverage</h2>
            </div>

            {!coverageSource ? (
              <EmptyState text="No audit run selected yet. Extract records, then run the recommended audit module." />
            ) : (
              <div className="grid gap-3 md:grid-cols-4">
                <Metric label="Total" value={String(coverageSource.total_records)} />
                <Metric label="Checked" value={String(checkedRecords)} />
                <Metric label="Unchecked" value={String(coverageSource.unchecked_records)} />
                <Metric label="Issues" value={String(coverageSource.issues_found)} />
              </div>
            )}
          </Card>

          <Card>
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="font-medium">Audit run history</h2>
                <p className="mt-1 text-sm text-[#5F7D70]">
                  Search, filter, and select a run to continue review.
                </p>
              </div>

              <span className="rounded-full bg-[#EAF4EE] px-3 py-1 text-xs font-medium text-[#2F7866]">
                {filteredRunHistory.length} / {runHistory.length}
              </span>
            </div>

            {runHistory.length > 0 && (
              <div className="mb-4 grid gap-3 rounded-2xl border border-[#D6E6DD] bg-[#F6FBF8] p-3 md:grid-cols-[1fr_0.9fr_auto]">
                <input
                  value={runSearch}
                  onChange={(event) => setRunSearch(event.target.value)}
                  placeholder="Search run, type, status, ID..."
                  className="rounded-xl border border-[#C8DDD0] bg-white px-4 py-3 text-sm outline-none focus:border-[#4E9C81]"
                />

                <SearchableSelect
                  value={runTypeFilter}
                  onChange={setRunTypeFilter}
                  options={runTypeOptions}
                  placeholder="Filter audit type..."
                />

                <button
                  onClick={() => setShowAllRuns((current) => !current)}
                  className="rounded-xl border border-[#B4D6C1] bg-white px-4 py-3 text-sm font-medium text-[#17352E] transition hover:bg-[#EDF6F0]"
                >
                  {showAllRuns ? "Show latest 5" : "Show all"}
                </button>
              </div>
            )}

            {runHistory.length === 0 ? (
              <EmptyState text="No audit runs yet." />
            ) : visibleRunHistory.length === 0 ? (
              <EmptyState text="No audit runs match the current filters." />
            ) : (
              <div className="max-h-[720px] space-y-3 overflow-auto pr-1">
                {visibleRunHistory.map((run) => {
                  const active = run.id === selectedAuditRunId;
                  const statusCounts = run.status_counts ?? {};
                  const open = statusCounts.needs_review ?? 0;
                  const resolved = statusCounts.resolved ?? 0;
                  const confirmed = statusCounts.confirmed_issue ?? 0;
                  const progress = run.issues_found > 0
                    ? Math.round(((confirmed + resolved) / run.issues_found) * 100)
                    : 100;

                  return (
                    <div
                      key={run.id}
                      className={
                        active
                          ? "rounded-2xl border border-[#358873] bg-[#EDF6F0] p-4"
                          : "rounded-2xl border border-[#D6E6DD] bg-[#F8FCF9] p-4"
                      }
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <button
                          onClick={() => setSelectedAuditRunId(run.id)}
                          className="min-w-0 text-left"
                        >
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-medium text-[#17352E]">
                              {formatAuditType(run.audit_type)} #{run.id}
                            </p>
                            {active && (
                              <span className="rounded-full bg-[#358873] px-2 py-1 text-[11px] font-medium text-white">
                                Selected
                              </span>
                            )}
                          </div>
                          <p className="mt-1 text-xs text-[#5F7D70]">
                            {formatDateTime(run.created_at)} · {run.status} · {progress}% reviewed
                          </p>
                        </button>

                        <button
                          onClick={() => deleteAuditRun(run.id)}
                          disabled={busy}
                          className="rounded-lg border border-[#F3CACA] bg-white px-3 py-2 text-xs font-medium text-[#B42318] transition hover:bg-[#FDE8E8] disabled:opacity-50"
                        >
                          Delete
                        </button>
                      </div>

                      <div className="mt-3 grid gap-2 md:grid-cols-4">
                        <MiniCount label="Issues" value={run.issues_found} />
                        <MiniCount label="Open" value={open} />
                        <MiniCount label="Confirmed" value={confirmed} />
                        <MiniCount label="Resolved" value={resolved} />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </div>
      </div>
    </SectionShell>
  );
}

function FindingsSection({
  filteredFindings,
  findingTypes,
  high,
  medium,
  low,
  needsReview,
  confirmedIssues,
  falsePositive,
  needsClarification,
  resolved,
  riskFilter,
  typeFilter,
  statusFilter,
  noteDrafts,
  updatingFindingId,
  setRiskFilter,
  setTypeFilter,
  setStatusFilter,
  setNoteDrafts,
  updateFindingStatus,
  saveReviewerNote,
  exportCsv,
  exportPdf,
}: {
  findings: Finding[];
  filteredFindings: Finding[];
  findingTypes: string[];
  high: number;
  medium: number;
  low: number;
  needsReview: number;
  confirmedIssues: number;
  falsePositive: number;
  needsClarification: number;
  resolved: number;
  riskFilter: string;
  typeFilter: string;
  statusFilter: string;
  noteDrafts: Record<number, string>;
  updatingFindingId: number | null;
  setRiskFilter: (value: string) => void;
  setTypeFilter: (value: string) => void;
  setStatusFilter: (value: string) => void;
  setNoteDrafts: React.Dispatch<React.SetStateAction<Record<number, string>>>;
  updateFindingStatus: (findingId: number, status: string) => void;
  saveReviewerNote: (findingId: number) => void;
  exportCsv: () => void;
  exportPdf: () => void;
}) {
  return (
    <SectionShell
      title="Findings"
      subtitle="Review risk-ranked audit exceptions, mark decisions, add notes, and export reports."
    >
      <Card>
        <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="font-medium text-[#17352E]">Findings review</h2>
            <p className="text-sm text-[#5F7D70]">
              High {high} · Medium {medium} · Low {low}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              onClick={exportCsv}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-[#B4D6C1] bg-white px-4 py-2 text-sm font-medium text-[#17352E] transition hover:bg-[#EDF6F0]"
            >
              <Download size={16} />
              Export CSV
            </button>

            <button
              onClick={exportPdf}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#358873] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#2F7866]"
            >
              <Download size={16} />
              Export PDF
            </button>
          </div>
        </div>

        <div className="mb-5 rounded-xl border border-[#D6E6DD] bg-[#F6FBF8] p-4">
          <p className="mb-3 text-xs font-medium uppercase tracking-[0.16em] text-[#6B8E7F]">
            Review workload
          </p>
          <div className="grid gap-3 md:grid-cols-5">
            <StatusCount label="Needs review" value={needsReview} active={statusFilter === "needs_review"} onClick={() => setStatusFilter("needs_review")} />
            <StatusCount label="Confirmed" value={confirmedIssues} active={statusFilter === "confirmed_issue"} onClick={() => setStatusFilter("confirmed_issue")} />
            <StatusCount label="False positive" value={falsePositive} active={statusFilter === "false_positive"} onClick={() => setStatusFilter("false_positive")} />
            <StatusCount label="Clarification" value={needsClarification} active={statusFilter === "needs_client_clarification"} onClick={() => setStatusFilter("needs_client_clarification")} />
            <StatusCount label="Resolved" value={resolved} active={statusFilter === "resolved"} onClick={() => setStatusFilter("resolved")} />
          </div>
        </div>

        <div className="mb-5 grid gap-3 rounded-xl border border-[#D6E6DD] bg-[#F6FBF8] p-4 md:grid-cols-3">
          <div>
            <label className="mb-2 flex items-center gap-2 text-sm text-[#5F7D70]">
              <Filter size={14} />
              Risk
            </label>
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="w-full rounded-xl border border-[#C8DDD0] bg-white px-3 py-2 text-sm outline-none focus:border-[#4E9C81]"
            >
              <option value="all">All risks</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          <div>
            <label className="mb-2 block text-sm text-[#5F7D70]">Issue type</label>
            <SearchableSelect
              value={typeFilter}
              onChange={setTypeFilter}
              options={[
                { value: "all", label: "All issue types" },
                ...findingTypes.map((findingType) => ({
                  value: findingType,
                  label: formatIssueType(findingType),
                  description: findingType,
                })),
              ]}
              placeholder="Search issue type..."
            />
          </div>

          <div>
            <label className="mb-2 block text-sm text-[#5F7D70]">Review status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full rounded-xl border border-[#C8DDD0] bg-white px-3 py-2 text-sm outline-none focus:border-[#4E9C81]"
            >
              <option value="all">All statuses</option>
              <option value="needs_review">Needs review</option>
              <option value="confirmed_issue">Confirmed issue</option>
              <option value="false_positive">False positive</option>
              <option value="needs_client_clarification">Needs clarification</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
        </div>

        {filteredFindings.length === 0 ? (
          <EmptyState text="No findings match the current filters." />
        ) : (
          <div className="space-y-4">
            {filteredFindings.map((finding) => (
              <div
                key={finding.id}
                className="rounded-xl border border-[#D6E6DD] bg-[#F8FCF9] p-4"
              >
                <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <AlertTriangle size={16} className={riskClass(finding.risk_level)} />
                    <h3 className="font-medium text-[#17352E]">{findingDisplayTitle(finding)}</h3>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full px-3 py-1 text-xs font-medium ${riskBadge(finding.risk_level)}`}>
                      {finding.risk_level}
                    </span>
                    <span className={`rounded-full px-3 py-1 text-xs font-medium ${reviewStatusBadge(finding.status)}`}>
                      {formatStatus(finding.status)}
                    </span>
                  </div>
                </div>

                {findingMeta(finding) && (
                  <p className="mb-2 text-xs font-medium text-[#6B8E7F]">
                    {findingMeta(finding)}
                  </p>
                )}

                <p className="text-sm leading-6 text-[#5F7D70]">
                  {finding.description}
                </p>

                <div className="mt-4 flex flex-wrap gap-2">
                  <ActionButton label="Confirm" onClick={() => updateFindingStatus(finding.id, "confirmed_issue")} disabled={updatingFindingId === finding.id} />
                  <ActionButton label="False Positive" onClick={() => updateFindingStatus(finding.id, "false_positive")} disabled={updatingFindingId === finding.id} />
                  <ActionButton label="Needs Clarification" onClick={() => updateFindingStatus(finding.id, "needs_client_clarification")} disabled={updatingFindingId === finding.id} />
                  <ActionButton label="Resolved" onClick={() => updateFindingStatus(finding.id, "resolved")} disabled={updatingFindingId === finding.id} />
                </div>

                <div className="mt-4 rounded-xl border border-[#DCEAE2] bg-white p-3">
                  <label className="mb-2 block text-sm font-medium text-[#42685B]">
                    Reviewer note
                  </label>
                  <textarea
                    value={noteDrafts[finding.id] ?? ""}
                    onChange={(e) =>
                      setNoteDrafts((prev) => ({
                        ...prev,
                        [finding.id]: e.target.value,
                      }))
                    }
                    rows={3}
                    className="w-full rounded-xl border border-[#C8DDD0] bg-[#F6FBF8] px-3 py-2 text-sm outline-none focus:border-[#4E9C81]"
                    placeholder="Add audit note, explanation, or follow-up action..."
                  />
                  <div className="mt-3 flex justify-end">
                    <button
                      onClick={() => saveReviewerNote(finding.id)}
                      disabled={updatingFindingId === finding.id}
                      className="inline-flex items-center gap-2 rounded-xl bg-[#358873] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#2F7866] disabled:opacity-50"
                    >
                      <Save size={14} />
                      Save Note
                    </button>
                  </div>
                </div>

                <details className="mt-4">
                  <summary className="cursor-pointer text-sm text-[#5F7D70] hover:text-[#17352E]">
                    Evidence
                  </summary>
                  <pre className="mt-3 overflow-auto rounded-lg bg-[#EFF7F2] p-3 text-xs text-[#42685B]">
                    {JSON.stringify(finding.evidence, null, 2)}
                  </pre>
                </details>
              </div>
            ))}
          </div>
        )}
      </Card>
    </SectionShell>
  );
}

function RecordsSection({ records }: { records: RecordRow[] }) {
  return (
    <SectionShell
      title="Records"
      subtitle="Inspect normalized rows extracted from uploaded files."
    >
      <Card>
        {records.length === 0 ? (
          <EmptyState text="No parsed records yet. Apply mapping and extract records first." />
        ) : (
          <div className="max-h-[680px] overflow-auto">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-[#EDF6F0] text-[#5F7D70]">
                <tr>
                  <th className="py-3 pr-3">Row</th>
                  <th className="py-3 pr-3">Document</th>
                  <th className="py-3 pr-3">Party</th>
                  <th className="py-3 pr-3">Date</th>
                  <th className="py-3 pr-3">Amount</th>
                  <th className="py-3 pr-3">GSTIN</th>
                  <th className="py-3 pr-3">Confidence</th>
                </tr>
              </thead>
              <tbody className="text-[#17352E]">
                {records.map((record) => (
                  <tr key={record.id} className="border-t border-[#E0ECE5]">
                    <td className="py-3 pr-3 text-[#5F7D70]">{record.source_row}</td>
                    <td className="py-3 pr-3">{record.document_id ?? "-"}</td>
                    <td className="py-3 pr-3">{record.party_name ?? "-"}</td>
                    <td className="py-3 pr-3">{record.transaction_date ?? "-"}</td>
                    <td className="py-3 pr-3">
                      {record.amount === null ? "-" : `₹${record.amount.toLocaleString("en-IN")}`}
                    </td>
                    <td className="py-3 pr-3">{record.gstin ?? "-"}</td>
                    <td className="py-3 pr-3">{record.confidence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </SectionShell>
  );
}

function ReportsSection({
  findings,
  exportCsv,
  exportPdf,
}: {
  findings: number;
  exportCsv: () => void;
  exportPdf: () => void;
}) {
  return (
    <SectionShell
      title="Reports"
      subtitle="Export audit findings and review notes for sharing or documentation."
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <div className="mb-4 flex items-center gap-2">
            <Download size={18} className="text-[#358873]" />
            <h2 className="font-medium">CSV findings export</h2>
          </div>
          <p className="text-sm leading-6 text-[#5F7D70]">
            Export structured findings for Excel review, filtering, or further CA documentation.
          </p>
          <button
            onClick={exportCsv}
            className="mt-5 w-full rounded-xl border border-[#B4D6C1] bg-white px-5 py-3 text-sm font-medium text-[#17352E] transition hover:bg-[#EDF6F0]"
          >
            Export Findings CSV
          </button>
        </Card>

        <Card>
          <div className="mb-4 flex items-center gap-2">
            <FileSearch size={18} className="text-[#358873]" />
            <h2 className="font-medium">PDF audit report</h2>
          </div>
          <p className="text-sm leading-6 text-[#5F7D70]">
            Generate a PDF summary with client details, coverage, risk counts, findings, and reviewer notes.
          </p>
          <button
            onClick={exportPdf}
            className="mt-5 w-full rounded-xl bg-[#358873] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#2F7866]"
          >
            Export Audit Report PDF
          </button>
        </Card>
      </div>

      <div className="mt-6">
        <Card>
          <p className="text-sm text-[#5F7D70]">
            Current findings available for export:{" "}
            <span className="font-semibold text-[#17352E]">{findings}</span>
          </p>
        </Card>
      </div>
    </SectionShell>
  );
}

function ChatPlaceholder() {
  return (
    <SectionShell
      title="Audit Chat"
      subtitle="Ask questions about records, findings, risk, and reviewer status. Coming next."
    >
      <Card>
        <div className="rounded-2xl border border-dashed border-[#B4D6C1] bg-[#F6FBF8] p-8 text-center">
          <MessageSquare className="mx-auto text-[#358873]" size={34} />
          <h2 className="mt-4 text-xl font-semibold text-[#17352E]">
            Audit Chat is the next AI layer
          </h2>
          <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-[#5F7D70]">
            This will let users ask questions like “show high-risk findings,”
            “which entries need clarification,” and “summarize bank reconciliation issues.”
          </p>
        </div>
      </Card>
    </SectionShell>
  );
}

function SectionShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <section>
      <div className="mb-5">
        <h2 className="text-2xl font-semibold tracking-tight text-[#17352E]">{title}</h2>
        <p className="mt-1 text-sm text-[#5F7D70]">{subtitle}</p>
      </div>
      {children}
    </section>
  );
}

function Card({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-hidden rounded-3xl border border-[#C8DDD0] bg-white/88 p-5 shadow-sm backdrop-blur">
      {children}
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <p className="rounded-2xl border border-[#D6E6DD] bg-[#F6FBF8] p-4 text-sm text-[#5F7D70]">
      {text}
    </p>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-3xl border border-[#C8DDD0] bg-white/88 p-4 shadow-sm backdrop-blur">
      <p className="text-sm text-[#5F7D70]">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-[#17352E]">{value}</p>
    </div>
  );
}

function ReadinessRow({
  label,
  value,
  done,
}: {
  label: string;
  value: number;
  done: boolean;
}) {
  return (
    <div className="flex items-center justify-between rounded-xl bg-white/70 px-3 py-2">
      <div className="flex items-center gap-2">
        <CheckCircle2
          size={16}
          className={done ? "text-[#358873]" : "text-[#A8BDB1]"}
        />
        <span className="text-sm text-[#42685B]">{label}</span>
      </div>
      <span className="font-medium text-[#17352E]">{value}</span>
    </div>
  );
}

function RiskBox({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "high" | "medium" | "low";
}) {
  const className =
    tone === "high"
      ? "border-[#F3CACA] bg-[#FDE8E8] text-[#B42318]"
      : tone === "medium"
        ? "border-[#F4DDA8] bg-[#FFF4D6] text-[#A15C07]"
        : "border-[#BFD8CB] bg-[#EAF4EE] text-[#2F7866]";

  return (
    <div className={`rounded-2xl border p-4 ${className}`}>
      <p className="text-sm font-medium">{label}</p>
      <p className="mt-2 text-3xl font-semibold">{value}</p>
    </div>
  );
}



function MiniCount({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-[#D6E6DD] bg-white/80 px-3 py-2">
      <p className="text-xs text-[#6B8E7F]">{label}</p>
      <p className="mt-1 font-semibold text-[#17352E]">{value}</p>
    </div>
  );
}


function formatFileType(type: string) {
  return fileTypeOptions.find((option) => option.value === type)?.label ?? formatIssueType(type);
}

function formatIssueType(type: string) {
  return type
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function formatAuditType(type: string) {
  if (type === "purchase_audit") return "Purchase Audit";
  if (type === "sales_audit") return "Sales Audit";
  if (type === "expense_audit") return "Expense Audit";
  if (type === "document_matching") return "Document Matching";
  if (type === "aging_review") return "Receivables/Payables Aging";
  if (type === "trial_balance_review") return "Trial Balance Review";
  if (type === "fixed_asset_audit") return "Fixed Asset Audit";
  if (type === "tds_review") return "TDS Review";
  if (type === "ledger_scrutiny") return "Ledger Scrutiny";
  if (type === "gst_reconciliation") return "GST Reconciliation";
  if (type === "document_matching") return "Document Matching";
  if (type === "aging_review") return "Receivables/Payables Aging";
  if (type === "trial_balance_review") return "Trial Balance Review";
  if (type === "fixed_asset_audit") return "Fixed Asset Audit";
  if (type === "tds_review") return "TDS Review";
  if (type === "ledger_scrutiny") return "Ledger Scrutiny";
  if (type === "bank_reconciliation") return "Bank Reconciliation";
  return type;
}

function formatDateTime(value: string) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return value;
  }
}

function StatusCount({
  label,
  value,
  active,
  onClick,
}: {
  label: string;
  value: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={
        active
          ? "rounded-2xl bg-[#358873] p-3 text-left text-white shadow-sm"
          : "rounded-2xl border border-[#D6E6DD] bg-white p-3 text-left text-[#42685B] transition hover:bg-[#EDF6F0]"
      }
    >
      <p className="text-xs font-medium opacity-80">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </button>
  );
}

function ActionButton({
  label,
  onClick,
  disabled,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="rounded-lg border border-[#BFD8CB] bg-white px-3 py-2 text-xs font-medium text-[#17352E] transition hover:bg-[#EDF6F0] disabled:opacity-50"
    >
      {label}
    </button>
  );
}

function getNextAction({
  files,
  mappedFiles,
  records,
  findings,
  needsReview,
}: {
  files: number;
  mappedFiles: number;
  records: number;
  findings: number;
  needsReview: number;
}) {
  if (files === 0) {
    return {
      title: "Upload audit files",
      description: "Start by uploading a purchase register, bank statement, ledger, or Tally/SAP export.",
      section: "files",
    };
  }

  if (mappedFiles === 0) {
    return {
      title: "Map file columns",
      description: "Map source columns like Bill No, Party Name, Debit, Credit, and Narration before extraction.",
      section: "mapping",
    };
  }

  if (records === 0) {
    return {
      title: "Extract normalized records",
      description: "Apply the saved mappings so AuditPal can create structured records for audit checks.",
      section: "mapping",
    };
  }

  if (findings === 0) {
    return {
      title: "Run an audit module",
      description: "Run Purchase Audit or Bank Reconciliation to generate risk-ranked findings.",
      section: "audit",
    };
  }

  if (needsReview > 0) {
    return {
      title: "Review open findings",
      description: "Confirm issues, mark false positives, request clarification, or resolve reviewed findings.",
      section: "findings",
    };
  }

  return {
    title: "Export the audit report",
    description: "Export the findings as CSV or generate a PDF audit report for documentation.",
    section: "reports",
  };
}


function inferRecommendedAuditModule(files?: UploadedFile[]) {
  if (!files || !files.length) return "purchase";

  const candidates = files
    .filter((file) => file.status === "parsed" || file.status === "uploaded")
    .sort((a, b) => b.id - a.id);

  const latest = candidates[0] ?? files[files.length - 1];
  const type = latest?.file_type?.toLowerCase() ?? "";

  if (type.includes("ocr") || type.includes("support") || type.includes("document_extract") || type.includes("voucher_support")) return "document_match";
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
}

function findingDisplayTitle(finding: Finding) {
  const evidence = finding.evidence ?? {};
  const documentId = getEvidenceValue(evidence, "document_id");
  const partyName = getEvidenceValue(evidence, "party_name");
  const row = getEvidenceValue(evidence, "source_row");
  const rows = getEvidenceValue(evidence, "source_rows");

  const titleAlreadyHasContext =
    (documentId && finding.title.includes(documentId)) ||
    (partyName && finding.title.includes(partyName));

  if (titleAlreadyHasContext) return finding.title;

  const bits = [];
  if (documentId) bits.push(documentId);
  if (partyName) bits.push(partyName);
  if (row) bits.push(`row ${row}`);
  if (!row && rows) bits.push(`rows ${Array.isArray(rows) ? rows.join(", ") : rows}`);

  if (!bits.length) return finding.title;

  return `${finding.title} — ${bits.slice(0, 2).join(" · ")}`;
}

function findingMeta(finding: Finding) {
  const evidence = finding.evidence ?? {};
  const bits = [];

  const documentId = getEvidenceValue(evidence, "document_id");
  const partyName = getEvidenceValue(evidence, "party_name");
  const amount = getEvidenceValue(evidence, "amount");
  const date = getEvidenceValue(evidence, "transaction_date");
  const row = getEvidenceValue(evidence, "source_row");
  const rows = getEvidenceValue(evidence, "source_rows");

  if (documentId) bits.push(`Document: ${documentId}`);
  if (partyName) bits.push(`Party: ${partyName}`);
  if (date) bits.push(`Date: ${date}`);
  if (amount !== "" && amount !== null && amount !== undefined) bits.push(`Amount: ₹${Number(amount).toLocaleString("en-IN")}`);
  if (row) bits.push(`Row: ${row}`);
  if (!row && rows) bits.push(`Rows: ${Array.isArray(rows) ? rows.join(", ") : rows}`);

  return bits.join(" · ");
}

function getEvidenceValue(evidence: Record<string, unknown>, key: string) {
  const value = evidence[key];
  if (value === null || value === undefined || value === "") return "";
  return value as string | number | unknown[];
}

function riskClass(risk: string) {
  if (risk === "high") return "text-[#B42318]";
  if (risk === "medium") return "text-[#A15C07]";
  return "text-[#4E9C81]";
}

function riskBadge(risk: string) {
  if (risk === "high") return "bg-[#FDE8E8] text-[#B42318]";
  if (risk === "medium") return "bg-[#FFF4D6] text-[#A15C07]";
  return "bg-[#EAF4EE] text-[#42685B]";
}

function reviewStatusBadge(status: string) {
  if (status === "confirmed_issue") return "bg-[#FDE8E8] text-[#B42318]";
  if (status === "false_positive") return "bg-[#EAF4EE] text-[#42685B]";
  if (status === "needs_client_clarification") return "bg-[#FFF4D6] text-[#A15C07]";
  if (status === "resolved") return "bg-[#E6F4EC] text-[#2F7866]";
  return "bg-[#EEF4F0] text-[#5F7D70]";
}

function formatStatus(status: string) {
  if (status === "needs_review") return "Needs review";
  if (status === "confirmed_issue") return "Confirmed issue";
  if (status === "false_positive") return "False positive";
  if (status === "needs_client_clarification") return "Needs clarification";
  if (status === "resolved") return "Resolved";
  return status;
}
