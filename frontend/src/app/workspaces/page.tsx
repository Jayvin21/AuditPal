"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import AmbientBackground from "@/components/AmbientBackground";
import { ArrowRight, Plus } from "lucide-react";

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
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="relative min-h-screen bg-[#F6FBF8] px-6 py-8 text-[#17352E]">
      <AmbientBackground />

      <div className="mx-auto max-w-6xl">
        <div className="mb-8 flex items-center justify-between border-b border-[#C8DDD0] pb-5">
          <div>
            <Link href="/" className="text-sm text-[#5F7D70] hover:text-[#17352E]">
              ← Back
            </Link>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-[#17352E]">
              Audit Workspaces
            </h1>
            <p className="mt-2 text-[#5F7D70]">
              Create a client workspace and run real audit checks on uploaded files.
            </p>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
          <form
            onSubmit={createWorkspace}
            className="rounded-2xl border border-[#C8DDD0] bg-white/92 p-5 shadow-sm backdrop-blur"
          >
            <div className="mb-5 flex items-center gap-2 text-[#17352E]">
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
              <option value="expense_audit">Expense Audit</option>
              <option value="bank_reconciliation">Bank Reconciliation</option>
            </select>

            <button
              disabled={loading}
              className="w-full rounded-xl bg-[#358873] px-5 py-3 font-medium text-white transition hover:bg-[#2F7866] disabled:opacity-50"
            >
              {loading ? "Creating..." : "Create Workspace"}
            </button>
          </form>

          <section className="rounded-2xl border border-[#C8DDD0] bg-white/92 p-5 shadow-sm backdrop-blur">
            <h2 className="mb-5 font-medium text-[#17352E]">Existing Workspaces</h2>

            {workspaces.length === 0 ? (
              <p className="rounded-xl border border-[#D6E6DD] bg-[#F6FBF8] p-4 text-sm text-[#5F7D70]">
                No workspaces yet. Create one to start an audit.
              </p>
            ) : (
              <div className="space-y-3">
                {workspaces.map((workspace) => (
                  <Link
                    key={workspace.id}
                    href={`/workspaces/${workspace.id}`}
                    className="flex items-center justify-between rounded-xl border border-[#D6E6DD] bg-[#F6FBF8] p-4 transition hover:bg-[#EDF6F0]"
                  >
                    <div>
                      <h3 className="font-medium text-[#17352E]">{workspace.client_name}</h3>
                      <p className="mt-1 text-sm text-[#5F7D70]">
                        {workspace.audit_period} · {workspace.audit_type} · {workspace.status}
                      </p>
                    </div>
                    <ArrowRight size={18} className="text-[#4E9C81]" />
                  </Link>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}