"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import AmbientBackground from "@/components/AmbientBackground";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  FileSearch,
  ShieldCheck,
  Sparkles,
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
    <main className="relative min-h-screen overflow-hidden bg-[#F6FBF8] text-[#17352E]">
      <AmbientBackground />

      <div className="pointer-events-none absolute left-[-120px] top-24 h-72 w-72 rounded-full bg-[#BFE3D0]/40 blur-3xl animate-pulse" />
      <div className="pointer-events-none absolute bottom-[-120px] right-[-80px] h-96 w-96 rounded-full bg-[#D8EFE2]/70 blur-3xl animate-pulse" />

      <section className="relative z-10 mx-auto flex min-h-screen max-w-6xl flex-col px-6 py-8">
        <nav className="fade-down flex items-center justify-between border-b border-[#C8DDD0] pb-5">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-[#17352E]">
              AuditPal
            </h1>
            <p className="text-sm text-[#5F7D70]">
              Agentic AI audit assistant with human review
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden rounded-full border border-[#B4D6C1] bg-white/90 px-4 py-2 text-sm text-[#5F7D70] shadow-sm backdrop-blur md:block">
              Built by <span className="font-medium text-[#17352E]">Jayvin Parmar</span>
            </div>

            <div className="rounded-full border border-[#B4D6C1] bg-white/90 px-4 py-2 text-sm text-[#5F7D70] shadow-sm backdrop-blur">
              API:{" "}
              <span
                className={
                  health?.status === "ok"
                    ? "font-medium text-[#358873]"
                    : "font-medium text-red-600"
                }
              >
                {health?.status === "ok" ? "Connected" : "Offline"}
              </span>
            </div>
          </div>
        </nav>

        <div className="grid flex-1 items-center gap-10 py-16 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="fade-up">
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-[#B4D6C1] bg-[#EDF6F0]/90 px-4 py-2 text-sm text-[#42685B] backdrop-blur">
              <ShieldCheck size={16} />
              Built for CA interns, audit teams, and Excel-heavy workflows
            </div>

            <h2 className="max-w-3xl text-5xl font-semibold leading-tight tracking-tight text-[#17352E] md:text-6xl">
              Find audit issues across Excel, Tally exports, bank statements,
              and document proofs.
            </h2>

            <p className="mt-6 max-w-2xl text-lg leading-8 text-[#5F7D70]">
              AuditPal turns manual verification into an exception-review
              workflow: upload records, match proofs, detect mismatches, rank
              risks, and keep every finding human-reviewable.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/workspaces"
                className="group inline-flex items-center gap-2 rounded-xl bg-[#358873] px-5 py-3 font-medium text-white shadow-sm transition hover:-translate-y-0.5 hover:bg-[#2F7866] hover:shadow-md"
              >
                Create Workspace
                <ArrowRight size={17} className="transition group-hover:translate-x-0.5" />
              </Link>
              <Link
                href="/workspaces"
                className="rounded-xl border border-[#B4D6C1] bg-white/90 px-5 py-3 font-medium text-[#17352E] transition hover:-translate-y-0.5 hover:bg-[#EDF6F0] hover:shadow-sm"
              >
                Open Workspaces
              </Link>
            </div>

            <div className="mt-8 flex flex-wrap items-center gap-3 text-sm text-[#5F7D70]">
              <span className="inline-flex items-center gap-2 rounded-full border border-[#D6E6DD] bg-white/80 px-3 py-2">
                <Sparkles size={15} className="text-[#358873]" />
                Full-stack audit automation project
              </span>
              <span className="rounded-full border border-[#D6E6DD] bg-white/80 px-3 py-2">
                Next.js · FastAPI · SQLite · Rule engine · Audit chat
              </span>
            </div>
          </div>

          <div className="fade-up-delay rounded-2xl border border-[#C8DDD0] bg-white/92 p-5 shadow-lg backdrop-blur transition hover:-translate-y-1 hover:shadow-xl">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <h3 className="font-medium text-[#17352E]">Audit Coverage</h3>
                <p className="text-sm text-[#5F7D70]">Real uploaded records only</p>
              </div>
              <FileSearch className="text-[#4E9C81]" />
            </div>

            <div className="space-y-3">
              <Metric label="Excel/CSV ingestion" value="Ready" icon="checked" />
              <Metric label="11 audit modules" value="Ready" icon="checked" />
              <Metric label="Risk-ranked findings" value="Ready" icon="warning" />
              <Metric label="Agentic audit chat" value="Ready" icon="upload" />
            </div>

            <div className="mt-6 rounded-xl border border-[#D6E6DD] bg-[#F6FBF8] p-4">
              <p className="mb-2 text-sm font-medium text-[#17352E]">
                Current build
              </p>
              <p className="text-sm leading-6 text-[#5F7D70]">
                Upload audit files, map module-specific columns, extract records,
                run deterministic audit checks, review findings, chat with the
                workspace, and export reports.
              </p>
            </div>
          </div>
        </div>

        <footer className="fade-up-delay border-t border-[#C8DDD0] py-5 text-sm text-[#5F7D70]">
          Built by <span className="font-medium text-[#17352E]">Jayvin Parmar</span> · Portfolio project for audit automation, data workflows, and AI-assisted review.
        </footer>
      </section>

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
          animation: fadeUp 700ms ease-out both;
        }

        .fade-up-delay {
          animation: fadeUp 850ms ease-out both;
          animation-delay: 120ms;
        }

        .fade-down {
          animation: fadeDown 600ms ease-out both;
        }
      `}</style>
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
    <div className="group flex items-center justify-between rounded-xl border border-[#D6E6DD] bg-[#F6FBF8] p-4 transition hover:-translate-y-0.5 hover:border-[#B4D6C1] hover:bg-white">
      <div className="flex items-center gap-3">
        <Icon size={18} className="text-[#4E9C81] transition group-hover:scale-110" />
        <span className="text-sm text-[#42685B]">{label}</span>
      </div>
      <span className="font-semibold text-[#17352E]">{value}</span>
    </div>
  );
}
