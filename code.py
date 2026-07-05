from pathlib import Path

PAGE = Path(r"D:\1Workspace\AuditPal\frontend\src\app\workspaces\[id]\page.tsx")

page = PAGE.read_text(encoding="utf-8")

old = '''function formatFileType(type: string) {
  return fileTypeOptions.find((option) => option.value === type)?.label ?? formatIssueType(type);
}

function formatIssueType(type: string) {
  return type
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}'''

new = '''function formatFileType(type?: string | null) {
  if (!type) return "Unknown file type";
  return fileTypeOptions.find((option) => option.value === type)?.label ?? formatIssueType(type);
}

function formatIssueType(type?: string | null) {
  if (!type) return "Unknown";
  return type
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}'''

if old not in page:
    raise SystemExit("Could not find exact formatter block. Paste the bottom helper functions if this fails.")

page = page.replace(old, new)

# Also make MappingSection file_type fallback safe in case backend response is stale.
page = page.replace(
    "{formatFileType(mappingPreview.file_type)} · {getMappingProfileKey(mappingPreview.file_type)} profile",
    "{formatFileType(mappingPreview.file_type)} · {getMappingProfileKey(mappingPreview.file_type ?? 'standard')} profile",
)

PAGE.write_text(page, encoding="utf-8")

print("Fixed null-safe formatter crash.")