from pathlib import Path

PAGE = Path(r"D:\1Workspace\AuditPal\frontend\src\app\workspaces\[id]\page.tsx")

page = PAGE.read_text(encoding="utf-8")

start = page.index("function RecordsSection({ records }: { records: RecordRow[] })")
end = page.index("function ReportsSection({", start)

new_records_section = r'''function RecordsSection({ records }: { records: RecordRow[] }) {
  const [recordSearch, setRecordSearch] = useState("");
  const [confidenceFilter, setConfidenceFilter] = useState("all");
  const [recordSort, setRecordSort] = useState("newest_first");

  const visibleRecords = useMemo(() => {
    const query = recordSearch.toLowerCase().trim();

    const filtered = records.filter((record) => {
      const confidence = Number(record.confidence ?? 0);

      const confidenceMatch =
        confidenceFilter === "all" ||
        (confidenceFilter === "high" && confidence >= 0.8) ||
        (confidenceFilter === "medium" && confidence >= 0.5 && confidence < 0.8) ||
        (confidenceFilter === "low" && confidence < 0.5);

      const searchBlob = [
        record.source_row,
        record.document_id,
        record.party_name,
        record.transaction_date,
        record.amount,
        record.gstin,
        record.confidence,
      ]
        .join(" ")
        .toLowerCase();

      const searchMatch = !query || searchBlob.includes(query);

      return confidenceMatch && searchMatch;
    });

    return [...filtered].sort((a, b) => {
      if (recordSort === "amount_high_first") {
        return Number(b.amount ?? -Infinity) - Number(a.amount ?? -Infinity);
      }

      if (recordSort === "amount_low_first") {
        return Number(a.amount ?? Infinity) - Number(b.amount ?? Infinity);
      }

      if (recordSort === "confidence_high_first") {
        return Number(b.confidence ?? 0) - Number(a.confidence ?? 0);
      }

      if (recordSort === "confidence_low_first") {
        return Number(a.confidence ?? 0) - Number(b.confidence ?? 0);
      }

      if (recordSort === "oldest_first") {
        return a.id - b.id;
      }

      return b.id - a.id;
    });
  }, [records, recordSearch, confidenceFilter, recordSort]);

  function exportVisibleRecordsCsv() {
    const headers = [
      "source_row",
      "document_id",
      "party_name",
      "transaction_date",
      "amount",
      "gstin",
      "confidence",
    ];

    const escapeCsv = (value: unknown) => {
      const text = String(value ?? "");
      if (text.includes(",") || text.includes("\"") || text.includes("\n")) {
        return `"${text.replace(/"/g, '""')}"`;
      }
      return text;
    };

    const rows = visibleRecords.map((record) =>
      headers.map((header) => escapeCsv(record[header as keyof RecordRow])).join(",")
    );

    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = "auditpal-visible-records.csv";
    link.click();

    URL.revokeObjectURL(url);
  }

  return (
    <SectionShell
      title="Records"
      subtitle="Inspect normalized rows extracted from uploaded files."
    >
      <Card>
        {records.length === 0 ? (
          <EmptyState text="No parsed records yet. Apply mapping and extract records first." />
        ) : (
          <div>
            <div className="mb-5 rounded-xl border border-[#D6E6DD] bg-[#F6FBF8] p-4">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-medium uppercase tracking-[0.16em] text-[#6B8E7F]">
                    Record filters
                  </p>
                  <p className="mt-1 text-sm text-[#5F7D70]">
                    Showing {visibleRecords.length} of {records.length} extracted records.
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => {
                      setRecordSearch("");
                      setConfidenceFilter("all");
                      setRecordSort("newest_first");
                    }}
                    className="rounded-xl border border-[#B4D6C1] bg-white px-4 py-2 text-sm font-medium text-[#17352E] transition hover:bg-[#EDF6F0]"
                  >
                    Clear filters
                  </button>

                  <button
                    onClick={exportVisibleRecordsCsv}
                    className="inline-flex items-center gap-2 rounded-xl bg-[#358873] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#2F7866]"
                  >
                    <Download size={15} />
                    Export Visible CSV
                  </button>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-4">
                <div className="md:col-span-2">
                  <label className="mb-2 block text-sm text-[#5F7D70]">
                    Search records
                  </label>
                  <input
                    value={recordSearch}
                    onChange={(event) => setRecordSearch(event.target.value)}
                    placeholder="Search invoice, party, date, GSTIN, amount..."
                    className="w-full rounded-xl border border-[#C8DDD0] bg-white px-3 py-2 text-sm outline-none focus:border-[#4E9C81]"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm text-[#5F7D70]">
                    Confidence
                  </label>
                  <select
                    value={confidenceFilter}
                    onChange={(event) => setConfidenceFilter(event.target.value)}
                    className="w-full rounded-xl border border-[#C8DDD0] bg-white px-3 py-2 text-sm outline-none focus:border-[#4E9C81]"
                  >
                    <option value="all">All confidence</option>
                    <option value="high">High confidence</option>
                    <option value="medium">Medium confidence</option>
                    <option value="low">Low confidence</option>
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm text-[#5F7D70]">
                    Sort
                  </label>
                  <select
                    value={recordSort}
                    onChange={(event) => setRecordSort(event.target.value)}
                    className="w-full rounded-xl border border-[#C8DDD0] bg-white px-3 py-2 text-sm outline-none focus:border-[#4E9C81]"
                  >
                    <option value="newest_first">Newest first</option>
                    <option value="oldest_first">Oldest first</option>
                    <option value="amount_high_first">Amount high first</option>
                    <option value="amount_low_first">Amount low first</option>
                    <option value="confidence_high_first">Confidence high first</option>
                    <option value="confidence_low_first">Confidence low first</option>
                  </select>
                </div>
              </div>
            </div>

            {visibleRecords.length === 0 ? (
              <EmptyState text="No records match the current filters." />
            ) : (
              <div className="max-h-[680px] overflow-auto rounded-xl border border-[#D6E6DD]">
                <table className="w-full text-left text-sm">
                  <thead className="sticky top-0 bg-[#EDF6F0] text-[#5F7D70]">
                    <tr>
                      <th className="whitespace-nowrap px-3 py-3">Row</th>
                      <th className="whitespace-nowrap px-3 py-3">Document</th>
                      <th className="whitespace-nowrap px-3 py-3">Party</th>
                      <th className="whitespace-nowrap px-3 py-3">Date</th>
                      <th className="whitespace-nowrap px-3 py-3">Amount</th>
                      <th className="whitespace-nowrap px-3 py-3">GSTIN</th>
                      <th className="whitespace-nowrap px-3 py-3">Confidence</th>
                    </tr>
                  </thead>
                  <tbody className="text-[#17352E]">
                    {visibleRecords.map((record) => (
                      <tr key={record.id} className="border-t border-[#E0ECE5] bg-white/70">
                        <td className="whitespace-nowrap px-3 py-3 text-[#5F7D70]">
                          {record.source_row}
                        </td>
                        <td className="whitespace-nowrap px-3 py-3">
                          {record.document_id ?? "-"}
                        </td>
                        <td className="min-w-[220px] px-3 py-3">
                          {record.party_name ?? "-"}
                        </td>
                        <td className="whitespace-nowrap px-3 py-3">
                          {record.transaction_date ?? "-"}
                        </td>
                        <td className="whitespace-nowrap px-3 py-3">
                          {record.amount === null || record.amount === undefined
                            ? "-"
                            : `₹${record.amount.toLocaleString("en-IN")}`}
                        </td>
                        <td className="whitespace-nowrap px-3 py-3">
                          {record.gstin ?? "-"}
                        </td>
                        <td className="whitespace-nowrap px-3 py-3">
                          <span className={confidenceBadge(record.confidence)}>
                            {record.confidence}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </Card>
    </SectionShell>
  );
}

'''

page = page[:start] + new_records_section + page[end:]

if "function confidenceBadge(" not in page:
    helper = r'''
function confidenceBadge(confidence: number | null | undefined) {
  const value = Number(confidence ?? 0);

  if (value >= 0.8) {
    return "rounded-full bg-[#EAF4EE] px-2 py-1 text-xs font-medium text-[#2F7866]";
  }

  if (value >= 0.5) {
    return "rounded-full bg-[#FFF7E6] px-2 py-1 text-xs font-medium text-[#B76E00]";
  }

  return "rounded-full bg-[#FDE8E8] px-2 py-1 text-xs font-medium text-[#B42318]";
}

'''
    page = page.replace("function formatFileType(type?: string | null) {", helper + "function formatFileType(type?: string | null) {")

PAGE.write_text(page, encoding="utf-8")

print("Pass 2 Task 5 applied.")
print("Updated Records UX:")
print("- Search records")
print("- Filter by mapping confidence")
print("- Sort records")
print("- Export visible records as CSV")
print(f"- {PAGE}")