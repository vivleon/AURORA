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
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

// Minimal, dependency-light dashboard page using Recharts
// Tabs are implemented with local state to avoid extra dependencies

type KPI = { success: number; blocked: number; p95_ms: number };

type ConsentAgg = { approved: number; denied: number; expired: number };

type SeriesPoint = { tool: string; latency_ms: number };

type BanditPoint = { ts: string; avg_reward: number };

type BanditWeight = { tool: string; weight: number };

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
        if (!r.ok) throw new Error(await r.text());
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
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps
  return { data, loading, error } as const;
};

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

  const kpi = useFetch<{ kpi: KPI }>(`/dash/kpi?window=1h`, { kpi: { success: 0, blocked: 0, p95_ms: 0 } }, [tab]);
  const latency = useFetch<{ series: SeriesPoint[] }>(`/dash/latency?p=95&window=1h`, { series: [] }, [tab]);
  const consentAgg = useFetch<{ approved: number; denied: number; expired: number }>(`/dash/consent/timeline?window=24h`, { approved: 0, denied: 0, expired: 0 }, [tab]);
  const banditPts = useFetch<{ points: BanditPoint[] }>(`/dash/bandit/reward?window=7d`, { points: [] }, [tab]);
  const banditWeights = useFetch<{ rows: BanditWeight[] }>(`/dash/bandit/weights?window=7d`, { rows: [] }, [tab]);

  const latencyData = useMemo(
    () => latency.data.series.map((d, i) => ({ idx: i, tool: d.tool, latency: d.latency_ms })),
    [latency.data.series]
  );

  const consentBars = useMemo(() => {
    // If timeline returns items, compute aggregate here; else expect server aggregate
    const anyTimeline = (consentAgg as any).data?.items as any[] | undefined;
    if (anyTimeline) {
      const agg = anyTimeline.reduce(
        (a, x) => {
          if (x.decision === "approved") a.approved++;
          else if (x.decision === "denied") a.denied++;
          else if (x.decision === "expired") a.expired++;
          return a;
        },
        { approved: 0, denied: 0, expired: 0 }
      );
      return [
        { type: "approved", count: agg.approved },
        { type: "denied", count: agg.denied },
        { type: "expired", count: agg.expired },
      ];
    }
    const agg = consentAgg.data as unknown as ConsentAgg;
    return [
      { type: "approved", count: (agg?.approved as any) ?? 0 },
      { type: "denied", count: (agg?.denied as any) ?? 0 },
      { type: "expired", count: (agg?.expired as any) ?? 0 },
    ];
  }, [consentAgg.data]);

  return (
    <div className="max-w-6xl mx-auto p-4 space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-bold">Aurora Dashboard</h1>
        <Badge>live</Badge>
      </div>
      <div className="flex gap-2">
        <Button variant={tab === "overview" ? "default" : "outline"} onClick={() => setTab("overview")}>Overview</Button>
        <Button variant={tab === "performance" ? "default" : "outline"} onClick={() => setTab("performance")}>Performance</Button>
        <Button variant={tab === "consent" ? "default" : "outline"} onClick={() => setTab("consent")}>Consent</Button>
        <Button variant={tab === "bandit" ? "default" : "outline"} onClick={() => setTab("bandit")}>Bandit</Button>
      </div>
      <Separator />

      {tab === "overview" && (
        <section className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <StatCard title="Success Rate" value={`${(kpi.data.kpi.success * 100).toFixed(1)}%`} subtitle="최근 1시간" />
            <StatCard title="Blocked Rate" value={`${(kpi.data.kpi.blocked * 100).toFixed(1)}%`} subtitle="최근 1시간" />
            <StatCard title="P95 Latency" value={`${kpi.data.kpi.p95_ms} ms`} subtitle="최근 1시간" />
          </div>
          <div className="rounded-2xl border p-4 h-[280px]">
            <h3 className="font-semibold mb-2">Consent (24h)</h3>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={consentBars}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="type" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {tab === "performance" && (
        <section className="space-y-4">
          <div className="rounded-2xl border p-4 h-[320px]">
            <h3 className="font-semibold mb-2">Latency P95 by Tool (1h)</h3>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={latencyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="tool" interval={0} angle={-15} textAnchor="end" height={70} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="latency" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {tab === "consent" && (
        <section className="space-y-4">
          <div className="rounded-2xl border p-4">
            <h3 className="font-semibold mb-2">정책 안내</h3>
            <p className="text-sm text-muted-foreground">고위험 작업은 사용자 동의가 필요합니다. TTL 만료 후 자동 철회됩니다.</p>
          </div>
        </section>
      )}

      {tab === "bandit" && (
        <section className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <div className="rounded-2xl border p-4 h-[260px]">
              <h3 className="font-semibold mb-2">Avg Reward (7d)</h3>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={banditPts.data.points}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="ts" hide />
                  <YAxis domain={[0, 1]} />
                  <Tooltip />
                  <Line type="monotone" dataKey="avg_reward" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="rounded-2xl border p-4 h-[260px]">
              <h3 className="font-semibold mb-2">Tool Weights</h3>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={banditWeights.data.rows}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="tool" interval={0} angle={-15} textAnchor="end" height={70} />
                  <YAxis domain={[0, 1]} />
                  <Tooltip />
                  <Bar dataKey="weight" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
