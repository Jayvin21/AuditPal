"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import AmbientBackground from "@/components/AmbientBackground";
import {
  ArrowLeft,
  ArrowRight,
  Loader2,
  Plus,
  Search,
  Sparkles,
  Trash2,
} from "lucide-react";

type Workspace = {
  id: number;
  client_name: string;
  audit_period: string;
  audit_type: string;
  status: string;
};

export default function WorkspacesPage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [clientName, setClientName] = useState("ABC Traders");
  const [auditPeriod, setAuditPeriod] = useState("FY 2025-26");
  const [auditType, setAuditType] = useState("purchase_audit");
  const [loading, setLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [workspaceSearch, setWorkspaceSearch] = useState("");
  const [statusMessage, setStatusMessage] = useState("");

  async function loadWorkspaces() {
    const res = await api.get("/workspaces");
    setWorkspaces(res.data);
  }

  useEffect(() => {
    loadWorkspaces();
  }, []);

  async function createWorkspace(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setStatusMessage("");

    try {
      await api.post("/workspaces", {
        client_name: clientName,
        audit_period: auditPeriod,
        audit_type: auditType,
      });

      await loadWorkspaces();
      setClientName("");
      setAuditPeriod("FY 2025-26");
      setAuditType("purchase_audit");
      setStatusMessage("Workspace created.");
    } catch {
      setStatusMessage("Could not create workspace.");
    } finally {
      setLoading(false);
    }
  }

  async function deleteWorkspace(workspace: Workspace) {
    const confirmed = window.confirm(
      `Delete workspace "${workspace.client_name}"? This will remove its files, mappings, extracted records, findings, and audit runs.`
    );

    if (!confirmed) return;

    setDeletingId(workspace.id);
    setStatusMessage("Deleting workspace...");

    try {
      await api.delete(`/workspaces/${workspace.id}`);
      await loadWorkspaces();
      setStatusMessage("Workspace deleted.");
    } catch {
      setStatusMessage("Could not delete workspace.");
    } finally {
      setDeletingId(null);
    }
  }

  const visibleWorkspaces = useMemo(() => {
    const query = workspaceSearch.toLowerCase().trim();

    if (!query) return workspaces;

    return workspaces.filter((workspace) =>
      [
        workspace.client_name,
        workspace.audit_period,
        workspace.audit_type,
        workspace.status,
        workspace.id,
      ]
        .join(" ")
        .toLowerCase()
        .includes(query)
    );
  }, [workspaces, workspaceSearch]);

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#F6FBF8] px-6 py-8 text-[#17352E]">
      <AmbientBackground />

      <div className="pointer-events-none absolute left-[-120px] top-28 h-72 w-72 rounded-full bg-[#CBE8D6]/50 blur-3xl animate-pulse" />
      <div className="pointer-events-none absolute bottom-[-160px] right-[-100px] h-96 w-96 rounded-full bg-[#E2F3E9]/80 blur-3xl animate-pulse" />

      <div className="relative z-10 mx-auto max-w-6xl">
        <div className="fade-down mb-8 flex items-center justify-between border-b border-[#C8DDD0] pb-5">
          <div>
            <Link
              href="/"
              className="inline-flex items-center gap-2 text-sm text-[#5F7D70] hover:text-[#17352E]"
            >
              <ArrowLeft size={15} />
              Back
            </Link>

            <h1 className="mt-3 text-3xl font-semibold tracking-tight">
              Audit Workspaces
            </h1>
            <p className="mt-2 text-[#5F7D70]">
              Create a client workspace and run real audit checks on uploaded files.
            </p>
          </div>

          <div className="hidden rounded-full border border-[#B4D6C1] bg-white/90 px-4 py-2 text-sm text-[#5F7D70] shadow-sm backdrop-blur md:block">
            Built by <span className="font-medium text-[#17352E]">Jayvin Parmar</span>
          </div>
        </div>

        {statusMessage && (
          <div className="fade-up mb-5 rounded-2xl border border-[#C8DDD0] bg-white/88 p-4 text-sm text-[#5F7D70] shadow-sm backdrop-blur">
            {statusMessage}
          </div>
        )}

        <div className="grid items-start gap-6 lg:grid-cols-[0.8fr_1.2fr]">
          <form
            onSubmit={createWorkspace}
            className="fade-up rounded-2xl border border-[#C8DDD0] bg-white/92 p-5 shadow-sm backdrop-blur transition hover:-translate-y-1 hover:shadow-md"
          >
            <div className="mb-5 flex items-center gap-2">
              <Plus size={18} className="text-[#358873]" />
              <h2 className="font-medium">Create Workspace</h2>
            </div>

            <label className="mb-2 block text-sm text-[#5F7D70]">Client name</label>
            <input
              value={clientName}
              onChange={(event) => setClientName(event.target.value)}
              className="mb-4 w-full rounded-xl border border-[#C8DDD0] bg-[#F6FBF8] px-4 py-3 outline-none focus:border-[#4E9C81]"
              placeholder="ABC Traders"
              required
            />

            <label className="mb-2 block text-sm text-[#5F7D70]">Audit period</label>
            <input
              value={auditPeriod}
              onChange={(event) => setAuditPeriod(event.target.value)}
              className="mb-4 w-full rounded-xl border border-[#C8DDD0] bg-[#F6FBF8] px-4 py-3 outline-none focus:border-[#4E9C81]"
              placeholder="FY 2025-26"
              required
            />

            <label className="mb-2 block text-sm text-[#5F7D70]">Audit type</label>
            <select
              value={auditType}
              onChange={(event) => setAuditType(event.target.value)}
              className="mb-5 w-full rounded-xl border border-[#C8DDD0] bg-[#F6FBF8] px-4 py-3 outline-none focus:border-[#4E9C81]"
            >
              <option value="purchase_audit">Purchase Audit</option>
              <option value="statutory_audit">Statutory Audit</option>
              <option value="internal_audit">Internal Audit</option>
              <option value="gst_review">GST Review</option>
              <option value="bank_reconciliation">Bank Reconciliation</option>
              <option value="fixed_asset_audit">Fixed Asset Audit</option>
              <option value="tds_review">TDS Review</option>
              <option value="full_audit">Full Audit Workflow</option>
            </select>

            <button
              disabled={loading}
              className="group flex w-full items-center justify-center gap-2 rounded-xl bg-[#358873] px-5 py-3 font-medium text-white transition hover:-translate-y-0.5 hover:bg-[#2F7866] hover:shadow-md disabled:opacity-50"
            >
              {loading ? <Loader2 size={17} className="animate-spin" /> : <Plus size={17} />}
              {loading ? "Creating..." : "Create Workspace"}
            </button>

            <div className="mt-5 rounded-xl border border-[#D6E6DD] bg-[#F6FBF8] p-4 text-sm leading-6 text-[#5F7D70]">
              <div className="mb-2 flex items-center gap-2 font-medium text-[#17352E]">
                <Sparkles size={15} className="text-[#358873]" />
                Portfolio demo tip
              </div>
              Create one clean workspace with sample files before recording your demo video.
            </div>
          </form>

          <section className="fade-up-delay rounded-2xl border border-[#C8DDD0] bg-white/92 p-5 shadow-sm backdrop-blur">
            <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="font-medium">Existing Workspaces</h2>
                <p className="mt-1 text-sm text-[#5F7D70]">
                  {visibleWorkspaces.length} of {workspaces.length} shown.
                </p>
              </div>

              <div className="relative w-full md:w-72">
                <Search size={15} className="absolute left-3 top-3.5 text-[#6B8E7F]" />
                <input
                  value={workspaceSearch}
                  onChange={(event) => setWorkspaceSearch(event.target.value)}
                  placeholder="Search workspaces..."
                  className="w-full rounded-xl border border-[#C8DDD0] bg-[#F6FBF8] py-3 pl-9 pr-3 text-sm outline-none focus:border-[#4E9C81]"
                />
              </div>
            </div>

            {workspaces.length === 0 ? (
              <div className="rounded-xl border border-dashed border-[#B4D6C1] bg-[#F6FBF8] p-8 text-center text-sm text-[#5F7D70]">
                No workspaces yet. Create your first audit workspace.
              </div>
            ) : visibleWorkspaces.length === 0 ? (
              <div className="rounded-xl border border-dashed border-[#B4D6C1] bg-[#F6FBF8] p-8 text-center text-sm text-[#5F7D70]">
                No workspaces match your search.
              </div>
            ) : (
              <div className="space-y-3">
                {visibleWorkspaces.map((workspace, index) => (
                  <div
                    key={workspace.id}
                    className="workspace-card group rounded-xl border border-[#D6E6DD] bg-[#F6FBF8] p-4 transition hover:-translate-y-0.5 hover:border-[#B4D6C1] hover:bg-white hover:shadow-sm"
                    style={{ animationDelay: `${index * 60}ms` }}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <Link href={`/workspaces/${workspace.id}`} className="min-w-0 flex-1">
                        <h3 className="font-medium text-[#17352E] transition group-hover:text-[#2F7866]">
                          {workspace.client_name}
                        </h3>
                        <p className="mt-1 text-sm text-[#5F7D70]">
                          {workspace.audit_period} · {formatAuditType(workspace.audit_type)} · {workspace.status}
                        </p>
                      </Link>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => deleteWorkspace(workspace)}
                          disabled={deletingId === workspace.id}
                          className="inline-flex items-center gap-2 rounded-xl border border-[#F3CACA] bg-white px-3 py-2 text-xs font-medium text-[#B42318] transition hover:bg-[#FDE8E8] disabled:opacity-50"
                          title="Delete workspace"
                        >
                          {deletingId === workspace.id ? (
                            <Loader2 size={14} className="animate-spin" />
                          ) : (
                            <Trash2 size={14} />
                          )}
                          Delete
                        </button>

                        <Link
                          href={`/workspaces/${workspace.id}`}
                          className="rounded-xl border border-[#B4D6C1] bg-white px-3 py-2 text-[#358873] transition hover:bg-[#EDF6F0]"
                          title="Open workspace"
                        >
                          <ArrowRight size={18} />
                        </Link>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>

      <style jsx global>{`
        @keyframes fadeUp {
          from {
            opacity: 0;
            transform: translateY(18px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes fadeDown {
          from {
            opacity: 0;
            transform: translateY(-12px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .fade-up {
          animation: fadeUp 650ms ease-out both;
        }

        .fade-up-delay {
          animation: fadeUp 760ms ease-out both;
          animation-delay: 100ms;
        }

        .fade-down {
          animation: fadeDown 550ms ease-out both;
        }

        .workspace-card {
          animation: fadeUp 520ms ease-out both;
        }
      `}</style>
    </main>
  );
}

function formatAuditType(value: string) {
  return value
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
