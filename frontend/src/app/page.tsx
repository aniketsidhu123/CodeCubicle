"use client";

import { useState } from "react";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [taskResult, setTaskResult] = useState<any>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    
    setIsSubmitting(true);
    try {
      const response = await fetch("http://localhost:8000/api/tasks", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ prompt }),
      });
      const data = await response.json();
      setTaskResult(data);
    } catch (error) {
      console.error("Error submitting task:", error);
      alert("Failed to submit task to the backend.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="container">
      <div style={{ textAlign: "center", marginBottom: "3rem" }}>
        <h1 className="header-title">Data Intelligence Platform</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "1.2rem" }}>
          Transform natural language into structured datasets instantly.
        </p>
      </div>

      <div className="glass-panel" style={{ padding: "2rem", maxWidth: "800px", margin: "0 auto" }}>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <label htmlFor="prompt" style={{ fontWeight: 600, fontSize: "1.1rem" }}>
            Describe the data you need:
          </label>
          <textarea
            id="prompt"
            className="input-field"
            rows={4}
            placeholder="e.g. Find all remote Software Engineer job openings on YCombinator and extract the job title, company name, and link."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
          <button type="submit" className="btn-primary" disabled={isSubmitting}>
            {isSubmitting ? "Initializing Agent..." : "Generate Workflow & Collect Data"}
          </button>
        </form>
      </div>

      {taskResult && (
        <div className="glass-panel" style={{ padding: "2rem", maxWidth: "800px", margin: "2rem auto", marginTop: "2rem" }}>
          <h2 style={{ marginBottom: "1rem", color: "var(--accent)" }}>Workflow Generated</h2>
          <div style={{ background: "rgba(0,0,0,0.3)", padding: "1rem", borderRadius: "8px", overflowX: "auto" }}>
            <pre style={{ fontSize: "0.9rem", color: "var(--success)" }}>
              {JSON.stringify(taskResult, null, 2)}
            </pre>
          </div>
          <p style={{ marginTop: "1rem", color: "var(--text-secondary)" }}>
            Task ID: <strong>{taskResult.id}</strong> (Executing in background...)
          </p>
        </div>
      )}
    </main>
  );
}
