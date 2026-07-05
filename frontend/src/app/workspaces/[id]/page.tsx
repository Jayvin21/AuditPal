"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import AmbientBackground from "@/components/AmbientBackground";
import {
  AlertTriangle,
  CheckCircle2,
  Columns3,
  FileSpreadsheet,
  Filter,
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
    purchase_records_checked: number;
    unchecked_records: number;
    issues_found: number;
    risk_counts?: Record<string, number>;
  };
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
  { key: "document_id", label: "Invoice / Bill / Voucher No" },
  { key: "party_name", label: "Vendor / Party Name" },
  { key: "transaction_date", label: "Transaction Date" },
  { key: "amount", label: "Amount" },
  { key: "gstin", label: "GSTIN" },
  { key: "description", label: "Description / Narration" },
];

export default function WorkspaceDetailPage() {
  const params = useParams<{ id: string }>();
  const workspaceId = Number(params.id);

  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileType, setFileType] = useState("purchase_register");

  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [records, setRecords] = useState<RecordRow[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [auditSummary, setAuditSummary] = useState<AuditRunResponse | null>(null);

  const [selectedMappingFileId, setSelectedMappingFileId] = useState<number | null>(null);
  const [mappingPreview, setMappingPreview] = useState<ColumnMappingResponse | null>(null);
  const [mappingDraft, setMappingDraft] = useState<Record<string, string | null>>({});

  const [riskFilter, setRiskFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  const [noteDrafts, setNoteDrafts] = useState<Record<number, string>>({});
  const [statusMessage, setStatusMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [updatingFindingId, setUpdatingFindingId] = useState<number | null>(null);

  async function refreshAll() {
    const [workspaceRes, filesRes, recordsRes, findingsRes] = await Promise.all([
      api.get(`/workspaces/${workspaceId}`),
      api.get(`/records/files/${workspaceId}`),
      api.get(`/records/workspace/${workspaceId}`),
      api.get(`/findings/${workspaceId}`),
    ]);

    setWorkspace(workspaceRes.data);
    setFiles(filesRes.data);
    setRecords(recordsRes.data);
    setFindings(findingsRes.data);

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
      setStatusMessage("File uploaded. Review column mapping before parsing.");
      await refreshAll();

      if (res.data?.id) {
        await openMapping(res.data.id);
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

      setStatusMessage("Column mapping saved. Re-parse files to apply it.");
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
    setStatusMessage("Parsing workspace files with saved mappings...");

    try {
      await api.post(`/records/parse-workspace/${workspaceId}?force_reparse=true`);
      setStatusMessage("Files parsed using latest mappings.");
      await refreshAll();
    } catch {
      setStatusMessage("Parsing failed.");
    } finally {
      setBusy(false);
    }
  }

  async function runAudit() {
    setBusy(true);
    setStatusMessage("Running purchase audit...");

    try {
      const res = await api.post(`/audit-runs/${workspaceId}/run-purchase-audit`);
      setAuditSummary(res.data);
      setStatusMessage("Purchase audit completed.");
      await refreshAll();
    } catch {
      setStatusMessage("Audit failed.");
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

  const high = findings.filter((f) => f.risk_level === "high").length;
  const medium = findings.filter((f) => f.risk_level === "medium").length;
  const low = findings.filter((f) => f.risk_level === "low").length;

  const findingTypes = useMemo(
    () => Array.from(new Set(findings.map((f) => f.finding_type))).sort(),
    [findings]
  );

  const filteredFindings = findings.filter((finding) => {
    const riskMatch = riskFilter === "all" || finding.risk_level === riskFilter;
    const typeMatch = typeFilter === "all" || finding.finding_type === typeFilter;
    const statusMatch = statusFilter === "all" || finding.status === statusFilter;
    return riskMatch && typeMatch && statusMatch;
  });

  return (
    <main className="relative min-h-screen bg-[#F6FBF8] px-6 py-8 text-[#17352E]">
      <AmbientBackground />

      <div className="mx-auto max-w-7xl">
        <div className="mb-8 border-b border-[#C8DDD0] pb-5">
          <Link href="/workspaces" className="text-sm text-[#5F7D70] hover:text-[#17352E]">
            ← Workspaces
          </Link>

          <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight text-[#17352E]">
                {workspace?.client_name ?? `Workspace #${workspaceId}`}
              </h1>
              <p className="mt-2 text-[#5F7D70]">
                {workspace?.audit_period ?? "—"} · {workspace?.audit_type ?? "—"} · {workspace?.status ?? "—"}
              </p>
            </div>

            <div className="rounded-2xl border border-[#C8DDD0] bg-white/92 px-4 py-3 text-sm text-[#5F7D70] shadow-sm backdrop-blur">
              Map columns → parse records → run audit → review issues
            </div>
          </div>
        </div>

        <div className="mb-6 grid gap-4 md:grid-cols-4">
          <Metric label="Files" value={String(files.length)} />
          <Metric label="Records" value={String(records.length)} />
          <Metric label="High Risk" value={String(high)} />
          <Metric label="Findings" value={String(findings.length)} />
        </div>

        <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <section className="space-y-6">
            <div className="rounded-2xl border border-[#C8DDD0] bg-white/92 p-5 shadow-sm backdrop-blur">
              <div className="mb-5 flex items-center gap-2">
                <Upload size={18} className="text-[#358873]" />
                <h2 className="font-medium text-[#17352E]">Upload audit file</h2>
              </div>

              <label className="mb-2 block text-sm text-[#5F7D70]">File type</label>
              <select
                value={fileType}
                onChange={(event) => setFileType(event.target.value)}
                className="mb-4 w-full rounded-xl border border-[#C8DDD0] bg-[#F6FBF8] px-4 py-3 outline-none focus:border-[#4E9C81]"
              >
                <option value="purchase_register">Purchase Register</option>
                <option value="expense_ledger">Expense Ledger</option>
                <option value="bank_statement">Bank Statement</option>
              </select>

              <input
                type="file"
                accept=".xlsx,.xls,.csv"
                onChange={handleFileChange}
                className="mb-4 w-full rounded-xl border border-[#C8DDD0] bg-[#F6FBF8] px-4 py-3 text-sm text-[#17352E]"
              />

              <button
                onClick={uploadFile}
                disabled={busy}
                className="w-full rounded-xl bg-[#358873] px-5 py-3 font-medium text-white transition hover:bg-[#2F7866] disabled:opacity-50"
              >
                Upload File
              </button>
            </div>

            <div className="rounded-2xl border border-[#C8DDD0] bg-white/92 p-5 shadow-sm backdrop-blur">
              <div className="mb-5 flex items-center gap-2">
                <FileSpreadsheet size={18} className="text-[#358873]" />
                <h2 className="font-medium text-[#17352E]">Uploaded files</h2>
              </div>

              {files.length === 0 ? (
                <p className="text-sm text-[#5F7D70]">No files uploaded yet.</p>
              ) : (
                <div className="space-y-3">
                  {files.map((file) => (
                    <div
                      key={file.id}
                      className="rounded-xl border border-[#D6E6DD] bg-[#F6FBF8] p-4"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="font-medium text-[#17352E]">{file.original_filename}</p>
                          <p className="mt-1 text-sm text-[#5F7D70]">
                            {file.file_type} · {file.status}
                          </p>
                        </div>
                        <button
                          onClick={() => openMapping(file.id)}
                          className="rounded-lg border border-[#BFD8CB] bg-white px-3 py-2 text-xs font-medium text-[#17352E] transition hover:bg-[#EDF6F0]"
                        >
                          Map Columns
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-[#C8DDD0] bg-white/92 p-5 shadow-sm backdrop-blur">
              <div className="mb-5 flex items-center gap-2">
                <Columns3 size={18} className="text-[#358873]" />
                <h2 className="font-medium text-[#17352E]">Column mapping</h2>
              </div>

              {!mappingPreview ? (
                <p className="rounded-xl border border-[#D6E6DD] bg-[#F6FBF8] p-4 text-sm text-[#5F7D70]">
                  Select “Map Columns” on an uploaded file. AuditPal will suggest mappings, but you should verify them before parsing.
                </p>
              ) : (
                <div className="space-y-4">
                  <p className="text-sm text-[#5F7D70]">
                    File #{mappingPreview.file_id}. Map the source columns to AuditPal fields.
                  </p>

                  <div className="space-y-3">
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
                  </div>

                  <button
                    onClick={saveMapping}
                    disabled={busy}
                    className="w-full rounded-xl bg-[#358873] px-5 py-3 font-medium text-white transition hover:bg-[#2F7866] disabled:opacity-50"
                  >
                    Save Column Mapping
                  </button>

                  <details className="rounded-xl border border-[#D6E6DD] bg-[#F6FBF8] p-4">
                    <summary className="cursor-pointer text-sm font-medium text-[#42685B]">
                      Preview first rows
                    </summary>

                    <div className="mt-4 max-h-[260px] overflow-auto">
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
                            <tr key={index} className="border-t border-[#D6E6DD]">
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
                  </details>
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-[#C8DDD0] bg-white/92 p-5 shadow-sm backdrop-blur">
              <div className="mb-5 flex items-center gap-2">
                <Play size={18} className="text-[#358873]" />
                <h2 className="font-medium text-[#17352E]">Run workflow</h2>
              </div>

              <div className="grid gap-3">
                <button
                  onClick={parseFiles}
                  disabled={busy}
                  className="rounded-xl border border-[#B4D6C1] bg-[#EDF6F0] px-5 py-3 font-medium text-[#17352E] transition hover:bg-[#DFEAE2] disabled:opacity-50"
                >
                  Parse Files With Mapping
                </button>

                <button
                  onClick={runAudit}
                  disabled={busy}
                  className="rounded-xl bg-[#358873] px-5 py-3 font-medium text-white transition hover:bg-[#2F7866] disabled:opacity-50"
                >
                  Run Purchase Audit
                </button>
              </div>

              {statusMessage && (
                <p className="mt-4 rounded-xl border border-[#D6E6DD] bg-[#F6FBF8] p-3 text-sm text-[#5F7D70]">
                  {statusMessage}
                </p>
              )}
            </div>
          </section>

          <section className="space-y-6">
            {auditSummary && (
              <div className="rounded-2xl border border-[#C8DDD0] bg-white/92 p-5 shadow-sm backdrop-blur">
                <div className="mb-4 flex items-center gap-2">
                  <CheckCircle2 size={18} className="text-[#358873]" />
                  <h2 className="font-medium text-[#17352E]">Audit Coverage</h2>
                </div>

                <div className="grid gap-3 md:grid-cols-4">
                  <Metric label="Total" value={String(auditSummary.coverage.total_records)} />
                  <Metric label="Checked" value={String(auditSummary.coverage.purchase_records_checked)} />
                  <Metric label="Unchecked" value={String(auditSummary.coverage.unchecked_records)} />
                  <Metric label="Issues" value={String(auditSummary.coverage.issues_found)} />
                </div>
              </div>
            )}

            <div className="rounded-2xl border border-[#C8DDD0] bg-white/92 p-5 shadow-sm backdrop-blur">
              <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h2 className="font-medium text-[#17352E]">Findings</h2>
                  <p className="text-sm text-[#5F7D70]">
                    High {high} · Medium {medium} · Low {low}
                  </p>
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
                  <select
                    value={typeFilter}
                    onChange={(e) => setTypeFilter(e.target.value)}
                    className="w-full rounded-xl border border-[#C8DDD0] bg-white px-3 py-2 text-sm outline-none focus:border-[#4E9C81]"
                  >
                    <option value="all">All issue types</option>
                    {findingTypes.map((findingType) => (
                      <option key={findingType} value={findingType}>
                        {findingType}
                      </option>
                    ))}
                  </select>
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
                <p className="rounded-xl border border-[#D6E6DD] bg-[#F6FBF8] p-4 text-sm text-[#5F7D70]">
                  No findings match the current filters.
                </p>
              ) : (
                <div className="max-h-[760px] space-y-4 overflow-auto pr-2">
                  {filteredFindings.map((finding) => (
                    <div
                      key={finding.id}
                      className="rounded-xl border border-[#D6E6DD] bg-[#F8FCF9] p-4"
                    >
                      <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <AlertTriangle size={16} className={riskClass(finding.risk_level)} />
                          <h3 className="font-medium text-[#17352E]">{finding.title}</h3>
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
            </div>

            <div className="rounded-2xl border border-[#C8DDD0] bg-white/92 p-5 shadow-sm backdrop-blur">
              <h2 className="mb-5 font-medium text-[#17352E]">Extracted Records</h2>

              {records.length === 0 ? (
                <p className="text-sm text-[#5F7D70]">No parsed records yet.</p>
              ) : (
                <div className="max-h-[320px] overflow-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="sticky top-0 bg-[#EDF6F0] text-[#5F7D70]">
                      <tr>
                        <th className="py-2 pr-3">Row</th>
                        <th className="py-2 pr-3">Document</th>
                        <th className="py-2 pr-3">Party</th>
                        <th className="py-2 pr-3">Amount</th>
                        <th className="py-2 pr-3">GSTIN</th>
                      </tr>
                    </thead>
                    <tbody className="text-[#17352E]">
                      {records.slice(0, 100).map((record) => (
                        <tr key={record.id} className="border-t border-[#E0ECE5]">
                          <td className="py-2 pr-3 text-[#5F7D70]">{record.source_row}</td>
                          <td className="py-2 pr-3">{record.document_id ?? "-"}</td>
                          <td className="py-2 pr-3">{record.party_name ?? "-"}</td>
                          <td className="py-2 pr-3">
                            {record.amount === null ? "-" : `₹${record.amount.toLocaleString("en-IN")}`}
                          </td>
                          <td className="py-2 pr-3">{record.gstin ?? "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-[#C8DDD0] bg-white/92 p-4 shadow-sm backdrop-blur">
      <p className="text-sm text-[#5F7D70]">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-[#17352E]">{value}</p>
    </div>
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