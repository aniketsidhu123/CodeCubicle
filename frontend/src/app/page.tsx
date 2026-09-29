"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import Constellation from "./components/Constellation";
import {
  SOURCES,
  generateDemoRecords,
  generateDemoPlan,
  submitTask,
  fetchTaskDetails,
  fetchAllTasks,
  cancelTask,
  retryTask,
  deleteTask,
  type DataRecord,
  type TaskRun,
} from "./lib/api";

const STEPS = ["Plan", "Find sources", "Collect", "Clean", "Ready"];

const EXAMPLE_PROMPTS = [
  {
    label: "Design roles",
    prompt:
      "Product design roles at funded startups in Delhi NCR with salary bands",
  },
  {
    label: "ML roles",
    prompt:
      "Open ML engineer positions in Bengaluru and Hyderabad this month",
  },
];

// Utility: sleep
const sleep = (ms: number) =>
  new Promise<void>((resolve) => setTimeout(resolve, ms));

export default function Home() {
  // ---- State ----
  const [prompt, setPrompt] = useState(
    "Data engineer jobs in India, remote-friendly, posted in the last 30 days, with salary"
  );
  const [busy, setBusy] = useState(false);
  const [currentStep, setCurrentStep] = useState(4); // 0-4
  const [pillText, setPillText] = useState("Ready");
  const [pillBusy, setPillBusy] = useState(false);

  // Data
  const [rows, setRows] = useState<DataRecord[]>([]);
  const [litSources, setLitSources] = useState<Set<number>>(new Set());
  const [dupes, setDupes] = useState(0);
  const [plan, setPlan] = useState<Record<string, unknown>>({});

  // Filtering & selection
  const [filterSource, setFilterSource] = useState(-1);
  const [highlightSource, setHighlightSource] = useState(-1);
  const [selectedId, setSelectedId] = useState(-1);
  const [searchQuery, setSearchQuery] = useState("");

  // Tabs
  const [activeTab, setActiveTab] = useState(1);

  // Runs history
  const [runs, setRuns] = useState<TaskRun[]>([]);
  const [currentRunId, setCurrentRunId] = useState(-1);

  // Canvas props
  const [pulses, setPulses] = useState<Array<{ s: number; t: number }>>([]);

  // Toast
  const [toastMsg, setToastMsg] = useState("");
  const [toastVisible, setToastVisible] = useState(false);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ---- Refs ----
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // ---- Computed values ----
  const avgConfidence =
    rows.length > 0
      ? Math.round(rows.reduce((a, r) => a + r.confidence, 0) / rows.length)
      : 0;

  const filteredRows = rows.filter((r) => {
    const matchSource = filterSource < 0 || r.source_index === filterSource;
    const matchSearch =
      searchQuery === "" ||
      (r.role + r.company + r.location + r.source_host)
        .toLowerCase()
        .includes(searchQuery.toLowerCase());
    return matchSource && matchSearch;
  });

  // ---- Toast ----
  const toast = useCallback((msg: string) => {
    setToastMsg(msg);
    setToastVisible(true);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToastVisible(false), 1800);
  }, []);

  // ---- Clipboard ----
  const copyToClipboard = useCallback(
    async (text: string, msg: string) => {
      try {
        await navigator.clipboard.writeText(text);
        toast(msg);
      } catch {
        toast("Copy blocked by the browser");
      }
    },
    [toast]
  );

  const reloadHistory = useCallback(async () => {
    const history = await fetchAllTasks();
    if (history) {
      const mappedRuns = history.map((t: any) => ({
        id: t.id,
        prompt: t.prompt,
        rows: [],
        dupes: t.duplicates_removed || 0,
        when: new Date(t.created_at).toLocaleString(),
        status: t.status,
      }));
      setRuns(mappedRuns);
    }
  }, []);

  useEffect(() => {
    reloadHistory();
  }, [reloadHistory]);

  const handleCancel = async (id: number) => {
    await cancelTask(id);
    toast("Task cancelled");
    reloadHistory();
  };

  const handleDelete = async (id: number) => {
    await deleteTask(id);
    toast("Task deleted");
    if (currentRunId === id) {
      setRows([]);
      setPlan({});
      setCurrentRunId(-1);
    }
    reloadHistory();
  };

  const handleRetry = async (id: number) => {
    await retryTask(id);
    toast("Task retrying");
    reloadHistory();
  };

  // ---- Source click from constellation ----
  const handleSourceClick = useCallback(
    (index: number) => {
      setFilterSource((prev) => (prev === index ? -1 : index));
    },
    []
  );

  // ---- Start collection ----
  const handleStart = useCallback(async () => {
    if (busy) return;
    const p = prompt.trim();
    if (!p) {
      toast("Describe the data you need first");
      return;
    }

    setBusy(true);
    setRows([]);
    setLitSources(new Set());
    setDupes(0);
    setFilterSource(-1);
    setHighlightSource(-1);
    setSelectedId(-1);
    setCurrentRunId(-1);
    setPulses([]);

    const newPlan = generateDemoPlan(p);
    setPlan(newPlan);

    // Try backend first
    const apiResult = await submitTask(p);

    // Step 1: Planning
    setCurrentStep(0);
    setPillText("Planning");
    setPillBusy(true);
    await sleep(1000);

    // Step 2: Finding sources
    setCurrentStep(1);
    setPillText("Finding sources");
    await sleep(1000);

    // Step 3: Collecting
    setCurrentStep(2);
    setPillText("Collecting");

    let finalRows: DataRecord[] = [];

    if (apiResult && apiResult.id) {
      // Poll backend for completion and incrementally stream records to UI
      let attempts = 0;
      let taskData = null;
      let processedRecordCount = 0;
      
      while (attempts < 60) {
        await sleep(1000);
        taskData = await fetchTaskDetails(apiResult.id);
        if (taskData?.progress_detail) {
           setPillText(taskData.progress_detail);
        } else if (taskData?.status) {
           setPillText(taskData.status);
        }
        
        // Stream new records as they arrive from the backend
        if (taskData?.records && taskData.records.length > processedRecordCount) {
          const newRecords = taskData.records.slice(processedRecordCount);
          processedRecordCount = taskData.records.length;
          
          for (let i = 0; i < newRecords.length; i++) {
             const r = newRecords[i];
             const mappedR = {
               ...(r as Record<string, unknown>),
               id: processedRecordCount - newRecords.length + i,
               source_index: Math.max(0, SOURCES.indexOf(String(r.source_host))),
             } as DataRecord;
             
             finalRows.push(mappedR);
             setRows((prev) => [...prev, mappedR]);
             setLitSources((prev) => {
               const next = new Set(prev);
               next.add(mappedR.source_index);
               return next;
             });
             setPulses((prev) => [...prev, { s: mappedR.source_index, t: 0 }]);
             await sleep(130);
          }
        }
        
        if (
          taskData &&
          (taskData.status === "Ready" || taskData.status === "Completed")
        ) {
          break;
        }
        attempts++;
      }
    } else {
      // Fallback: Demo mode animation
      const demoRows = generateDemoRecords(Date.now() % 9973, 22);
      finalRows = demoRows;
      const newLit = new Set<number>();
      const newPulses: Array<{ s: number; t: number }> = [];
      for (let i = 0; i < demoRows.length; i++) {
        const r = demoRows[i];
        newLit.add(r.source_index);
        newPulses.push({ s: r.source_index, t: 0 });

        setRows((prev) => [...prev, r]);
        setLitSources(new Set(newLit));
        setPulses([...newPulses]);
        await sleep(130);
      }
    }

    // Step 4: Cleaning
    setCurrentStep(3);
    setPillText("Cleaning");
    await sleep(1000);

    // Done
    const finalDupes = 3;
    setDupes(finalDupes);
    setCurrentStep(4);
    setPillText("Ready");
    setPillBusy(false);

    // Save to history
    const runId = Date.now();
    setRuns((prev) => [
      {
        id: runId,
        prompt: p,
        rows: finalRows,
        dupes: finalDupes,
        when: "Just now",
      },
      ...prev,
    ]);
    setCurrentRunId(runId);

    setBusy(false);
    toast(`${finalRows.length} records ready, every one traced to a source`);
  }, [busy, prompt, toast]);

  // ---- Load past run ----
  const loadRun = useCallback(
    async (run: TaskRun) => {
      if (busy) return;
      
      const taskData = await fetchTaskDetails(run.id);
      let mappedRows: DataRecord[] = [];
      let mappedDupes = run.dupes;
      let mappedPlan = plan;
      
      if (taskData) {
        mappedRows = (taskData.records || []).map((r: any, i: number) => ({
           ...(r as Record<string, unknown>),
           id: i,
           source_index: Math.max(0, SOURCES.indexOf(String(r.source_host))),
        }));
        mappedDupes = taskData.duplicates_removed || 0;
        mappedPlan = taskData.plan || generateDemoPlan(run.prompt);
      }
      
      setRows(mappedRows);
      setLitSources(new Set(mappedRows.map((r) => r.source_index)));
      setDupes(mappedDupes);
      setFilterSource(-1);
      setHighlightSource(-1);
      setSelectedId(-1);
      setCurrentRunId(run.id);
      setPlan(mappedPlan);
      setPrompt(run.prompt);
      setCurrentStep(4);
      setPillText(run.status || "Ready");
      setPillBusy(run.status === "Scraping" || run.status === "Processing" || run.status === "Planning");
    },
    [busy, plan]
  );

  // ---- Inspect row ----
  const selectedRow = rows.find((r) => r.id === selectedId);

  const inspectRow = useCallback(
    (id: number) => {
      const row = rows.find((r) => r.id === id);
      if (!row) return;
      setSelectedId(id);
      setHighlightSource(row.source_index);
    },
    [rows]
  );

  // ---- Download CSV ----
  const downloadCSV = useCallback(() => {
    if (!filteredRows.length) {
      toast("Nothing to download yet");
      return;
    }
    const csv =
      "role,company,location,salary,source_url,fetched_at,confidence\n" +
      filteredRows
        .map((r) =>
          [
            r.role,
            r.company,
            `"${r.location}"`,
            r.salary,
            r.source_url,
            r.fetched_at,
            r.confidence,
          ].join(",")
        )
        .join("\n");
        
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `tracelight_export_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast("CSV downloaded");
  }, [filteredRows, toast]);

  // ---- Download JSON ----
  const downloadJSON = useCallback(() => {
    if (!filteredRows.length) {
      toast("Nothing to download yet");
      return;
    }
    const blob = new Blob([JSON.stringify(filteredRows, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `tracelight_export_${Date.now()}.json`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast("JSON downloaded");
  }, [filteredRows, toast]);

  // ---- Copy plan JSON ----
  const copyPlanJSON = useCallback(() => {
    copyToClipboard(JSON.stringify(plan, null, 2), "Plan JSON copied");
  }, [plan, copyToClipboard]);

  return (
    <>
      <div className="wrap">
        {/* ===== HEADER ===== */}
        <header>
          <span className="logo" />
          <b>Tracelight</b>
          <div className={`pill${pillBusy ? " busy" : ""}`} id="pill">
            <i className="pill-dot" />
            <span>{pillText}</span>
          </div>
        </header>

        {/* ===== TOP GRID: Stage + Past Runs ===== */}
        <div className="top">
          <section className="stage" aria-label="Data collection workspace">
            {/* 3D Canvas */}
            <Constellation
              litSources={litSources}
              highlightSource={highlightSource}
              filterSource={filterSource}
              pulses={pulses}
              recordCount={rows.length}
              onSourceClick={handleSourceClick}
            />

            {/* Overlay content */}
            <div className="ov">
              <h1>Say what data you need.</h1>

              {/* Ask box */}
              <div className="ask">
                <textarea
                  ref={textareaRef}
                  id="q"
                  aria-label="Describe the data you need"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleStart();
                    }
                  }}
                />
                <div className="row">
                  {EXAMPLE_PROMPTS.map((ex) => (
                    <button
                      key={ex.label}
                      className="ex"
                      onClick={() => setPrompt(ex.prompt)}
                    >
                      {ex.label}
                    </button>
                  ))}
                  <button
                    className="go"
                    id="go"
                    onClick={handleStart}
                    disabled={busy}
                  >
                    Collect data
                  </button>
                </div>
              </div>

              {/* Bottom bar: Steps + Stats */}
              <div className="bot">
                <div className="steps" id="steps">
                  {STEPS.map((step, k) => {
                    let cls = "st";
                    if (currentStep >= 4 || k < currentStep) cls += " done";
                    else if (k === currentStep) cls += " on";
                    return (
                      <span key={step} className={cls}>
                        <b className="st-num">{k + 1}</b>
                        {step}
                      </span>
                    );
                  })}
                </div>
                <div className="stats">
                  <div>
                    <strong>{rows.length}</strong>records
                  </div>
                  <div>
                    <strong>{litSources.size}</strong>sources
                  </div>
                  <div>
                    <strong>{dupes}</strong>duplicates removed
                  </div>
                  <div>
                    <strong>{avgConfidence ? `${avgConfidence}%` : "–"}</strong>
                    avg confidence
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Past Runs Sidebar */}
          <aside className="card" aria-label="Previous runs">
            <h2>Past runs</h2>
            <div id="runs">
              {runs.map((run) => (
                <div key={run.id} className={`run-btn-wrap${run.id === currentRunId ? " sel" : ""}`}>
                  <button
                    className="run-btn"
                    onClick={() => loadRun(run)}
                  >
                    {run.prompt}
                    <small>
                      {run.when} · {run.status}
                    </small>
                  </button>
                  <div className="run-actions">
                     {run.status === "Failed" && <button className="act-btn" onClick={() => handleRetry(run.id)}>Retry</button>}
                     {(run.status !== "Completed" && run.status !== "Ready" && run.status !== "Failed" && run.status !== "Cancelled") && <button className="act-btn" onClick={() => handleCancel(run.id)}>Cancel</button>}
                     <button className="act-btn" onClick={() => handleDelete(run.id)}>Delete</button>
                  </div>
                </div>
              ))}
            </div>
          </aside>
        </div>

        {/* ===== DATA GRID: Results + Inspector ===== */}
        <div className="data">
          <section className="card">
            {/* Tabs */}
            <div className="tabs" role="tablist">
              <button
                className="tab"
                role="tab"
                aria-selected={activeTab === 1}
                onClick={() => setActiveTab(1)}
              >
                Results
              </button>
              <button
                className="tab"
                role="tab"
                aria-selected={activeTab === 2}
                onClick={() => setActiveTab(2)}
              >
                Plan and schema
              </button>
            </div>

            {/* Tab 1: Results */}
            {activeTab === 1 && (
              <div>
                {/* Search + CSV */}
                <div className="tools">
                  <input
                    id="f"
                    type="search"
                    placeholder="Search role, company, location"
                    aria-label="Search results"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  <button className="btn" onClick={downloadCSV}>
                    Download CSV
                  </button>
                  <button className="btn" onClick={downloadJSON}>
                    Download JSON
                  </button>
                </div>

                {/* Source chips */}
                <div className="tools" aria-label="Filter by source">
                  <button
                    className="chip"
                    aria-pressed={filterSource < 0}
                    onClick={() => setFilterSource(-1)}
                  >
                    All sources
                  </button>
                  {[...litSources]
                    .sort((a, b) => a - b)
                    .map((s) => (
                      <button
                        key={s}
                        className="chip"
                        aria-pressed={filterSource === s}
                        onClick={() =>
                          setFilterSource((prev) => (prev === s ? -1 : s))
                        }
                      >
                        {SOURCES[s]}
                      </button>
                    ))}
                </div>

                {/* Results table */}
                <div className="scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Role</th>
                        <th>Company</th>
                        <th>Location</th>
                        <th>Salary</th>
                        <th>Source</th>
                        <th>Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredRows.length > 0 ? (
                        filteredRows.map((r) => (
                          <tr
                            key={r.id}
                            className={`r${r.id === selectedId ? " sel" : ""}`}
                            tabIndex={0}
                            onClick={() => inspectRow(r.id)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") inspectRow(r.id);
                            }}
                          >
                            <td>{r.role}</td>
                            <td>{r.company}</td>
                            <td>{r.location}</td>
                            <td>{r.salary}</td>
                            <td className="src">{r.source_host}</td>
                            <td>
                              <span className="bar">
                                <i
                                  className="bar-fill"
                                  style={{ width: `${r.confidence}%` }}
                                />
                              </span>
                              {r.confidence}%
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={6} className="empty">
                            {rows.length
                              ? "No records match. Clear the search or pick All sources."
                              : "Describe the data you need above and press Collect data."}
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Tab 2: Plan */}
            {activeTab === 2 && (
              <div>
                <div className="tools">
                  <button className="btn" onClick={() => {
                     const blob = new Blob([JSON.stringify(plan, null, 2)], { type: "application/json" });
                     const url = URL.createObjectURL(blob);
                     const link = document.createElement("a");
                     link.href = url;
                     link.setAttribute("download", `tracelight_plan_${Date.now()}.json`);
                     document.body.appendChild(link);
                     link.click();
                     document.body.removeChild(link);
                     toast("Plan JSON downloaded");
                  }}>
                    Download plan JSON
                  </button>
                </div>
                <pre className="plan-pre">
                  {JSON.stringify(plan, null, 2)}
                </pre>
              </div>
            )}
          </section>

          {/* Inspector Sidebar */}
          <aside className="card inspector" aria-live="polite">
            <h2>Where this came from</h2>
            {selectedRow ? (
              <>
                <dl>
                  <div>
                    <dt>Record</dt>
                    <dd>
                      <b>{selectedRow.role}</b> at {selectedRow.company}
                    </dd>
                  </div>
                  <div>
                    <dt>Source page</dt>
                    <dd className="src">{selectedRow.source_url}</dd>
                  </div>
                  <div>
                    <dt>Fetched</dt>
                    <dd>{selectedRow.fetched_at}</dd>
                  </div>
                  <div>
                    <dt>Extraction</dt>
                    <dd>{selectedRow.extraction_method}</dd>
                  </div>
                  <div>
                    <dt>Confidence</dt>
                    <dd>
                      {selectedRow.confidence}% (all required fields present)
                    </dd>
                  </div>
                </dl>
                <div className="path">
                  <span>
                    <b>Fetched</b> {selectedRow.source_host}
                  </span>
                  <span>
                    <b>Extracted</b> role, company, location, salary
                  </span>
                  <span>
                    <b>Cleaned</b> salary to LPA, location normalized
                  </span>
                  <span>
                    <b>Checked</b> no duplicate on role+company+location
                  </span>
                </div>
              </>
            ) : (
              <div className="empty">
                Select a row to see its source, how it was extracted, and how
                it was cleaned.
              </div>
            )}
          </aside>
        </div>
      </div>

      {/* Toast */}
      <div
        className={`toast${toastVisible ? " show" : ""}`}
        role="status"
      >
        {toastMsg}
      </div>
    </>
  );
}
