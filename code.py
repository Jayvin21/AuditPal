from pathlib import Path
import re

ROOT = Path(r"D:\1Workspace\AuditPal")
PAGE = ROOT / "frontend" / "src" / "app" / "workspaces" / "[id]" / "page.tsx"

page = PAGE.read_text(encoding="utf-8")

# ----------------------------------------------------
# 1. Add reusable option type
# ----------------------------------------------------

if "type SearchableOption =" not in page:
    page = page.replace(
        '''const standardFields = [
  { key: "document_id", label: "Invoice / Bill / Voucher / UTR No" },
  { key: "party_name", label: "Vendor / Party / Payee Name" },
  { key: "transaction_date", label: "Transaction Date" },
  { key: "amount", label: "Amount" },
  { key: "debit_amount", label: "Debit / Withdrawal / Payment" },
  { key: "credit_amount", label: "Credit / Deposit / Receipt" },
  { key: "gstin", label: "GSTIN" },
  { key: "description", label: "Description / Narration" },
];''',
        '''const standardFields = [
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
};'''
    )

# ----------------------------------------------------
# 2. Add centralized file type options
# ----------------------------------------------------

if "const fileTypeOptions: SearchableOption[]" not in page:
    file_type_options = r'''
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
'''
    page = page.replace("const importTemplates = [", file_type_options + "\nconst importTemplates = [")

# ----------------------------------------------------
# 3. Add reusable searchable selector component
# ----------------------------------------------------

if "function SearchableSelect({" not in page:
    component = r'''
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

'''
    page = page.replace("function OverviewSection({", component + "function OverviewSection({")

# ----------------------------------------------------
# 4. Replace FilesSection with searchable file type + uploaded file search
# ----------------------------------------------------

files_start = page.index("function FilesSection({")
files_end = page.index("function MappingSection({")

new_files_section = r'''function FilesSection({
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

'''

page = page[:files_start] + new_files_section + page[files_end:]

# ----------------------------------------------------
# 5. Replace AuditSection with searchable module selector + compact run history
# ----------------------------------------------------

audit_start = page.index("function AuditSection({")
audit_end = page.index("function FindingsSection({")

new_audit_section = r'''function AuditSection({
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

'''

page = page[:audit_start] + new_audit_section + page[audit_end:]

# ----------------------------------------------------
# 6. Make issue type selector searchable and readable
# ----------------------------------------------------

old_issue_select = r'''            <select
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
            </select>'''

new_issue_select = r'''            <SearchableSelect
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
            />'''

page = page.replace(old_issue_select, new_issue_select)

# ----------------------------------------------------
# 7. Add readable format helpers
# ----------------------------------------------------

if "function formatFileType(type: string)" not in page:
    helpers = r'''
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

'''
    page = page.replace("function formatAuditType(type: string) {", helpers + "function formatAuditType(type: string) {")

# ----------------------------------------------------
# 8. Clean duplicated coverage type fields from earlier patching
# ----------------------------------------------------

page = re.sub(
    r'''    checked_records\?: number;
(?:    ledger_records_checked\?: number;\n)?(?:    fixed_asset_records_checked\?: number;\n)?(?:    aging_records_checked\?: number;\n)?(?:    document_match_records_checked\?: number;\n)?(?:    trial_balance_records_checked\?: number;\n)?(?:    document_match_records_checked\?: number;\n)?(?:    aging_records_checked\?: number;\n)?(?:    document_match_records_checked\?: number;\n)?(?:    tds_records_checked\?: number;\n)?(?:    fixed_asset_records_checked\?: number;\n)?(?:    aging_records_checked\?: number;\n)?(?:    document_match_records_checked\?: number;\n)?(?:    trial_balance_records_checked\?: number;\n)?(?:    document_match_records_checked\?: number;\n)?(?:    aging_records_checked\?: number;\n)?(?:    document_match_records_checked\?: number;\n)?''',
    '''    checked_records?: number;
    ledger_records_checked?: number;
    tds_records_checked?: number;
    fixed_asset_records_checked?: number;
    trial_balance_records_checked?: number;
    aging_records_checked?: number;
    document_match_records_checked?: number;
''',
    page,
)

PAGE.write_text(page, encoding="utf-8")

print("UI utility patch applied.")
print("Added:")
print("- Searchable file type selector")
print("- Uploaded file search")
print("- Searchable audit module selector")
print("- Audit run search and audit-type filter")
print("- Compact latest-5 audit history with Show all toggle")
print("- Readable issue type labels")
print("- Cleaned duplicate coverage type fields")