// Tracelight API client
// Connects to the FastAPI backend with fallback to demo mode

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Demo data generators (used when backend is unreachable)
// ---------------------------------------------------------------------------

const SOURCES = [
  "boards.hirewell.io",
  "careers.nimbus.dev",
  "jobs.stackpond.com",
  "openings.kestrel.co",
  "work.lumenhub.in",
  "talent.orbitdesk.io",
];

const ROLES = [
  "Senior Data Engineer",
  "Data Platform Engineer",
  "Analytics Engineer",
  "ML Engineer",
  "Backend Engineer",
  "Product Designer",
  "Data Analyst",
  "Staff Engineer",
];

const COMPANIES = [
  "Northwind",
  "Nimbus",
  "Kestrel Labs",
  "Pinecrest",
  "Orbital",
  "Lumen",
  "Vantage",
  "Helix",
];

const LOCATIONS = [
  "Remote (India)",
  "Bengaluru",
  "Gurugram",
  "Hyderabad",
  "Pune",
  "Delhi NCR",
];

const METHODS = [
  "JSON-LD JobPosting",
  "DOM selectors",
  "LLM field extraction",
];

function seededRng(seed: number) {
  let a = seed | 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function slug(s: string) {
  return s.toLowerCase().replace(/\W+/g, "-");
}

function stamp(d: Date) {
  return d.toISOString().slice(0, 16).replace("T", " ") + " UTC";
}

export function generateDemoRecords(
  seed: number,
  count: number
): DataRecord[] {
  const r = seededRng(seed);
  const pick = <T>(arr: T[]) => arr[Math.floor(r() * arr.length)];

  return Array.from({ length: count }, (_, i) => {
    const sIdx = Math.floor(r() * SOURCES.length);
    const role = pick(ROLES);
    const co = pick(COMPANIES);
    const loc = pick(LOCATIONS);
    const salLow = 18 + Math.floor(r() * 40);
    const salHigh = 45 + Math.floor(r() * 40);
    const conf = Math.round(78 + r() * 21);
    const posted = 1 + Math.floor(r() * 28);
    const method = pick(METHODS);

    return {
      id: i,
      role,
      company: co,
      location: loc,
      salary: `₹${salLow}–${salHigh} LPA`,
      posted_days_ago: posted,
      source_url: `https://${SOURCES[sIdx]}/${slug(co)}/${slug(role)}-${1000 + i}`,
      source_host: SOURCES[sIdx],
      source_index: sIdx,
      fetched_at: stamp(new Date(Date.now() - r() * 3e5)),
      extraction_method: method,
      confidence: conf,
    };
  });
}

export function generateDemoPlan(prompt: string) {
  return {
    intent: prompt,
    workflow: [
      {
        step: "Plan",
        do: "Parse request into fields, filters and freshness window",
      },
      {
        step: "Find sources",
        do: "Pick sources from the allowlist; honor robots.txt and rate limits",
      },
      {
        step: "Collect",
        do: "Fetch listing pages, follow detail links, extract fields",
      },
      {
        step: "Clean",
        do: "Normalize salary and location, validate, dedupe on role+company+location",
      },
      {
        step: "Ready",
        do: "Attach source_url and fetched_at to every record",
      },
    ],
    sources: SOURCES.map((host) => ({ host, allowlisted: true })),
    schema: {
      role: "string",
      company: "string",
      location: "string",
      salary: "string",
      posted_days_ago: "integer",
      _trace: {
        source_url: "url",
        fetched_at: "iso8601",
        method: "string",
        confidence: "0-100",
      },
    },
    dedupe_key: ["role", "company", "location"],
  };
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DataRecord {
  id: number;
  role: string;
  company: string;
  location: string;
  salary: string;
  posted_days_ago: number;
  source_url: string;
  source_host: string;
  source_index: number;
  fetched_at: string;
  extraction_method: string;
  confidence: number;
}

export interface TaskRun {
  id: number;
  prompt: string;
  rows: DataRecord[];
  dupes: number;
  when: string;
  status?: string;
  plan?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// API Functions
// ---------------------------------------------------------------------------

export async function submitTask(prompt: string) {
  try {
    const res = await fetch(`${API_BASE}/api/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.warn("Backend unreachable, using demo mode:", e);
    return null;
  }
}

export async function fetchTaskStatus(taskId: number) {
  try {
    const res = await fetch(`${API_BASE}/api/tasks/${taskId}/status`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchTaskDetails(taskId: number) {
  try {
    const res = await fetch(`${API_BASE}/api/tasks/${taskId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchAllTasks() {
  try {
    const res = await fetch(`${API_BASE}/api/tasks`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return null;
  }
}

export { SOURCES };
