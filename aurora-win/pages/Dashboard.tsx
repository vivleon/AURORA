"use client";
import React, { useEffect, useMemo, useState } from "react";
import {
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  BarChart,
  Bar,
  ResponsiveContainer,
} from "recharts";
import RagPanel from "@/webui_RagPanel"; // RAG 패널 재사용

// --- 데이터 Fetching (기존과 동일) ---
type KPI = { success: number; blocked: number; p95_ms: number };
type SeriesPoint = { tool: string; latency_ms: number };
type BanditWeight = { tool: string; weight: number };
type ConsentTimelineItem = { ts: string, action: string, decision: string, session_id: string };

const useFetch = <T,>(path: string, initial: T, deps: any[] = []) => {
  const [data, setData] = useState<T>(initial);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(path); // next.config.js의 proxy가 8000번 포트로 보냄
        if (!r.ok) throw new Error(`[${r.status}] ${await r.text()}`);
        const j = await r.json();
        if (!cancelled) setData(j);
      } catch (e: any) {
        // (오류 무시)
      }
    })();
    return () => { cancelled = true; };
  }, [path, ...deps]);
  return { data } as const;
};

// --- 신규 UI 컴포넌트 ---
const HudPanel: React.FC<{ title: string; children: React.ReactNode, className?: string }> = ({ title, children, className = "" }) => (
  <div className={`border border-hud-cyan-dark bg-hud-bg/50 p-4 rounded-lg backdrop-blur-sm ${className}`}>
    <h3 className="text-hud-cyan font-bold text-lg mb-3 tracking-widest uppercase">{title}</h3>
    <div className="text-hud-text-muted">{children}</div>
  </div>
);

const HudStat: React.FC<{ title: string; value: string; unit?: string }> = ({ title, value, unit }) => (
  <div className="text-left">
    <div className="text-sm text-hud-text-muted uppercase tracking-wider">{title}</div>
    <div className="text-4xl text-hud-text font-light mt-1">
      {value} <span className="text-xl text-hud-text-muted">{unit}</span>
    </div>
  </div>
);

// --- 메인 대시보드 (자비스 스타일) ---
export default function DashboardPage() {
  const [tab, setTab] = useState<"overview" | "performance" | "security_consent" | "bandit">("overview");

  // 데이터 Fetching (기존과 동일)
  const kpi = useFetch<{ kpi: KPI }>(`/dash/kpi?window=1h`, { kpi: { success: 0, blocked: 0, p95_ms: 0 } }, [tab]);
  const latency = useFetch<{ series: SeriesPoint[] }>(`/dash/latency?p=95&window=1h`, { series: [] }, [tab]);
  const highRisk = useFetch<{ rows: ConsentTimelineItem[] }>(`/dash/highrisk?window=24h`, { rows: [] }, [tab]);
  const banditWeights = useFetch<{ rows: BanditWeight[] }>(`/dash/bandit/weights?window=7d`, { rows: [] }, [tab]);

  // 차트 데이터 (기존과 동일)
  const latencyData = useMemo(() => latency.data.series.map((d) => ({ name: d.tool || "N/A", value: d.latency_ms })), [latency.data.series]);
  const banditData = useMemo(() => banditWeights.data.rows.map(d => ({ name: d.tool, value: d.weight })), [banditWeights.data.rows]);

  return (
    <main className="p-8 h-screen flex flex-col max-w-7xl mx-auto space-y-4">
      {/* 1. 헤더 */}
      <div className="flex justify-between items-center border-b border-hud-cyan-dark pb-3">
        <h1 className="text-4xl font-light text-hud-cyan tracking-widest">AURORA SYSTEM</h1>
        <div className="text-right">
          <div className="text-lg text-hud-cyan">LIVE</div>
          <div className="text-sm text-hud-text-muted">Mode: Reactive-Proactive</div>
        </div>
      </div>

      {/* 2. 탭 (기존과 동일) */}
      <div className="flex gap-2">
        <Button variant={tab === "overview" ? "default" : "outline"} onClick={() => setTab("overview")}>Overview</Button>
        <Button variant={tab === "performance" ? "default" : "outline"} onClick={() => setTab("performance")}>Performance</Button>
        <Button variant={tab === "security_consent" ? "default" : "outline"} onClick={() => setTab("security_consent")}>Security & Consent</Button>
        <Button variant={tab === "bandit" ? "default" : "outline"} onClick={() => setTab("bandit")}>Bandit Analytics</Button>
      </div>

      {/* 3. 메인 그리드 */}
      <div className="flex-1 grid grid-cols-4 grid-rows-3 gap-4">
        
        {/* 중앙 통계 (Overview) */}
        {tab === "overview" && (
          <>
            <HudPanel title="Key Performance Indicators" className="col-span-3 row-span-1 grid grid-cols-3 gap-4">
               <HudStat title="Success Rate" value={(kpi.data.kpi.success * 100).toFixed(1)} unit="%" />
               <HudStat title="Blocked Rate" value={(kpi.data.kpi.blocked * 100).toFixed(1)} unit="%" />
               <HudStat title="P95 Latency" value={kpi.data.kpi.p95_ms.toString()} unit="ms" />
            </HudPanel>
            <HudPanel title="RAG Quality" className="col-span-1 row-span-3">
              <RagPanel />
            </HudPanel>
            <HudPanel title="Tools (Mock)" className="col-span-3 row-span-2">
              <p className="text-hud-text-muted"> (TODO: Add Tool Status / Input Box) </p>
            </HudPanel>
          </>
        )}

        {/* Performance 탭 */}
        {tab === "performance" && (
          <HudPanel title="P95 Latency (ms)" className="col-span-4 row-span-3">
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={latencyData}>
                <XAxis dataKey="name" stroke="#7A9AAB" />
                <YAxis stroke="#7A9AAB" />
                <Tooltip wrapperClassName="bg-hud-bg" />
                <Bar dataKey="value" fill="#00BFFF" />
              </BarChart>
            </ResponsiveContainer>
          </HudPanel>
        )}

        {/* Consent 탭 */}
        {tab === "security_consent" && (
          <HudPanel title="High-Risk Executions (24h)" className="col-span-4 row-span-3">
             <table className="w-full text-left text-sm">
                <thead><tr><th>Time</th><th>Action</th><th>Decision</th></tr></thead>
                <tbody>
                  {highRisk.data.rows.map((r, i) => (
                    <tr key={i} className="border-t border-hud-cyan-dark/50">
                      <td className="py-2">{new Date(r.ts).toLocaleTimeString()}</td>
                      <td className="py-2">{r.action}</td>
                      <td className="py-2 text-hud-accent">{r.decision}</td>
                    </tr>
                  ))}
                </tbody>
             </table>
          </HudPanel>
        )}

        {/* Bandit 탭 */}
        {tab === "bandit" && (
          <HudPanel title="Tool Weights (Learned)" className="col-span-4 row-span-3">
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={banditData}>
                <XAxis dataKey="name" stroke="#7A9AAB" />
                <YAxis stroke="#7A9AAB" />
                <Tooltip wrapperClassName="bg-hud-bg" />
                <Bar dataKey="value" fill="#FFA500" />
              </BarChart>
            </ResponsiveContainer>
          </HudPanel>
        )}

      </div>
    </main>
  );
}

// [신규] shadcn/ui 폴더가 아닌 곳에 있는 컴포넌트를 위한 임시 버튼 (스타일 적용)
const Button: React.FC<{ variant: string; onClick: () => void; children: React.ReactNode }> = ({ variant, onClick, children }) => (
  <button 
    onClick={onClick} 
    className={`px-4 py-1.5 rounded-md text-sm font-medium ${
      variant === 'default' 
      ? 'bg-hud-cyan text-hud-bg' 
      : 'border border-hud-cyan-dark text-hud-text-muted hover:bg-hud-cyan-dark/30'
    }`}
  >
    {children}
  </button>
);
