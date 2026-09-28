"use client";

import { useRef, useEffect, useCallback } from "react";
import { SOURCES } from "../lib/api";

interface ConstellationProps {
  litSources: Set<number>;
  highlightSource: number;
  filterSource: number;
  pulses: Array<{ s: number; t: number }>;
  recordCount: number;
  onSourceClick: (index: number) => void;
}

// Fibonacci sphere distribution
function fib(n: number, i: number): [number, number, number] {
  const y = 1 - (2 * (i + 0.5)) / n;
  const r = Math.sqrt(1 - y * y);
  const a = i * 2.39996;
  return [Math.cos(a) * r, y, Math.sin(a) * r];
}

const PT = Array.from({ length: 170 }, (_, i) => fib(170, i));
const SN = Array.from({ length: 6 }, (_, i) => fib(6, i));

export default function Constellation({
  litSources,
  highlightSource,
  filterSource,
  pulses,
  recordCount,
  onSourceClick,
}: ConstellationProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef({
    ay: 0,
    ax: 0.35,
    drag: null as null | { x: number; y: number },
    moved: 0,
    hover: -1,
    T: 0,
    W: 0,
    H: 0,
    dpr: 1,
    scr: [] as Array<{ x: number; y: number; z: number; f: number }>,
    animationId: 0,
    reduce: false,
  });

  // Project 3D point to 2D
  const project = useCallback(
    (
      p: [number, number, number],
      k: number,
      W: number,
      H: number,
      ay: number,
      ax: number
    ) => {
      const c = Math.cos(ay),
        s = Math.sin(ay),
        c2 = Math.cos(ax),
        s2 = Math.sin(ax);
      const x = p[0] * k,
        y = p[1] * k,
        z = p[2] * k;
      const x1 = x * c - z * s,
        z1 = x * s + z * c;
      const y1 = y * c2 - z1 * s2,
        z2 = y * s2 + z1 * c2;
      const f = 700 / (700 + z2);
      const wide = W > 800;
      return {
        x: (wide ? W * 0.68 : W / 2) + x1 * f,
        y: (wide ? H * 0.48 : H * 0.72) + y1 * f,
        z: z2,
        f,
      };
    },
    []
  );

  // Glow effect
  const glow = useCallback(
    (
      cx: CanvasRenderingContext2D,
      x: number,
      y: number,
      r: number,
      col: string,
      a: number
    ) => {
      const g = cx.createRadialGradient(x, y, 0, x, y, r);
      g.addColorStop(0, col.replace("A", String(a)));
      g.addColorStop(1, col.replace("A", "0"));
      cx.fillStyle = g;
      cx.beginPath();
      cx.arc(x, y, r, 0, 7);
      cx.fill();
    },
    []
  );

  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv) return;
    const cx = cv.getContext("2d");
    if (!cx) return;

    const st = stateRef.current;
    st.reduce = window.matchMedia(
      "(prefers-reduced-motion:reduce)"
    ).matches;

    function fit() {
      if (!cv) return;
      st.dpr = Math.min(devicePixelRatio || 1, 2);
      st.W = cv.clientWidth;
      st.H = cv.clientHeight;
      cv.width = st.W * st.dpr;
      cv.height = st.H * st.dpr;
      cx!.setTransform(st.dpr, 0, 0, st.dpr, 0, 0);
    }

    const resizeObserver = new ResizeObserver(fit);
    resizeObserver.observe(cv);
    fit();

    function draw() {
      if (!cx || !cv) return;
      st.T += 0.016;
      if (!st.drag) st.ay += st.reduce ? 0.0004 : 0.0032;

      const { W, H, ay, ax } = st;
      const wide = W > 800;
      const R = wide
        ? Math.min(H * 0.34, W * 0.2)
        : Math.min(W * 0.3, H * 0.15);

      cx.clearRect(0, 0, W, H);
      cx.globalCompositeOperation = "lighter";

      // Latitude rings
      for (const lat of [-0.5, 0, 0.5]) {
        cx.beginPath();
        for (let i = 0; i <= 48; i++) {
          const a = (i / 48) * 6.2832;
          const r = Math.sqrt(1 - lat * lat);
          const p = project(
            [Math.cos(a) * r, lat, Math.sin(a) * r],
            R,
            W,
            H,
            ay,
            ax
          );
          i ? cx.lineTo(p.x, p.y) : cx.moveTo(p.x, p.y);
        }
        cx.strokeStyle = "rgba(123,245,184,.22)";
        cx.lineWidth = 1;
        cx.stroke();
      }

      // Star field
      const lightN = recordCount * 6;
      PT.forEach((p, i) => {
        const q = project(p, R, W, H, ay, ax);
        const d = 1 - (q.z + R) / (2 * R);
        const on = i < lightN;
        glow(
          cx,
          q.x,
          q.y,
          on ? 6 * q.f : 3 * q.f,
          on ? "rgba(255,255,255,A)" : "rgba(93,255,176,A)",
          (on ? 0.55 : 0.18) + 0.3 * d
        );
      });

      // Source lines to core
      const core = project([0, 0, 0], 0, W, H, ay, ax);
      litSources.forEach((s) => {
        if (!SN[s]) return; // Guard against invalid indices
        const q = project(SN[s], R * 1.22, W, H, ay, ax);
        const g = cx.createLinearGradient(q.x, q.y, core.x, core.y);
        g.addColorStop(0, "rgba(255,255,255,.6)");
        g.addColorStop(1, "rgba(60,240,160,.3)");
        cx.strokeStyle = g;
        cx.lineWidth = 1.2;
        cx.beginPath();
        cx.moveTo(q.x, q.y);
        cx.lineTo(core.x, core.y);
        cx.stroke();
      });

      // Pulses
      pulses.forEach((u) => {
        if (u.t >= 1 || !SN[u.s]) return;
        u.t += 0.02;
        const q = project(SN[u.s], R * 1.22, W, H, ay, ax);
        const x = q.x + (core.x - q.x) * u.t;
        const y = q.y + (core.y - q.y) * u.t;
        glow(cx, x, y, 10, "rgba(255,255,255,A)", 0.9);
      });

      // Core glow
      const cr =
        26 + Math.min(recordCount, 22) * 1.3 + Math.sin(st.T * 2) * 3;
      glow(cx, core.x, core.y, cr * 2.2, "rgba(18,183,106,A)", 0.55);
      glow(cx, core.x, core.y, cr, "rgba(93,255,176,A)", 0.85);
      glow(cx, core.x, core.y, cr * 0.35, "rgba(255,255,255,A)", 1);

      // Source nodes
      st.scr = [];
      cx.globalCompositeOperation = "source-over";
      cx.font =
        '600 12px "Bricolage Grotesque",system-ui,sans-serif';

      SN.forEach((p, i) => {
        const q = project(p, R * 1.22, W, H, ay, ax);
        const on = litSources.has(i);
        const act =
          i === highlightSource || i === filterSource || i === st.hover;
        st.scr[i] = q;

        cx.globalCompositeOperation = "lighter";
        glow(
          cx,
          q.x,
          q.y,
          (on ? 20 : 9) * q.f * (act ? 1.4 : 1),
          "rgba(255,255,255,A)",
          on ? 0.9 : 0.4
        );

        cx.globalCompositeOperation = "source-over";
        cx.fillStyle = on ? "#ffffff" : "#6fae92";
        cx.beginPath();
        cx.arc(q.x, q.y, 4 * q.f, 0, 7);
        cx.fill();

        if (act) {
          cx.strokeStyle = "#5dffb0";
          cx.lineWidth = 2;
          cx.beginPath();
          cx.arc(q.x, q.y, 12 * q.f, 0, 7);
          cx.stroke();
        }

        if ((on || act) && q.z < R) {
          cx.fillStyle = act ? "#fff" : "rgba(235,255,245,.8)";
          cx.fillText(SOURCES[i], q.x + 14, q.y + 4);
        }
      });

      st.animationId = requestAnimationFrame(draw);
    }

    st.animationId = requestAnimationFrame(draw);

    // Pointer events
    function nodeAt(e: PointerEvent | MouseEvent) {
      const b = cv!.getBoundingClientRect();
      const x = e.clientX - b.left;
      const y = e.clientY - b.top;
      return st.scr.findIndex(
        (q) => q && Math.hypot(q.x - x, q.y - y) < 16
      );
    }

    function onPointerDown(e: PointerEvent) {
      st.drag = { x: e.clientX, y: e.clientY };
      st.moved = 0;
      cv!.setPointerCapture(e.pointerId);
      cv!.classList.add("grabbing");
    }

    function onPointerMove(e: PointerEvent) {
      if (st.drag) {
        const dx = e.clientX - st.drag.x;
        const dy = e.clientY - st.drag.y;
        st.moved += Math.abs(dx) + Math.abs(dy);
        st.ay += dx * 0.006;
        st.ax = Math.max(-1, Math.min(1, st.ax + dy * 0.004));
        st.drag = { x: e.clientX, y: e.clientY };
      }
      st.hover = nodeAt(e);
      if (!st.drag)
        cv!.style.cursor = st.hover >= 0 ? "pointer" : "grab";
    }

    function onPointerUp(e: PointerEvent) {
      st.drag = null;
      cv!.classList.remove("grabbing");
      cv!.style.cursor = "grab";
      if (st.moved < 6) {
        const n = nodeAt(e);
        if (n >= 0 && litSources.has(n)) {
          onSourceClick(n);
        }
      }
    }

    cv.addEventListener("pointerdown", onPointerDown);
    cv.addEventListener("pointermove", onPointerMove);
    cv.addEventListener("pointerup", onPointerUp);

    return () => {
      cancelAnimationFrame(st.animationId);
      resizeObserver.disconnect();
      cv.removeEventListener("pointerdown", onPointerDown);
      cv.removeEventListener("pointermove", onPointerMove);
      cv.removeEventListener("pointerup", onPointerUp);
    };
  }, [
    litSources,
    highlightSource,
    filterSource,
    pulses,
    recordCount,
    onSourceClick,
    project,
    glow,
  ]);

  return (
    <canvas
      ref={canvasRef}
      className="stage-canvas"
      aria-label="3D constellation of data sources. Drag to rotate, click a source to filter results."
    />
  );
}
