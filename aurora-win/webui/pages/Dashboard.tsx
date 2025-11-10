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
// (가정) shadcn/ui 컴포넌트가 @/components/ui/ 경로에 설치되어 있음
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
// [FIX]: 경로 수정. "@/webui/components/WhyHowChips" -> "@/components/WhyHowChips"
import { WhyHowChips } from "@/components/WhyHowChips";
// RAG 패널 임포트 (대시보드 Overview 탭에 추가)
import RagPanel from "@/webui_RagPanel";

// API 응답 타입 정의
type KPI = { success: number; blocked: number; p95_ms: number };
type ConsentAgg = { approved: number; denied: number; expired: number };
type SeriesPoint = { tool: string; latency_ms: number };
type BanditPoint = { ts: string; avg_reward: number };
type BanditWeight = { tool: string; weight: number };
type ConsentTimelineItem = { ts: string, action: string, decision: string, session_id: string };

// 공용 데이터 페치(fetch) 훅
const useFetch = <T,>(path: string, initial: T, deps: any[] = []) => {
  const [data, setData] = useState<T>(initial);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const r = await fetch(path);
        if (!r.ok) throw new Error(`[${r.status}] ${await r.text()}`);
        const j = await r.json();
        if (!cancelled) setData(j);
      } catch (e: any) {
        if (!cancelled) setError(e?.message ?? "Fetch failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps]); // deps 배열을 통해 탭 변경 시 다시 불러오기
  
  return { data, loading, error } as const;
};

// 통계 카드 컴포넌트
function StatCard({ title, value, subtitle }: { title: string; value: React.ReactNode; subtitle?: string }) {
  return (
    <div className="rounded-2xl border p-4">
      <div className="text-sm text-muted-foreground">{title}</div>
      <div className="text-2xl font-semibold mt-1">{value}</div>
      {subtitle && <div className="text-xs text-muted-foreground mt-1">{subtitle}</div>}
    </div>
  );
}

export default function DashboardPage() {
  const [tab, setTab] = useState<"overview" | "performance" | "consent" | "bandit">("overview");

  // 1. Overview 탭 데이터
  const kpi = useFetch<{ kpi: KPI }>(`/dash/kpi?window=1h`, { kpi: { success: 0, blocked: 0, p95_ms: 0 } }, [tab]);
  const consentAgg = useFetch<{ items: ConsentTimelineItem[] }>(`/dash/consent/timeline?window=24h`, { items: [] }, [tab]);
  // RAG 패널은 내부적으로 자체 데이터를 fetch합니다.
  
  // 2. Performance 탭 데이터
  const latency = useFetch<{ series: SeriesPoint[] }>(`/dash/latency?p=95&window=1h`, { series: [] }, [tab]);
  const errors = useFetch<{ rows: { tool: string, err_code: string, count: number }[] }>(`/dash/errors/top?window=1h`, { rows: [] }, [tab]);

  // 3. Consent 탭 데이터
  const highRisk = useFetch<{ rows: ConsentTimelineItem[] }>(`/dash/highrisk?window=24h`, { rows: [] }, [tab]);

  // 4. Bandit 탭 데이터
  const banditPts = useFetch<{ points: BanditPoint[] }>(`/dash/bandit/reward?window=7d`, { points: [] }, [tab]);
  const banditWeights = useFetch<{ rows: BanditWeight[] }>(`/dash/bandit/weights?window=7d`, { rows: [] }, [tab]);

  // 차트 데이터 가공
  const latencyData = useMemo(
    () => latency.data.series.map((d, i) => ({ idx: i, tool: d.tool || "N/A", latency: d.latency_ms })),
    [latency.data.series]
  );

  const consentBars = useMemo(() => {
    // /dash/consent/timeline 응답(items 배열)을 집계
    const agg = consentAgg.data.items.reduce(
      (a, x) => {
        if (x.decision === "approved") a.approved++;
        else if (x.decision === "denied") a.denied++;
        else if (x.decision === "expired") a.expired++;
        return a;
      },
      { approved: 0, denied: 0, expired: 0 }
    );
    return [
      { type: "approved", count: agg.approved, fill: "var(--color-ok, #a6e3a1)" },
      { type: "denied", count: agg.denied, fill: "var(--color-err, #f38ba8)" },
      { type: "expired", count: agg.expired, fill: "var(--color-warn, #f9e2af)" },
    ];
  }, [consentAgg.data]);

  const banditRewardData = useMemo(
    () => banditPts.data.points.map(p => ({ ts: new Date(p.ts).toLocaleTimeString(), reward: p.avg_reward })),
    [banditPts.data.points]
  );

  return (
    <div className="max-w-6xl mx-auto p-4 space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-bold">Aurora Dashboard</h1>
        <Badge>Live</Badge>
      </div>
      <div className="flex gap-2 flex-wrap">
        <Button variant={tab === "overview" ? "default" : "outline"} onClick={() => setTab("overview")}>Overview</Button>
        <Button variant={tab === "performance" ? "default" : "outline"} onClick={() => setTab("performance")}>Performance</Button>
        <Button variant={tab === "consent" ? "default" : "outline"} onClick={() => setTab("consent")}>Security & Consent</Button>
        <Button variant={tab === "bandit" ? "default" : "outline"} onClick={() => setTab("bandit")}>Bandit Analytics</Button>
      </div>
      <Separator />

      {/* 1. Overview 탭 */}
      {tab === "overview" && (
        <section className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <StatCard title="Success Rate" value={kpi.loading ? "..." : `${(kpi.data.kpi.success * 100).toFixed(1)}%`} subtitle="최근 1시간" />
            <StatCard title="Blocked Rate" value={kpi.loading ? "..." : `${(kpi.data.kpi.blocked * 100).toFixed(1)}%`} subtitle="최근 1시간" />
            <StatCard title="P95 Latency" value={kpi.loading ? "..." : `${kpi.data.kpi.p95_ms} ms`} subtitle="최근 1시간" />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <div className="rounded-2xl border p-4 h-[280px]">
              <h3 className="font-semibold mb-2">Consent (24h)</h3>
              <ResponsiveContainer width="100%" height="calc(100% - 30px)">
                <BarChart data={consentBars}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="type" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="count" fill="#8884d8" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            {/* RAG 패널 삽입 */}
            <RagPanel />
          </div>
        </section>
      )}

      {/* 2. Performance 탭 */}
      {tab === "performance" && (
        <section className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <div className="rounded-2xl border p-4 h-[320px]">
              <h3 className="font-semibold mb-2">Latency P95 by Tool (1h)</h3>
              <ResponsiveContainer width="100%" height="calc(100% - 30px)">
                <BarChart data={latencyData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="tool" interval={0} angle={-15} textAnchor="end" height={70} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="latency" fill="#89b4fa" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="rounded-2xl border p-4 h-[320px]">
              <h3 className="font-semibold mb-2">Top Errors (1h)</h3>
              <div className="overflow-auto h-[260px]">
                <table className="w-full text-sm">
                  <thead><tr className="text-left text-muted-foreground"><th className="py-2 pr-2">Tool</th><th className="py-2 pr-2">Error</th><th className="py-2 pr-2">Count</th></tr></thead>
                  <tbody>
                    {errors.data.rows.map((r, i) => (
                      <tr key={i} className="border-t"><td className="py-2 pr-2">{r.tool}</td><td className="py-2 pr-2">{r.err_code}</td><td className="py-2 pr-2">{r.count}</td></tr>
                    ))}
                    {!errors.loading && !errors.data.rows.length && (
                      <tr><td className="py-4 text-muted-foreground" colSpan={3}>No errors</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* 3. Consent 탭 */}
      {tab === "consent" && (
        <section className="space-y-4">
          <div className="rounded-2xl border p-4">
            <h3 className="font-semibold mb-2">High-Risk Executions (24h)</h3>
            <div className="overflow-auto h-[300px]">
              <table className="w-full text-sm">
                <thead><tr className="text-left text-muted-foreground"><th className="py-2 pr-2">Time</th><th className="py-2 pr-2">Action</th><th className="py-2 pr-2">Decision</th><th className="py-2 pr-2">Session</th></tr></thead>
                <tbody>
                  {highRisk.data.rows.map((r, i) => (
                    <tr key={i} className="border-t">
                      <td className="py-2 pr-2">{new Date(r.ts).toLocaleTimeString()}</td>
                      <td className="py-2 pr-2">{r.action}</td>
                      <td className="py-2 pr-2"><Badge variant={r.decision === 'approved' ? 'default' : 'destructive'}>{r.decision}</Badge></td>
                      <td className="py-2 pr-2 truncate max-w-[100px]">{r.session_id}</td>
                    </tr>
                  ))}
                  {!highRisk.loading && !highRisk.data.rows.length && (
                      <tr><td className="py-4 text-muted-foreground" colSpan={4}>No high-risk actions</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}

      {/* 4. Bandit 탭 */}
      {tab === "bandit" && (
        <section className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <div className="rounded-2xl border p-4 h-[260px]">
              <h3 className="font-semibold mb-2">Avg Reward (7d)</h3>
              <ResponsiveContainer width="100%" height="calc(100% - 30px)">
                <LineChart data={banditRewardData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="ts" hide />
                  <YAxis domain={[0, 1]} />
                  <Tooltip />
                  <Line type="monotone" dataKey="reward" stroke="#89b4fa" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="rounded-2xl border p-4 h-[260px]">
              <h3 className="font-semibold mb-2">Tool Weights</h3>
              <ResponsiveContainer width="100%" height="calc(100% - 30px)">
                <BarChart data={banditWeights.data.rows}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="tool" interval={0} angle={-15} textAnchor="end" height={70} />
                  <YAxis domain={[0, 1]} />
                  <Tooltip />
                  <Bar dataKey="weight" fill="#a6e3a1" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}