import { useState, useRef, useCallback } from "react"; 
 
// ─── DESIGN TOKENS 
const C = { 
  bg:        "#0d0f11", 
  surface:   "#111315", 
  surface2:  "#1a1d21", 
  border:    "#1e2228", 
  border2:   "#2a2d33", 
  text:      "#F5F5F2", 
  textMid:   "#8a8fa0", 
  textDim:   "#5a6272", 
  textFaint: "#3a3f4e", 
  red:       "#9E1B32", 
  redDim:    "#6b1222", 
  gold:      "#8C7853", 
  // violation overlay colors — muted, institutional 
  vioHigh:   "rgba(248, 113, 113, 0.18)",  // critical 
  vioMed:    "rgba(245, 158, 11, 0.15)",   // major 
  vioLow:    "rgba(96, 165, 250, 0.12)",   // minor 
  vioBorder: { 
    critical: "rgba(248,113,113,0.5)", 
    major:    "rgba(245,158,11,0.45)", 
    minor:    "rgba(96,165,250,0.35)", 
  }, 

}; 
 
// ─── RUBRIC 
// ALL checks are purely formatting / structural. Zero semantic evaluation. 
// conf: confidence level when scoring from PDF (visual) vs DOCX (XML) 
// zone: which region of the resume preview this maps to for heatmap 
// pdfConf: confidence when source is PDF 
// docxConf: confidence when source is DOCX 
 
const RUBRIC = [ 
  // ── HEADER 
  { 
    id: "H1", cat: "Header", pts: 5, sev: "critical", 
    label: "Name centered on top line", 
    desc:  "The applicant's full name must appear on the first line, horizontally centered, with no other text on that line.",
    docxConf: "HIGH", pdfConf: "HIGH", 
    zone: "header-name", 
    heatmapNote: "Name line alignment", 
  }, 
  { 
    id: "H2", cat: "Header", pts: 10, sev: "critical", 
    label: "Dual address in header", 
    desc:  "Corsair format requires exactly two city/state addresses in the contact line: one home address and one Athens/school address. Only one address detected.",

    docxConf: "HIGH", pdfConf: "MEDIUM", 
    zone: "header-contact", 
    heatmapNote: "Missing second address", 
  }, 
  { 
    id: "H3", cat: "Header", pts: 5, sev: "major", 
    label: "Contact info on single row", 
    desc:  "Phone, email, and both city/state locations must appear on one horizontal line separated by tab stops — not stacked across multiple lines.",
    docxConf: "HIGH", pdfConf: "HIGH", 
    zone: "header-contact", 
    heatmapNote: "Contact line layout", 
  }, 
 
  // ── SECTION HEADERS 
  { 
    id: "S1", cat: "Section Headers", pts: 5, sev: "critical", 
    label: "Section labels fully capitalized", 
    desc:  "Every section header must be fully capitalized (e.g. EDUCATION, PROFESSIONAL EXPERIENCE). Mixed-case headers are a direct rubric violation.",
    docxConf: "HIGH", pdfConf: "HIGH", 
    zone: "section-header", 
    heatmapNote: "Section capitalization", 
  }, 
  { 
    id: "S2", cat: "Section Headers", pts: 5, sev: "major", 

    label: "Section headers bold", 
    desc:  "All section header text must carry bold formatting. Non-bold section headers fail the typography hierarchy requirement.",
    docxConf: "HIGH", pdfConf: "ESTIMATED", 
    zone: "section-header", 
    heatmapNote: "Header bold weight", 
  }, 
  { 
    id: "S3", cat: "Section Headers", pts: 5, sev: "major", 
    label: "Horizontal rule beneath each header", 
    desc:  "A full-width horizontal divider rule must appear directly beneath every section header. Missing or partial rules are a layout violation.",
    docxConf: "HIGH", pdfConf: "HIGH", 
    zone: "section-header", 
    heatmapNote: "Missing divider rule", 
  }, 
 
  // ── ENTRY LINES ───────────────────────────────────────────────────────────── 
  { 
    id: "E1", cat: "Entry Lines", pts: 5, sev: "critical", 
    label: "Organization name bold", 
    desc:  "The organization or institution name must be bold at the start of every entry line. Plain-weight org names fail the entry formatting standard.",
    docxConf: "HIGH", pdfConf: "ESTIMATED", 
    zone: "entry-line", 
    heatmapNote: "Org name weight", 
  }, 

  { 
    id: "E2", cat: "Entry Lines", pts: 5, sev: "major", 
    label: "Title or role in italics", 
    desc:  "The position title or degree must appear in italics immediately following the organization name on the same line. Non-italic titles are a formatting violation.",
    docxConf: "HIGH", pdfConf: "ESTIMATED", 
    zone: "entry-line", 
    heatmapNote: "Title italic formatting", 
  }, 
  { 
    id: "E3", cat: "Entry Lines", pts: 5, sev: "major", 
    label: "Date range right-aligned via tab stop", 
    desc:  "Date ranges must be right-aligned to the page margin using a right-aligned tab stop on the same line as the organization name. Left-aligned or floating dates are a violation.",
    docxConf: "HIGH", pdfConf: "HIGH", 
    zone: "entry-date", 
    heatmapNote: "Date alignment", 
  }, 
  { 
    id: "E4", cat: "Entry Lines", pts: 5, sev: "minor", 
    label: "Location present on entry line", 
    desc:  "City, ST must appear on the same line as the organization name. Entries missing location information deviate from Corsair structure.",
    docxConf: "HIGH", pdfConf: "HIGH", 
    zone: "entry-line", 
    heatmapNote: "Missing location", 

  }, 
  { 
    id: "E5", cat: "Entry Lines", pts: 5, sev: "major", 
    label: "Entry indent depth consistent", 
    desc:  "All entry lines across all sections must share identical left indent depth. Variation (e.g. 0.25\" vs 0.5\") indicates template drift or copy-paste errors.",
    docxConf: "HIGH", pdfConf: "MEDIUM", 
    zone: "entry-line", 
    heatmapNote: "Entry indent inconsistency", 
  }, 
 
  // ── BULLET POINTS ─────────────────────────────────────────────────────────── 
  { 
    id: "B1", cat: "Bullets", pts: 5, sev: "critical", 
    label: "Bullet hanging indent uniform", 
    desc:  "All bullet points must use the same hanging indent depth throughout the document. Mixed indent values are among the most common Corsair violations.",
    docxConf: "HIGH", pdfConf: "MEDIUM", 
    zone: "bullets", 
    heatmapNote: "Bullet indent inconsistency", 
  }, 
  { 
    id: "B3", cat: "Bullets", pts: 5, sev: "major", 
    label: "No nested or sub-bullet structure", 
    desc:  "Corsair format is strictly flat. No nested bullets at any level are permitted. Sub- bullets represent a structural deviation.",
    docxConf: "HIGH", pdfConf: "HIGH", 

    zone: "bullets", 
    heatmapNote: "Nested bullet detected", 
  }, 
  { 
    id: "B4", cat: "Bullets", pts: 5, sev: "minor", 
    label: "Bullet line length within range", 
    desc:  "Bullets must not exceed two wrapped lines and must not be fewer than six words. Extremes in either direction indicate spacing or content issues.",
    docxConf: "HIGH", pdfConf: "MEDIUM", 
    zone: "bullets", 
    heatmapNote: "Bullet length out of range", 
  }, 
 
  // ── TYPOGRAPHY 
  { 
    id: "T1", cat: "Typography", pts: 5, sev: "critical", 
    label: "Single font family throughout", 
    desc:  "Only one font family may appear in the document. Mixed fonts (e.g. Times New Roman and Calibri co-occurring) are a direct typography violation.",
    docxConf: "HIGH", pdfConf: "MEDIUM", 
    zone: "typography", 
    heatmapNote: "Mixed font families", 
  }, 
  { 
    id: "T2", cat: "Typography", pts: 5, sev: "major", 
    label: "Body font size consistent", 

    desc:  "All body text must use a uniform point size (10–12pt). Size variation in body copy — even 0.5pt — indicates template inconsistency.",
    docxConf: "HIGH", pdfConf: "MEDIUM", 
    zone: "typography", 
    heatmapNote: "Mixed body font sizes", 
  }, 
  { 
    id: "T3", cat: "Typography", pts: 5, sev: "minor", 
    label: "No unauthorized inline emphasis", 
    desc:  "Bold and italic formatting must only appear in structurally defined positions (org names, titles, section headers). Mid-sentence or arbitrary emphasis is a violation.",
    docxConf: "HIGH", pdfConf: "ESTIMATED", 
    zone: "typography", 
    heatmapNote: "Unauthorized inline emphasis", 
  }, 
 
  // ── PAGE LAYOUT 
  { 
    id: "P2", cat: "Page Layout", pts: 5, sev: "major", 
    label: "Margins symmetric and within range", 
    desc:  "Left, right, top, and bottom margins must be uniform between 0.5\" and 1.0\". Asymmetric or out-of-range margins are a layout violation.",
    docxConf: "HIGH", pdfConf: "HIGH", 
    zone: "margins", 
    heatmapNote: "Margin inconsistency", 
  }, 

]; 
 
const TOTAL_PTS = RUBRIC.reduce((s, r) => s + r.pts, 0); 
 
// ─── HARD REJECT 
const REJECT_MULTI_PAGE = { 
  code: "MULTI_PAGE", 
  title: "Resume exceeds one page", 
  detail: "Corsair format requires a single-page resume without exception. This document contains multiple pages and cannot be evaluated.",
  fix: "Condense content to fit within one page. Remove older entries, tighten bullet points, or reduce inter-section spacing.",
}; 
 
// ─── SCORING ENGINE 
// Deterministic simulation seeded on filename. 
// In production: DOCX → XML parse for exact twip/pt values; PDF → rendered page 
geometry. 
// NO semantic evaluation. Every check is a formatting/structural measurement. 
 
function detectFileType(name) { 
  return name.split(".").pop().toLowerCase() === "pdf" ? "pdf" : "docx"; 
} 
 
function runGateCheck(name) { 

  const lower = name.toLowerCase(); 
  if (lower.includes("2page") || lower.includes("two_page") || lower.includes("pg2") || 
lower.includes("long")) 
    return REJECT_MULTI_PAGE; 
  return null; 
} 
 
function scoreResume(name) { 
  const fileType = detectFileType(name); 
  const gate = runGateCheck(name); 
  if (gate) return { rejected: true, reason: gate, fileType }; 
 
  const seed = name.split("").reduce((a, c) => a + c.charCodeAt(0), 0); 
 
  const issues = [], passing = []; 
 
  RUBRIC.forEach((rule, i) => { 
    // PDF cannot reliably verify these checks — mark unverifiable, not failed 
    const pdfUnverifiable = fileType === "pdf" && ["T1", "E5", "T2", "S2", "E1", "E2", 
"T3"].includes(rule.id); 
    if (pdfUnverifiable) { 
      passing.push({ ...rule, unverified: true, conf: rule.pdfConf }); 
      return; 
    } 
    const threshold = rule.sev === "critical" ? 0.84 : rule.sev === "major" ? 0.71 : 0.53; 
    const roll = ((seed * (i + 7) * 1_234_567 + 99_991) % 100_000) / 100_000; 
    const conf = fileType === "pdf" ? rule.pdfConf : rule.docxConf; 

    if (roll > threshold) { 
      issues.push({ ...rule, conf, detail: getDetail(rule.id, fileType) }); 
    } else { 
      passing.push({ ...rule, conf }); 
    } 
  }); 
 
  const lost  = issues.reduce((s, r) => s + r.pts, 0); 
  const score = Math.max(0, Math.round(((TOTAL_PTS - lost) / TOTAL_PTS) * 100)); 
  return { rejected: false, score, issues, passing, fileType, totalPts: TOTAL_PTS }; 
} 
 
function getDetail(id, src) { 
  const xml = src === "docx" ? " · detected in document XML" : " · detected via layout geometry";
  const vis = " · estimated from rendered page"; 
  const m = { 
    H1:  "Name line is not horizontally centered" + xml, 
    H2:  "Only one city/state string found in header region. Dual address (home + school) is required.",
    H3:  "Contact information spans multiple lines instead of a single tab-separated row" + 
xml, 
    S1:  "One or more section headers contain lowercase characters" + xml, 
    S2:  "Section header detected without bold formatting" + xml, 
    S3:  "Horizontal rule absent beneath one or more section headers" + xml, 
    E1:  "Organization name on one or more entries lacks bold formatting" + xml, 
    E2:  "Role or title on one or more entries lacks italic formatting" + xml, 

    E3:  "Date range on one or more entries is not right-aligned to the margin" + xml, 
    E4:  "City, ST absent from one or more entry lines" + xml, 
    E5:  "Left indent depth varies across entry lines — inconsistent tab stop usage" + xml, 
    B1:  "Hanging indent depth is not uniform across all bullet points" + xml, 
    B3:  "Nested bullet structure detected — Corsair format is strictly flat" + xml, 
    B4:  "One or more bullets exceed two wrapped lines or are under six words" + xml, 
    T1:  "More than one font family detected in document" + xml, 
    T2:  "Body text point size varies — consistent sizing required" + xml, 
    T3:  "Bold or italic formatting detected outside structurally defined positions" + vis, 
    P2:  "Left/right margin values are not symmetric, or fall outside 0.5\"–1.0\" range" + xml, 
  }; 
  return m[id] || "Formatting deviation detected" + xml; 
} 
 
// ─── RESUME PREVIEW DATA (Zachary's resume as canonical Corsair reference) ──── 
// Used to render the simulated document preview for the heatmap. 
const PREVIEW_SECTIONS = [ 
  { 
    type: "header", 
    name: "Zachary Teichman", 
    contact: "(678) 200-6585   ·   Marietta, GA 30068   ·   zach.teichman@gmail.com   ·   Athens, GA 30602",
  }, 
  { 
    type: "section", label: "EDUCATION", 
    entries: [ 

      { org: "The University of Georgia", role: "Terry College of Business", loc: "Athens, GA", 
date: "May 2029", 
        bullets: ["Bachelor of Business Administration in Finance and Real Estate", "GPA: 4.0/4.0  ·  Zell Miller Scholarship, Presidential Scholar"] },
      { org: "George Walton Comprehensive High School", role: "", loc: "Marietta, GA", date: 
"May 2025", 
        bullets: ["GPA: 4.6/4.0  ·  Georgia Certificate of Merit, AP Scholar Award with Distinction"] },
    ] 
  }, 
  { 
    type: "section", label: "PROFESSIONAL EXPERIENCE", 
    entries: [ 
      { org: "Corcoran Classic Living", role: "Real Estate Intern", loc: "Athens, GA", date: "Jan 2026 – Present",
        bullets: ["Support brokerage by managing property signage, lockbox installation, and supervising on-site access for inspectors and vendors", "Maintain accurate property records for 30+ realtors within the local MLS and CRM systems while assisting with public relations"] },
      { org: "Cogent Growth Partners", role: "M&A Support Intern", loc: "Woodstock, GA", date: 
"May – Aug 2025", 
        bullets: ["Streamlined Salesforce M&A database by updating 1,000+ company records, cold calling, and improving deal sourcing accuracy", "Leveraged LinkedIn, ZoomInfo, Lusha, and Gemini to research hundreds of potential acquisition targets"] },
    ] 
  }, 
  { 
    type: "section", label: "LEADERSHIP & RELEVANT EXPERIENCE", 
    entries: [ 

      { org: "Terry Student Consulting", role: "Associate Consultant", loc: "Athens, GA", date: 
"Apr 2026 – Present", 
        bullets: ["Selected as 1 of 40 students from 225 applicants to join a student-run, pro bono consultancy serving local firms"] },
      { org: "Dean William Tate Society", role: "Treasurer", loc: "Athens, GA", date: "Feb 2026 – Present",
        bullets: ["Spearheaded financial tracking by monitoring fundraising revenue and allocating funds to support chapter events"] },
      { org: "The Orion Society", role: "Energy Sector Analyst", loc: "Athens, GA", date: "Sep 2025 – Present",
        bullets: ["Selected as 1 of 42 to a fictitious M&A sell-side group; research and defend energy sector M&A merger recommendations"] },
    ] 
  }, 
]; 
 
// Maps rule IDs to which zones in the preview they visually affect 
// zone format: { sectionIdx, entryIdx (or null for section-level), part } 
const ZONE_MAP = { 
  "H1":  [{ region: "header-name" }], 
  "H2":  [{ region: "header-contact" }], 
  "H3":  [{ region: "header-contact" }], 
  "S1":  [{ region: "section-label", sectionIdx: 1 }], 
  "S2":  [{ region: "section-label", sectionIdx: 2 }], 
  "S3":  [{ region: "section-rule",  sectionIdx: 1 }], 
  "E1":  [{ region: "entry-org",     sectionIdx: 1, entryIdx: 0 }], 
  "E2":  [{ region: "entry-role",    sectionIdx: 1, entryIdx: 1 }], 
  "E3":  [{ region: "entry-date",    sectionIdx: 2, entryIdx: 0 }], 

  "E4":  [{ region: "entry-loc",     sectionIdx: 2, entryIdx: 1 }], 
  "E5":  [{ region: "entry-indent",  sectionIdx: 3, entryIdx: 0 }, { region: "entry-indent", 
sectionIdx: 3, entryIdx: 2 }], 
  "B1":  [{ region: "bullet",        sectionIdx: 2, entryIdx: 0, bulletIdx: 1 }], 
  "B3":  [{ region: "bullet",        sectionIdx: 3, entryIdx: 1, bulletIdx: 0 }], 
  "B4":  [{ region: "bullet",        sectionIdx: 1, entryIdx: 0, bulletIdx: 1 }], 
  "T1":  [{ region: "typography-body" }], 
  "T2":  [{ region: "typography-body" }], 
  "T3":  [{ region: "typography-inline", sectionIdx: 2, entryIdx: 1, bulletIdx: 0 }], 
  "P2":  [{ region: "margin" }], 
}; 
 
// ─── MOCK REVIEWER APPLICANTS 
const MOCK_APPLICANTS = [ 
  { id:1,  name:"Zachary Teichman",  major:"Finance / Real Estate", score:97, 
issueCount:1,  status:"pass",      file:"Teichman_Resume.pdf",   elapsed:"2m",  ungraded:fals
e }, 
  { id:2,  name:"Madison Clarke",    major:"Marketing",             score:81, 
issueCount:4,  status:"pass",      file:"Clarke_Resume.pdf",     elapsed:"5m",  ungraded:false 
}, 
  { id:3,  name:"Jordan Williams",   major:"Accounting",            score:74, 
issueCount:6,  status:"review",    file:"Williams_Resume.pdf",   elapsed:"12m", 
ungraded:false }, 
  { id:4,  name:"Priya Nair",        major:"Management",            score:68, 
issueCount:7,  status:"review",    file:"Nair_Resume.pdf",       elapsed:"18m", ungraded:false 
}, 
  { id:5,  name:"Connor O'Brien",    major:"Finance",               score:52, issueCount:11, 
status:"fail",      file:"OBrien_Resume.pdf",     elapsed:"31m", ungraded:false }, 

  { id:6,  name:"Aisha Johnson",     major:"Real Estate",           score:88, 
issueCount:3,  status:"pass",      file:"Johnson_Resume.pdf",    elapsed:"44m", 
ungraded:false }, 
  { id:7,  name:"Derek Huang",       major:"Finance",               score:61, 
issueCount:9,  status:"fail",      file:"Huang_Resume.pdf",      elapsed:"1h",  ungraded:false }, 
  { id:8,  name:"Samantha Reed",     major:"Economics",             score:91, 
issueCount:2,  status:"pass",      file:"Reed_Resume.pdf",       elapsed:"1h",  ungraded:false }, 
  { id:9,  name:"Tyler Brooks",      major:"Finance",               score:null, issueCount:0, 
status:"ungraded", 
file:"Brooks_Resume.pdf",     elapsed:"2h",  ungraded:true,  ungradedReason:"Resume exceeds one page — does not meet Corsair one-page requirement." },
  { id:10, name:"Leila Mostafavi",   major:"Accounting",            score:null, issueCount:0, 
status:"ungraded", 
file:"Mostafavi_Resume.pdf",  elapsed:"2h",  ungraded:true,  ungradedReason:"No recognizable Corsair section structure detected. Applicant should resubmit using the standard template." },
]; 
 
// ─── ANALYTICS DATA 
const ANALYTICS = { 
  violationFreq: [ 
    { id:"B1", label:"Bullet indent inconsistency",     count:67, pct:82 }, 
    { id:"E3", label:"Date not right-aligned",          count:58, pct:71 }, 
    { id:"T2", label:"Mixed body font sizes",           count:52, pct:64 }, 
    { id:"E5", label:"Entry indent inconsistent",       count:49, pct:60 }, 
    { id:"H2", label:"Missing dual address",            count:41, pct:50 }, 
    { id:"T1", label:"Mixed font families",             count:38, pct:46 }, 
    { id:"S3", label:"Missing section divider rule",    count:35, pct:43 }, 
    { id:"E2", label:"Title not italic",                count:29, pct:35 }, 

  ], 
  scoreDistribution: [ 
    { range:"90–100", count:14 }, 
    { range:"80–89",  count:19 }, 
    { range:"70–79",  count:21 }, 
    { range:"60–69",  count:13 }, 
    { range:"50–59",  count:9  }, 
    { range:"<50",    count:5  }, 
  ], 
  rejectionReasons: [ 
    { reason:"Multi-page resume", count:7  }, 
    { reason:"No Corsair structure detected", count:3  }, 
    { reason:"Non-PDF file (reviewer)", count:2  }, 
  ], 
  avgScore: 74, 
  totalScored: 81, 
  totalRejected: 12, 
  passRate: 40, 
}; 
 
// ─── SHARED UI 
 
const ScoreRing = ({ score, size = 120 }) => { 
  const r = size/2 - 9; 
  const circ = 2 * Math.PI * r; 

  const color = score >= 85 ? "#4ade80" : score >= 65 ? "#f59e0b" : "#f87171"; 
  return ( 
    <div style={{ position:"relative", width:size, height:size, flexShrink:0 }}> 
      <svg width={size} height={size} style={{ transform:"rotate(-90deg)" }}> 
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={C.surface2} strokeWidth="7"/> 
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth="7" 
          strokeDasharray={`${(score/100)*circ} ${circ}`} strokeLinecap="round" 
          style={{ transition:"stroke-dasharray 1.2s cubic-bezier(.4,0,.2,1)" }}/> 
      </svg> 
      <div style={{ position:"absolute", inset:0, display:"flex", flexDirection:"column", 
alignItems:"center", justifyContent:"center" }}> 
        <span style={{ fontSize:size*.21, fontWeight:700, color, fontFamily:"'DM Mono',monospace", letterSpacing:"-1px" }}>{score}</span>
        <span style={{ fontSize:size*.09, color:C.textDim, letterSpacing:".05em", 
textTransform:"uppercase" }}>/ 100</span> 
      </div> 
    </div> 
  ); 
}; 
 
const ConfBadge = ({ conf }) => { 
  const m = { 
    HIGH:      { bg:"#0d1f14", color:"#4ade80",  label:"High confidence"      }, 
    MEDIUM:    { bg:"#1a1a0a", color:"#a3a333",  label:"Medium confidence"    }, 
    ESTIMATED: { bg:"#141826", color:"#6b7fa0",  label:"Estimated visually"   }, 
  }; 
  const s = m[conf] || m.ESTIMATED; 

  return ( 
    <span style={{ background:s.bg, color:s.color, fontSize:10, fontWeight:600, 
      padding:"2px 7px", borderRadius:3, letterSpacing:".05em", textTransform:"uppercase", 
      fontFamily:"'DM Mono',monospace", whiteSpace:"nowrap" }}> 
      {s.label} 
    </span> 
  ); 
}; 
 
const SevBadge = ({ sev }) => { 
  const m = { 
    critical: { bg:"#2d1515", color:"#f87171", label:"Critical" }, 
    major:    { bg:"#2d2015", color:"#f59e0b", label:"Major"    }, 
    minor:    { bg:"#141c2a", color:"#60a5fa", label:"Minor"    }, 
  }; 
  const s = m[sev] || m.minor; 
  return ( 
    <span style={{ background:s.bg, color:s.color, fontSize:10, fontWeight:600, 
      padding:"2px 7px", borderRadius:3, letterSpacing:".06em", textTransform:"uppercase", 
      whiteSpace:"nowrap" }}> 
      {s.label} 
    </span> 
  ); 
}; 
 
const StatusPill = ({ status }) => { 

  const m = { 
    pass:     ["#0d2b1a","#4ade80","Pass"], 
    review:   ["#2d2008","#f59e0b","Review"], 
    fail:     ["#2d0e0e","#f87171","Fail"], 
    ungraded: ["#1a1a1a","#6b7280","Ungraded"], 
  }; 
  const [bg,color,label] = m[status]||m.ungraded; 
  return <span style={{ background:bg, color, fontSize:11, fontWeight:600, 
    padding:"3px 10px", borderRadius:20, letterSpacing:".04em", whiteSpace:"nowrap" 
}}>{label}</span>; 
}; 
 
const FileBadge = ({ type }) => ( 
  <span style={{ 
    background: type==="pdf" ? "#1a1526" : "#0d1f2d", 
    color:      type==="pdf" ? "#a78bfa" : "#38bdf8", 
    fontSize:10, fontWeight:700, padding:"2px 7px", borderRadius:3, 
    letterSpacing:".08em", textTransform:"uppercase", fontFamily:"'DM Mono',monospace", 
  }}>{type}</span> 
); 
 
const ScoreBar = ({ score }) => { 
  if (score===null) return <span style={{ color:C.textFaint, fontSize:12, fontStyle:"italic" 
}}>Ungraded</span>; 
  const color = score>=85?"#4ade80":score>=65?"#f59e0b":"#f87171"; 
  return ( 
    <div style={{ display:"flex", alignItems:"center", gap:8 }}> 

      <div style={{ flex:1, height:3, background:C.surface2, borderRadius:2, overflow:"hidden" 
}}> 
        <div style={{ width:`${score}%`, height:"100%", background:color, borderRadius:2 }}/> 
      </div> 
      <span style={{ color, fontFamily:"'DM Mono',monospace", fontSize:13, fontWeight:600, 
minWidth:26, textAlign:"right" }}>{score}</span> 
    </div> 
  ); 
}; 
 
// ─── HEATMAP PREVIEW 
// Renders a simulated resume document with violation overlays. 
 
const HeatmapPreview = ({ issues }) => { 
  const [hoveredIssue, setHoveredIssue] = useState(null); 
 
  // Build a lookup: region-key → issue 
  const regionIssueMap = {}; 
  issues.forEach(issue => { 
    const zones = ZONE_MAP[issue.id] || []; 
    zones.forEach(z => { 
      const key = z.sectionIdx != null 
        ? `${z.region}-${z.sectionIdx}-${z.entryIdx ?? ""}-${z.bulletIdx ?? ""}` 
        : z.region; 
      regionIssueMap[key] = issue; 
    }); 

  }); 
 
  const getOverlay = (key) => { 
    const issue = regionIssueMap[key]; 
    if (!issue) return null; 
    const isHovered = hoveredIssue?.id === issue.id; 
    const bg = issue.sev === "critical" ? C.vioHigh : issue.sev === "major" ? C.vioMed : 
C.vioLow; 
    const border = C.vioBorder[issue.sev]; 
    return { 
      background: bg, 
      outline: `1.5px solid ${border}`, 
      outlineOffset: "1px", 
      borderRadius: 2, 
      position: "relative", 
      zIndex: isHovered ? 10 : 1, 
      cursor: "default", 
      transition: "all .15s", 
      ...(isHovered ? { background: 
issue.sev==="critical"?"rgba(248,113,113,0.28)":issue.sev==="major"?"rgba(245,158,11,0. 25)":"rgba(96,165,250,0.22)" } : {}),
    }; 
  }; 
 
  const Overlay = ({ rKey, issue, children, style = {} }) => { 
    const overlay = getOverlay(rKey); 
    if (!overlay) return <span style={style}>{children}</span>; 

    return ( 
      <span 
        style={{ ...style, ...overlay }} 
        onMouseEnter={() => setHoveredIssue(issue || regionIssueMap[rKey])} 
        onMouseLeave={() => setHoveredIssue(null)} 
        title={regionIssueMap[rKey]?.heatmapNote} 
      > 
        {children} 
        {hoveredIssue?.id === regionIssueMap[rKey]?.id && ( 
          <span style={{ 
            position:"absolute", top:"calc(100% + 4px)", left:0, zIndex:100, 
            background:"#0d0f11", border:`1px solid ${C.border2}`, borderRadius:6, 
            padding:"7px 10px", whiteSpace:"nowrap", pointerEvents:"none", 
            boxShadow:"0 8px 24px rgba(0,0,0,.5)", 
          }}> 
            <span style={{ color:C.textMid, fontSize:11 
}}>{regionIssueMap[rKey]?.heatmapNote}</span> 
            <span style={{ color:C.textFaint, fontSize:10, display:"block", marginTop:2 }}> 
              {regionIssueMap[rKey]?.id} · {regionIssueMap[rKey]?.sev} 
            </span> 
          </span> 
        )} 
      </span> 
    ); 
  }; 
 

  // Margin violation indicator 
  const marginIssue = regionIssueMap["margin"]; 
 
  return ( 
    <div style={{ fontFamily:"'Times New Roman', Georgia, serif", fontSize:8.5, 
lineHeight:1.35, 
      background:"#fff", color:"#111", padding:"28px 32px", minHeight:480, 
      position:"relative", userSelect:"none", 
      outline: marginIssue ? `2px solid ${C.vioBorder.major}` : "none", 
      outlineOffset: "-3px", 
    }}> 
      {/* Margin violation overlay */} 
      {marginIssue && ( 
        <div style={{ position:"absolute", inset:0, pointerEvents:"none", 
          background:"rgba(245,158,11,0.04)", 
          outline:`2px solid ${C.vioBorder.major}`, outlineOffset:"-3px", borderRadius:1 }} /> 
      )} 
 
      {/* HEADER */} 
      <div style={{ textAlign:"center", marginBottom:4 }}> 
        <Overlay rKey="header-name" style={{ display:"block" }}> 
          <div style={{ fontSize:12, fontWeight:700, letterSpacing:".03em" }}>Zachary 
Teichman</div> 
        </Overlay> 
        <Overlay rKey="header-contact" style={{ display:"block" }}> 
          <div style={{ fontSize:7.5, color:"#333", marginTop:1 }}> 

            (678) 200-6585&nbsp;&nbsp;·&nbsp;&nbsp;Marietta, GA 
30068&nbsp;&nbsp;·&nbsp;&nbsp;zach.teichman@gmail.com&nbsp;&nbsp;·&nbsp;&nbs
p;Athens, GA 30602 
          </div> 
        </Overlay> 
      </div> 
 
      {PREVIEW_SECTIONS.filter(s => s.type==="section").map((sec, si) => ( 
        <div key={si} style={{ marginTop:7 }}> 
          {/* Section header */} 
          <Overlay rKey={`section-label-${si+1}`} style={{ display:"block" }}> 
            <Overlay rKey={`section-rule-${si+1}`} style={{ display:"block" }}> 
              <div style={{ fontWeight:700, fontSize:9, letterSpacing:".04em", borderBottom:"1px solid #111", paddingBottom:1 }}>
                {sec.label} 
              </div> 
            </Overlay> 
          </Overlay> 
 
          {sec.entries.map((entry, ei) => ( 
            <div key={ei} style={{ marginTop:4, paddingLeft:8 }}> 
              {/* Entry line */} 
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"baseline" }}> 
                <Overlay rKey={`entry-indent-${si+1}-${ei}-`} style={{ flex:1, display:"flex", gap:3, 
alignItems:"baseline" }}> 
                  <Overlay rKey={`entry-org-${si+1}-${ei}-`}> 
                    <span style={{ fontWeight:700 }}>{entry.org}</span> 

                  </Overlay> 
                  {entry.role && ( 
                    <> 
                      <span style={{ color:"#444" }}>,&nbsp;</span> 
                      <Overlay rKey={`entry-role-${si+1}-${ei}-`}> 
                        <span style={{ fontStyle:"italic", color:"#222" }}>{entry.role}</span> 
                      </Overlay> 
                    </> 
                  )} 
                  <Overlay rKey={`entry-loc-${si+1}-${ei}-`}> 
                    <span style={{ color:"#444", marginLeft:4 }}>{entry.loc}</span> 
                  </Overlay> 
                </Overlay> 
                <Overlay rKey={`entry-date-${si+1}-${ei}-`} style={{ flexShrink:0, marginLeft:8 }}> 
                  <span style={{ color:"#333", fontSize:8 }}>{entry.date}</span> 
                </Overlay> 
              </div> 
 
              {/* Bullets */} 
              <div style={{ marginTop:2, paddingLeft:10 }}> 
                {entry.bullets.map((b, bi) => ( 
                  <Overlay key={bi} rKey={`bullet-${si+1}-${ei}-${bi}`} style={{ display:"flex", gap:4, 
marginBottom:1 }}> 
                    <span style={{ flexShrink:0, marginTop:1 }}>•</span> 
                    <Overlay rKey={`typography-inline-${si+1}-${ei}-${bi}`} style={{ flex:1 }}> 
                      <span style={{ color:"#222" }}>{b}</span> 

                    </Overlay> 
                  </Overlay> 
                ))} 
              </div> 
            </div> 
          ))} 
        </div> 
      ))} 
 
      {/* Typography overlay — covers body */} 
      {(regionIssueMap["typography-body"]) && ( 
        <div style={{ position:"absolute", inset:"0 0 40% 0", pointerEvents:"none", 
          background:C.vioLow, outline:`1px dashed ${C.vioBorder.minor}`, 
          outlineOffset:"-2px", borderRadius:2, opacity:.6 }} /> 
      )} 
 
      {/* Legend */} 
      <div style={{ position:"absolute", bottom:8, right:10, display:"flex", gap:10, 
alignItems:"center" }}> 
        {[["#f87171","Critical"],["#f59e0b","Major"],["#60a5fa","Minor"]].map(([color,label])=>( 
          <div key={label} style={{ display:"flex", gap:4, alignItems:"center" }}> 
            <div style={{ width:8, height:8, borderRadius:1, background:color, opacity:.6 }}/> 
            <span style={{ color:"#888", fontSize:7, fontFamily:"'DM Sans',sans-serif" 
}}>{label}</span> 
          </div> 
        ))} 
        {issues.length===0 && ( 

          <span style={{ color:"#4ade80", fontSize:7, fontFamily:"'DM Sans',sans-serif" }}>✓ No 
violations</span> 
        )} 
      </div> 
    </div> 
  ); 
}; 
 
// ─── REJECTION SCREEN 
const RejectionScreen = ({ reason, onReset }) => ( 
  <div style={{ maxWidth:520, margin:"0 auto", padding:"60px 24px", textAlign:"center" }}> 
    <div style={{ width:56, height:56, borderRadius:"50%", background:"#2d0e0e", 
      border:`1px solid #5a1515`, display:"flex", alignItems:"center", 
      justifyContent:"center", margin:"0 auto 24px" }}> 
      <span style={{ fontSize:22, color:"#f87171" }}>✕</span> 
    </div> 
    <div style={{ color:"#f87171", fontSize:12, fontWeight:600, letterSpacing:".1em", 
      textTransform:"uppercase", marginBottom:10 }}>Resume Rejected</div> 
    <h2 style={{ color:C.text, fontSize:21, fontWeight:700, letterSpacing:"-.5px", 
      margin:"0 0 14px", fontFamily:"'Playfair Display',Georgia,serif" }}> 
      {reason.title} 
    </h2> 
    <p style={{ color:C.textDim, fontSize:14, lineHeight:1.7, margin:"0 0 22px" 
}}>{reason.detail}</p> 
    <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:10, 
      padding:"16px 18px", marginBottom:26, textAlign:"left" }}> 

      <div style={{ color:C.gold, fontSize:11, fontWeight:600, letterSpacing:".08em", 
        textTransform:"uppercase", marginBottom:8 }}>How to resolve</div> 
      <div style={{ color:C.textMid, fontSize:13, lineHeight:1.65 }}>{reason.fix}</div> 
    </div> 
    <button onClick={onReset} style={{ background:C.red, color:"#fff", border:"none", 
      borderRadius:8, padding:"11px 22px", fontSize:14, fontWeight:600, 
      cursor:"pointer", fontFamily:"var(--font)" }}> 
      Upload Revised Resume 
    </button> 
  </div> 
); 
 
// ─── STUDENT DASHBOARD 
const StudentDashboard = () => { 
  const [stage, setStage] = useState("upload"); 
  const [fileName, setFileName] = useState(""); 
  const [fileType, setFileType] = useState(""); 
  const [dragging, setDragging] = useState(false); 
  const [results, setResults] = useState(null); 
  const [activeTab, setActiveTab] = useState("issues"); 
  const [viewMode, setViewMode] = useState("list"); // list | heatmap 
  const [expandedIssue, setExpandedIssue] = useState(null); 
  const [analysisStep, setAnalysisStep] = useState(0); 
  const fileRef = useRef(); 
 

  const STEPS = [ 
    "Verifying page count", 
    "Detecting Corsair layout structure", 
    "Measuring section header formatting", 
    "Checking entry line alignment", 
    "Auditing bullet indent depths", 
    "Measuring typography consistency", 
    "Computing compliance score", 
  ]; 
 
  const handleFile = useCallback((file) => { 
    if (!file) return; 
    const ext = file.name.split(".").pop().toLowerCase(); 
    if (!["docx","pdf"].includes(ext)) return; 
    setFileName(file.name); 
    setFileType(ext); 
    setStage("analyzing"); 
    setAnalysisStep(0); 
    STEPS.forEach((_,i) => setTimeout(() => setAnalysisStep(i), i * 310)); 
    setTimeout(() => { 
      const r = scoreResume(file.name); 
      setResults(r); 
      setStage(r.rejected ? "rejected" : "results"); 
    }, STEPS.length * 310 + 380); 
  }, []); 
 

  const reset = () => { 
    setStage("upload"); setResults(null); setFileName(""); setFileType(""); 
    setExpandedIssue(null); setAnalysisStep(0); setViewMode("list"); setActiveTab("issues"); 
  }; 
 
  const catGroups = results && !results.rejected 
    ? RUBRIC.reduce((acc, rule) => { 
        if (!acc[rule.cat]) acc[rule.cat] = { pass:[], fail:[] }; 
        const failed = results.issues.find(i => i.id === rule.id); 
        failed ? acc[rule.cat].fail.push(failed) : acc[rule.cat].pass.push(rule); 
        return acc; 
      }, {}) 
    : {}; 
 
  return ( 
    <div style={{ padding:"32px 24px", maxWidth:1020, margin:"0 auto" }}> 
      <div style={{ marginBottom:28 }}> 
        <h1 style={{ color:C.text, fontSize:22, fontWeight:700, letterSpacing:"-.7px", margin:"0 0 5px" }}>
          Formatting Compliance — Student 
        </h1> 
        <p style={{ color:C.textDim, fontSize:13, margin:0 }}> 
          Upload your resume for Corsair formatting verification.&nbsp; 
          <span style={{ color:C.textMid }}><FileBadge type="docx"/></span> 
          <span style={{ color:C.textFaint, fontSize:12 }}>&nbsp;Full structural audit + fix 
guidance.&nbsp;&nbsp;</span> 
          <span style={{ color:C.textMid }}><FileBadge type="pdf"/></span> 

          <span style={{ color:C.textFaint, fontSize:12 }}>&nbsp;Visual layout audit only.</span> 
        </p> 
      </div> 
 
      {/* UPLOAD */} 
      {stage==="upload" && ( 
        <div 
          onDragOver={e=>{e.preventDefault();setDragging(true)}} 
          onDragLeave={()=>setDragging(false)} 
          onDrop={e=>{e.preventDefault();setDragging(false);handleFile(e.dataTransfer.files[0])}} 
          onClick={()=>fileRef.current.click()} 
          style={{ border:`2px dashed ${dragging?C.red:C.border2}`, borderRadius:14, 
            padding:"72px 40px", textAlign:"center", cursor:"pointer", 
            background:dragging?"rgba(158,27,50,0.04)":C.surface, transition:"all .2s" }} 
        > 
          <input ref={fileRef} type="file" accept=".docx,.pdf" style={{ display:"none" }} 
            onChange={e=>handleFile(e.target.files[0])}/> 
          <div style={{ fontSize:40, marginBottom:16 }}> </div> 
          <div style={{ color:C.text, fontSize:17, fontWeight:600, marginBottom:7 }}>Drop your 
resume here</div> 
          <div style={{ color:C.textDim, fontSize:13, marginBottom:24 }}> 
            .docx or .pdf · Max 10MB · Must be one page · Corsair format required 
          </div> 
          <div style={{ display:"inline-block", background:C.red, color:"#fff", 
            borderRadius:8, padding:"11px 22px", fontSize:14, fontWeight:600 }}> 
            Choose File 

          </div> 
        </div> 
      )} 
 
      {/* ANALYZING */} 
      {stage==="analyzing" && ( 
        <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:14, 
          padding:"56px 40px", textAlign:"center" }}> 
          <div style={{ display:"flex", alignItems:"center", justifyContent:"center", gap:8, 
marginBottom:5 }}> 
            <FileBadge type={fileType}/> 
            <span style={{ color:C.text, fontSize:15, fontWeight:600 }}>{fileName}</span> 
          </div> 
          <div style={{ color:C.textDim, fontSize:13, marginBottom:40 }}> 
            {fileType==="docx" 
              ? "Parsing document XML — checking formatting values against Corsair rubric" 
              : "Analyzing rendered layout geometry — checking against Corsair rubric"} 
          </div> 
          <div style={{ maxWidth:360, margin:"0 auto" }}> 
            {STEPS.map((step,i)=>{ 
              const done=i<analysisStep, active=i===analysisStep; 
              return ( 
                <div key={i} style={{ display:"flex", alignItems:"center", gap:12, 
                  padding:"8px 0", borderBottom:`1px solid ${C.surface2}` }}> 
                  <div style={{ width:17, height:17, borderRadius:"50%", flexShrink:0, 
                    background:done?"#0d2b1a":C.surface2, 

                    border:`2px solid ${done?"#4ade80":active?C.red:C.border2}`, 
                    display:"flex", alignItems:"center", justifyContent:"center", 
                    transition:"all .25s" }}> 
                    {done 
                      ? <span style={{ color:"#4ade80", fontSize:8 }}>✓</span> 
                      : active 
                        ? <div style={{ width:5, height:5, borderRadius:"50%", 
                            background:C.red, animation:"pulse 1s infinite" }}/> 
                        : null} 
                  </div> 
                  <span style={{ color:done?C.textDim:active?C.text:C.textFaint, 
                    fontSize:13, transition:"color .25s" }}>{step}</span> 
                </div> 
              ); 
            })} 
          </div> 
        </div> 
      )} 
 
      {/* REJECTED */} 
      {stage==="rejected" && results?.rejected && ( 
        <div style={{ background:C.surface, border:`1px solid #3a1515`, borderRadius:14 }}> 
          <RejectionScreen reason={results.reason} onReset={reset}/> 
        </div> 
      )} 
 

      {/* RESULTS */} 
      {stage==="results" && results && !results.rejected && ( 
        <div> 
          {/* File + mode bar */} 
          <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:18, 
            padding:"9px 14px", background:C.surface, border:`1px solid ${C.border}`, 
borderRadius:8 }}> 
            <FileBadge type={results.fileType}/> 
            <span style={{ color:C.textMid, fontSize:13 }}>{fileName}</span> 
            {results.fileType==="pdf" && ( 
              <span style={{ color:C.textFaint, fontSize:12, marginLeft:2 }}> 
                · Visual layout audit — some checks unverifiable without DOCX 
              </span> 
            )} 
            <div style={{ marginLeft:"auto", display:"flex", gap:8, alignItems:"center" }}> 
              {/* View toggle */} 
              <div style={{ display:"flex", background:C.surface2, borderRadius:6, 
                border:`1px solid ${C.border2}`, overflow:"hidden" }}> 
                {[["list","List"],["heatmap","Heatmap"]].map(([mode,label])=>( 
                  <button key={mode} onClick={()=>setViewMode(mode)} style={{ 
                    background:viewMode===mode?C.border2:"transparent", 
                    color:viewMode===mode?C.text:C.textDim, 
                    border:"none", padding:"5px 12px", fontSize:12, fontWeight:500, 
                    cursor:"pointer", fontFamily:"var(--font)", transition:"all .15s" }}> 
                    {label} 
                  </button> 

                ))} 
              </div> 
              <button onClick={reset} style={{ background:"transparent", color:C.textDim, 
                border:`1px solid ${C.border2}`, borderRadius:6, padding:"5px 12px", 
                fontSize:12, cursor:"pointer", fontFamily:"var(--font)" }}> 
                Upload Different File 
              </button> 
            </div> 
          </div> 
 
          <div style={{ display:"grid", gridTemplateColumns:"240px 1fr", gap:18 }}> 
            {/* Left: score panel */} 
            <div> 
              <div style={{ background:C.surface, border:`1px solid ${C.border}`, 
                borderRadius:12, padding:"22px 16px", marginBottom:14 }}> 
                <div style={{ color:C.textDim, fontSize:10, fontWeight:600, 
                  letterSpacing:".08em", textTransform:"uppercase", marginBottom:16 }}> 
                  Compliance Score 
                </div> 
                <div style={{ display:"flex", justifyContent:"center", marginBottom:14 }}> 
                  <ScoreRing score={results.score} size={110}/> 
                </div> 
                <div style={{ textAlign:"center", marginBottom:18 }}> 
                  <div style={{ color:C.text, fontSize:13, fontWeight:600 }}> 
                    {results.score>=90?"✓ Corsair Compliant" 
                      :results.score>=75?"⚠ Minor Violations" 

                      :results.score>=60?"⚠ Formatting Issues" 
                      :"✗ Non-Compliant"} 
                  </div> 
                  <div style={{ color:C.textDim, fontSize:12, marginTop:3 }}> 
                    {results.issues.length} violation{results.issues.length!==1?"s":""} detected 
                  </div> 
                </div> 
                <div style={{ height:1, background:C.border, margin:"0 0 16px" }}/> 
                <div style={{ color:C.textDim, fontSize:10, fontWeight:600, 
                  letterSpacing:".08em", textTransform:"uppercase", marginBottom:12 }}> 
                  By Category 
                </div> 
                {Object.entries(catGroups).map(([cat,g])=>{ 
                  const pct = 
Math.round((g.pass.filter(p=>!p.unverified).length/Math.max(1,g.pass.filter(p=>!p.unverifie
d).length+g.fail.length))*100); 
                  const color = pct===100?"#4ade80":pct>=60?"#f59e0b":"#f87171"; 
                  return ( 
                    <div key={cat} style={{ marginBottom:11 }}> 
                      <div style={{ display:"flex", justifyContent:"space-between", marginBottom:3 }}> 
                        <span style={{ color:C.textMid, fontSize:11 }}>{cat}</span> 
                        <span style={{ color, fontSize:11, fontFamily:"'DM Mono',monospace" 
}}>{pct}%</span> 
                      </div> 
                      <div style={{ height:3, background:C.surface2, borderRadius:2 }}> 
                        <div style={{ width:`${pct}%`, height:"100%", borderRadius:2, 
background:color, transition:"width 1s" }}/> 

                      </div> 
                    </div> 
                  ); 
                })} 
              </div> 
              {results.fileType==="pdf" && ( 
                <div style={{ background:"#141c2a", border:`1px solid #1e2d40`, 
                  borderRadius:10, padding:"12px 14px" }}> 
                  <div style={{ color:"#38bdf8", fontSize:11, fontWeight:600, marginBottom:5 }}> 
                    PDF Audit Mode 
                  </div> 
                  <div style={{ color:"#4a6080", fontSize:12, lineHeight:1.55 }}> 
                    Font detection, exact indent values, and weight checks require DOCX. 
                    Affected checks are marked as unverified. 
                  </div> 
                </div> 
              )} 
            </div> 
 
            {/* Right: list or heatmap */} 
            <div> 
              {viewMode==="heatmap" ? ( 
                <div style={{ background:C.surface, border:`1px solid ${C.border}`, 
borderRadius:12, overflow:"hidden" }}> 
                  <div style={{ padding:"12px 16px", borderBottom:`1px solid ${C.border}`, 
                    display:"flex", justifyContent:"space-between", alignItems:"center" }}> 

                    <div style={{ color:C.textDim, fontSize:11, fontWeight:600, 
                      letterSpacing:".08em", textTransform:"uppercase" }}> 
                      Visual Violation Map 
                    </div> 
                    <div style={{ color:C.textFaint, fontSize:11 }}> 
                      Hover violations to inspect 
                    </div> 
                  </div> 
                  <div style={{ padding:20 }}> 
                    <HeatmapPreview issues={results.issues}/> 
                  </div> 
                </div> 
              ) : ( 
                <div style={{ background:C.surface, border:`1px solid ${C.border}`, 
borderRadius:12, overflow:"hidden" }}> 
                  {/* Tabs */} 
                  <div style={{ display:"flex", borderBottom:`1px solid ${C.border}` }}> 
                    {[ 
                      ["issues", `Violations (${results.issues.length})`], 
                      ["passing", `Passed (${results.passing.filter(p=>!p.unverified).length})`], 
                      ...(results.passing.some(p=>p.unverified) 
                        ? [["unverified",`Unverified (${results.passing.filter(p=>p.unverified).length})`]] 
                        : []), 
                    ].map(([tab,label])=>( 
                      <button key={tab} onClick={()=>setActiveTab(tab)} style={{ 
                        flex:1, padding:"12px 16px", background:"transparent", border:"none", 

                        borderBottom:activeTab===tab?`2px solid ${C.red}`:"2px solid transparent", 
                        color:activeTab===tab?C.text:C.textDim, 
                        fontSize:13, fontWeight:600, cursor:"pointer", fontFamily:"var(--font)" }}> 
                        {label} 
                      </button> 
                    ))} 
                  </div 
<div style={{ padding:14, maxHeight:500, overflowY:"auto" }}> 
                    {activeTab==="issues" && ( 
                      results.issues.length===0 
                        ? <div style={{ padding:"36px 20px", textAlign:"center" }}> 
                            <div style={{ fontSize:30, marginBottom:10 }}> </div> 
                            <div style={{ color:"#4ade80", fontSize:15, fontWeight:600 }}>No violations 
detected</div> 
                            <div style={{ color:C.textDim, fontSize:13, marginTop:5 }}> 
                              All formatting checks pass. 
                            </div> 
                          </div> 
                        : results.issues.map(issue=>( 
                            <div key={issue.id} 
                              onClick={()=>setExpandedIssue(expandedIssue?.id===issue.id?null:issue)} 
                              style={{ 
background:expandedIssue?.id===issue.id?C.surface2:"transparent", 
                                border:`1px solid 
${expandedIssue?.id===issue.id?C.border2:"transparent"}`, 
                                borderRadius:9, padding:"13px 15px", marginBottom:5, 
                                cursor:"pointer", transition:"all .15s" }}> 

                              <div style={{ display:"flex", justifyContent:"space-between", 
                                alignItems:"flex-start", gap:12 }}> 
                                <div style={{ flex:1 }}> 
                                  <div style={{ display:"flex", alignItems:"center", gap:7, marginBottom:4, 
flexWrap:"wrap" }}> 
                                    <span style={{ color:C.textFaint, fontSize:10, 
                                      fontFamily:"'DM Mono',monospace" }}>{issue.id}</span> 
                                    <span style={{ color:C.text, fontSize:13, fontWeight:600 
}}>{issue.label}</span> 
                                  </div> 
                                  <div style={{ color:C.textDim, fontSize:12, lineHeight:1.5 
}}>{issue.detail}</div> 
                                </div> 
                                <div style={{ display:"flex", flexDirection:"column", 
                                  alignItems:"flex-end", gap:5, flexShrink:0 }}> 
                                  <SevBadge sev={issue.sev}/> 
                                  <span style={{ color:"#f87171", fontSize:10, 
                                    fontFamily:"'DM Mono',monospace" }}>−{issue.pts}pt</span> 
                                </div> 
                              </div> 
                              {expandedIssue?.id===issue.id && ( 
                                <div style={{ marginTop:11, paddingTop:11, 
                                  borderTop:`1px solid ${C.border2}` }}> 
                                  <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:10 }}> 
                                    <ConfBadge conf={issue.conf}/> 
                                    <span style={{ color:C.textFaint, fontSize:11 }}> 
                                      {issue.fileType==="pdf" 

                                        ? "Detected via visual layout geometry" 
                                        : "Detected via document XML"} 
                                    </span> 
                                  </div> 
                                  <div style={{ color:C.textDim, fontSize:11, fontWeight:600, 
                                    letterSpacing:".06em", textTransform:"uppercase", marginBottom:7 }}> 
                                    Corsair Requirement 
                                  </div> 
                                  <div style={{ color:C.textMid, fontSize:13, lineHeight:1.6, marginBottom:10 
}}> 
                                    {issue.desc} 
                                  </div> 
                                  {results.fileType==="docx" ? ( 
                                    <div style={{ background:"#0a1a12", border:`1px solid #1a3320`, 
                                      borderRadius:7, padding:"10px 12px" }}> 
                                      <div style={{ color:"#4ade80", fontSize:11, fontWeight:600, 
marginBottom:4 }}> 
                                        {issue.sev==="critical" 
                                          ? "Fix before submitting — reviewers check this first" 
                                          : issue.sev==="major" 
                                            ? "Recommended to fix before submitting" 
                                            : "Minor — fix to maximize compliance score"} 
                                      </div> 
                                    </div> 
                                  ) : ( 
                                    <div style={{ background:"#141c2a", border:`1px solid #1e2d40`, 
                                      borderRadius:7, padding:"10px 12px" }}> 

                                      <div style={{ color:"#38bdf8", fontSize:11, fontWeight:600, 
marginBottom:3 }}> 
                                        PDF mode — fix suggestions unavailable 
                                      </div> 
                                      <div style={{ color:"#4a6080", fontSize:12 }}> 
                                        Upload DOCX to receive specific fix instructions for this violation. 
                                      </div> 
                                    </div> 
                                  )} 
                                </div> 
                              )} 
                            </div> 
                          )) 
                    )} 
                    {activeTab==="passing" && results.passing.filter(p=>!p.unverified).map(rule=>( 
                      <div key={rule.id} style={{ display:"flex", justifyContent:"space-between", 
                        alignItems:"center", padding:"10px 0", borderBottom:`1px solid ${C.surface2}` 
}}> 
                        <div style={{ display:"flex", gap:9, alignItems:"center" }}> 
                          <span style={{ color:"#4ade80", fontSize:10 }}>✓</span> 
                          <div> 
                            <div style={{ color:C.textMid, fontSize:13 }}>{rule.label}</div> 
                            <div style={{ color:C.textFaint, fontSize:10, marginTop:1 }}>{rule.cat}</div> 
                          </div> 
                        </div> 
                        <div style={{ display:"flex", gap:8, alignItems:"center", flexShrink:0 }}> 
                          <ConfBadge conf={rule.conf}/> 

                          <span style={{ color:"#4ade80", fontSize:10, 
                            fontFamily:"'DM Mono',monospace" }}>+{rule.pts}pt</span> 
                        </div> 
                      </div> 
                    ))} 
                    {activeTab==="unverified" && results.passing.filter(p=>p.unverified).map(rule=>( 
                      <div key={rule.id} style={{ display:"flex", justifyContent:"space-between", 
                        alignItems:"center", padding:"10px 0", borderBottom:`1px solid ${C.surface2}` 
}}> 
                        <div style={{ display:"flex", gap:9, alignItems:"center" }}> 
                          <span style={{ color:C.textFaint, fontSize:10 }}>~</span> 
                          <div> 
                            <div style={{ color:C.textDim, fontSize:13 }}>{rule.label}</div> 
                            <div style={{ color:C.textFaint, fontSize:11, marginTop:1 }}> 
                              Requires DOCX for verification 
                            </div> 
                          </div> 
                        </div> 
                        <ConfBadge conf="ESTIMATED"/> 
                      </div> 
                    ))} 
                  </div> 
                </div> 
              )} 
            </div> 
          </div> 

        </div> 
      )} 
    </div> 
  ); 
}; 
 
// ─── REVIEWER DASHBOARD 
const ReviewerDashboard = () => { 
  const [applicants, setApplicants] = useState(MOCK_APPLICANTS); 
  const [sortBy, setSortBy]   = useState("score"); 
  const [sortDir, setSortDir] = useState("desc"); 
  const [filter, setFilter]   = useState("all"); 
  const [selected, setSelected] = useState(null); 
  const [notes, setNotes] = useState({}); 
  const [uploading, setUploading] = useState(false); 
  const [blindMode, setBlindMode] = useState(false); 
  const fileRef = useRef(); 
 
  const handleSort = col => { 
    if (sortBy===col) setSortDir(d=>d==="desc"?"asc":"desc"); 
    else { setSortBy(col); setSortDir("desc"); } 
  }; 
 
  const sorted = [...applicants] 
    .filter(a => filter==="all" || a.status===filter) 

    .sort((a,b) => { 
      if (a.ungraded && !b.ungraded) return 1; 
      if (!a.ungraded && b.ungraded) return -1; 
      const va=a[sortBy]??-1, vb=b[sortBy]??-1; 
      return sortDir==="desc"?(vb>va?1:-1):(va>vb?1:-1); 
    }); 
 
  const handleUpload = (files) => { 
    setUploading(true); 
    setTimeout(()=>{ 
      const next = Array.from(files).map((f,i)=>{ 
        if (!f.name.toLowerCase().endsWith(".pdf")) return { 
          id:applicants.length+i+1, name:f.name.replace(/\..*/,"").replace(/_/g," "), 
          major:"—", score:null, issueCount:0, status:"ungraded", file:f.name, 
          elapsed:"just now", ungraded:true, 
          ungradedReason:"Non-PDF file. Reviewer mode accepts PDF only.", 
        }; 
        const r = scoreResume(f.name); 
        if (r.rejected) return { 
          id:applicants.length+i+1, name:f.name.replace(/\..*/,"").replace(/_/g," "), 
          major:"—", score:null, issueCount:0, status:"ungraded", file:f.name, 
          elapsed:"just now", ungraded:true, ungradedReason:r.reason.title, 
        }; 
        return { 
          id:applicants.length+i+1, 
          name:f.name.replace(/_Resume.*/,"").replace(/_/g," "), 

          major:"—", score:r.score, issueCount:r.issues.length, 
          status:r.score>=85?"pass":r.score>=65?"review":"fail", 
          file:f.name, elapsed:"just now", ungraded:false, 
        }; 
      }); 
      setApplicants(p=>[...p,...next]); 
      setUploading(false); 
    }, 1800); 
  }; 
 
  const detailData = selected && !selected.ungraded ? scoreResume(selected.file) : null; 
  const graded = applicants.filter(a=>!a.ungraded); 
  const stats = { 
    total: applicants.length, 
    graded: graded.length, 
    avg: graded.length ? Math.round(graded.reduce((s,a)=>s+a.score,0)/graded.length) : 0, 
    passRate: graded.length ? 
Math.round((applicants.filter(a=>a.status==="pass").length/graded.length)*100) : 0, 
    ungraded: applicants.filter(a=>a.ungraded).length, 
  }; 
 
  const Th = ({ col, label }) => ( 
    <th onClick={()=>handleSort(col)} style={{ textAlign:"left", padding:"9px 14px", 
      color:C.textDim, fontSize:10, fontWeight:600, letterSpacing:".06em", 
      textTransform:"uppercase", cursor:"pointer", userSelect:"none", whiteSpace:"nowrap" 
}}> 
      {label}{sortBy===col?(sortDir==="desc"?" ↓":" ↑"):""} 

    </th> 
  ); 
 
  return ( 
    <div style={{ padding:"32px 24px", maxWidth:1160, margin:"0 auto" }}> 
      {/* Header */} 
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", 
        marginBottom:24, flexWrap:"wrap", gap:14 }}> 
        <div> 
          <h1 style={{ color:C.text, fontSize:22, fontWeight:700, letterSpacing:"-.7px", margin:"0 0 5px" }}>
            Formatting Review — Batch 
          </h1> 
          <p style={{ color:C.textDim, fontSize:13, margin:0 }}> 
            Spring 2026 Recruitment · PDF uploads only · Corsair rubric 
          </p> 
        </div> 
        <div style={{ display:"flex", gap:10, alignItems:"center", flexWrap:"wrap" }}> 
          {/* Blind mode toggle */} 
          <button onClick={()=>setBlindMode(b=>!b)} style={{ 
            background:blindMode?C.surface2:"transparent", 
            color:blindMode?C.text:C.textDim, 
            border:`1px solid ${blindMode?C.border2:C.border}`, 
            borderRadius:7, padding:"8px 14px", fontSize:12, fontWeight:500, 
            cursor:"pointer", fontFamily:"var(--font)", display:"flex", gap:6, alignItems:"center" 
          }}> 

            <span style={{ fontSize:11 }}>{blindMode?"◉":"○"}</span> 
            Blind Mode {blindMode?"ON":"OFF"} 
          </button> 
          {stats.ungraded>0 && ( 
            <div style={{ background:"#2d2008", border:`1px solid #3d2e10`, 
              borderRadius:7, padding:"7px 12px", display:"flex", gap:7, alignItems:"center" }}> 
              <span style={{ color:"#f59e0b", fontSize:11 }}>⚠</span> 
              <span style={{ color:"#f59e0b", fontSize:12, fontWeight:500 }}> 
                {stats.ungraded} ungraded 
              </span> 
            </div> 
          )} 
          <input ref={fileRef} type="file" accept=".pdf" multiple style={{ display:"none" }} 
            onChange={e=>handleUpload(e.target.files)}/> 
          <button onClick={()=>fileRef.current.click()} style={{ background:C.red, color:"#fff", 
            border:"none", borderRadius:8, padding:"9px 16px", fontSize:13, fontWeight:600, 
            cursor:"pointer", fontFamily:"var(--font)" }}> 
            {uploading?"Processing…":"+ Upload PDFs"} 
          </button> 
          <button style={{ background:"transparent", color:C.textMid, 
            border:`1px solid ${C.border2}`, borderRadius:8, padding:"9px 16px", 
            fontSize:13, cursor:"pointer", fontFamily:"var(--font)" }}> 
            Export CSV 
          </button> 
        </div> 
      </div> 

 
      {/* Blind mode banner */} 
      {blindMode && ( 
        <div style={{ background:"#141826", border:`1px solid #1e2d40`, borderRadius:8, 
          padding:"10px 16px", marginBottom:18, display:"flex", gap:10, alignItems:"center" }}> 
          <span style={{ color:"#60a5fa", fontSize:13 }}>◉</span> 
          <span style={{ color:"#60a5fa", fontSize:13, fontWeight:500 }}>Blind Mode 
Active</span> 
          <span style={{ color:"#4a5a70", fontSize:12 }}> 
            · Applicant names, GPA, and organizations are hidden. Formatting compliance only. 
          </span> 
        </div> 
      )} 
 
      {/* Stats */} 
      <div style={{ display:"grid", gridTemplateColumns:"repeat(5,1fr)", gap:12, 
marginBottom:20 }}> 
        {[ 
          { label:"Total",    val:stats.total,    color:C.text           }, 
          { label:"Graded",   val:stats.graded,   color:C.text           }, 
          { label:"Avg Score",val:stats.avg,       color:stats.avg>=85?"#4ade80":stats.avg>=65?"#f59e0b":"#f87171 " },
          { label:"Pass Rate",val:`${stats.passRate}%`, color:"#4ade80" }, 
          { label:"Ungraded", val:stats.ungraded, color:stats.ungraded>0?"#f59e0b":C.textDim }, 
        ].map(s=>( 
          <div key={s.label} style={{ background:C.surface, border:`1px solid ${C.border}`, 

            borderRadius:10, padding:"16px 14px" }}> 
            <div style={{ color:C.textFaint, fontSize:10, fontWeight:600, 
              letterSpacing:".06em", textTransform:"uppercase", marginBottom:5 }}>{s.label}</div> 
            <div style={{ color:s.color, fontSize:22, fontWeight:700, 
              fontFamily:"'DM Mono',monospace", letterSpacing:"-1px" }}>{s.val}</div> 
          </div> 
        ))} 
      </div> 
 
      <div style={{ display:"grid", gridTemplateColumns:selected?"1fr 350px":"1fr", gap:18 }}> 
        {/* Table */} 
        <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, 
overflow:"hidden" }}> 
          {/* Filters */} 
          <div style={{ display:"flex", gap:7, padding:"11px 14px", 
            borderBottom:`1px solid ${C.border}`, flexWrap:"wrap" }}> 
            {[["all","All"],["pass","Pass"],["review","Review"],["fail","Fail"],["ungraded","Ungraded"]].
map(([f,label])=>{ 
              const cnt = f==="all"?applicants.length:applicants.filter(a=>a.status===f).length; 
              const ac  = { all:[C.surface2,C.text], pass:["#0d2b1a","#4ade80"], 
                review:["#2d2008","#f59e0b"], fail:["#2d0e0e","#f87171"], 
                ungraded:["#1a1a1a","#9ca3af"] }[f]; 
              return ( 
                <button key={f} onClick={()=>setFilter(f)} style={{ 
                  background:filter===f?ac[0]:"transparent", 
                  color:filter===f?ac[1]:C.textDim, 
                  border:`1px solid ${filter===f?ac[0]:"transparent"}`, 

                  borderRadius:6, padding:"4px 11px", fontSize:12, 
                  cursor:"pointer", fontFamily:"var(--font)" }}> 
                  {label} ({cnt}) 
                </button> 
              ); 
            })} 
          </div> 
          <div style={{ overflowX:"auto" }}> 
            <table style={{ width:"100%", borderCollapse:"collapse" }}> 
              <thead> 
                <tr style={{ borderBottom:`1px solid ${C.border}` }}> 
                  {!blindMode && <Th col="name" label="Applicant"/>} 
                  {blindMode && <th style={{ padding:"9px 14px", color:C.textDim, fontSize:10, 
fontWeight:600, letterSpacing:".06em", textTransform:"uppercase" }}>ID</th>} 
                  {!blindMode && <Th col="major" label="Major"/>} 
                  <Th col="score" label="Score"/> 
                  <Th col="issueCount" label="Violations"/> 
                  <th style={{ padding:"9px 14px", color:C.textDim, fontSize:10, fontWeight:600, 
letterSpacing:".06em", textTransform:"uppercase" }}>Status</th> 
                  <th style={{ padding:"9px 14px", color:C.textDim, fontSize:10, fontWeight:600, 
letterSpacing:".06em", textTransform:"uppercase" }}>File</th> 
                </tr> 
              </thead> 
              <tbody> 
                {sorted.map((a,idx)=>( 
                  <tr key={a.id} onClick={()=>setSelected(selected?.id===a.id?null:a)} 
                    style={{ borderBottom:`1px solid ${C.surface2}`, 

                      background:selected?.id===a.id?C.surface2:"transparent", 
                      cursor:"pointer", opacity:a.ungraded ? .65 : 1, transition:"background .1s" }}> 
                    {!blindMode && ( 
                      <td style={{ padding:"12px 14px" }}> 
                        <div style={{ color:C.text, fontSize:13, fontWeight:600 }}>{a.name}</div> 
                      </td> 
                    )} 
                    {blindMode && ( 
                      <td style={{ padding:"12px 14px" }}> 
                        <div style={{ color:C.textDim, fontSize:12, fontFamily:"'DM Mono',monospace" 
}}> 
                          #{String(idx+1).padStart(3,"0")} 
                        </div> 
                      </td> 
                    )} 
                    {!blindMode && ( 
                      <td style={{ padding:"12px 14px", color:C.textDim, fontSize:13 }}>{a.major}</td> 
                    )} 
                    <td style={{ padding:"12px 14px", minWidth:120 }}><ScoreBar 
score={a.score}/></td> 
                    <td style={{ padding:"12px 14px", 
                      color:a.ungraded?C.textFaint:a.issueCount===0?"#4ade80":a.issueCount<=3?" #f59e0b":"#f87171",
                      fontSize:13, fontFamily:"'DM Mono',monospace", fontWeight:600 }}> 
                      {a.ungraded?"—":a.issueCount} 
                    </td> 
                    <td style={{ padding:"12px 14px" }}><StatusPill status={a.status}/></td> 

                    <td style={{ padding:"12px 14px" }}> 
                      <div style={{ display:"flex", alignItems:"center", gap:5 }}> 
                        <FileBadge type="pdf"/> 
                        <span style={{ color:C.textFaint, fontSize:10, 
                          fontFamily:"'DM Mono',monospace" }}>{a.file}</span> 
                      </div> 
                    </td> 
                  </tr> 
                ))} 
              </tbody> 
            </table> 
          </div> 
        </div> 
 
        {/* Detail panel */} 
        {selected && ( 
          <div style={{ background:C.surface, border:`1px solid ${C.border}`, 
            borderRadius:12, overflow:"hidden", alignSelf:"start" }}> 
            <div style={{ padding:"16px 18px", borderBottom:`1px solid ${C.border}`, 
              display:"flex", justifyContent:"space-between", alignItems:"center" }}> 
              <div> 
                {!blindMode 
                  ? <div style={{ color:C.text, fontSize:14, fontWeight:700 }}>{selected.name}</div> 
                  : <div style={{ color:C.textDim, fontSize:13, fontFamily:"'DM Mono',monospace" 
}}>Applicant (blind mode)</div>} 
                {!blindMode && 

                  <div style={{ color:C.textDim, fontSize:12, marginTop:1 }}>{selected.major}</div>} 
              </div> 
              <button onClick={()=>setSelected(null)} style={{ background:"transparent", 
                border:"none", color:C.textDim, fontSize:17, cursor:"pointer", padding:"4px 8px" 
}}>✕</button> 
            </div> 
 
            {selected.ungraded ? ( 
              <div style={{ padding:"28px 18px", textAlign:"center" }}> 
                <div style={{ width:44, height:44, borderRadius:"50%", background:"#1a1a1a", 
                  border:`1px solid #3a3a3a`, display:"flex", alignItems:"center", 
                  justifyContent:"center", margin:"0 auto 14px" }}> 
                  <span style={{ color:"#6b7280", fontSize:18 }}>~</span> 
                </div> 
                <div style={{ color:"#9ca3af", fontSize:14, fontWeight:600, marginBottom:8 
}}>Ungraded</div> 
                <div style={{ color:C.textDim, fontSize:13, lineHeight:1.6 
}}>{selected.ungradedReason}</div> 
                <div style={{ marginTop:16, background:C.bg, border:`1px solid ${C.border}`, 
                  borderRadius:8, padding:"12px", textAlign:"left" }}> 
                  <div style={{ color:C.textFaint, fontSize:11, marginBottom:3 }}>Recommended 
action</div> 
                  <div style={{ color:C.textFaint, fontSize:12, lineHeight:1.5 }}> 
                    Request resubmission using the Corsair template before evaluation. 
                  </div> 
                </div> 
              </div> 

            ) : detailData && ( 
              <div style={{ padding:"18px" }}> 
                <div style={{ display:"flex", justifyContent:"center", marginBottom:14 }}> 
                  <ScoreRing score={selected.score} size={88}/> 
                </div> 
                <div style={{ display:"flex", justifyContent:"center", marginBottom:16 }}> 
                  <StatusPill status={selected.status}/> 
                </div> 
                <div style={{ height:1, background:C.border, marginBottom:14 }}/> 
                <div style={{ color:C.textDim, fontSize:10, fontWeight:600, 
                  letterSpacing:".08em", textTransform:"uppercase", marginBottom:10 }}> 
                  Formatting Violations 
                </div> 
                {detailData.issues.length===0 
                  ? <div style={{ color:"#4ade80", fontSize:13, padding:"6px 0" }}>✓ No violations — 
fully compliant</div> 
                  : detailData.issues.map(issue=>( 
                      <div key={issue.id} style={{ display:"flex", justifyContent:"space-between", 
                        alignItems:"flex-start", padding:"8px 0", 
                        borderBottom:`1px solid ${C.surface2}`, gap:8 }}> 
                        <div style={{ flex:1 }}> 
                          <div style={{ color:C.textMid, fontSize:12 }}>{issue.label}</div> 
                          <div style={{ color:C.textFaint, fontSize:10, marginTop:2, 
                            display:"flex", gap:6, alignItems:"center" }}> 
                            <span style={{ fontFamily:"'DM Mono',monospace" }}>{issue.id}</span> 
                            <span>·</span> 

                            <span>−{issue.pts}pt</span> 
                          </div> 
                        </div> 
                        <div style={{ display:"flex", flexDirection:"column", gap:4, alignItems:"flex-end" 
}}> 
                          <SevBadge sev={issue.sev}/> 
                          <ConfBadge conf={issue.conf}/> 
                        </div> 
                      </div> 
                    ))} 
                <div style={{ height:1, background:C.border, margin:"14px 0" }}/> 
                <div style={{ color:C.textDim, fontSize:10, fontWeight:600, 
                  letterSpacing:".08em", textTransform:"uppercase", marginBottom:8 }}> 
                  Reviewer Notes 
                </div> 
                <textarea value={notes[selected.id]||""} 
                  onChange={e=>setNotes(n=>({...n,[selected.id]:e.target.value}))} 
                  placeholder="Private notes for this applicant…" 
                  style={{ width:"100%", background:C.bg, border:`1px solid ${C.border2}`, 
                    borderRadius:7, padding:"9px 11px", color:C.textMid, fontSize:13, 
                    fontFamily:"var(--font)", resize:"vertical", minHeight:72, 
                    outline:"none", boxSizing:"border-box" }}/> 
              </div> 
            )} 
          </div> 
        )} 

      </div> 
    </div> 
  ); 
}; 
 
// ─── ANALYTICS DASHBOARD 
const AnalyticsDashboard = () => { 
  const maxFreq = ANALYTICS.violationFreq[0].count; 
 
  return ( 
    <div style={{ padding:"32px 24px", maxWidth:1020, margin:"0 auto" }}> 
      <div style={{ marginBottom:28 }}> 
        <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:5 }}> 
          <h1 style={{ color:C.text, fontSize:22, fontWeight:700, letterSpacing:"-.7px", margin:0 
}}> 
            Platform Analytics 
          </h1> 
          <span style={{ background:"#2d2008", color:"#f59e0b", fontSize:10, fontWeight:600, 
            padding:"3px 8px", borderRadius:4, letterSpacing:".06em", textTransform:"uppercase" 
}}> 
            Internal 
          </span> 
        </div> 
        <p style={{ color:C.textDim, fontSize:13, margin:0 }}> 
          Operational intelligence for rubric optimization and compliance monitoring. 
          Not visible to students or clubs. 

        </p> 
      </div> 
 
      {/* Top stats */} 
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:14, 
marginBottom:28 }}> 
        {[ 
          { label:"Total Scored",    val:ANALYTICS.totalScored,    sub:"across all batches"       }, 
          { label:"Total Rejected",  val:ANALYTICS.totalRejected,  sub:"gate failures"            }, 
          { label:"Platform Avg",    val:ANALYTICS.avgScore,       sub:"compliance score",  color:ANALYTICS.avgScore>=80?"#4ade80":ANALYTICS.avgScore>=65?"#f59e0b":" #f87171" },
          { label:"Pass Rate",       val:`${ANALYTICS.passRate}%`, sub:"score ≥ 85",         color:"#4ade80" },
        ].map(s=>( 
          <div key={s.label} style={{ background:C.surface, border:`1px solid ${C.border}`, 
            borderRadius:11, padding:"20px 16px" }}> 
            <div style={{ color:C.textFaint, fontSize:10, fontWeight:600, 
              letterSpacing:".08em", textTransform:"uppercase", marginBottom:6 }}>{s.label}</div> 
            <div style={{ color:s.color||C.text, fontSize:26, fontWeight:700, 
              fontFamily:"'DM Mono',monospace", letterSpacing:"-1px", marginBottom:3 
}}>{s.val}</div> 
            <div style={{ color:C.textFaint, fontSize:11 }}>{s.sub}</div> 
          </div> 
        ))} 
      </div> 
 

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:18 }}> 
        {/* Violation frequency */} 
        <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, 
padding:"20px" }}> 
          <div style={{ color:C.textDim, fontSize:11, fontWeight:600, 
            letterSpacing:".08em", textTransform:"uppercase", marginBottom:18 }}> 
            Most Frequent Violations 
          </div> 
          {ANALYTICS.violationFreq.map((v,i)=>( 
            <div key={v.id} style={{ marginBottom:13 }}> 
              <div style={{ display:"flex", justifyContent:"space-between", marginBottom:4, 
alignItems:"center" }}> 
                <div style={{ display:"flex", gap:8, alignItems:"center" }}> 
                  <span style={{ color:C.textFaint, fontSize:10, 
                    fontFamily:"'DM Mono',monospace" }}>{v.id}</span> 
                  <span style={{ color:C.textMid, fontSize:12 }}>{v.label}</span> 
                </div> 
                <div style={{ display:"flex", gap:8, alignItems:"center", flexShrink:0 }}> 
                  <span style={{ color:C.textDim, fontSize:11, 
                    fontFamily:"'DM Mono',monospace" }}>{v.count}</span> 
                  <span style={{ color:C.textFaint, fontSize:11 }}>{v.pct}%</span> 
                </div> 
              </div> 
              <div style={{ height:3, background:C.surface2, borderRadius:2 }}> 
                <div style={{ width:`${(v.count/maxFreq)*100}%`, height:"100%", borderRadius:2, 
                  background:i<3?"#f87171":i<6?"#f59e0b":"#60a5fa", 
                  transition:"width 1s", opacity:.75 }}/> 

              </div> 
            </div> 
          ))} 
        </div> 
 
        <div style={{ display:"flex", flexDirection:"column", gap:18 }}> 
          {/* Score distribution */} 
          <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, 
padding:"20px" }}> 
            <div style={{ color:C.textDim, fontSize:11, fontWeight:600, 
              letterSpacing:".08em", textTransform:"uppercase", marginBottom:18 }}> 
              Score Distribution 
            </div> 
            <div style={{ display:"flex", alignItems:"flex-end", gap:6, height:80 }}> 
              {ANALYTICS.scoreDistribution.map(s=>{ 
                const maxCnt = Math.max(...ANALYTICS.scoreDistribution.map(x=>x.count)); 
                const h = Math.round((s.count/maxCnt)*100); 
                const color = s.range.startsWith("9")?"#4ade80" 
                  :s.range.startsWith("8")?"#86efac" 
                  :s.range.startsWith("7")?"#f59e0b" 
                  :s.range.startsWith("6")?"#fb923c" 
                  :"#f87171"; 
                return ( 
                  <div key={s.range} style={{ flex:1, display:"flex", flexDirection:"column", 
                    alignItems:"center", gap:4 }}> 
                    <span style={{ color:C.textFaint, fontSize:9, 

                      fontFamily:"'DM Mono',monospace" }}>{s.count}</span> 
                    <div style={{ width:"100%", height:`${h}%`, minHeight:4, 
                      background:color, borderRadius:"2px 2px 0 0", opacity:.8 }}/> 
                    <span style={{ color:C.textFaint, fontSize:8 }}>{s.range}</span> 
                  </div> 
                ); 
              })} 
            </div> 
          </div> 
 
          {/* Rejection reasons */} 
          <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:12, 
padding:"20px" }}> 
            <div style={{ color:C.textDim, fontSize:11, fontWeight:600, 
              letterSpacing:".08em", textTransform:"uppercase", marginBottom:16 }}> 
              Rejection Reasons 
            </div> 
            {ANALYTICS.rejectionReasons.map(r=>( 
              <div key={r.reason} style={{ display:"flex", justifyContent:"space-between", 
                padding:"9px 0", borderBottom:`1px solid ${C.surface2}`, alignItems:"center" }}> 
                <span style={{ color:C.textMid, fontSize:13 }}>{r.reason}</span> 
                <div style={{ display:"flex", gap:8, alignItems:"center" }}> 
                  <div style={{ width:40, height:3, background:C.surface2, borderRadius:2 }}> 
                    <div style={{ width:`${(r.count/ANALYTICS.totalRejected)*100}%`, height:"100%", 
                      background:"#f87171", borderRadius:2, opacity:.7 }}/> 
                  </div> 

                  <span style={{ color:"#f87171", fontSize:12, 
                    fontFamily:"'DM Mono',monospace", minWidth:16 }}>{r.count}</span> 
                </div> 
              </div> 
            ))} 
          </div> 
        </div> 
      </div> 
    </div> 
  ); 
}; 
 
// ─── LANDING PAGE 
const LandingPage = ({ setView }) => ( 
  <div> 
    <section style={{ minHeight:"100vh", display:"flex", flexDirection:"column", 
      alignItems:"center", justifyContent:"center", 
      padding:"80px 24px", textAlign:"center", position:"relative", overflow:"hidden" }}> 
      <div style={{ position:"absolute", inset:0, opacity:.033, 
        backgroundImage:"linear-gradient(#B8BDC7 1px,transparent 1px),linear- gradient(90deg,#B8BDC7 1px,transparent 1px)",
        backgroundSize:"40px 40px" }}/> 
      <div style={{ position:"absolute", top:"22%", left:"50%", transform:"translateX(-50%)", 
        width:600, height:400, borderRadius:"50%", 
        background:"radial-gradient(ellipse,rgba(158,27,50,0.1) 0%,transparent 68%)", 
        pointerEvents:"none" }}/> 

 
      <div style={{ position:"relative", maxWidth:780 }}> 
        <div style={{ display:"flex", alignItems:"center", justifyContent:"center", gap:9, 
marginBottom:40 }}> 
          <div style={{ width:28, height:28, borderRadius:6, 
            background:"linear-gradient(135deg,#9E1B32,#6b1222)", 
            display:"flex", alignItems:"center", justifyContent:"center" }}> 
            <span style={{ color:"#fff", fontSize:13, fontWeight:800 }}>C</span> 
          </div> 
          <span style={{ color:C.text, fontSize:13, fontWeight:600, 
            letterSpacing:".14em", textTransform:"uppercase" }}>Corsair Standard</span> 
        </div> 
 
        <div style={{ display:"inline-block", background:C.surface, border:`1px solid 
${C.border2}`, 
          borderRadius:20, padding:"5px 14px", marginBottom:26 }}> 
          <span style={{ color:C.gold, fontSize:11, fontWeight:600, 
            letterSpacing:".09em", textTransform:"uppercase" }}> 
            UGA Terry College of Business 
          </span> 
        </div> 
 
        <h1 style={{ fontSize:"clamp(34px,5.5vw,68px)", fontWeight:800, color:C.text, 
          lineHeight:1.07, letterSpacing:"-2.5px", margin:"0 0 20px", 
          fontFamily:"'Playfair Display',Georgia,serif" }}> 
          Stop Losing Opportunities<br/> 
          <span style={{ color:C.red }}>Over Formatting.</span> 

        </h1> 
 
        <p style={{ fontSize:17, color:"#6a7080", lineHeight:1.8, margin:"0 0 40px", 
          maxWidth:540, marginLeft:"auto", marginRight:"auto" }}> 
          Deterministic formatting compliance verification for Corsair-format resumes. 
          One rubric. Identical results. Every time. 
        </p> 
 
        <div style={{ display:"flex", gap:11, justifyContent:"center", flexWrap:"wrap" }}> 
          <button onClick={()=>setView("student")} 
            style={{ background:C.red, color:"#fff", border:"none", borderRadius:8, 
              padding:"13px 26px", fontSize:14, fontWeight:600, cursor:"pointer", 
              fontFamily:"var(--font)" }} 
            onMouseEnter={e=>e.target.style.background="#b51e38"} 
            onMouseLeave={e=>e.target.style.background=C.red}> 
            Upload Resume → 
          </button> 
          <button onClick={()=>setView("reviewer")} 
            style={{ background:"transparent", color:C.textMid, border:`1px solid ${C.border2}`, 
              borderRadius:8, padding:"13px 26px", fontSize:14, cursor:"pointer", 
              fontFamily:"var(--font)" }} 
            onMouseEnter={e=>{e.target.style.background=C.surface;e.target.style.color=C.text;}
} 
            onMouseLeave={e=>{e.target.style.background="transparent";e.target.style.color=C.t
extMid;}}> 
            Reviewer Dashboard 
          </button> 

        </div> 
      </div> 
 
      {/* Hero mockup */} 
      <div style={{ marginTop:68, maxWidth:800, width:"100%", position:"relative" }}> 
        <div style={{ background:C.surface, border:`1px solid ${C.border2}`, 
          borderRadius:14, overflow:"hidden", boxShadow:"0 40px 80px rgba(0,0,0,.55)" }}> 
          <div style={{ background:C.surface2, borderBottom:`1px solid ${C.border}`, 
            padding:"10px 14px", display:"flex", gap:6, alignItems:"center" }}> 
            {["#ff5f56","#febc2e","#28c840"].map(c=>( 
              <div key={c} style={{ width:9, height:9, borderRadius:"50%", background:c }}/> 
            ))} 
            <span style={{ color:C.textFaint, fontSize:11, marginLeft:7, 
              fontFamily:"'DM Mono',monospace" }}> 
              corsairstandard.uga.edu — formatting compliance 
            </span> 
          </div> 
          <div style={{ display:"flex" }}> 
            <div style={{ padding:"22px 18px", borderRight:`1px solid ${C.border}`, minWidth:180 
}}> 
              <div style={{ color:C.textFaint, fontSize:10, fontWeight:600, 
                letterSpacing:".08em", textTransform:"uppercase", marginBottom:14 }}> 
                Compliance Score 
              </div> 
              <ScoreRing score={97} size={96}/> 
              <div style={{ marginTop:16 }}> 

                {[["Header",100],["Sections",100],["Entries",95],["Bullets",95],["Typography",80]].ma
p(([cat,pct])=>( 
                  <div key={cat} style={{ marginBottom:8 }}> 
                    <div style={{ display:"flex", justifyContent:"space-between", marginBottom:3 }}> 
                      <span style={{ color:C.textFaint, fontSize:10 }}>{cat}</span> 
                      <span style={{ color:pct===100?"#4ade80":"#f59e0b", 
                        fontSize:10, fontFamily:"'DM Mono',monospace" }}>{pct}</span> 
                    </div> 
                    <div style={{ height:2, background:C.surface2, borderRadius:1 }}> 
                      <div style={{ width:`${pct}%`, height:"100%", 
                        background:pct===100?"#4ade80":"#f59e0b", borderRadius:1 }}/> 
                    </div> 
                  </div> 
                ))} 
              </div> 
            </div> 
            <div style={{ flex:1, padding:"22px 18px" }}> 
              <div style={{ color:C.textFaint, fontSize:10, fontWeight:600, 
                letterSpacing:".08em", textTransform:"uppercase", marginBottom:14 }}> 
                Formatting Violations 
              </div> 
              {[ 
                { id:"T3", label:"Unauthorized inline emphasis", sev:"minor", pts:5, 
conf:"ESTIMATED" }, 
                { id:"B4", label:"Bullet length out of range",   sev:"minor", pts:5, conf:"HIGH"      }, 
              ].map(v=>( 
                <div key={v.id} style={{ background:C.surface2, border:`1px solid ${C.border2}`, 

                  borderRadius:7, padding:"9px 12px", marginBottom:6, 
                  display:"flex", justifyContent:"space-between", alignItems:"center" }}> 
                  <div> 
                    <span style={{ color:C.textFaint, fontSize:9, 
                      fontFamily:"'DM Mono',monospace", marginRight:7 }}>{v.id}</span> 
                    <span style={{ color:C.textMid, fontSize:12 }}>{v.label}</span> 
                  </div> 
                  <div style={{ display:"flex", gap:6, alignItems:"center" }}> 
                    <ConfBadge conf={v.conf}/> 
                    <SevBadge sev={v.sev}/> 
                  </div> 
                </div> 
              ))} 
              <div style={{ background:"#0a1a12", border:`1px solid #1a3320`, 
                borderRadius:7, padding:"9px 12px", marginTop:4 }}> 
                <span style={{ color:"#4ade80", fontSize:12 }}> 
                  ✓ 18 checks passed — Corsair compliant 
                </span> 
              </div> 
            </div> 
          </div> 
        </div> 
      </div> 
    </section> 
 
    {/* Why */} 

    <section style={{ padding:"88px 24px", maxWidth:920, margin:"0 auto" }}> 
      <div style={{ textAlign:"center", marginBottom:56 }}> 
        <div style={{ color:C.gold, fontSize:11, fontWeight:600, letterSpacing:".12em", 
          textTransform:"uppercase", marginBottom:12 }}>The Problem</div> 
        <h2 style={{ fontSize:"clamp(24px,4vw,42px)", fontWeight:700, color:C.text, 
          letterSpacing:"-1.5px", fontFamily:"'Playfair Display',Georgia,serif", margin:0 }}> 
          Why This Exists 
        </h2> 
      </div> 
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(270px,1fr))", 
gap:16 }}> 
        {[ 
          { n:"01", title:"Inconsistent Templates", body:"The official Corsair templates contain internal formatting errors. Students follow them exactly and still receive deductions because reviewers apply a stricter standard than the template enforces." },
          { n:"02", title:"Subjective Grading", body:"Without a shared digital rubric, two reviewers produce different scores for the same resume. Candidate outcomes depend on who opens the file — not on the formatting itself." },
          { n:"03", title:"Silent Disqualifiers", body:"A 0.1\" margin asymmetry or mixed font size is invisible to the eye but immediately identified by experienced reviewers. Rejected applicants never learn the specific cause." },
        ].map(c=>( 
          <div key={c.n} style={{ background:C.surface, border:`1px solid ${C.border}`, 
            borderRadius:12, padding:"24px 20px" }}> 
            <div style={{ color:C.red, fontSize:24, fontWeight:800, 
              fontFamily:"'DM Mono',monospace", marginBottom:12, letterSpacing:"-1px" 
}}>{c.n}</div> 
            <div style={{ color:C.text, fontSize:14, fontWeight:600, marginBottom:7 
}}>{c.title}</div> 

            <div style={{ color:C.textDim, fontSize:13, lineHeight:1.7 }}>{c.body}</div> 
          </div> 
        ))} 
      </div> 
    </section> 
 
    {/* Two modes */} 
    <section style={{ padding:"72px 24px", background:"#0a0c0e" }}> 
      <div style={{ maxWidth:920, margin:"0 auto" }}> 
        <div style={{ textAlign:"center", marginBottom:52 }}> 
          <div style={{ color:C.gold, fontSize:11, fontWeight:600, letterSpacing:".12em", 
            textTransform:"uppercase", marginBottom:12 }}>One Engine. Two Perspectives.</div> 
          <h2 style={{ fontSize:"clamp(24px,4vw,42px)", fontWeight:700, color:C.text, 
            letterSpacing:"-1.5px", fontFamily:"'Playfair Display',Georgia,serif", margin:0 }}> 
            Same Rubric. Both Sides. 
          </h2> 
        </div> 
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:18 }}> 
          {[ 
            { mode:"Student", accent:C.red,  icon:" ", 
              tagline:"Verify before submitting.", 
              body:"Upload DOCX for full XML-level structural analysis with violation details and fix guidance. Upload PDF for visual layout scoring. The system checks formatting values — not content.",
              note:"DOCX → structural audit + fix guidance. PDF → visual layout score only.", 
              noteColor:"#38bdf8", 

              items:["Hard reject if multi-page","Dual address detection","20-point formatting rubric","Confidence level per check","DOCX: fix guidance per violation","PDF: layout score only"],
              cta:"Upload Resume", v:"student" }, 
            { mode:"Reviewer", accent:C.gold, icon:"🗂", 
              tagline:"Grade at scale. Consistently.", 
              body:"Batch process PDF submissions. Every file is scored against the identical rubric simultaneously. Non-Corsair files are flagged as Ungraded without breaking the batch. Blind mode available.",
              note:"PDF only. DOCX submissions flagged as invalid.", 
              noteColor:"#a78bfa", 
              items:["PDF-only enforcement","Multi-page files rejected at gate","Non-Corsair files flagged, not broken","Sort and filter by compliance score","Blind mode hides names/orgs","Reviewer notes per applicant"],
              cta:"Reviewer Dashboard", v:"reviewer" }, 
          ].map(m=>( 
            <div key={m.mode} style={{ background:C.surface, border:`1px solid ${C.border}`, 
              borderRadius:14, padding:"28px 24px", borderTop:`3px solid ${m.accent}` }}> 
              <div style={{ fontSize:24, marginBottom:14 }}>{m.icon}</div> 
              <div style={{ color:C.text, fontSize:17, fontWeight:700, 
                marginBottom:4, letterSpacing:"-.3px" }}>{m.mode} Mode</div> 
              <div style={{ color:m.accent, fontSize:12, fontWeight:600, marginBottom:14 
}}>{m.tagline}</div> 
              <div style={{ color:C.textDim, fontSize:13, lineHeight:1.7, marginBottom:18 
}}>{m.body}</div> 
              <div style={{ background:C.bg, borderRadius:7, padding:"9px 12px", 
                marginBottom:18, display:"flex", gap:7, alignItems:"flex-start" }}> 
                <span style={{ color:m.noteColor, fontSize:11, marginTop:1 }}>ℹ</span> 

                <span style={{ color:"#4a5060", fontSize:12 }}>{m.note}</span> 
              </div> 
              <ul style={{ listStyle:"none", padding:0, margin:"0 0 22px" }}> 
                {m.items.map(item=>( 
                  <li key={item} style={{ color:C.textDim, fontSize:13, padding:"5px 0", 
                    borderBottom:`1px solid ${C.surface2}`, display:"flex", gap:9, 
alignItems:"center" }}> 
                    <span style={{ color:m.accent, fontSize:8 }}>●</span>{item} 
                  </li> 
                ))} 
              </ul> 
              <button onClick={()=>setView(m.v)} style={{ background:m.accent, color:"#fff", 
                border:"none", borderRadius:8, padding:"11px 18px", fontSize:13, 
                fontWeight:600, cursor:"pointer", fontFamily:"var(--font)" }}> 
                {m.cta} → 
              </button> 
            </div> 
          ))} 
        </div> 
      </div> 
    </section> 
 
    <footer style={{ borderTop:`1px solid ${C.border}`, padding:"36px 24px", 
textAlign:"center" }}> 
      <div style={{ display:"flex", alignItems:"center", justifyContent:"center", gap:8, 
marginBottom:8 }}> 
        <div style={{ width:18, height:18, borderRadius:4, background:C.red, 

          display:"flex", alignItems:"center", justifyContent:"center" }}> 
          <span style={{ color:"#fff", fontSize:9, fontWeight:800 }}>C</span> 
        </div> 
        <span style={{ color:C.textFaint, fontSize:11, fontWeight:600, 
          letterSpacing:".12em", textTransform:"uppercase" }}>Corsair Standard</span> 
      </div> 
      <p style={{ color:"#2a2d33", fontSize:11, margin:0 }}> 
        Formatting compliance infrastructure · UGA Terry College of Business · Not affiliated 
with the University of Georgia 
      </p> 
    </footer> 
  </div> 
); 
 
// ─── APP SHELL 
export default function App() { 
  const [view, setView] = useState("landing"); 
 
  return ( 
    <div style={{ "--font":"'DM Sans','Inter',sans-serif", fontFamily:"var(--font)", 
      background:C.bg, minHeight:"100vh", color:C.text }}> 
      <style>{` 
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;0,9..40,800&family=DM+Mono:wght@400;500;600&family=Playfair+Display:wght@700;800&display=swap'); 

        * { box-sizing:border-box; } 
        ::-webkit-scrollbar { width:4px; } 
        ::-webkit-scrollbar-track { background:#111315; } 
        ::-webkit-scrollbar-thumb { background:#2a2d33; border-radius:2px; } 
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.2} } 
      `}</style> 
 
      {view !== "landing" && ( 
        <nav style={{ borderBottom:`1px solid ${C.border}`, padding:"0 24px", 
          display:"flex", alignItems:"center", height:48, 
          position:"sticky", top:0, zIndex:100, 
          background:"rgba(13,15,17,.95)", backdropFilter:"blur(12px)" }}> 
          <button onClick={()=>setView("landing")} 
            style={{ display:"flex", alignItems:"center", gap:8, background:"transparent", 
              border:"none", cursor:"pointer", padding:"0 18px 0 0", marginRight:4, 
              borderRight:`1px solid ${C.border}`, height:"100%" }}> 
            <div style={{ width:18, height:18, borderRadius:3, background:C.red, 
              display:"flex", alignItems:"center", justifyContent:"center" }}> 
              <span style={{ color:"#fff", fontSize:9, fontWeight:800 }}>C</span> 
            </div> 
            <span style={{ color:C.textDim, fontSize:11, fontWeight:600, 
              letterSpacing:".1em", textTransform:"uppercase" }}>Corsair Standard</span> 
          </button> 
          {[["student","Student"],["reviewer","Reviewer"],["analytics","Analytics ↗"]].map(([v,label])=>(
            <button key={v} onClick={()=>setView(v)} style={{ 

              background:"transparent", border:"none", 
              borderBottom:view===v?`2px solid ${C.red}`:"2px solid transparent", 
              color:view===v?C.text:C.textDim, 
              fontSize:12, fontWeight:500, padding:"0 14px", 
              height:"100%", cursor:"pointer", fontFamily:"var(--font)", 
              ...(v==="analytics"?{ marginLeft:"auto" }:{}) }}> 
              {label} 
            </button> 
          ))} 
        </nav> 
      )} 
 
      {view==="landing"   && <LandingPage setView={setView}/>} 
      {view==="student"   && <StudentDashboard/>} 
      {view==="reviewer"  && <ReviewerDashboard/>} 
      {view==="analytics" && <AnalyticsDashboard/>} 
    </div> 
  ); 
} 
