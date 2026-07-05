"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import {
  AlertTriangle,
  CheckCircle2,
  FileSearch,
  ShieldCheck,
  Upload,
} from "lucide-react";

type HealthResponse = {
  status: string;
  service: string;
};

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    api
      .get("/health")
      .then((res) => setHealth(res.data))
      .catch(() => setHealth(null));
  }, []);

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      <section className="mx-auto flex min-h-screen max-w-6xl flex-col px-6 py-8">
        <nav className="flex items-center justify-between border-b border-zinc-800 pb-5">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">AuditPal</h1>
            <p className="text-sm text-zinc-400">
              Agentic AI audit assistant with human review
            </p>
          </div>

          <div className="rounded-full border border-zinc-800 px-4 py-2 text-sm text-zinc-300">
            API:{" "}
            <span
              className={
                health?.status === "ok" ? "text-emerald-400" : "text-red-400"
              }
            >
              {health?.status === "ok" ? "Connected" : "Offline"}
            </span>
          </div>
        </nav>

        <div className="grid flex-1 items-center gap-10 py-16 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-zinc-800 bg-zinc-900 px-4 py-2 text-sm text-zinc-300">
              <ShieldCheck size={16} />
              Built for CA interns, audit teams, and Excel-heavy workflows
            </div>

            <h2 className="max-w-3xl text-5xl font-semibold leading-tight tracking-tight">
              Find audit issues across Excel, Tally exports, bank statements,
              and document proofs.
            </h2>

            <p className="mt-6 max-w-2xl text-lg leading-8 text-zinc-400">
              AuditPal turns manual verification into an exception-review
              workflow: upload records, match proofs, detect mismatches, rank
              risks, and keep every finding human-reviewable.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <button className="rounded-xl bg-zinc-100 px-5 py-3 font-medium text-zinc-950 hover:bg-white">
                Create Workspace
              </button>
              <button className="rounded-xl border border-zinc-800 px-5 py-3 font-medium text-zinc-200 hover:bg-zinc-900">
                View Demo Audit
              </button>
            </div>
          </div>

          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-5 shadow-2xl">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <h3 className="font-medium">Audit Coverage</h3>
                <p className="text-sm text-zinc-400">ABC Traders FY 2025-26</p>
              </div>
              <FileSearch className="text-zinc-400" />
            </div>

            <div className="space-y-3">
              <Metric label="Records reviewed" value="1,240" icon="checked" />
              <Metric label="Matched with proof" value="1,032" icon="checked" />
              <Metric label="High-risk findings" value="12" icon="warning" />
              <Metric label="Needs manual review" value="148" icon="upload" />
            </div>

            <div className="mt-6 rounded-xl border border-zinc-800 bg-zinc-950 p-4">
              <p className="mb-2 text-sm font-medium text-zinc-200">
                Latest finding
              </p>
              <p className="text-sm leading-6 text-zinc-400">
                Invoice INV-1042 exists in the purchase register, but no
                matching uploaded proof was found. Risk: High.
              </p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

function Metric({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon: "checked" | "warning" | "upload";
}) {
  const Icon =
    icon === "checked" ? CheckCircle2 : icon === "warning" ? AlertTriangle : Upload;

  return (
    <div className="flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-950 p-4">
      <div className="flex items-center gap-3">
        <Icon size={18} className="text-zinc-400" />
        <span className="text-sm text-zinc-300">{label}</span>
      </div>
      <span className="font-semibold">{value}</span>
    </div>
  );
}
