from pathlib import Path

PAGE = Path(r"D:\1Workspace\AuditPal\frontend\src\app\workspaces\[id]\page.tsx")

page = PAGE.read_text(encoding="utf-8")

# ----------------------------------------------------
# 1. Add findings search/sort state
# ----------------------------------------------------

page = page.replace(
    '''  const [riskFilter, setRiskFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("needs_review");''',
    '''  const [riskFilter, setRiskFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("needs_review");
  const [findingSearch, setFindingSearch] = useState("");
  const [findingSort, setFindingSort] = useState("risk_high_first");'''
)

# ----------------------------------------------------
# 2. Replace filteredFindings logic with search + sort
# ----------------------------------------------------

old_filtered = '''  const filteredFindings = visibleFindings.filter((finding) => {
    const riskMatch = riskFilter === "all" || finding.risk_level === riskFilter;
    const typeMatch = typeFilter === "all" || finding.finding_type === typeFilter;
    const statusMatch = statusFilter === "all" || finding.status === statusFilter;
    return riskMatch && typeMatch && statusMatch;
  });'''

new_filtered = '''  const filteredFindings = useMemo(() => {
    const riskRank: Record<string, number> = { high: 3, medium: 2, low: 1 };
    const statusRank: Record<string, number> = {
      needs_review: 5,
      needs_client_clarification: 4,
      confirmed_issue: 3,
      false_positive: 2,
      resolved: 1,
    };

    const query = findingSearch.toLowerCase().trim();

    const filtered = visibleFindings.filter((finding) => {
      const riskMatch = riskFilter === "all" || finding.risk_level === riskFilter;
      const typeMatch = typeFilter === "all" || finding.finding_type === typeFilter;
      const statusMatch = statusFilter === "all" || finding.status === statusFilter;

      const searchBlob = [
        finding.title,
        finding.description,
        finding.finding_type,
        finding.risk_level,
        finding.status,
        JSON.stringify(finding.evidence ?? {}),
      ]
        .join(" ")
        .toLowerCase();

      const searchMatch = !query || searchBlob.includes(query);

      return riskMatch && typeMatch && statusMatch && searchMatch;
    });

    return [...filtered].sort((a, b) => {
      if (findingSort === "risk_high_first") {
        return (riskRank[b.risk_level] ?? 0) - (riskRank[a.risk_level] ?? 0) || b.id - a.id;
      }

      if (findingSort === "risk_low_first") {
        return (riskRank[a.risk_level] ?? 0) - (riskRank[b.risk_level] ?? 0) || b.id - a.id;
      }

      if (findingSort === "status_open_first") {
        return (statusRank[b.status] ?? 0) - (statusRank[a.status] ?? 0) || b.id - a.id;
      }

      if (findingSort === "oldest_first") {
        return a.id - b.id;
      }

      return b.id - a.id;
    });
  }, [visibleFindings, riskFilter, typeFilter, statusFilter, findingSearch, findingSort]);'''

if old_filtered not in page:
    raise SystemExit("Could not find filteredFindings block. Patch stopped.")

page = page.replace(old_filtered, new_filtered)

# ----------------------------------------------------
# 3. Pass new props into FindingsSection
# ----------------------------------------------------

page = page.replace(
    '''                riskFilter={riskFilter}
                typeFilter={typeFilter}
                statusFilter={statusFilter}
                noteDrafts={noteDrafts}''',
    '''                riskFilter={riskFilter}
                typeFilter={typeFilter}
                statusFilter={statusFilter}
                findingSearch={findingSearch}
                findingSort={findingSort}
                noteDrafts={noteDrafts}'''
)

page = page.replace(
    '''                setRiskFilter={setRiskFilter}
                setTypeFilter={setTypeFilter}
                setStatusFilter={setStatusFilter}
                setNoteDrafts={setNoteDrafts}''',
    '''                setRiskFilter={setRiskFilter}
                setTypeFilter={setTypeFilter}
                setStatusFilter={setStatusFilter}
                setFindingSearch={setFindingSearch}
                setFindingSort={setFindingSort}
                setNoteDrafts={setNoteDrafts}'''
)

# ----------------------------------------------------
# 4. Update FindingsSection destructuring/signature
# ----------------------------------------------------

page = page.replace(
    '''  riskFilter,
  typeFilter,
  statusFilter,
  noteDrafts,''',
    '''  riskFilter,
  typeFilter,
  statusFilter,
  findingSearch,
  findingSort,
  noteDrafts,'''
)

page = page.replace(
    '''  setRiskFilter,
  setTypeFilter,
  setStatusFilter,
  setNoteDrafts,''',
    '''  setRiskFilter,
  setTypeFilter,
  setStatusFilter,
  setFindingSearch,
  setFindingSort,
  setNoteDrafts,'''
)

page = page.replace(
    '''  riskFilter: string;
  typeFilter: string;
  statusFilter: string;
  noteDrafts: Record<number, string>;''',
    '''  riskFilter: string;
  typeFilter: string;
  statusFilter: string;
  findingSearch: string;
  findingSort: string;
  noteDrafts: Record<number, string>;'''
)

page = page.replace(
    '''  setRiskFilter: (value: string) => void;
  setTypeFilter: (value: string) => void;
  setStatusFilter: (value: string) => void;
  setNoteDrafts: React.Dispatch<React.SetStateAction<Record<number, string>>>;''',
    '''  setRiskFilter: (value: string) => void;
  setTypeFilter: (value: string) => void;
  setStatusFilter: (value: string) => void;
  setFindingSearch: (value: string) => void;
  setFindingSort: (value: string) => void;
  setNoteDrafts: React.Dispatch<React.SetStateAction<Record<number, string>>>;'''
)

# ----------------------------------------------------
# 5. Replace Findings filter panel with search/sort/filter UX
# ----------------------------------------------------

old_filter_panel = r'''        <div className="mb-5 grid gap-3 rounded-xl border border-[#D6E6DD] bg-[#F6FBF8] p-4 md:grid-cols-3">
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
        </div>'''

new_filter_panel = r'''        <div className="mb-5 rounded-xl border border-[#D6E6DD] bg-[#F6FBF8] p-4">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-[#6B8E7F]">
                Filters
              </p>
              <p className="mt-1 text-sm text-[#5F7D70]">
                Showing {filteredFindings.length} matching finding{filteredFindings.length === 1 ? "" : "s"}.
              </p>
            </div>

            <button
              onClick={() => {
                setRiskFilter("all");
                setTypeFilter("all");
                setStatusFilter("all");
                setFindingSearch("");
                setFindingSort("risk_high_first");
              }}
              className="rounded-xl border border-[#B4D6C1] bg-white px-4 py-2 text-sm font-medium text-[#17352E] transition hover:bg-[#EDF6F0]"
            >
              Clear filters
            </button>
          </div>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <div className="xl:col-span-2">
              <label className="mb-2 flex items-center gap-2 text-sm text-[#5F7D70]">
                <Filter size={14} />
                Search findings
              </label>
              <input
                value={findingSearch}
                onChange={(event) => setFindingSearch(event.target.value)}
                placeholder="Search vendor, invoice, issue, evidence..."
                className="w-full rounded-xl border border-[#C8DDD0] bg-white px-3 py-2 text-sm outline-none focus:border-[#4E9C81]"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm text-[#5F7D70]">Risk</label>
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

            <div>
              <label className="mb-2 block text-sm text-[#5F7D70]">Sort</label>
              <select
                value={findingSort}
                onChange={(e) => setFindingSort(e.target.value)}
                className="w-full rounded-xl border border-[#C8DDD0] bg-white px-3 py-2 text-sm outline-none focus:border-[#4E9C81]"
              >
                <option value="risk_high_first">High risk first</option>
                <option value="risk_low_first">Low risk first</option>
                <option value="status_open_first">Open review first</option>
                <option value="newest_first">Newest first</option>
                <option value="oldest_first">Oldest first</option>
              </select>
            </div>

            <div className="md:col-span-2 xl:col-span-5">
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
          </div>
        </div>'''

if old_filter_panel not in page:
    raise SystemExit("Could not find Findings filter panel. Patch stopped.")

page = page.replace(old_filter_panel, new_filter_panel)

# ----------------------------------------------------
# 6. Make risk/status labels prettier in finding cards
# ----------------------------------------------------

page = page.replace(
    '''                      {finding.risk_level}''',
    '''                      {formatIssueType(finding.risk_level)}'''
)

# Add issue type pill under title if not already added
old_meta_block = '''                {findingMeta(finding) && (
                  <p className="mb-2 text-xs font-medium text-[#6B8E7F]">
                    {findingMeta(finding)}
                  </p>
                )}'''

new_meta_block = '''                <div className="mb-2 flex flex-wrap items-center gap-2 text-xs font-medium text-[#6B8E7F]">
                  <span className="rounded-full bg-[#EAF4EE] px-2 py-1 text-[#2F7866]">
                    {formatIssueType(finding.finding_type)}
                  </span>
                  {findingMeta(finding) && <span>{findingMeta(finding)}</span>}
                </div>'''

if old_meta_block in page:
    page = page.replace(old_meta_block, new_meta_block)

PAGE.write_text(page, encoding="utf-8")

print("Pass 2 Task 4 applied.")
print("Updated Findings UX:")
print("- Finding search")
print("- Sorting")
print("- Result count")
print("- Clear filters")
print("- Readable issue/risk labels")
print(f"- {PAGE}")