from pathlib import Path
import re

ROOT = Path(r"D:\1Workspace\AuditPal")

PAGE = ROOT / "frontend" / "src" / "app" / "workspaces" / "[id]" / "page.tsx"
CSS = ROOT / "frontend" / "src" / "app" / "globals.css"

page = PAGE.read_text(encoding="utf-8")
css = CSS.read_text(encoding="utf-8")

# ----------------------------------------------------
# 1. Global animation utilities
# ----------------------------------------------------

animation_css = r'''

/* Workspace detail polish animations */
@keyframes auditFadeUp {
  from {
    opacity: 0;
    transform: translateY(18px);
    filter: blur(3px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
    filter: blur(0);
  }
}

@keyframes auditFadeDown {
  from {
    opacity: 0;
    transform: translateY(-12px);
    filter: blur(3px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
    filter: blur(0);
  }
}

@keyframes auditSlideInLeft {
  from {
    opacity: 0;
    transform: translateX(-18px);
    filter: blur(3px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
    filter: blur(0);
  }
}

@keyframes auditScaleIn {
  from {
    opacity: 0;
    transform: scale(0.975) translateY(10px);
    filter: blur(3px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
    filter: blur(0);
  }
}

@keyframes auditSoftPulse {
  0% {
    box-shadow: 0 0 0 0 rgba(53, 136, 115, 0.16);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(53, 136, 115, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(53, 136, 115, 0);
  }
}

.audit-nav-enter {
  animation: auditFadeDown 520ms ease-out both;
}

.audit-sidebar-enter {
  animation: auditSlideInLeft 620ms ease-out both;
}

.audit-stage-enter {
  animation: auditFadeUp 620ms ease-out both;
}

.audit-header-enter {
  animation: auditScaleIn 650ms ease-out both;
}

.audit-metrics-enter {
  animation: auditFadeUp 700ms ease-out both;
  animation-delay: 80ms;
}

.audit-status-enter {
  animation: auditScaleIn 420ms ease-out both;
}

.audit-section-enter {
  animation: auditFadeUp 520ms ease-out both;
}

.audit-card-motion {
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    border-color 180ms ease,
    background-color 180ms ease;
}

.audit-card-motion:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 34px rgba(23, 53, 46, 0.075);
}

.audit-list-item {
  animation: auditFadeUp 420ms ease-out both;
  transition:
    transform 160ms ease,
    box-shadow 160ms ease,
    border-color 160ms ease,
    background-color 160ms ease;
}

.audit-list-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 22px rgba(23, 53, 46, 0.06);
}

.audit-button-motion {
  transition:
    transform 150ms ease,
    box-shadow 150ms ease,
    background-color 150ms ease,
    border-color 150ms ease;
}

.audit-button-motion:hover {
  transform: translateY(-1px);
}

.audit-button-motion:active {
  transform: translateY(0);
}

.audit-active-pulse {
  animation: auditSoftPulse 1800ms ease-out infinite;
}

.audit-stagger-1 { animation-delay: 60ms; }
.audit-stagger-2 { animation-delay: 120ms; }
.audit-stagger-3 { animation-delay: 180ms; }
.audit-stagger-4 { animation-delay: 240ms; }

@media (prefers-reduced-motion: reduce) {
  .audit-nav-enter,
  .audit-sidebar-enter,
  .audit-stage-enter,
  .audit-header-enter,
  .audit-metrics-enter,
  .audit-status-enter,
  .audit-section-enter,
  .audit-list-item {
    animation: none !important;
  }

  .audit-card-motion,
  .audit-list-item,
  .audit-button-motion {
    transition: none !important;
  }

  .audit-card-motion:hover,
  .audit-list-item:hover,
  .audit-button-motion:hover {
    transform: none !important;
  }
}
'''

if "Workspace detail polish animations" not in css:
    css = css.rstrip() + "\n" + animation_css + "\n"

CSS.write_text(css, encoding="utf-8")

# ----------------------------------------------------
# 2. Workspace page container/header/sidebar entrance classes
# ----------------------------------------------------

page = page.replace(
    '<main className="relative min-h-screen bg-[#F6FBF8] text-[#17352E]">',
    '<main className="relative min-h-screen overflow-hidden bg-[#F6FBF8] text-[#17352E]">'
)

page = page.replace(
    '<div className="border-b border-[#C8DDD0] bg-white/78 backdrop-blur">',
    '<div className="audit-nav-enter border-b border-[#C8DDD0] bg-white/78 backdrop-blur">'
)

page = page.replace(
    '<div className="sticky top-6 rounded-3xl border border-[#C8DDD0] bg-white/88 p-4 shadow-sm backdrop-blur">',
    '<div className="audit-sidebar-enter sticky top-6 rounded-3xl border border-[#C8DDD0] bg-white/88 p-4 shadow-sm backdrop-blur">'
)

page = page.replace(
    '<section className="min-w-0">',
    '<section className="audit-stage-enter min-w-0">'
)

page = page.replace(
    '<header className="mb-5 rounded-3xl border border-[#C8DDD0] bg-white/88 p-5 shadow-sm backdrop-blur">',
    '<header className="audit-header-enter audit-card-motion mb-5 rounded-3xl border border-[#C8DDD0] bg-white/88 p-5 shadow-sm backdrop-blur">'
)

page = page.replace(
    '<section className="mb-5 grid gap-4 md:grid-cols-4">',
    '<section className="audit-metrics-enter mb-5 grid gap-4 md:grid-cols-4">'
)

page = page.replace(
    '<div className="mb-5 rounded-2xl border border-[#C8DDD0] bg-white/88 p-4 text-sm text-[#5F7D70] shadow-sm backdrop-blur">',
    '<div className="audit-status-enter mb-5 rounded-2xl border border-[#C8DDD0] bg-white/88 p-4 text-sm text-[#5F7D70] shadow-sm backdrop-blur">'
)

# ----------------------------------------------------
# 3. Re-animate active section when switching tabs
# ----------------------------------------------------

page = page.replace(
    '''            {activeSection === "overview" && (
              <OverviewSection''',
    '''            {activeSection === "overview" && (
              <div key="overview" className="audit-section-enter">
                <OverviewSection'''
)

page = page.replace(
    '''                setActiveSection={setActiveSection}
              />
            )}''',
    '''                setActiveSection={setActiveSection}
              />
              </div>
            )}''',
    1
)

section_replacements = [
    ("templates", "ImportTemplatesSection"),
    ("files", "FilesSection"),
    ("mapping", "MappingSection"),
    ("audit", "AuditSection"),
    ("findings", "FindingsSection"),
    ("records", "RecordsSection"),
    ("reports", "ReportsSection"),
    ("chat", "AuditChatSection"),
]

for section_key, component_name in section_replacements:
    page = page.replace(
        f'''            {{activeSection === "{section_key}" && (
              <{component_name}''',
        f'''            {{activeSection === "{section_key}" && (
              <div key="{section_key}" className="audit-section-enter">
                <{component_name}'''
    )

# Add closing divs for section blocks using targeted replacements
page = page.replace(
    '''              <ImportTemplatesSection />
            )}''',
    '''              <ImportTemplatesSection />
              </div>
            )}'''
)

page = page.replace(
    '''                setActiveSection={setActiveSection}
              />
            )}''',
    '''                setActiveSection={setActiveSection}
              />
              </div>
            )}''',
    1
)

page = page.replace(
    '''                parseFiles={parseFiles}
              />
            )}''',
    '''                parseFiles={parseFiles}
              />
              </div>
            )}''',
    1
)

page = page.replace(
    '''                runBankReconciliation={runBankReconciliation}
              />
            )}''',
    '''                runBankReconciliation={runBankReconciliation}
              />
              </div>
            )}'''
)

page = page.replace(
    '''                exportPdf={exportPdf}
              />
            )}''',
    '''                exportPdf={exportPdf}
              />
              </div>
            )}''',
    1
)

page = page.replace(
    '''              <RecordsSection records={records} />
            )}''',
    '''              <RecordsSection records={records} />
              </div>
            )}'''
)

page = page.replace(
    '''                exportPdf={exportPdf}
              />
            )}''',
    '''                exportPdf={exportPdf}
              />
              </div>
            )}''',
    1
)

page = page.replace(
    '''              <AuditChatSection workspaceId={workspaceId} refreshAll={refreshAll} />
            )}''',
    '''              <AuditChatSection workspaceId={workspaceId} refreshAll={refreshAll} />
              </div>
            )}'''
)

# ----------------------------------------------------
# 4. Nav/button/card/list micro-interactions
# ----------------------------------------------------

# Active sidebar buttons
page = page.replace(
    '''? "flex w-full items-center gap-3 rounded-2xl bg-[#358873] px-4 py-3 text-left text-sm font-medium text-white shadow-sm"''',
    '''? "audit-active-pulse flex w-full items-center gap-3 rounded-2xl bg-[#358873] px-4 py-3 text-left text-sm font-medium text-white shadow-sm transition"'''
)

page = page.replace(
    ''': "flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-left text-sm font-medium text-[#5F7D70] transition hover:bg-[#EDF6F0] hover:text-[#17352E]"''',
    ''': "flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-left text-sm font-medium text-[#5F7D70] transition hover:-translate-y-0.5 hover:bg-[#EDF6F0] hover:text-[#17352E]"'''
)

# Mobile nav
page = page.replace(
    '? "rounded-xl bg-[#358873] px-4 py-2 text-sm font-medium text-white"',
    '? "rounded-xl bg-[#358873] px-4 py-2 text-sm font-medium text-white shadow-sm transition"'
)

page = page.replace(
    ': "rounded-xl px-4 py-2 text-sm font-medium text-[#5F7D70]"',
    ': "rounded-xl px-4 py-2 text-sm font-medium text-[#5F7D70] transition hover:bg-[#EDF6F0]"'
)

# Common primary and secondary button interactions
page = page.replace(
    'className="rounded-xl bg-[#358873] px-5 py-3',
    'className="audit-button-motion rounded-xl bg-[#358873] px-5 py-3'
)

page = page.replace(
    'className="w-full rounded-xl bg-[#358873] px-5 py-3',
    'className="audit-button-motion w-full rounded-xl bg-[#358873] px-5 py-3'
)

page = page.replace(
    'className="rounded-xl border border-[#B4D6C1] bg-white px-5 py-3',
    'className="audit-button-motion rounded-xl border border-[#B4D6C1] bg-white px-5 py-3'
)

page = page.replace(
    'className="w-full rounded-xl border border-[#B4D6C1] bg-white px-5 py-3',
    'className="audit-button-motion w-full rounded-xl border border-[#B4D6C1] bg-white px-5 py-3'
)

page = page.replace(
    'className="rounded-lg border border-[#BFD8CB] bg-white px-3 py-2',
    'className="audit-button-motion rounded-lg border border-[#BFD8CB] bg-white px-3 py-2'
)

page = page.replace(
    'className="rounded-lg border border-[#F3CACA] bg-white px-3 py-2',
    'className="audit-button-motion rounded-lg border border-[#F3CACA] bg-white px-3 py-2'
)

# List item cards: files, audit runs, findings, mapping fields, chat bubbles where safe
list_patterns = [
    'className="rounded-xl border border-[#D6E6DD] bg-[#F6FBF8] p-4"',
    'className="rounded-xl border border-[#D6E6DD] bg-[#F8FCF9] p-4"',
    'className="rounded-2xl border border-[#D6E6DD] bg-[#F8FCF9] p-4"',
    'className="rounded-2xl border border-[#D6E6DD] bg-white p-4"',
    'className="rounded-2xl border border-[#B4D6C1] bg-[#F6FBF8] p-4"',
]

for pattern in list_patterns:
    if pattern in page:
        page = page.replace(pattern, pattern.replace('className="', 'className="audit-list-item '))

# Active audit-run card special branch
page = page.replace(
    '? "rounded-2xl border border-[#358873] bg-[#EDF6F0] p-4"',
    '? "audit-list-item audit-active-pulse rounded-2xl border border-[#358873] bg-[#EDF6F0] p-4"'
)

# ----------------------------------------------------
# 5. Upgrade Card component if present
# ----------------------------------------------------

card_pattern = re.compile(
    r'''function Card\(\{\s*children,\s*\}:\s*\{\s*children:\s*ReactNode;\s*\}\)\s*\{\s*return\s*\(\s*<div\s+className="([^"]+)"\s*>''',
    re.MULTILINE
)

match = card_pattern.search(page)
if match and "audit-card-motion" not in match.group(1):
    original_class = match.group(1)
    upgraded_class = "audit-card-motion " + original_class
    page = page[:match.start(1)] + upgraded_class + page[match.end(1):]

# ----------------------------------------------------
# 6. Upgrade Metric component if present
# ----------------------------------------------------

metric_pattern = 'className="rounded-2xl border border-[#C8DDD0] bg-white/88 p-4 shadow-sm backdrop-blur"'
if metric_pattern in page:
    page = page.replace(
        metric_pattern,
        'className="audit-card-motion rounded-2xl border border-[#C8DDD0] bg-white/88 p-4 shadow-sm backdrop-blur"'
    )

PAGE.write_text(page, encoding="utf-8")

print("Workspace detail animation patch applied.")
print("Updated:")
print("- globals.css animation utilities")
print("- workspace detail sidebar/header/metrics/sections")
print("- active-section re-entry animations")
print("- card/list/button hover micro-interactions")
print("- reduced-motion support")