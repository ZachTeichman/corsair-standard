const form = document.querySelector("#upload-form");
const fileInput = document.querySelector("#resume-file");
const dropzone = document.querySelector("#dropzone");
const fileTitle = document.querySelector("#file-title");
const fileDetail = document.querySelector("#file-detail");
const submitButton = document.querySelector("#submit-button");
const statusLine = document.querySelector("#status-line");
const scoreRing = document.querySelector("#score-ring");
const scoreValue = document.querySelector("#score-value");
const resultTitle = document.querySelector("#result-title");
const resultCopy = document.querySelector("#result-copy");
const violationList = document.querySelector("#violation-list");
const violationPill = document.querySelector("#violation-pill");
const resumePage = document.querySelector("#resume-page");
const modeTabs = document.querySelectorAll(".mode-tab");
const views = document.querySelectorAll(".view");
const batchInput = document.querySelector("#batch-files");
const exportCsvButton = document.querySelector("#export-csv");
const applicantTable = document.querySelector("#applicant-table");
const filterTabs = document.querySelectorAll(".filter-tab");
const dashboardEls = {
  total: document.querySelector("#dash-total"),
  average: document.querySelector("#dash-average"),
  passRate: document.querySelector("#dash-pass-rate"),
  review: document.querySelector("#dash-review"),
  all: document.querySelector("#filter-all"),
  pass: document.querySelector("#filter-pass"),
  fail: document.querySelector("#filter-fail"),
  reviewFilter: document.querySelector("#filter-review"),
};

const HISTORY_STORAGE_KEY = "corsair.auditHistory.v1";
let auditHistory = loadAuditHistory();
let activeFilter = "all";
let currentPayload = null;
let pendingViewerWindow = null;
let selectedFile = null;

const countEls = {
  critical: document.querySelector("#critical-count"),
  major: document.querySelector("#major-count"),
  minor: document.querySelector("#minor-count"),
  penalty: document.querySelector("#penalty-count"),
};

const ruleLabels = {
  "document.margin_range": "Margins in range",
  "layout.no_tables": "No layout tables",
  "layout.no_textboxes": "No text boxes",
  "header.name_centered_top_line": "Name header structure",
  "header.dual_address": "Dual address in header",
  "header.address_line_integrity": "Header address line integrity",
  "header.contact_single_row": "Contact info on one row",
  "section.corsair_structure_detected": "Corsair section structure",
  "section.required_presence": "Required sections present",
  "section.order": "Section order",
  "section.label_spelling": "Section heading spelling",
  "section.labels_all_caps": "Section labels all caps",
  "section.headers_bold": "Section headers bold",
  "section.divider_rule": "Section divider rules",
  "section.reverse_chronological_order": "Reverse chronological order",
  "entry.date_right_tab": "Entry dates right-aligned",
  "entry.date_range_en_dash": "Date range dash",
  "entry.date_range_valid": "Date range valid",
  "entry.organization_bold": "Organization names bold",
  "entry.role_italic": "Roles italicized",
  "entry.location_present": "Entry locations present",
  "paragraph.no_consecutive_blank_lines": "No consecutive blank lines",
  "paragraph.no_leading_spaces": "No literal leading spaces",
  "paragraph.no_manual_alignment_spaces": "Spacebar alignment",
  "paragraph.tab_space_alignment_hacks": "Mixed tab/space alignment",
  "paragraph.excessive_alignment_tabs": "Repeated tab alignment",
  "paragraph.tabs_require_defined_stops": "Missing saved tab stop",
  "paragraph.right_tab_consistency": "Right tab consistency",
  "paragraph.body_alignment_consistency": "Body alignment consistency",
  "header.contact_spacing_hack": "Header manual spacing",
  "entry.date_alignment_spacing_hack": "Date manual spacing",
  "bullet.indent_consistency": "First-level bullet indent",
  "typography.single_font_family": "Single font family",
  "typography.body_font_size_consistency": "Body font size consistency",
  "typography.no_unauthorized_inline_emphasis": "No unauthorized emphasis",
};

const fixGuidance = {
  "document.margin_range": "Set all page margins to the allowed Corsair range and keep them symmetric.",
  "layout.no_tables": "Remove layout tables and rebuild the content as normal Word paragraphs.",
  "layout.no_textboxes": "Move floating text box content into regular document paragraphs.",
  "header.name_centered_top_line": "This can look centered, but it should be centered with Word alignment or a saved center tab stop so it stays stable.",
  "header.dual_address": "Put exactly two city/state addresses in the header contact area.",
  "header.address_line_integrity": "Clean up the header location line so each city/state/ZIP stays on its own side with no stray characters or wrapped ZIP code.",
  "header.contact_single_row": "Keep phone, email, and both locations on one tab-separated contact row.",
  "section.corsair_structure_detected": "Restore the canonical Corsair section structure before auditing details.",
  "section.required_presence": "Add the missing required section labels in the Corsair sequence.",
  "section.order": "Reorder sections to match the required Corsair flow.",
  "section.label_spelling": "Fix the section heading text so it exactly matches the required heading.",
  "section.labels_all_caps": "Make section labels fully uppercase.",
  "section.headers_bold": "Apply bold formatting to every section label.",
  "section.divider_rule": "Add a bottom divider rule directly beneath each section header.",
  "section.reverse_chronological_order": "Move entries so each section runs newest to oldest. Check Education, Professional Experience, and Leadership separately.",
  "entry.date_right_tab": "Use one right-aligned tab stop for dates instead of spacing them manually.",
  "entry.date_range_en_dash": "Use an en dash between date ranges, like January 2026 – Present, instead of a keyboard hyphen.",
  "entry.date_range_valid": "Correct the date range so the end date is valid and comes after the start date.",
  "entry.organization_bold": "Apply bold formatting to the organization or institution at the start of the entry.",
  "entry.role_italic": "Italicize the role, title, or program descriptor before the date tab.",
  "entry.location_present": "Add City, ST to the entry line before the date.",
  "paragraph.no_consecutive_blank_lines": "Remove extra blank paragraphs and use paragraph spacing instead.",
  "paragraph.no_leading_spaces": "Delete literal leading spaces and use paragraph indentation.",
  "paragraph.no_manual_alignment_spaces": "Delete repeated spaces and use Word tab stops, paragraph alignment, or indentation so the line stays stable after edits.",
  "paragraph.tab_space_alignment_hacks": "Delete the spaces around tabs and use one tab with a saved tab stop instead.",
  "paragraph.excessive_alignment_tabs": "Replace repeated tab presses with one tab and a saved tab stop.",
  "paragraph.tabs_require_defined_stops": "If this tab is meant to align text, add a tab stop in Word's ruler or paragraph settings.",
  "paragraph.right_tab_consistency": "Use the same right tab stop position across date-aligned lines.",
  "paragraph.body_alignment_consistency": "Keep bullet paragraph alignment consistent across the document.",
  "header.contact_spacing_hack": "The header may look aligned, but rebuild it with Word tab stops or paragraph alignment so phone, email, and locations do not drift.",
  "entry.date_alignment_spacing_hack": "The date may look aligned, but delete the space padding and use a right-aligned tab stop.",
  "bullet.indent_consistency": "Use a 0.25in bullet position with the text starting at 0.5in. Intentional sub-bullets can be indented farther in.",
  "typography.single_font_family": "Use one font family across the document.",
  "typography.body_font_size_consistency": "Normalize body copy to one 10-12pt size.",
  "typography.no_unauthorized_inline_emphasis": "Remove bold or italic emphasis that is not part of the target visual hierarchy.",
};

function setSelectedFile(file) {
  if (!file) {
    selectedFile = null;
    fileTitle.textContent = "Choose a resume file";
    fileDetail.textContent = "or drop a .docx here";
    submitButton.disabled = true;
    return;
  }

  selectedFile = file;
  fileTitle.textContent = file.name;
  fileDetail.textContent = `${formatBytes(file.size)} selected`;
  submitButton.disabled = !file.name.toLowerCase().endsWith(".docx");
  statusLine.textContent = submitButton.disabled
    ? "Only DOCX files are supported in this draft checker."
    : "Ready to run a format audit.";
}

function formatBytes(bytes) {
  if (!bytes) return "0 KB";
  const kb = bytes / 1024;
  if (kb < 1024) return `${Math.round(kb)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading || !selectedFile;
  submitButton.textContent = isLoading ? "Auditing document..." : "Run format audit";
  statusLine.textContent = isLoading
    ? "Reading DOCX structure, adding Word comments, and preparing the preview."
    : statusLine.textContent;
}

function updateScore(score) {
  scoreRing.style.setProperty("--score", String(score));
  scoreValue.textContent = String(score);
}

function severityCounts(violations) {
  return violations.reduce(
    (counts, item) => {
      counts[item.severity] = (counts[item.severity] || 0) + 1;
      return counts;
    },
    { critical: 0, major: 0, minor: 0 }
  );
}

function renderResult(payload) {
  currentPayload = payload;
  const result = payload.result;
  const violations = result.violations || [];
  const counts = severityCounts(violations);

  updateScore(result.score);
  resultTitle.textContent = payload.source.filename;
  const visualScore = result.visual_compliance_score ?? result.score;
  const structuralScore = result.structural_quality_score ?? result.score;
  resultCopy.textContent = violations.length
    ? `${violations.length} formatting issue${violations.length === 1 ? "" : "s"} found. Visual ${visualScore}; structure ${structuralScore}; overall ${result.score}.`
    : `No draft formatting violations found. Visual ${visualScore}; structure ${structuralScore}; overall ${result.score}.`;

  countEls.critical.textContent = counts.critical;
  countEls.major.textContent = counts.major;
  countEls.minor.textContent = counts.minor;
  countEls.penalty.textContent = result.total_penalty;

  violationPill.textContent = violations.length ? `${violations.length} found` : "Clean";
  renderViolations(violations);
  renderDocumentPreview(payload, violations);
  statusLine.textContent = "Audit complete.";
}

async function analyzeFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch("/api/analyze", {
    method: "POST",
    body: formData,
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "The audit request failed.");
  }
  return payload;
}

function loadAuditHistory() {
  try {
    const parsed = JSON.parse(localStorage.getItem(HISTORY_STORAGE_KEY) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveAuditHistory() {
  localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(auditHistory.slice(0, 100)));
}

function auditId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function upsertAudit(item) {
  const filename = item.payload.source.filename;
  auditHistory = [
    item,
    ...auditHistory.filter((candidate) => candidate.payload.source.filename !== filename),
  ];
}

function errorAudit(filename, error) {
  return {
    id: auditId(),
    error: error?.message || "Audit failed.",
    payload: {
      source: { filename },
      result: { score: null, total_penalty: 0, violations: [] },
      preview: [],
    },
  };
}

function rememberAudit(payload) {
  upsertAudit({ id: auditId(), payload });
  saveAuditHistory();
  renderReviewerDashboard();
}

async function mapWithConcurrency(items, limit, worker) {
  const results = new Array(items.length);
  let nextIndex = 0;
  const runners = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (nextIndex < items.length) {
      const currentIndex = nextIndex;
      nextIndex += 1;
      results[currentIndex] = await worker(items[currentIndex], currentIndex);
    }
  });
  await Promise.all(runners);
  return results;
}

function renderViolations(violations) {
  if (!violations.length) {
    violationList.innerHTML = '<div class="empty-state">No suggestions needed for the current draft checks.</div>';
    return;
  }

  violationList.innerHTML = violations
    .map((violation, index) => {
      const evidence = evidenceItems(violation);
      const shownEvidence = evidence.slice(0, 3);
      const moreCount = Math.max(0, evidence.length - shownEvidence.length);
      const evidenceMarkup = shownEvidence.length
        ? `<ul class="evidence-list">${shownEvidence.map((item) => evidenceRow(item)).join("")}</ul>`
        : "";
      const moreMarkup = moreCount
        ? `<p class="more-evidence">+${moreCount} more location${moreCount === 1 ? "" : "s"} flagged</p>`
        : "";

      return `
        <article class="violation ${escapeHtml(violation.severity)}" data-issue-index="${index}">
          <div class="violation-main">
            <div class="violation-top">
              <h3>${escapeHtml(ruleLabels[violation.rule_id] || violation.rule_id)}</h3>
              <span class="severity ${escapeHtml(violation.severity)}">${escapeHtml(violation.severity)}</span>
            </div>
            <p>${escapeHtml(violation.message)}</p>
            <p class="fix-guidance">${escapeHtml(fixGuidance[violation.rule_id] || "Review the highlighted formatting evidence and rebuild it with stable Word formatting.")}</p>
          </div>
          ${evidenceMarkup}
          ${moreMarkup}
        </article>
      `;
    })
    .join("");

  document.querySelectorAll(".violation").forEach((card) => {
    card.addEventListener("mouseenter", () => setActiveIssue(card.dataset.issueIndex));
    card.addEventListener("mouseleave", clearActiveIssue);
    card.addEventListener("focusin", () => setActiveIssue(card.dataset.issueIndex));
    card.addEventListener("focusout", clearActiveIssue);
    card.addEventListener("click", () => {
      setActiveIssue(card.dataset.issueIndex);
      document.querySelector(`[data-issue-line="${card.dataset.issueIndex}"]`)?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    });
  });
}

function evidenceItems(violation) {
  const evidence = violation.evidence || {};
  if (Array.isArray(evidence.paragraphs)) {
    return evidence.paragraphs.map((paragraph) => ({
      label: `P${paragraph.index}`,
      text: cleanEvidenceText(paragraph.text),
      rawText: displayEvidenceText(paragraph.text),
      paragraphIndex: paragraph.index,
    }));
  }
  if (evidence.paragraph) {
    return [{
      label: `P${evidence.paragraph.index}`,
      text: cleanEvidenceText(evidence.paragraph.text),
      rawText: displayEvidenceText(evidence.paragraph.text),
      paragraphIndex: evidence.paragraph.index,
    }];
  }
  if (evidence.detected_addresses) {
    return [{ label: "Header", text: `Detected addresses: ${evidence.detected_addresses.join(", ") || "none"}` }];
  }
  if (evidence.fonts) {
    return [{ label: "Fonts", text: Object.keys(evidence.fonts).join(", ") }];
  }
  if (evidence.body_sizes_pt) {
    return [{ label: "Sizes", text: `${evidence.body_sizes_pt.join(", ")} pt` }];
  }
  return [];
}

function evidenceRow(item) {
  return `
    <li>
      <span class="evidence-label">${escapeHtml(item.label)}</span>
      <span class="evidence-text">${escapeHtml(item.text || "No text snippet available")}</span>
    </li>
  `;
}

function cleanEvidenceText(text) {
  return String(text || "")
    .replaceAll("\\t", " [tab] ")
    .replace(/\t/g, " [tab] ")
    .replace(/\s+/g, " ")
    .trim();
}

function displayEvidenceText(text) {
  return String(text || "")
    .replaceAll("\\t", "\t")
    .replace(/\t/g, " [tab] ")
    .replace(/\s+$/g, "");
}

function previewText(text) {
  return String(text || "")
    .replace(/\t/g, "    ")
    .replace(/\s+$/g, "");
}

function renderDocumentPreview(payload, violations) {
  const officeViewerOpen = payload.document_links?.office_viewer_open;
  const issueCount = violations.length;

  resumePage.innerHTML = `
    ${officeViewerOpen ? `
      <div class="office-preview-redirect">
        <span class="section-kicker">Annotated Word preview</span>
        <h3>Opening Microsoft Viewer</h3>
        <p>${issueCount ? `${issueCount} Corsair Standard comment${issueCount === 1 ? "" : "s"} added to a copied DOCX.` : "Clean DOCX copy ready."}</p>
        <p class="muted-note">The annotated preview opens in a separate tab so this audit stays available.</p>
        <a class="docx-button" href="${escapeHtml(officeViewerOpen)}">Open annotated preview</a>
      </div>
    ` : `
      <div class="preview-empty">
        Microsoft Viewer preview needs a public DOCX URL. Start the Cloudflare tunnel and restart the server with PUBLIC_BASE_URL.
      </div>
    `}
  `;
}

function buildStructureOutline(sections, violations) {
  const sortedSections = [...sections].sort((a, b) => a.paragraph_index - b.paragraph_index);
  const rows = { unsectioned: [] };
  sortedSections.forEach((section) => {
    rows[section.name] = [];
  });

  violations.forEach((violation, issueIndex) => {
    evidenceItems(violation).forEach((item) => {
      const row = {
        issueIndex,
        severity: violation.severity,
        ruleId: violation.rule_id,
        title: ruleLabels[violation.rule_id] || violation.rule_id,
        message: violation.message,
        text: item.text,
        rawText: item.rawText || item.text,
        paragraphIndex: item.paragraphIndex,
      };
      const section = sectionForParagraph(sortedSections, item.paragraphIndex);
      if (section) rows[section.name].push(row);
      else rows.unsectioned.push(row);
    });
  });

  Object.keys(rows).forEach((key) => {
    rows[key] = dedupeStructureRows(rows[key]);
  });
  return rows;
}

function sectionForParagraph(sections, paragraphIndex) {
  if (!Number.isFinite(paragraphIndex)) return null;
  return sections
    .filter((section) => section.paragraph_index <= paragraphIndex)
    .sort((a, b) => b.paragraph_index - a.paragraph_index)[0] || null;
}

function dedupeStructureRows(rows) {
  const seen = new Set();
  return rows.filter((row) => {
    const key = `${row.paragraphIndex}:${row.ruleId}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function sectionOutlineItem(section, outlineRows) {
  const rows = outlineRows[section.name] || [];
  const status = rows.length ? `${rows.length} issue${rows.length === 1 ? "" : "s"}` : "clear";
  return `
    <li class="section-outline-item ${rows.length ? "has-issues" : "is-clear"}">
      <div class="section-outline-head">
        <span>${escapeHtml(section.name)}</span>
        <small>${escapeHtml(status)}</small>
      </div>
      ${rows.length ? `<div class="structure-issues">${rows.map(structureIssueRow).join("")}</div>` : ""}
    </li>
  `;
}

function structureIssueRow(row) {
  return `
    <button class="structure-issue ${escapeHtml(row.severity)}" type="button" data-issue-line="${row.issueIndex}">
      <span class="severity ${escapeHtml(row.severity)}">${escapeHtml(row.severity)}</span>
      <strong>${escapeHtml(row.title)}</strong>
      <small>${Number.isFinite(row.paragraphIndex) ? `P${row.paragraphIndex}` : "Document"}</small>
      ${row.rawText ? `<p>${renderEvidenceMarkup(row.rawText, row.title)}</p>` : ""}
    </button>
  `;
}

function shortIssueLabel(label) {
  return label
    .replace("Tabs use defined stops", "Tab stop")
    .replace("Entry dates right-aligned", "Date align")
    .replace("No manual alignment spaces", "Manual spaces")
    .replace("Dual address in header", "Header address")
    .replace("Name centered on top line", "Name center")
    .replace("First-level bullet indent", "Bullet indent");
}

function renderEvidenceMarkup(text, label = "") {
  const escaped = escapeHtml(text || "");
  const hasTabIssue = /tab|date|contact/i.test(label);
  const hasSpaceIssue = /space|leading/i.test(label);

  if (hasTabIssue && / {4,}/.test(text)) {
    return escaped.replace(/ {4,}/g, (match) => `<span class="format-mark tab-gap">${"&nbsp;".repeat(Math.min(match.length, 8))}</span>`);
  }

  if (hasSpaceIssue && /^\s+/.test(text)) {
    return escaped.replace(/^ +/, (match) => `<span class="format-mark leading-gap">${"&nbsp;".repeat(match.length)}</span>`);
  }

  return escaped;
}

function highestPriorityIssue(issues) {
  const rank = { critical: 3, major: 2, minor: 1 };
  return [...issues].sort((a, b) => (rank[b.severity] || 0) - (rank[a.severity] || 0))[0];
}

function setActiveIssue(issueIndex) {
  document.querySelectorAll(".structure-issue, .violation").forEach((node) => {
    node.classList.toggle("is-active", node.dataset.issueIndex === String(issueIndex));
    node.classList.toggle("is-active", node.dataset.issueLine === String(issueIndex));
  });
}

function clearActiveIssue() {
  document.querySelectorAll(".structure-issue, .violation").forEach((node) => {
    node.classList.remove("is-active");
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

fileInput.addEventListener("change", () => {
  setSelectedFile(fileInput.files[0] || null);
});

fileInput.addEventListener("click", () => {
  fileInput.value = "";
});

["dragenter", "dragover", "drop"].forEach((eventName) => {
  document.addEventListener(eventName, (event) => {
    if (event.dataTransfer?.types?.includes("Files")) {
      event.preventDefault();
    }
  });
});

dropzone.addEventListener("dragenter", (event) => {
  event.preventDefault();
  dropzone.classList.add("is-dragging");
});

dropzone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropzone.classList.add("is-dragging");
});

dropzone.addEventListener("dragleave", (event) => {
  if (event.relatedTarget && dropzone.contains(event.relatedTarget)) return;
  dropzone.classList.remove("is-dragging");
});

dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropzone.classList.remove("is-dragging");
  const files = [...event.dataTransfer.files];
  const file = files.find((item) => item.name.toLowerCase().endsWith(".docx")) || files[0];
  if (!file) {
    setSelectedFile(null);
    statusLine.textContent = "Drop a DOCX file to run a format audit.";
    return;
  }

  setSelectedFile(file);
  try {
    const transfer = new DataTransfer();
    transfer.items.add(file);
    fileInput.files = transfer.files;
  } catch {
    // Some browsers block assigning dropped files back to the input.
    // The app uses selectedFile above, so the upload still works.
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = selectedFile || fileInput.files[0];
  if (!file) {
    statusLine.textContent = "Choose or drop a DOCX file first.";
    return;
  }
  if (!file.name.toLowerCase().endsWith(".docx")) {
    statusLine.textContent = "Only DOCX files are supported in this draft checker.";
    return;
  }

  pendingViewerWindow = window.open("about:blank", "_blank");
  if (pendingViewerWindow) {
    pendingViewerWindow.document.write(
      "<p style='font-family: system-ui, sans-serif; padding: 24px;'>Preparing annotated Microsoft Word preview...</p>"
    );
  }

  setLoading(true);
  try {
    const payload = await analyzeFile(file);
    rememberAudit(payload);
    renderResult(payload);
    const viewerUrl = payload.document_links?.office_viewer_open;
    if (viewerUrl) {
      if (pendingViewerWindow) {
        pendingViewerWindow.location.href = viewerUrl;
        pendingViewerWindow.focus();
        statusLine.textContent = "Audit complete. Annotated Word preview opened in a separate tab.";
      } else {
        statusLine.textContent = "Audit complete. Use the preview fallback link to open the annotated Word document.";
      }
    }
  } catch (error) {
    if (pendingViewerWindow) pendingViewerWindow.close();
    statusLine.textContent = error.message;
    resultTitle.textContent = "Audit failed";
    resultCopy.textContent = "The backend returned an error before completing the format check.";
  } finally {
    pendingViewerWindow = null;
    setLoading(false);
  }
});

modeTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    const target = tab.dataset.view;
    modeTabs.forEach((item) => item.classList.toggle("is-active", item === tab));
    views.forEach((view) => view.classList.toggle("is-active", view.id === target));
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
});

batchInput.addEventListener("change", async () => {
  const files = [...batchInput.files].filter((file) => file.name.toLowerCase().endsWith(".docx"));
  if (!files.length) return;

  setReviewerBusy(true, `Auditing ${files.length} file${files.length === 1 ? "" : "s"}...`);
  const results = await mapWithConcurrency(files, 4, async (file) => {
    try {
      return { ok: true, file, payload: await analyzeFile(file) };
    } catch (error) {
      return { ok: false, file, error };
    }
  });

  for (const result of results) {
    if (result.ok) {
      upsertAudit({ id: auditId(), payload: result.payload });
    } else {
      upsertAudit(errorAudit(result.file.name, result.error));
    }
  }
  saveAuditHistory();
  renderReviewerDashboard();
  setReviewerBusy(false);
  batchInput.value = "";
});

filterTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    activeFilter = tab.dataset.filter;
    filterTabs.forEach((item) => item.classList.toggle("is-active", item === tab));
    renderReviewerDashboard();
  });
});

exportCsvButton.addEventListener("click", () => {
  const rows = [
    ["filename", "score", "issues", "critical", "major", "minor", "status"],
    ...auditHistory.map((item) => {
      const payload = item.payload;
      const violations = payload.result.violations || [];
      const counts = severityCounts(violations);
      const status = applicantStatus(payload.result.score, item.error);
      return [
        payload.source.filename,
        item.error ? "" : payload.result.score,
        violations.length,
        counts.critical,
        counts.major,
        counts.minor,
        status.label,
      ];
    }),
  ];
  const csv = rows.map((row) => row.map(csvCell).join(",")).join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "corsair-format-audit.csv";
  link.click();
  URL.revokeObjectURL(url);
});

function setReviewerBusy(isBusy, message = "") {
  const label = document.querySelector(".secondary-upload");
  label.classList.toggle("is-busy", isBusy);
  label.childNodes[0].textContent = isBusy ? message : "Upload resumes";
}

function renderReviewerDashboard() {
  const total = auditHistory.length;
  const scored = auditHistory
    .filter((item) => !item.error && Number.isFinite(item.payload.result.score))
    .map((item) => item.payload.result.score);
  const average = scored.length ? Math.round(scored.reduce((sum, score) => sum + score, 0) / scored.length) : null;
  const statuses = auditHistory.map((item) => applicantStatus(item.payload.result.score, item.error).key);
  const completedTotal = statuses.filter((status) => status !== "error").length;
  const pass = statuses.filter((status) => status === "pass").length;
  const fail = statuses.filter((status) => status === "fail").length;
  const review = statuses.filter((status) => status === "review").length;

  dashboardEls.total.textContent = total;
  dashboardEls.average.textContent = average ?? "--";
  dashboardEls.passRate.textContent = completedTotal ? `${Math.round((pass / completedTotal) * 100)}%` : "--";
  dashboardEls.review.textContent = review;
  dashboardEls.all.textContent = `(${total})`;
  dashboardEls.pass.textContent = `(${pass})`;
  dashboardEls.fail.textContent = `(${fail})`;
  dashboardEls.reviewFilter.textContent = `(${review})`;
  exportCsvButton.disabled = !total;

  const filtered = auditHistory.filter((item) => {
    if (activeFilter === "all") return true;
    return applicantStatus(item.payload.result.score, item.error).key === activeFilter;
  });

  applicantTable.innerHTML = `
    <div class="table-header">
      <span>Applicant file</span>
      <span>Score</span>
      <span>Issues</span>
      <span>Status</span>
    </div>
    ${filtered.length ? filtered.map(applicantRow).join("") : '<div class="empty-state">No files match this filter.</div>'}
  `;

  applicantTable.querySelectorAll(".applicant-row").forEach((row) => {
    row.addEventListener("click", () => {
      const item = auditHistory.find((candidate) => candidate.id === row.dataset.auditId);
      if (!item || item.error) return;
      renderResult(item.payload);
      document.querySelector('[data-view="student-view"]').click();
      document.querySelector("#student-view").scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

function applicantRow(item) {
  const payload = item.payload;
  const result = payload.result;
  const status = applicantStatus(result.score, item.error);
  const violations = result.violations || [];
  return `
    <button class="applicant-row ${item.error ? "is-error" : ""}" type="button" data-audit-id="${escapeHtml(item.id)}" ${item.error ? "disabled" : ""}>
      <span>
        <strong>${escapeHtml(filenameToName(payload.source.filename))}</strong>
        <small>${escapeHtml(item.error || payload.source.filename)}</small>
      </span>
      <span class="score-cell ${escapeHtml(status.key)}">${item.error ? "--" : result.score}</span>
      <span>${violations.length}</span>
      <span class="status-pill ${escapeHtml(status.key)}">${escapeHtml(status.label)}</span>
    </button>
  `;
}

function applicantStatus(score, error = null) {
  if (error) return { key: "error", label: "Error" };
  if (score >= 90) return { key: "pass", label: "Pass" };
  if (score >= 75) return { key: "review", label: "Review" };
  return { key: "fail", label: "Fail" };
}

function filenameToName(filename) {
  return filename
    .replace(/\.[^.]+$/, "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function csvCell(value) {
  return `"${String(value).replaceAll('"', '""')}"`;
}

renderReviewerDashboard();
