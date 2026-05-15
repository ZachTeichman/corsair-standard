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
const previewEmpty = document.querySelector("#preview-empty");
const debugToggle = document.querySelector("#debug-toggle");
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

let auditHistory = [];
let activeFilter = "all";
let currentPayload = null;
let officeStatus = { configured: false, connected: false };

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
  "header.name_centered_top_line": "Name centered on top line",
  "header.dual_address": "Dual address in header",
  "header.contact_single_row": "Contact info on one row",
  "section.corsair_structure_detected": "Corsair section structure",
  "section.required_presence": "Required sections present",
  "section.order": "Section order",
  "section.labels_all_caps": "Section labels all caps",
  "section.headers_bold": "Section headers bold",
  "section.divider_rule": "Section divider rules",
  "entry.date_right_tab": "Entry dates right-aligned",
  "entry.organization_bold": "Organization names bold",
  "entry.role_italic": "Roles italicized",
  "entry.location_present": "Entry locations present",
  "paragraph.no_consecutive_blank_lines": "No consecutive blank lines",
  "paragraph.no_leading_spaces": "No literal leading spaces",
  "paragraph.no_manual_alignment_spaces": "No manual alignment spaces",
  "paragraph.tab_space_alignment_hacks": "Tabs mixed with space padding",
  "paragraph.excessive_alignment_tabs": "Excessive tab alignment",
  "paragraph.tabs_require_defined_stops": "Tabs use defined stops",
  "paragraph.right_tab_consistency": "Right tab consistency",
  "paragraph.body_alignment_consistency": "Body alignment consistency",
  "header.contact_spacing_hack": "Header spacing hack",
  "entry.date_alignment_spacing_hack": "Date spacing hack",
  "bullet.indent_consistency": "Bullet indent consistency",
  "bullet.no_nested_bullets": "No nested bullets",
  "bullet.single_line_length": "Bullet length risk",
  "typography.single_font_family": "Single font family",
  "typography.body_font_size_consistency": "Body font size consistency",
  "typography.no_unauthorized_inline_emphasis": "No unauthorized emphasis",
};

const fixGuidance = {
  "document.margin_range": "Set all page margins to the allowed Corsair range and keep them symmetric.",
  "layout.no_tables": "Remove layout tables and rebuild the content as normal Word paragraphs.",
  "layout.no_textboxes": "Move floating text box content into regular document paragraphs.",
  "header.name_centered_top_line": "Place the name on the first visible line using the canonical centered header setup.",
  "header.dual_address": "Put exactly two city/state addresses in the header contact area.",
  "header.contact_single_row": "Keep phone, email, and both locations on one tab-separated contact row.",
  "section.corsair_structure_detected": "Restore the canonical Corsair section structure before auditing details.",
  "section.required_presence": "Add the missing required section labels in the Corsair sequence.",
  "section.order": "Reorder sections to match the required Corsair flow.",
  "section.labels_all_caps": "Make section labels fully uppercase.",
  "section.headers_bold": "Apply bold formatting to every section label.",
  "section.divider_rule": "Add a bottom divider rule directly beneath each section header.",
  "entry.date_right_tab": "Use one right-aligned tab stop for dates instead of spacing them manually.",
  "entry.organization_bold": "Apply bold formatting to the organization or institution at the start of the entry.",
  "entry.role_italic": "Italicize the role, title, or program descriptor before the date tab.",
  "entry.location_present": "Add City, ST to the entry line before the date.",
  "paragraph.no_consecutive_blank_lines": "Remove extra blank paragraphs and use paragraph spacing instead.",
  "paragraph.no_leading_spaces": "Delete literal leading spaces and use paragraph indentation.",
  "paragraph.no_manual_alignment_spaces": "Replace repeated spaces with tab stops or paragraph formatting.",
  "paragraph.tab_space_alignment_hacks": "Remove space padding around tabs and use defined tab stops or paragraph settings.",
  "paragraph.excessive_alignment_tabs": "Replace long keyboard-tab runs with a small set of explicit tab stops.",
  "paragraph.tabs_require_defined_stops": "Define tab stops for paragraphs that use tab characters.",
  "paragraph.right_tab_consistency": "Use the same right tab stop position across date-aligned lines.",
  "paragraph.body_alignment_consistency": "Keep bullet paragraph alignment consistent across the document.",
  "header.contact_spacing_hack": "Rebuild the header contact row with structured tabs/tab stops, not space padding.",
  "entry.date_alignment_spacing_hack": "Use a clean right-aligned tab stop for dates instead of spaces mixed with tabs.",
  "bullet.indent_consistency": "Use one bullet indent and hanging indent pattern throughout.",
  "bullet.no_nested_bullets": "Flatten nested bullet levels into the standard Corsair bullet level.",
  "bullet.single_line_length": "Tighten long bullets or adjust spacing so they fit the expected line length.",
  "typography.single_font_family": "Use one font family across the document.",
  "typography.body_font_size_consistency": "Normalize body copy to one 10-12pt size.",
  "typography.no_unauthorized_inline_emphasis": "Remove bold or italic emphasis that is not part of the template hierarchy.",
};

function setSelectedFile(file) {
  if (!file) {
    fileTitle.textContent = "Choose a resume file";
    fileDetail.textContent = "or drop a .docx here";
    submitButton.disabled = true;
    return;
  }

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
  submitButton.disabled = isLoading || !fileInput.files.length;
  submitButton.textContent = isLoading ? "Auditing document..." : "Run format audit";
  statusLine.textContent = isLoading
    ? "Reading DOCX structure and checking deterministic formatting rules."
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

function rememberAudit(payload) {
  const filename = payload.source.filename;
  auditHistory = [
    { id: `${Date.now()}-${Math.random().toString(16).slice(2)}`, payload },
    ...auditHistory.filter((item) => item.payload.source.filename !== filename),
  ];
  renderReviewerDashboard();
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
            <p class="fix-guidance">${escapeHtml(fixGuidance[violation.rule_id] || "Review the highlighted formatting evidence and restore the canonical template formatting.")}</p>
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
      paragraphIndex: paragraph.index,
    }));
  }
  if (evidence.paragraph) {
    return [{
      label: `P${evidence.paragraph.index}`,
      text: cleanEvidenceText(evidence.paragraph.text),
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

function previewText(text) {
  return String(text || "")
    .replace(/\t/g, "    ")
    .replace(/\s+$/g, "");
}

function renderDocumentPreview(payload, violations) {
  const originalDocx = payload.document_links?.original_docx;
  const uploadId = payload.document_links?.upload_id;
  const officePreview = payload.document_links?.office_preview;
  resumePage.innerHTML = `
    <div class="docx-native-card">
      <span class="section-kicker">Word-native document</span>
      <h3>${officePreview?.get_url ? "Office preview ready" : "Preview requires Microsoft 365"}</h3>
      <p>
        DOCX rendering is not simulated in the browser. Use Microsoft Word or Office Online
        for the high-fidelity layout view.
      </p>
      <div class="docx-actions">
        ${originalDocx ? `<a class="docx-button" href="${escapeHtml(originalDocx)}">Download DOCX</a>` : ""}
        ${officePreview?.get_url ? `<a class="docx-button secondary" href="${escapeHtml(officePreview.get_url)}" target="_blank" rel="noreferrer">Open Office preview</a>` : ""}
        ${!officePreview?.get_url && officeStatus.connected && uploadId ? `<button class="docx-button secondary" type="button" id="office-preview-button">Create Office preview</button>` : ""}
        ${!officeStatus.connected ? `<button class="docx-button secondary" type="button" id="office-connect-button">${officeStatus.configured ? "Connect Microsoft 365" : "Microsoft 365 not configured"}</button>` : ""}
        <span>${officeStatus.connected ? "Connected to Microsoft 365." : "Office preview uploads the DOCX to the signed-in user’s OneDrive."}</span>
      </div>
    </div>
  `;
}

async function refreshOfficeStatus() {
  try {
    const response = await fetch("/api/office/status");
    officeStatus = await response.json();
  } catch {
    officeStatus = { configured: false, connected: false };
  }
}

async function connectOffice() {
  const response = await fetch("/api/office/connect");
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Microsoft 365 is not configured.");
  }
  window.open(payload.auth_url, "_blank", "noopener,noreferrer");
}

async function createOfficePreview() {
  const uploadId = currentPayload?.document_links?.upload_id;
  if (!uploadId) return;
  statusLine.textContent = "Requesting Microsoft Office preview...";
  const response = await fetch(`/api/uploads/${uploadId}/office-preview`, { method: "POST" });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Microsoft Office preview failed.");
  }
  currentPayload.document_links.office_preview = payload.preview;
  currentPayload.document_links.office_online = payload.preview?.get_url || null;
  renderDocumentPreview(currentPayload, currentPayload.result?.violations || []);
  statusLine.textContent = "Microsoft Office preview ready.";
}

function renderHighlightMarkup(mark) {
  const y = Number(mark.y) + Number(mark.height) - 0.4;
  return `
    <button
      class="render-highlight ${escapeHtml(mark.severity)}"
      type="button"
      data-issue-line="${mark.issue_index}"
      style="left:${mark.x}%; top:${y}%; width:${mark.width}%; height:${Math.max(0.8, mark.height * 0.22)}%;"
      aria-label="Formatting issue"
    ></button>
  `;
}

function renderIssueOverlay(layout, pageNumber = 1) {
  const blockById = new Map((layout.blocks || []).map((block) => [block.id, block]));
  return (layout.issues || []).slice(0, 7)
    .filter((issue) => (issue.page || 1) === pageNumber)
    .map((issue) => {
      const issueIndex = Number(String(issue.id).replace("issue-", ""));
      const blocks = issue.affectedBlocks
        .map((id) => blockById.get(id))
        .filter(Boolean)
        .filter((block) => block.page === pageNumber)
        .slice(0, 12);
      if (!blocks.length) return "";
      const representative = pickRepresentativeBlock(blocks, issue.geometry);
      const target = userIssueGeometry(issue, blocks, representative);
      return `${renderIssueTarget(issue, issueIndex, target)}${renderIssuePopover(issue, issueIndex, representative)}`;
    })
    .join("");
}

function renderDebugOverlay(layout, pageNumber = 1) {
  return `
    <div class="debug-layer">
      ${(layout.blocks || []).filter((block) => block.page === pageNumber).map((block) => `
        <span
          class="debug-box"
          style="left:${block.x}%; top:${block.y}%; width:${block.width}%; height:${block.height}%;"
          title="${escapeHtml(block.id)}"
        ></span>
      `).join("")}
    </div>
  `;
}

function unionClientGeometry(blocks) {
  const x0 = Math.min(...blocks.map((block) => block.x));
  const y0 = Math.min(...blocks.map((block) => block.y));
  const x1 = Math.max(...blocks.map((block) => block.x + block.width));
  const y1 = Math.max(...blocks.map((block) => block.y + block.height));
  return {
    x: x0,
    y: y0,
    width: x1 - x0,
    height: y1 - y0,
  };
}

function pickRepresentativeBlock(blocks, fallback) {
  if (!blocks.length) return fallback || {};
  return blocks
    .slice()
    .sort((a, b) => (a.y - b.y) || (a.x - b.x))[0];
}

function userIssueGeometry(issue, blocks, representative) {
  if (!blocks.length) return issue.geometry || representative || {};
  if (["bullet_format", "indentation"].includes(issue.category)) {
    return clampGeometry(unionClientGeometry(blocks), 18);
  }
  if (issue.category === "spacing" && issue.geometry?.width && issue.geometry?.height) {
    return issue.geometry;
  }
  return representative;
}

function clampGeometry(geometry, maxHeight) {
  return {
    ...geometry,
    height: Math.min(geometry.height, maxHeight),
  };
}

function renderIssueTarget(issue, issueIndex, geometry) {
  if (!geometry.width || !geometry.height) return "";
  return `
    <button
      class="issue-target ${escapeHtml(issue.severity)}"
      type="button"
      data-issue-line="${issueIndex}"
      style="left:${geometry.x}%; top:${geometry.y}%; width:${geometry.width}%; height:${geometry.height}%;"
      aria-label="${escapeHtml(issue.category)} issue region"
      title="${escapeHtml(issue.category)}"
    ></button>
  `;
}

function renderIssuePopover(issue, issueIndex, geometry) {
  if (!geometry.width || !geometry.height) return "";
  const grouped = geometry.width > 55 || geometry.height > 18;
  const x = grouped
    ? 63
    : Math.min(62, Math.max(4, geometry.x + geometry.width + 1.2));
  const y = grouped
    ? Math.min(74, Math.max(5, geometry.y + 1))
    : Math.min(78, Math.max(3, geometry.y + geometry.height + 0.8));
  return `
    <aside
      class="issue-popover ${escapeHtml(issue.severity)}${grouped ? " is-side-card" : ""}"
      data-issue-line="${issueIndex}"
      style="left:${x}%; top:${y}%;"
    >
      <span>${escapeHtml(shortIssuePill(issue))}</span>
      <strong>${escapeHtml(issueTitle(issue))}</strong>
      <p>${escapeHtml(issue.explanation || issue.message)}</p>
    </aside>
  `;
}

function issueTitle(issue) {
  const ruleId = issue.sourceRuleId || "";
  return ruleLabels[ruleId] || issue.message || "Formatting issue";
}

function shortIssuePill(issue) {
  const ruleId = issue.sourceRuleId || "";
  if (ruleId.includes("tab_space") || ruleId.includes("excessive_alignment") || ruleId.includes("spacing_hack")) return "Structure";
  if (ruleId.includes("manual_alignment") || ruleId.includes("tabs_require")) return "Spacing";
  if (ruleId.includes("date")) return "Date align";
  if (ruleId.includes("name_centered")) return "Align";
  if (ruleId.includes("dual_address") || ruleId.includes("contact")) return "Header";
  if (ruleId.includes("bullet.indent")) return "Indent";
  if (ruleId.includes("nested")) return "Bullet";
  if (ruleId.includes("length")) return "Density";
  return {
    manual_formatting: "Spacing",
    date_alignment: "Date",
    bullet_format: "Bullet",
    indentation: "Indent",
    alignment: "Align",
    consistency: "Style",
    spacing: "Space",
    font: "Font",
    section_order: "Order",
    readability: "Density",
  }[issue.category] || "Issue";
}

function buildIssueMap(violations) {
  const map = new Map();
  violations.forEach((violation, issueIndex) => {
    evidenceItems(violation).forEach((item) => {
      if (!Number.isFinite(item.paragraphIndex)) return;
      const current = map.get(item.paragraphIndex) || [];
      current.push({
        issueIndex,
        severity: violation.severity,
        label: ruleLabels[violation.rule_id] || violation.rule_id,
      });
      map.set(item.paragraphIndex, current);
    });
  });
  return map;
}

function previewParagraphMarkup(paragraph, issues) {
  const primaryIssue = highestPriorityIssue(issues);
  const classes = ["preview-line", paragraph.kind];
  const dataAttrs = [];
  if (primaryIssue) {
    classes.push("has-issue", primaryIssue.severity);
    dataAttrs.push(`data-issue-line="${primaryIssue.issueIndex}"`);
  }
  const issueBadges = issues.length
    ? `<span class="line-badges">${issues.slice(0, 2).map((issue) => `
        <span class="line-badge ${escapeHtml(issue.severity)}">${escapeHtml(shortIssueLabel(issue.label))}</span>
      `).join("")}${issues.length > 2 ? `<span class="line-badge more">+${issues.length - 2}</span>` : ""}</span>`
    : "";
  const text = previewText(paragraph.text);

  return `
    <p class="${classes.map(escapeHtml).join(" ")}" ${dataAttrs.join(" ")}>
      <span class="preview-text">${renderMarkedPreviewText(text, issues)}</span>
      ${issueBadges}
    </p>
  `;
}

function shortIssueLabel(label) {
  return label
    .replace("Tabs use defined stops", "Tab stop")
    .replace("Entry dates right-aligned", "Date align")
    .replace("No manual alignment spaces", "Manual spaces")
    .replace("Dual address in header", "Header address")
    .replace("Name centered on top line", "Name center")
    .replace("Bullet indent consistency", "Bullet indent")
    .replace("No nested bullets", "Nested bullet")
    .replace("Bullet length risk", "Line length");
}

function renderMarkedPreviewText(text, issues) {
  const escaped = escapeHtml(text || "");
  if (!issues.length) return escaped;

  const labels = issues.map((issue) => issue.label);
  const hasTabIssue = labels.some((label) => /tab|date|contact/i.test(label));
  const hasSpaceIssue = labels.some((label) => /space|leading/i.test(label));

  if (hasTabIssue && /\s{4,}/.test(text)) {
    return escaped.replace(/ {4,}/g, (match) => `<span class="format-mark tab-gap">${"&nbsp;".repeat(Math.min(match.length, 8))}</span>`);
  }

  if (hasSpaceIssue && /^\s+/.test(text)) {
    return escaped.replace(/^ +/, (match) => `<span class="format-mark leading-gap">${"&nbsp;".repeat(match.length)}</span>`);
  }

  if (text.length > 90) {
    const midpoint = Math.floor(text.length * 0.55);
    const before = escapeHtml(text.slice(0, midpoint));
    const marked = escapeHtml(text.slice(midpoint, Math.min(text.length, midpoint + 36)));
    const after = escapeHtml(text.slice(Math.min(text.length, midpoint + 36)));
    return `${before}<span class="format-mark text-span">${marked}</span>${after}`;
  }

  return `<span class="format-mark text-span">${escaped}</span>`;
}

function highestPriorityIssue(issues) {
  const rank = { critical: 3, major: 2, minor: 1 };
  return [...issues].sort((a, b) => (rank[b.severity] || 0) - (rank[a.severity] || 0))[0];
}

function setActiveIssue(issueIndex) {
  document.querySelectorAll(".preview-line, .render-highlight, .issue-popover, .issue-target, .violation").forEach((node) => {
    node.classList.toggle("is-active", node.dataset.issueIndex === String(issueIndex));
    node.classList.toggle("is-active", node.dataset.issueLine === String(issueIndex));
  });
}

function clearActiveIssue() {
  document.querySelectorAll(".preview-line, .render-highlight, .issue-popover, .issue-target, .violation").forEach((node) => {
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
  setSelectedFile(fileInput.files[0]);
});

dropzone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropzone.classList.add("is-dragging");
});

dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("is-dragging");
});

dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropzone.classList.remove("is-dragging");
  const [file] = event.dataTransfer.files;
  if (!file) return;

  const transfer = new DataTransfer();
  transfer.items.add(file);
  fileInput.files = transfer.files;
  setSelectedFile(file);
});

debugToggle.addEventListener("change", () => {
  resumePage.classList.toggle("show-debug", debugToggle.checked);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = fileInput.files[0];
  if (!file) return;

  setLoading(true);
  try {
    const payload = await analyzeFile(file);
    rememberAudit(payload);
    renderResult(payload);
  } catch (error) {
    statusLine.textContent = error.message;
    resultTitle.textContent = "Audit failed";
    resultCopy.textContent = "The backend returned an error before completing the format check.";
  } finally {
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
  for (const file of files) {
    try {
      rememberAudit(await analyzeFile(file));
    } catch (error) {
      auditHistory = [
        {
          id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
          error: error.message,
          payload: {
            source: { filename: file.name },
            result: { score: 0, total_penalty: 0, violations: [] },
            preview: [],
          },
        },
        ...auditHistory,
      ];
      renderReviewerDashboard();
    }
  }
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
      return [
        payload.source.filename,
        payload.result.score,
        violations.length,
        counts.critical,
        counts.major,
        counts.minor,
        applicantStatus(payload.result.score).label,
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

resumePage.addEventListener("click", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  try {
    if (target.id === "office-connect-button") {
      await connectOffice();
      statusLine.textContent = "Finish Microsoft sign-in, then return here and run Office preview.";
    }
    if (target.id === "office-preview-button") {
      target.setAttribute("disabled", "true");
      target.textContent = "Creating preview...";
      await createOfficePreview();
    }
  } catch (error) {
    statusLine.textContent = error.message;
    if (currentPayload) renderDocumentPreview(currentPayload, currentPayload.result?.violations || []);
  }
});

window.addEventListener("focus", async () => {
  await refreshOfficeStatus();
  if (currentPayload) renderDocumentPreview(currentPayload, currentPayload.result?.violations || []);
});

refreshOfficeStatus();

function setReviewerBusy(isBusy, message = "") {
  const label = document.querySelector(".secondary-upload");
  label.classList.toggle("is-busy", isBusy);
  label.childNodes[0].textContent = isBusy ? message : "Upload resumes";
}

function renderReviewerDashboard() {
  const total = auditHistory.length;
  const scored = auditHistory.map((item) => item.payload.result.score);
  const average = scored.length ? Math.round(scored.reduce((sum, score) => sum + score, 0) / scored.length) : null;
  const statuses = auditHistory.map((item) => applicantStatus(item.payload.result.score).key);
  const pass = statuses.filter((status) => status === "pass").length;
  const fail = statuses.filter((status) => status === "fail").length;
  const review = statuses.filter((status) => status === "review").length;

  dashboardEls.total.textContent = total;
  dashboardEls.average.textContent = average ?? "--";
  dashboardEls.passRate.textContent = total ? `${Math.round((pass / total) * 100)}%` : "--";
  dashboardEls.review.textContent = review;
  dashboardEls.all.textContent = `(${total})`;
  dashboardEls.pass.textContent = `(${pass})`;
  dashboardEls.fail.textContent = `(${fail})`;
  dashboardEls.reviewFilter.textContent = `(${review})`;
  exportCsvButton.disabled = !total;

  const filtered = auditHistory.filter((item) => {
    if (activeFilter === "all") return true;
    return applicantStatus(item.payload.result.score).key === activeFilter;
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
      if (!item) return;
      renderResult(item.payload);
      document.querySelector('[data-view="student-view"]').click();
      document.querySelector("#student-view").scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

function applicantRow(item) {
  const payload = item.payload;
  const result = payload.result;
  const status = applicantStatus(result.score);
  const violations = result.violations || [];
  return `
    <button class="applicant-row" type="button" data-audit-id="${escapeHtml(item.id)}">
      <span>
        <strong>${escapeHtml(filenameToName(payload.source.filename))}</strong>
        <small>${escapeHtml(payload.source.filename)}</small>
      </span>
      <span class="score-cell ${escapeHtml(status.key)}">${result.score}</span>
      <span>${violations.length}</span>
      <span class="status-pill ${escapeHtml(status.key)}">${escapeHtml(status.label)}</span>
    </button>
  `;
}

function applicantStatus(score) {
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
