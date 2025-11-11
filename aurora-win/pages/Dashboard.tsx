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
import RagPanel from "@/webui_RagPanel";

// --- SystemInfo 타입 및 Hook ---
type SystemInfo = {
  location: string;
  timestamp_utc: string;
  weather: {
    description: string;
    temperature_c: number;
    humidity_percent: number;
  };
  // [FIX] 'system_load' 타입을 추가합니다.
  system_load: {
    cpu_usage_percent: number;
    ram_free_gb: number;
    network_status: string;
  };
  status?: string; // API 오류 처리용
};

// [수정] SystemInfo를 직접 /aurora/execute 를 통해 가져오도록 수정
const useSystemInfo = () => {
    const [info, setInfo] = useState<SystemInfo | null>(null);
    useEffect(() => {
        const fetchInfo = async () => {
            try {
                // /aurora/execute 엔드포인트로 system_info 도구 실행 요청
                const r = await fetch(`/aurora/execute`, { 
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        plan: { steps: [{ tool: "system_info", op: "get_info", args: {} }] },
                        session_id: "system-info-fetch"
                    }),
                });

                if (!r.ok) throw new Error("API failed");
                const j = await r.json();
                
                // executor.run()의 결과 구조: j.result[0].out 에 담겨있음
                const result = j.result[0]?.out;
                
                if (result && result.status === 'ok' && result.system_load) {
                    setInfo(result as SystemInfo); 
                } else {
                    throw new Error("Tool failed");
                }
            } catch (e) {
                console.error("Failed to fetch system info:", e);
                setInfo({
                    timestamp_utc: new Date().toISOString(),
                    location: "Error",
                    weather: { description: "Offline", temperature_c: 0, humidity_percent: 0 },
                    status: "Error Loading Data",
                    // [FIX] system_load 기본값 추가
                    system_load: { cpu_usage_percent: 0, ram_free_gb: 0, network_status: "N/A" } 
                } as SystemInfo);
            }
        };
        fetchInfo();
        const interval = setInterval(fetchInfo, 30000); // 30초마다 갱신
        return () => clearInterval(interval);
    }, []);
    return info;
};


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
        const r = await fetch(path); 
        if (!r.ok) throw new Error(`[${r.status}] ${await r.text()}`);
        const j = await r.json();
        if (!cancelled) setData(j);
      } catch (e: any) {
        // console.warn("Fetch error:", e.message);
      }
    })();
    return () => { cancelled = true; };
  }, [path, ...deps]);
  return { data } as const;
};

// --- UI 컴포넌트 ---
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

// --- Command Input Area Component (상호작용) ---
const CommandInput: React.FC = () => {
    const [command, setCommand] = useState('');
    const [output, setOutput] = useState('시스템 명령 대기 중...');

    const sendCommand = async () => {
        setOutput('계획 및 실행 중...');
        const sessionId = `user-cmd-${Date.now()}`;

        try {
            // 1. Plan: 사용자 입력을 계획으로 변환
            const planResp = await fetch('/aurora/plan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ input: command, context: {} }),
            });
            const planData = await planResp.json();
            if (!planResp.ok) throw new Error(`Plan Failed: ${planData.detail || planData.error}`);
            
            const plan = planData.plan;

            // 2. Execute: 계획 실행
            const execResp = await fetch('/aurora/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ plan: plan, session_id: sessionId }),
            });
            const execData = await execResp.json();
            
            if (execData.requires_consent) {
                // 고위험 작업 (자비스가 동의를 요청하는 부분)
                setOutput(`[CONSENT REQUIRED] Action: ${execData.requires_consent.action}\nPurpose: ${execData.requires_consent.purpose}\n\n-> Approve Token: ${execData.requires_consent.token}`);
                // TODO: ConsentModal을 띄우는 로직 필요
            } else if (execResp.ok) {
                // 성공적으로 실행 완료
                const result = execData.result[0]?.out;
                setOutput(`[SUCCESS] Tool: ${plan.steps[0].tool}.${plan.steps[0].op}\nResult: ${JSON.stringify(result, null, 2)}`);
            } else {
                throw new Error(`Execution Failed: ${execData.detail || JSON.stringify(execData)}`);
            }

        } catch (e: any) {
            setOutput(`[ERROR] ${e.message}`);
        }
    };

    return (
        <HudPanel title="COMMAND INTERFACE" className="mt-4 col-span-3">
            <div className="flex space-x-2">
                <input 
                    type="text" 
                    value={command} 
                    onChange={(e) => setCommand(e.target.value)}
                    onKeyPress={(e) => { if (e.key === 'Enter') sendCommand(); }} 
                    placeholder="여기에 명령어를 입력하세요. (예: 내일 일정 알려줘)"
                    className="flex-1 p-2 bg-hud-bg/70 border border-hud-cyan-dark text-hud-text focus:outline-none"
                />
                <Button variant="default" onClick={sendCommand} className="bg-hud-accent text-hud-bg">
                    SEND
                </Button>
            </div>
            <pre className="mt-3 p-2 bg-hud-bg/50 border border-hud-cyan-dark/50 text-hud-text-muted text-xs whitespace-pre-wrap h-20 overflow-y-auto">
                {output}
            </pre>
        </HudPanel>
    );
}


// --- 메인 대시보드 (자비스 스타일) ---
export default function DashboardPage() {
  const [tab, setTab] = useState<"overview" | "performance" | "security_consent" | "bandit">("overview");
  const systemInfo = useSystemInfo(); 
  
  // 데이터 Fetching 
  const kpi = useFetch<{ kpi: KPI }>(`/dash/kpi?window=1h`, { kpi: { success: 0, blocked: 0, p95_ms: 0 } }, [tab]);
  const latency = useFetch<{ series: SeriesPoint[] }>(`/dash/latency?p=95&window=1h`, { series: [] }, [tab]);
  const highRisk = useFetch<{ rows: ConsentTimelineItem[] }>(`/dash/highrisk?window=24h`, { rows: [] }, [tab]);
  const banditWeights = useFetch<{ rows: BanditWeight[] }>(`/dash/bandit/weights?window=7d`, { rows: [] }, [tab]);

  // 차트 데이터 (간결화)
  const latencyData = useMemo(() => latency.data.series.map((d) => ({ name: d.tool || "N/A", value: d.latency_ms })), [latency.data.series]);
  const banditData = useMemo(() => banditWeights.data.rows.map(d => ({ name: d.tool, value: d.weight })), [banditWeights.data.rows]);

  return (
    <main className="p-8 h-screen flex flex-col max-w-7xl mx-auto space-y-4">
      {/* 1. 헤더 (환경 정보 포함) */}
      <div className="flex justify-between items-center border-b border-hud-cyan-dark pb-3">
        <h1 className="text-4xl font-light text-hud-cyan tracking-widest">AURORA SYSTEM</h1>
        <div className="text-right">
          <div className="text-lg text-hud-cyan">LIVE</div>
          <div className="text-sm text-hud-text-muted">Mode: Reactive-Proactive</div>
          {/* [시스템 정보 표시] */}
          {systemInfo && (
            <div className="mt-1 text-xs text-hud-text-muted">
              {systemInfo.status === 'Error Loading Data' ? 'ERROR LOADING INFO' : `${systemInfo.timestamp_utc.slice(11, 19)} KST | ${systemInfo.location.split(',')[0]}`}
              <br/>
              {systemInfo.status === 'Error Loading Data' ? null : `${systemInfo.weather.temperature_c}°C (${systemInfo.weather.description}) | Hum: ${systemInfo.weather.humidity_percent}%`}
            </div>
          )}
        </div>
      </div>

      {/* 2. 탭 */}
      <div className="flex gap-2">
        <Button variant={tab === "overview" ? "default" : "outline"} onClick={() => setTab("overview")}>Overview</Button>
        <Button variant={tab === "performance" ? "default" : "outline"} onClick={() => setTab("performance")}>Performance</Button>
        <Button variant={tab === "security_consent" ? "default" : "outline"} onClick={() => setTab("security_consent")}>Security & Consent</Button>
        <Button variant={tab === "bandit" ? "default" : "outline"} onClick={() => setTab("bandit")}>Bandit Analytics</Button>
      </div>

      {/* 3. 메인 그리드 */}
      <div className="flex-1 grid grid-cols-4 grid-rows-3 gap-4">
        
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
            
            <CommandInput /> 

            <HudPanel title="System Load" className="col-span-3 row-span-2">
                <div className="grid grid-cols-3 gap-4 h-full">
                    {/* [FIX] systemInfo가 null일 때를 대비 (Optional Chaining) */}
                    <HudStat title="CPU USAGE" value={systemInfo?.system_load?.cpu_usage_percent?.toFixed(1) || 'N/A'} unit="%" />
                    <HudStat title="RAM FREE" value={systemInfo?.system_load?.ram_free_gb?.toFixed(1) || 'N/A'} unit="GB" />
                    <HudStat title="NETWORK" value={systemInfo?.system_load?.network_status || 'N/A'} unit="" />
                </div>
            </HudPanel>
          </>
        )}

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
// [FIXED] className prop 추가 및 Promise<void> 타입 지원
const Button: React.FC<{ 
    variant: string; 
    onClick: () => void | Promise<void>; 
    children: React.ReactNode; 
    className?: string; 
}> = ({ variant, onClick, children, className = "" }) => (
  <button 
    onClick={onClick as (e: React.MouseEvent) => void} 
    className={`px-4 py-1.5 rounded-md text-sm font-medium ${
      variant === 'default' 
      ? 'bg-hud-cyan text-hud-bg' 
      : 'border border-hud-cyan-dark text-hud-text-muted hover:bg-hud-cyan-dark/30'
    } ${className}`}
  >
    {children}
  </button>
);