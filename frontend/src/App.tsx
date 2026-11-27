import React, { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Bot,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Cpu,
  Download,
  ExternalLink,
  FolderKanban,
  GitCompare,
  Globe,
  History,
  LayoutDashboard,
  Link2,
  LogOut,
  Network,
  Play,
  Plus,
  Search,
  Settings,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Square,
  Tag,
  X,
  XCircle,
} from "lucide-react";
import * as API from "./services/api";

type PageKey =
  | "dashboard"
  | "authority"
  | "backlinks"
  | "referring"
  | "anchors"
  | "pagerank"
  | "quality"
  | "spam"
  | "ai"
  | "competitors"
  | "crawler"
  | "jobs"
  | "projects"
  | "settings";

interface Toast { id: number; message: string; type: "success" | "error" }

interface NavSection {
  group: string;
  items: { key: PageKey; label: string; icon: React.ReactNode }[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    group: "Overview",
    items: [
      { key: "dashboard", label: "Executive Dashboard", icon: <LayoutDashboard className="w-4 h-4" /> },
      { key: "authority", label: "Domain Authority (LAS)", icon: <ShieldCheck className="w-4 h-4" /> },
      { key: "competitors", label: "Competitor Gap", icon: <GitCompare className="w-4 h-4" /> },
    ],
  },
  {
    group: "Link Intelligence",
    items: [
      { key: "backlinks", label: "Backlink Explorer", icon: <Link2 className="w-4 h-4" /> },
      { key: "referring", label: "Referring Domains", icon: <Globe className="w-4 h-4" /> },
      { key: "anchors", label: "Anchor Profile", icon: <Tag className="w-4 h-4" /> },
      { key: "quality", label: "Link Quality (LQS)", icon: <Activity className="w-4 h-4" /> },
    ],
  },
  {
    group: "Algorithms & AI",
    items: [
      { key: "pagerank", label: "PageRank Graph", icon: <Network className="w-4 h-4" /> },
      { key: "spam", label: "ML Spam & Anomalies", icon: <ShieldAlert className="w-4 h-4" /> },
      { key: "ai", label: "DeepSeek AI Reports", icon: <Bot className="w-4 h-4" /> },
    ],
  },
  {
    group: "Operations",
    items: [
      { key: "crawler", label: "Crawler & Seeds", icon: <Cpu className="w-4 h-4" /> },
      { key: "jobs", label: "Crawl Job History", icon: <History className="w-4 h-4" /> },
      { key: "projects", label: "Projects", icon: <FolderKanban className="w-4 h-4" /> },
      { key: "settings", label: "System Settings", icon: <Settings className="w-4 h-4" /> },
    ],
  },
];

const PAGE_TITLES: Record<PageKey, { title: string; subtitle: string }> = {
  dashboard: { title: "Executive Overview", subtitle: "Live index metrics, link health, and crawl performance" },
  authority: { title: "Local Authority Score (LAS)", subtitle: "Independent logarithmic scoring model from local index evidence" },
  backlinks: { title: "Backlink Explorer", subtitle: "Filter, search, inspect history, and export verified backlinks" },
  referring: { title: "Referring Domains", subtitle: "Unique linking root domains and link attribute distribution" },
  anchors: { title: "Anchor Text Profile", subtitle: "Natural distribution analysis across branded, naked, and exact anchors" },
  pagerank: { title: "Internal PageRank Graph", subtitle: "NetworkX directed graph scoring (damping factor 0.85)" },
  quality: { title: "Backlink Quality (LQS)", subtitle: "Multi-factor link evaluation with unknown-signal protection" },
  spam: { title: "ML Risk & Anomaly Detection", subtitle: "Scikit-learn Isolation Forest, rule indicators, and K-Means clusters" },
  ai: { title: "DeepSeek AI Intelligence", subtitle: "Structured JSON assessments isolated from raw crawl facts" },
  competitors: { title: "Competitor Backlink Comparison", subtitle: "Compare up to 5 domains side by side with coverage checks" },
  crawler: { title: "Crawler & Seed Management", subtitle: "Manage permitted seed domains and launch BFS Scrapy crawls" },
  jobs: { title: "Crawl Job History", subtitle: "Monitor active workers, pages scraped, and historical jobs" },
  projects: { title: "Project Workspace", subtitle: "Organize tracked domains into dedicated SEO workspaces" },
  settings: { title: "System Configuration", subtitle: "16 GB RAM resource limits, security rules, and API status" },
};

export default function App() {
  const [token, setToken] = useState<string>(() => localStorage.getItem("seo_token") || "");
  const [page, setPage] = useState<PageKey>("dashboard");
  const [activeDomain, setActiveDomain] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [stats, setStats] = useState<any>(null);
  const [backendOnline, setBackendOnline] = useState(false);
  const [overview, setOverview] = useState<any>(null);
  const [lasData, setLasData] = useState<any>(null);
  const [backlinks, setBacklinks] = useState<any>({ total: 0, items: [] });
  const [blFilter, setBlFilter] = useState({ status_filter: "all", link_attr: "", search: "", page: 1 });
  const [blDetail, setBlDetail] = useState<any>(null);
  const [refDomains, setRefDomains] = useState<any>({ total_unique_referring_domains: 0, items: [] });
  const [refPage, setRefPage] = useState(1);
  const [qualityData, setQualityData] = useState<any>(null);
  const [prData, setPrData] = useState<any>(null);
  const [spamData, setSpamData] = useState<any>(null);
  const [spamBacklinks, setSpamBacklinks] = useState<any[]>([]);
  const [labelStatus, setLabelStatus] = useState<Record<number, boolean>>({});
  const [aiReports, setAiReports] = useState<any[]>([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [compInput, setCompInput] = useState("");
  const [compData, setCompData] = useState<any>(null);
  const [seeds, setSeeds] = useState<any[]>([]);
  const [seedInput, setSeedInput] = useState("");
  const [crawlMaxPages, setCrawlMaxPages] = useState(500);
  const [crawlMaxDepth, setCrawlMaxDepth] = useState(2);
  const [jobs, setJobs] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [projForm, setProjForm] = useState({ name: "", root_domain: "", description: "" });
  const [metricsHistory, setMetricsHistory] = useState<any[]>([]);
  const [authorityHistory, setAuthorityHistory] = useState<any[]>([]);
  const [trainingLabels, setTrainingLabels] = useState<any>(null);
  const [error, setError] = useState("");
  const [domainLoading, setDomainLoading] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [refSearch, setRefSearch] = useState("");

  const handleLogin = (t: string) => { localStorage.setItem("seo_token", t); setToken(t); };
  const handleLogout = () => { localStorage.removeItem("seo_token"); setToken(""); };

  const addToast = (message: string, type: Toast["type"] = "success") => {
    const id = Date.now();
    setToasts((prev) => [...prev.slice(-3), { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  };

  const refreshGlobal = async () => {
    try {
      const [s, j, sd, prj] = await Promise.all([
        API.fetchDashboardStats(),
        API.fetchCrawlJobs(),
        API.fetchSeeds(),
        API.fetchProjects(),
      ]);
      setStats(s);
      setJobs(j.jobs || []);
      setSeeds(sd.seeds || []);
      setProjects(prj.projects || []);
      setBackendOnline(true);
    } catch {
      setBackendOnline(false);
    }
  };

  useEffect(() => {
    refreshGlobal();
    const timer = setInterval(refreshGlobal, 10000);
    return () => clearInterval(timer);
  }, []);

  const loadDomainWorkspace = async (dom: string) => {
    setError("");
    setDomainLoading(true);
    setRefSearch("");
    setRefPage(1);
    try {
      const ov = await API.analyzeDomain(dom);
      const clean = ov.domain;
      setActiveDomain(clean);
      setOverview(ov);
      const [las, bl, qual, pr, sp, air, hist, authHist] = await Promise.all([
        API.fetchAuthority(clean),
        API.fetchBacklinks(clean, blFilter),
        API.fetchQualityAndAnchors(clean),
        API.fetchPageRank(clean, false),
        API.fetchSpamAnalysis(clean),
        API.fetchAiReports(clean),
        API.fetchMetricsHistory(clean),
        API.fetchAuthorityHistory(clean),
      ]);
      setLasData(las);
      setBacklinks(bl);
      setQualityData(qual);
      setPrData(pr);
      setSpamData(sp);
      setAiReports(air.reports || []);
      setMetricsHistory(hist.history || []);
      setAuthorityHistory(authHist.history || []);
      setSpamBacklinks(bl.items || []);
      addToast(`Workspace loaded for ${ov.domain}`);
    } catch (e: any) {
      const msg = e?.response?.data?.detail || "Backend API is offline or domain validation failed.";
      setError(msg);
      addToast(msg, "error");
    } finally {
      setDomainLoading(false);
    }
  };

  useEffect(() => {
    if (activeDomain) {
      API.fetchBacklinks(activeDomain, blFilter).then(setBacklinks).catch(() => {});
    }
  }, [blFilter, activeDomain]);

  useEffect(() => {
    if (activeDomain) {
      API.fetchReferringDomains(activeDomain, { search: refSearch, page: refPage, page_size: 25 })
        .then(setRefDomains)
        .catch(() => {});
    }
  }, [activeDomain, refSearch, refPage]);

  const handleAnalyzeSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.trim()) loadDomainWorkspace(searchInput.trim());
  };

  const handleLabelBacklink = async (backlinkId: number, isSpam: boolean) => {
    try {
      await API.addTrainingLabel(backlinkId, isSpam);
      setLabelStatus((prev) => ({ ...prev, [backlinkId]: isSpam }));
      addToast(`Backlink #${backlinkId} labeled as ${isSpam ? "spam" : "not spam"}`);
      if (activeDomain) {
        API.fetchTrainingLabels(activeDomain).then(setTrainingLabels).catch(() => {});
      }
    } catch {
      const msg = "Failed to save label — ensure backend is online.";
      setError(msg);
      addToast(msg, "error");
    }
  };

  const anchorChartData = qualityData?.anchors?.distribution
    ? Object.entries(qualityData.anchors.distribution).map(([name, value]) => ({ name, value }))
    : [];

  const followPieData = stats
    ? [
        { name: "DoFollow", value: stats.dofollow_backlinks },
        { name: "NoFollow", value: stats.nofollow_backlinks },
      ]
    : [];

  const lasBarData = lasData?.components
    ? Object.entries(lasData.components).map(([k, v]) => ({ component: k, score: Math.round(Number(v) * 100) }))
    : [];

  const trendData = metricsHistory.map((r: any) => ({
    date: new Date(r.recorded_at).toLocaleDateString("en-GB", { month: "short", day: "numeric" }),
    total: r.total_backlinks,
    active: r.active_count,
    lost: r.lost_count,
    referring: r.unique_referring_domains,
  }));

  const compBarData = compData?.profiles
    ? compData.profiles.map((p: any) => ({
        domain: p.domain,
        backlinks: p.total_discovered_backlinks,
        referring: p.unique_referring_domains,
        indexed: p.indexed_pages,
      }))
    : [];

  const blTotalPages = Math.max(1, Math.ceil((backlinks.total || 0) / 25));
  const currentMeta = PAGE_TITLES[page];

  if (!token) return <LoginPage onLogin={handleLogin} />;

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-[#0F1123] text-slate-300 flex flex-col shrink-0 border-r border-indigo-950/60 shadow-xl">
        <div className="px-5 py-5 border-b border-white/10 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-teal-400 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <ShieldCheck className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-bold text-sm text-white tracking-tight">SEO Intelligence</div>
            <div className="text-[11px] text-indigo-300/80 font-medium">Enterprise Local Suite</div>
          </div>
        </div>

        <nav className="px-3 py-4 flex-1 space-y-5 overflow-y-auto">
          {NAV_SECTIONS.map((section) => (
            <div key={section.group}>
              <div className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                {section.group}
              </div>
              <div className="space-y-0.5">
                {section.items.map((item) => {
                  const active = page === item.key;
                  return (
                    <button
                      key={item.key}
                      onClick={() => setPage(item.key)}
                      className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all ${
                        active
                          ? "bg-indigo-600 text-white shadow-md shadow-indigo-950/40"
                          : "text-slate-300/90 hover:bg-white/5 hover:text-white"
                      }`}
                    >
                      <span className={active ? "text-white" : "text-slate-400"}>{item.icon}</span>
                      <span className="truncate">{item.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="p-4 border-t border-white/10 bg-white/[0.02]">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">API Engine</span>
            <span className="flex items-center gap-1.5 font-medium">
              <span className={`w-2 h-2 rounded-full ${backendOnline ? "bg-emerald-400 animate-pulse" : "bg-amber-400"}`} />
              <span className={backendOnline ? "text-emerald-300" : "text-amber-300"}>
                {backendOnline ? "Connected" : "Preview Mode"}
              </span>
            </span>
          </div>
          <div className="text-[11px] text-slate-500 mt-1">PostgreSQL • Redis • Scrapy</div>
          <button
            onClick={handleLogout}
            className="mt-3 w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-slate-400 hover:text-rose-300 hover:bg-rose-500/10 transition cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <header className="sticky top-0 z-20 bg-white/85 backdrop-blur-md border-b border-slate-200/80 px-7 py-3.5 flex flex-wrap items-center justify-between gap-4">
          <form onSubmit={handleAnalyzeSubmit} className="flex items-center gap-2.5 flex-1 max-w-2xl">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Analyze any root domain or URL (e.g. example.com)..."
                className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition"
              />
            </div>
            <button
              type="submit"
              disabled={domainLoading}
              className="bg-indigo-600 hover:bg-indigo-700 active:scale-[0.99] disabled:opacity-60 text-white px-5 py-2.5 rounded-xl text-sm font-semibold shadow-sm shadow-indigo-600/20 transition cursor-pointer"
            >
              {domainLoading ? "Analyzing…" : "Analyze"}
            </button>
          </form>

          <div className="flex items-center gap-3">
            {activeDomain ? (
              <span className="inline-flex items-center gap-1.5 text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200 px-3 py-1.5 rounded-full">
                <Globe className="w-3.5 h-3.5" />
                {activeDomain}
              </span>
            ) : (
              <span className="text-xs text-slate-500 bg-slate-100 border border-slate-200 px-3 py-1.5 rounded-full">
                No target selected
              </span>
            )}
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-indigo-600 transition"
            >
              API Docs <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </header>

        {/* Page Body */}
        <main className="p-7 max-w-[1440px] w-full mx-auto space-y-6 flex-1">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">{currentMeta.title}</h1>
              <p className="text-sm text-slate-500 mt-0.5">{currentMeta.subtitle}</p>
            </div>
            {page === "dashboard" && (
              <button
                onClick={() => setPage("crawler")}
                className="inline-flex items-center gap-1.5 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 px-3.5 py-2 rounded-xl text-xs font-semibold shadow-xs transition cursor-pointer"
              >
                <Play className="w-3.5 h-3.5 text-indigo-600" /> Manage Crawls
              </button>
            )}
          </div>

          {error && (
            <div className="bg-rose-50 border border-rose-200 text-rose-700 px-4 py-3 rounded-xl text-sm flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
              <button onClick={() => setError("")} className="text-rose-500 hover:text-rose-700">
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* ── DASHBOARD ─────────────────────────────────────────────────── */}
          {page === "dashboard" && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <KpiCard label="Total Indexed Pages" value={stats?.total_indexed_pages ?? 0} icon={<Globe className="w-4 h-4" />} tone="indigo" />
                <KpiCard label="Total Backlinks" value={stats?.total_backlinks ?? 0} icon={<Link2 className="w-4 h-4" />} tone="emerald" />
                <KpiCard label="Referring Domains" value={stats?.referring_domains ?? 0} icon={<Network className="w-4 h-4" />} tone="violet" />
                <KpiCard
                  label="Average LAS"
                  value={stats?.average_las !== null && stats?.average_las !== undefined ? `${stats.average_las} / 100` : "Insufficient Data"}
                  icon={<ShieldCheck className="w-4 h-4" />}
                  tone="amber"
                />
              </div>

              <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
                <CompactStat label="Active Backlinks" value={stats?.active_backlinks ?? 0} dot="bg-emerald-500" />
                <CompactStat label="Lost Backlinks" value={stats?.lost_backlinks ?? 0} dot="bg-rose-500" />
                <CompactStat label="New (7d)" value={stats?.newly_discovered_backlinks ?? 0} dot="bg-sky-500" />
                <CompactStat label="Running Crawl Jobs" value={stats?.running_crawl_jobs ?? 0} dot="bg-indigo-500" />
                <CompactStat label="Total Crawl Jobs" value={stats?.total_crawl_jobs ?? 0} dot="bg-slate-400" />
              </div>

              <div className="grid lg:grid-cols-2 gap-6">
                <Panel title="DoFollow vs NoFollow Distribution" subtitle="Attribute split across all verified backlinks in local index">
                  {stats && stats.total_backlinks > 0 ? (
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie data={followPieData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={88} paddingAngle={3} label>
                            <Cell fill="#059669" />
                            <Cell fill="#D97706" />
                          </Pie>
                          <Tooltip contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e2e8f0", borderRadius: "10px", fontSize: "12px" }} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <EmptyState title="No backlink records indexed yet" msg="Register permitted seed domains and start a Scrapy BFS crawl." actionLabel="Open Crawler & Seeds" onAction={() => setPage("crawler")} />
                  )}
                </Panel>

                <Panel title="Local Authority Score (LAS) Breakdown" subtitle="Normalized 0–100 contribution of R, Q, D, S, and G components">
                  {lasBarData.length > 0 ? (
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={lasBarData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                          <XAxis dataKey="component" stroke="#64748b" fontSize={12} tickLine={false} />
                          <YAxis stroke="#64748b" fontSize={12} domain={[0, 100]} tickLine={false} />
                          <Tooltip contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e2e8f0", borderRadius: "10px", fontSize: "12px" }} />
                          <Bar dataKey="score" fill="#4F46E5" radius={[8, 8, 0, 0]} maxBarSize={44} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <EmptyState title="Awaiting domain selection" msg="Search an indexed domain to inspect its LAS breakdown." />
                  )}
                </Panel>
              </div>

              {/* Trend charts — only shown when metrics history exists */}
              {trendData.length >= 2 && (
                <div className="grid lg:grid-cols-2 gap-6">
                  <Panel title="Backlink Discovery Trend" subtitle="Total and active backlinks over time (snapshots)">
                    <div className="h-56">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={trendData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                          <XAxis dataKey="date" stroke="#64748b" fontSize={11} tickLine={false} />
                          <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                          <Tooltip contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e2e8f0", borderRadius: "10px", fontSize: "12px" }} />
                          <Legend wrapperStyle={{ fontSize: "12px" }} />
                          <Line type="monotone" dataKey="total" stroke="#4F46E5" strokeWidth={2} dot={false} name="Total" />
                          <Line type="monotone" dataKey="active" stroke="#059669" strokeWidth={2} dot={false} name="Active" />
                          <Line type="monotone" dataKey="lost" stroke="#E11D48" strokeWidth={2} dot={false} name="Lost" />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </Panel>

                  <Panel title="Referring Domain Growth" subtitle="Unique referring domains over time">
                    <div className="h-56">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={trendData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                          <XAxis dataKey="date" stroke="#64748b" fontSize={11} tickLine={false} />
                          <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                          <Tooltip contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e2e8f0", borderRadius: "10px", fontSize: "12px" }} />
                          <Line type="monotone" dataKey="referring" stroke="#7C3AED" strokeWidth={2} dot={false} name="Referring Domains" />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </Panel>
                </div>
              )}

              {/* Database usage summary */}
              {stats?.database_usage && (
                <Panel title="Database Record Counts" subtitle="Row counts for major tables — lightweight index health indicator">
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                    {Object.entries(stats.database_usage as Record<string, number>).map(([table, count]) => (
                      <div key={table} className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-center">
                        <p className="text-xs text-slate-500 capitalize mb-1">{table.replace(/_/g, " ")}</p>
                        <p className="text-lg font-bold text-slate-800 tabular-nums">{count.toLocaleString()}</p>
                      </div>
                    ))}
                  </div>
                </Panel>
              )}
            </div>
          )}

          {/* ── DOMAIN AUTHORITY (LAS) ────────────────────────────────────── */}
          {page === "authority" && (
            <Panel title="Local Authority Score Report" subtitle="Experimental internal metric — clearly separated from Moz DA, Ahrefs DR, and Semrush AS">
              {!overview ? (
                <EmptyState title="No domain analyzed" msg="Enter a root domain or URL in the top search bar to compute its Local Authority Score." />
              ) : (
                <div className="space-y-5">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <KpiCard label="Local Authority (LAS)" value={lasData?.las_score ?? "Insufficient Data"} icon={<ShieldCheck className="w-4 h-4" />} tone="indigo" />
                    <KpiCard label="Confidence Level" value={lasData?.confidence_level ?? "insufficient_data"} icon={<Activity className="w-4 h-4" />} tone="emerald" />
                    <KpiCard label="Formula Version" value={lasData?.formula_version ?? "LAS-v1.0"} icon={<Sparkles className="w-4 h-4" />} tone="violet" />
                    <KpiCard label="Index Coverage" value={`${Math.round((lasData?.data_coverage ?? 0) * 100)}%`} icon={<Globe className="w-4 h-4" />} tone="amber" />
                  </div>
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs text-slate-600">
                    Formula: <code className="font-mono text-indigo-700 font-semibold">LAS = 100 * (0.30R + 0.25Q + 0.20D + 0.15S + 0.10G)</code>. Missing or insufficient index evidence is reported transparently rather than fabricated.
                  </div>
                  {lasBarData.length > 0 && (
                    <div className="h-56">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={lasBarData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                          <XAxis dataKey="component" stroke="#64748b" fontSize={12} tickLine={false} />
                          <YAxis stroke="#64748b" fontSize={12} domain={[0, 100]} tickLine={false} />
                          <Tooltip contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e2e8f0", borderRadius: "10px", fontSize: "12px" }} />
                          <Bar dataKey="score" fill="#4F46E5" radius={[8, 8, 0, 0]} maxBarSize={44} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}

                  {authorityHistory.length >= 2 && (
                    <div>
                      <p className="text-sm font-semibold text-slate-700 mb-2">LAS Score Trend</p>
                      <div className="h-52">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={authorityHistory.map((r: any) => ({
                            date: new Date(r.recorded_at).toLocaleDateString("en-GB", { month: "short", day: "numeric" }),
                            las: r.las_score,
                          }))}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                            <XAxis dataKey="date" stroke="#64748b" fontSize={11} tickLine={false} />
                            <YAxis stroke="#64748b" fontSize={11} domain={[0, 100]} tickLine={false} />
                            <Tooltip contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e2e8f0", borderRadius: "10px", fontSize: "12px" }} />
                            <Line type="monotone" dataKey="las" stroke="#4F46E5" strokeWidth={2} dot={false} name="LAS Score" />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </Panel>
          )}

          {/* ── BACKLINK EXPLORER ─────────────────────────────────────────── */}
          {page === "backlinks" && (
            <Panel title={`Backlink Explorer${activeDomain ? ` — ${activeDomain}` : ""}`} subtitle="Verified inbound links with status tracking, attributes, and CSV export">
              {!activeDomain ? (
                <EmptyState title="Select a target domain" msg="Search a domain in the top bar to inspect its inbound backlink profile." />
              ) : (
                <div className="space-y-4">
                  {/* Filters row */}
                  <div className="flex flex-wrap gap-2.5 items-center justify-between bg-slate-50 border border-slate-200 p-3 rounded-xl">
                    <div className="flex flex-wrap gap-2">
                      <select
                        value={blFilter.status_filter}
                        onChange={(e) => setBlFilter({ ...blFilter, status_filter: e.target.value, page: 1 })}
                        className="bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs font-medium text-slate-700 focus:outline-none focus:border-indigo-500"
                      >
                        <option value="all">All Statuses</option>
                        <option value="active">Active</option>
                        <option value="lost">Lost</option>
                        <option value="temp_unavailable">Temporarily Unavailable</option>
                        <option value="redirected">Redirected</option>
                        <option value="not_verified">Not Verified</option>
                      </select>
                      <select
                        value={blFilter.link_attr}
                        onChange={(e) => setBlFilter({ ...blFilter, link_attr: e.target.value, page: 1 })}
                        className="bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs font-medium text-slate-700 focus:outline-none focus:border-indigo-500"
                      >
                        <option value="">All Attributes</option>
                        <option value="dofollow">DoFollow</option>
                        <option value="nofollow">NoFollow</option>
                        <option value="sponsored">Sponsored</option>
                        <option value="ugc">UGC</option>
                      </select>
                      <input
                        placeholder="Search anchor or source..."
                        value={blFilter.search}
                        onChange={(e) => setBlFilter({ ...blFilter, search: e.target.value, page: 1 })}
                        className="bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                    <a
                      href={`http://localhost:8000/api/export/backlinks?domain=${encodeURIComponent(activeDomain)}`}
                      className="inline-flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-xs transition"
                    >
                      <Download className="w-3.5 h-3.5" /> Export CSV
                    </a>
                  </div>

                  {backlinks.items?.length === 0 ? (
                    <EmptyState title="No matching backlinks" msg="No backlinks match your current filters in the local index." />
                  ) : (
                    <div className="overflow-x-auto border border-slate-200 rounded-xl">
                      <table className="w-full text-xs text-left">
                        <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider border-b border-slate-200">
                          <tr>
                            <th className="py-3 px-4 font-semibold">Source Domain</th>
                            <th className="py-3 px-4 font-semibold">Anchor Text</th>
                            <th className="py-3 px-4 font-semibold">Target URL</th>
                            <th className="py-3 px-4 font-semibold">Attribute</th>
                            <th className="py-3 px-4 font-semibold">Status</th>
                            <th className="py-3 px-4 font-semibold text-right">Details</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 bg-white">
                          {backlinks.items.map((b: any) => (
                            <tr key={b.id} className="hover:bg-slate-50/80 transition">
                              <td className="py-3 px-4 font-medium text-indigo-600">{b.source_domain}</td>
                              <td className="py-3 px-4 text-slate-700">{b.anchor_text || <span className="text-slate-400 italic">(empty)</span>}</td>
                              <td className="py-3 px-4 truncate max-w-xs text-slate-500">{b.target_url}</td>
                              <td className="py-3 px-4">
                                <Badge tone={b.is_dofollow ? "emerald" : "amber"}>
                                  {b.is_dofollow ? "DoFollow" : b.is_sponsored ? "Sponsored" : b.is_ugc ? "UGC" : "NoFollow"}
                                </Badge>
                              </td>
                              <td className="py-3 px-4">
                                <Badge tone={b.status === "active" ? "emerald" : b.status === "lost" ? "rose" : "slate"}>
                                  {b.status}
                                </Badge>
                              </td>
                              <td className="py-3 px-4 text-right">
                                <button
                                  onClick={() =>
                                    API.fetchBacklinkDetail(b.id).then((d) =>
                                      setBlDetail(blDetail?.backlink?.id === b.id ? null : d)
                                    )
                                  }
                                  className="text-indigo-600 hover:text-indigo-800 font-semibold cursor-pointer"
                                >
                                  Inspect
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* Pagination controls */}
                  {backlinks.total > 25 && (
                    <div className="flex items-center justify-between pt-1">
                      <span className="text-xs text-slate-500">
                        Showing {((blFilter.page - 1) * 25) + 1}–{Math.min(blFilter.page * 25, backlinks.total)} of {backlinks.total} backlinks
                      </span>
                      <div className="flex items-center gap-1.5">
                        <button
                          disabled={blFilter.page <= 1}
                          onClick={() => setBlFilter((f) => ({ ...f, page: f.page - 1 }))}
                          className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer"
                        >
                          <ChevronLeft className="w-4 h-4" />
                        </button>
                        <span className="text-xs font-medium text-slate-700 px-2">
                          Page {blFilter.page} / {blTotalPages}
                        </span>
                        <button
                          disabled={blFilter.page >= blTotalPages}
                          onClick={() => setBlFilter((f) => ({ ...f, page: f.page + 1 }))}
                          className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Backlink detail panel with full history */}
                  {blDetail && (
                    <div className="bg-indigo-50/60 border border-indigo-200 rounded-xl p-4 space-y-3 text-xs">
                      <div className="flex justify-between items-center">
                        <b className="text-indigo-950">Backlink #{blDetail.backlink.id} — Detail &amp; Verification History</b>
                        <button onClick={() => setBlDetail(null)} className="text-slate-500 hover:text-slate-800 cursor-pointer">
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                      <div className="grid sm:grid-cols-2 gap-2 text-slate-700">
                        <div><span className="font-semibold text-slate-500">Source URL:</span> <span className="break-all">{blDetail.backlink.source_url}</span></div>
                        <div><span className="font-semibold text-slate-500">Target URL:</span> <span className="break-all">{blDetail.backlink.target_url}</span></div>
                        <div><span className="font-semibold text-slate-500">Anchor:</span> {blDetail.backlink.anchor_text || <em className="text-slate-400">empty</em>}</div>
                        <div><span className="font-semibold text-slate-500">Placement:</span> {blDetail.backlink.placement_context || "Unavailable"}</div>
                        <div><span className="font-semibold text-slate-500">First Discovered:</span> {blDetail.backlink.first_discovered_at ? new Date(blDetail.backlink.first_discovered_at).toLocaleString() : "—"}</div>
                        <div><span className="font-semibold text-slate-500">Last Verified:</span> {blDetail.backlink.last_verified_at ? new Date(blDetail.backlink.last_verified_at).toLocaleString() : "—"}</div>
                      </div>
                      {blDetail.history.length === 0 ? (
                        <p className="text-slate-500 italic">No change events recorded yet.</p>
                      ) : (
                        <div className="space-y-1.5">
                          <div className="font-semibold text-indigo-800">Change History ({blDetail.history.length} events)</div>
                          <div className="overflow-x-auto border border-indigo-200 rounded-lg">
                            <table className="w-full text-left">
                              <thead className="bg-indigo-100/60 text-indigo-700 uppercase tracking-wider border-b border-indigo-200">
                                <tr>
                                  <th className="py-2 px-3">Recorded</th>
                                  <th className="py-2 px-3">Status Change</th>
                                  <th className="py-2 px-3">Anchor Change</th>
                                  <th className="py-2 px-3">HTTP</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-indigo-100 bg-white">
                                {blDetail.history.map((h: any, idx: number) => (
                                  <tr key={idx}>
                                    <td className="py-2 px-3 whitespace-nowrap">{h.recorded_at ? new Date(h.recorded_at).toLocaleString() : "—"}</td>
                                    <td className="py-2 px-3">
                                      {h.previous_status !== h.new_status
                                        ? <span className="text-amber-700">{h.previous_status} → {h.new_status}</span>
                                        : <span className="text-slate-400">unchanged</span>}
                                    </td>
                                    <td className="py-2 px-3">
                                      {h.previous_anchor !== h.new_anchor
                                        ? <span className="text-amber-700">changed</span>
                                        : <span className="text-slate-400">unchanged</span>}
                                    </td>
                                    <td className="py-2 px-3 font-mono">{h.http_status || "—"}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </Panel>
          )}

          {/* ── REFERRING DOMAINS ─────────────────────────────────────────── */}
          {page === "referring" && (
            <Panel title={`Referring Domains (${refDomains.total_unique_referring_domains ?? 0})`} subtitle="Unique linking domains discovered by your crawler">
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <div className="relative max-w-xs flex-1">
                    <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      placeholder="Filter by domain name..."
                      value={refSearch}
                      onChange={(e) => { setRefSearch(e.target.value); setRefPage(1); }}
                      className="w-full bg-white border border-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  {refSearch && (
                    <button onClick={() => { setRefSearch(""); setRefPage(1); }} className="text-slate-400 hover:text-slate-700 cursor-pointer">
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
                {!refDomains.items?.length ? (
                  <EmptyState title="No referring domains yet" msg="Analyze an indexed domain or crawl external seed sites to populate referring domains." />
                ) : (
                  <>
                    <div className="overflow-x-auto border border-slate-200 rounded-xl">
                      <table className="w-full text-xs text-left">
                        <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider border-b border-slate-200">
                          <tr>
                            <th className="py-3 px-4">Source Domain</th>
                            <th className="py-3 px-4">Total Links</th>
                            <th className="py-3 px-4">DoFollow</th>
                            <th className="py-3 px-4">NoFollow</th>
                            <th className="py-3 px-4">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 bg-white">
                          {refDomains.items.map((r: any) => (
                            <tr key={r.source_domain} className="hover:bg-slate-50">
                              <td className="py-3 px-4 font-medium text-indigo-600">{r.source_domain}</td>
                              <td className="py-3 px-4 font-semibold tabular-nums">{r.total_backlinks}</td>
                              <td className="py-3 px-4 text-emerald-700 tabular-nums">{r.dofollow_backlinks}</td>
                              <td className="py-3 px-4 text-amber-700 tabular-nums">{r.nofollow_backlinks}</td>
                              <td className="py-3 px-4"><Badge tone="emerald">{r.status}</Badge></td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {(refDomains.total_unique_referring_domains ?? 0) > 25 && (
                      <div className="flex items-center justify-between text-xs text-slate-500">
                        <span>Showing {(refPage - 1) * 25 + 1}–{Math.min(refPage * 25, refDomains.total_unique_referring_domains)} of {refDomains.total_unique_referring_domains}</span>
                        <div className="flex gap-2">
                          <button
                            disabled={refPage <= 1}
                            onClick={() => setRefPage((p) => Math.max(1, p - 1))}
                            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                          >
                            <ChevronLeft className="w-3.5 h-3.5" /> Prev
                          </button>
                          <span className="px-2 py-1.5 font-semibold">{refPage} / {Math.ceil(refDomains.total_unique_referring_domains / 25)}</span>
                          <button
                            disabled={refPage >= Math.ceil(refDomains.total_unique_referring_domains / 25)}
                            onClick={() => setRefPage((p) => p + 1)}
                            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                          >
                            Next <ChevronRight className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </Panel>
          )}

          {/* ── ANCHOR TEXT ───────────────────────────────────────────────── */}
          {page === "anchors" && (
            <Panel title="Anchor Text Distribution" subtitle="Classification across exact-match, partial-match, branded, generic, naked URL, and empty anchors">
              {anchorChartData.length === 0 ? (
                <EmptyState title="No anchor data available" msg="Analyze a domain with discovered backlinks to visualize its anchor text profile." />
              ) : (
                <div className="space-y-5">
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={anchorChartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                        <XAxis dataKey="name" stroke="#64748b" fontSize={12} tickLine={false} />
                        <YAxis stroke="#64748b" fontSize={12} tickLine={false} />
                        <Tooltip contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e2e8f0", borderRadius: "10px", fontSize: "12px" }} />
                        <Bar dataKey="value" fill="#0D9488" radius={[8, 8, 0, 0]} maxBarSize={48} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  {qualityData?.anchors?.top_anchors?.length > 0 && (
                    <div>
                      <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Top Anchor Texts</div>
                      <div className="flex flex-wrap gap-2">
                        {qualityData.anchors.top_anchors.map((a: any) => (
                          <span key={a.anchor} className="bg-teal-50 text-teal-800 border border-teal-200 px-2.5 py-1 rounded-full text-xs font-medium">
                            {a.anchor || <em>(empty)</em>} <span className="text-teal-500">×{a.count}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {qualityData?.anchors?.unusual_patterns?.length > 0 && (
                    <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-xs text-amber-800 space-y-1">
                      <div className="font-semibold">Observed Patterns</div>
                      {qualityData.anchors.unusual_patterns.map((p: string, i: number) => (
                        <div key={i}>• {p}</div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </Panel>
          )}

          {/* ── PAGERANK ──────────────────────────────────────────────────── */}
          {page === "pagerank" && (
            <Panel title="Internal NetworkX PageRank" subtitle="Computed strictly over your local crawled link graph (Not Google PageRank)">
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-xs text-slate-500">{prData?.disclaimer || "Internal graph PageRank (damping factor 0.85)."}</p>
                  <button
                    onClick={() => activeDomain && API.fetchPageRank(activeDomain, true).then(setPrData)}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-xs font-semibold shadow-xs transition cursor-pointer"
                  >
                    Recompute PageRank Graph
                  </button>
                </div>
                {prData?.top_indexed_domains?.length ? (
                  <div className="overflow-x-auto border border-slate-200 rounded-xl">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-slate-50 text-slate-500 uppercase border-b border-slate-200">
                        <tr>
                          <th className="py-3 px-4">Indexed Domain</th>
                          <th className="py-3 px-4">Internal PageRank</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 bg-white">
                        {prData.top_indexed_domains.map((t: any) => (
                          <tr key={t.domain} className="hover:bg-slate-50">
                            <td className="py-3 px-4 font-medium text-slate-800">{t.domain}</td>
                            <td className="py-3 px-4 font-mono text-indigo-700">{t.pagerank_score}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <EmptyState title="PageRank graph not computed" msg="Crawl seed domains first, then click Recompute PageRank Graph." />
                )}
              </div>
            </Panel>
          )}

          {/* ── LINK QUALITY (LQS) ────────────────────────────────────────── */}
          {page === "quality" && (
            <Panel title="Experimental Backlink Quality Score (LQS)" subtitle="Weighted across reputation, topical relevance, anchor, placement, and stability">
              {!qualityData?.quality?.items?.length ? (
                <EmptyState title="No quality scores computed" msg="Analyze an indexed domain with backlinks to evaluate per-link LQS metrics." />
              ) : (
                <div className="space-y-4">
                  <div className="inline-flex items-center gap-2 bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-2 rounded-xl font-semibold text-sm">
                    Average LQS: {qualityData.quality.average_lqs ?? "N/A"} / 100
                  </div>
                  <p className="text-xs text-slate-500">{qualityData.quality.formula}</p>
                  <div className="overflow-x-auto border border-slate-200 rounded-xl">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-slate-50 text-slate-500 uppercase border-b border-slate-200">
                        <tr>
                          <th className="py-3 px-4">Source</th>
                          <th className="py-3 px-4">Anchor</th>
                          <th className="py-3 px-4">DoFollow</th>
                          <th className="py-3 px-4">LQS Score</th>
                          <th className="py-3 px-4">Unknown Signals</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 bg-white">
                        {qualityData.quality.items.slice(0, 50).map((item: any) => (
                          <tr key={item.backlink_id} className="hover:bg-slate-50">
                            <td className="py-3 px-4 text-indigo-600 font-medium">{item.source_domain}</td>
                            <td className="py-3 px-4 text-slate-700">{item.anchor_text || <em className="text-slate-400">empty</em>}</td>
                            <td className="py-3 px-4">
                              <Badge tone={item.is_dofollow ? "emerald" : "amber"}>{item.is_dofollow ? "Yes" : "No"}</Badge>
                            </td>
                            <td className="py-3 px-4 font-semibold tabular-nums">
                              {item.lqs_score !== null ? `${item.lqs_score}` : <span className="text-slate-400">N/A</span>}
                            </td>
                            <td className="py-3 px-4 text-slate-500">{item.unknown_signals?.join(", ") || "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </Panel>
          )}

          {/* ── ML SPAM & ANOMALIES ───────────────────────────────────────── */}
          {page === "spam" && (
            <div className="space-y-6">
              <Panel title="ML Risk, Isolation Forest Anomalies & K-Means Clusters" subtitle="CPU-based Scikit-learn diagnostics with transparent fallback when human labels are insufficient">
                {!spamData ? (
                  <EmptyState title="No domain selected" msg="Analyze a domain to inspect rule-based risk indicators, Isolation Forest anomalies, and domain clusters." />
                ) : (
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <CompactStat label="Active Model Version" value={spamData.spam_and_anomalies.model_version?.slice(0, 28) + "…"} dot="bg-indigo-500" />
                      <CompactStat label="Risk Category" value={`${spamData.spam_and_anomalies.risk_category} (${spamData.spam_and_anomalies.risk_probability ?? "N/A"})`} dot="bg-amber-500" />
                      <CompactStat label="Isolation Forest Anomaly" value={String(spamData.spam_and_anomalies.anomaly_detected)} dot="bg-rose-500" />
                    </div>
                    {spamData.spam_and_anomalies.supporting_indicators?.length > 0 && (
                      <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-xs text-amber-800 space-y-1">
                        <div className="font-semibold">Rule-Based Indicators</div>
                        {spamData.spam_and_anomalies.supporting_indicators.map((s: string, i: number) => (
                          <div key={i}>• {s}</div>
                        ))}
                      </div>
                    )}
                    <p className="text-xs text-slate-500">{spamData.spam_and_anomalies.disclaimer}</p>
                    {spamData.domain_clusters?.clusters?.length > 0 && (
                      <div className="space-y-2">
                        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">K-Means Domain Clusters ({spamData.domain_clusters.total_clustered_domains} domains)</div>
                        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                          {spamData.domain_clusters.clusters.map((c: any) => (
                            <div key={c.cluster_id} className="bg-slate-50 border border-slate-200 rounded-xl p-3">
                              <div className="text-xs font-semibold text-indigo-700 mb-1.5">Cluster {c.cluster_id} — {c.domain_count} domains</div>
                              <div className="flex flex-wrap gap-1">
                                {c.domains.slice(0, 8).map((d: string) => (
                                  <span key={d} className="bg-white border border-slate-200 text-slate-700 px-2 py-0.5 rounded text-[11px]">{d}</span>
                                ))}
                                {c.domains.length > 8 && <span className="text-slate-400 text-[11px]">+{c.domains.length - 8} more</span>}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </Panel>

              {/* ML Training Label Panel */}
              <Panel title="Human Spam Labels — ML Training Dataset" subtitle="Label backlinks as spam / not spam to train the Random Forest classifier (minimum 20 labels required)">
                {!activeDomain ? (
                  <EmptyState title="No domain selected" msg="Analyze a domain to load its backlinks for labeling." />
                ) : (
                  <div className="space-y-4">
                    {trainingLabels && (
                      <div className="flex flex-wrap gap-3">
                        <CompactStat label="Total Labels" value={trainingLabels.total_labels ?? 0} dot="bg-indigo-500" />
                        <CompactStat label="Spam" value={trainingLabels.spam_labels ?? 0} dot="bg-rose-500" />
                        <CompactStat label="Not Spam" value={trainingLabels.not_spam_labels ?? 0} dot="bg-emerald-500" />
                        {(trainingLabels.total_labels ?? 0) >= 20 && (
                          <button
                            onClick={() => {
                              fetch("http://localhost:8000/api/ml/train-spam", { method: "POST" })
                                .then((r) => r.json())
                                .then((d) => alert(d.trained ? `Model trained! F1: ${d.metrics?.f1_score}` : d.reason));
                            }}
                            className="inline-flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-xs font-semibold shadow-xs transition cursor-pointer"
                          >
                            <Sparkles className="w-3.5 h-3.5" /> Train Classifier
                          </button>
                        )}
                      </div>
                    )}
                    <div className="text-xs text-slate-500">
                      Click <strong>Spam</strong> or <strong>Not Spam</strong> on each backlink below. Labels are stored and used to train the Random Forest model.
                    </div>
                    {spamBacklinks.length === 0 ? (
                      <EmptyState title="No backlinks loaded" msg="Analyze a domain with indexed backlinks to start labeling." />
                    ) : (
                      <div className="overflow-x-auto border border-slate-200 rounded-xl">
                        <table className="w-full text-xs text-left">
                          <thead className="bg-slate-50 text-slate-500 uppercase border-b border-slate-200">
                            <tr>
                              <th className="py-3 px-4">Source Domain</th>
                              <th className="py-3 px-4">Anchor Text</th>
                              <th className="py-3 px-4">Type</th>
                              <th className="py-3 px-4 text-center">Label</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 bg-white">
                            {spamBacklinks.map((b: any) => {
                              const labeled = labelStatus[b.id];
                              return (
                                <tr key={b.id} className="hover:bg-slate-50">
                                  <td className="py-3 px-4 font-medium text-indigo-600">{b.source_domain}</td>
                                  <td className="py-3 px-4 text-slate-700">{b.anchor_text || <em className="text-slate-400">empty</em>}</td>
                                  <td className="py-3 px-4">
                                    <Badge tone={b.is_dofollow ? "emerald" : "amber"}>{b.is_dofollow ? "DoFollow" : "NoFollow"}</Badge>
                                  </td>
                                  <td className="py-3 px-4">
                                    <div className="flex items-center justify-center gap-2">
                                      <button
                                        onClick={() => handleLabelBacklink(b.id, false)}
                                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-semibold border transition cursor-pointer ${labeled === false ? "bg-emerald-600 text-white border-emerald-600" : "text-emerald-700 border-emerald-200 hover:bg-emerald-50"}`}
                                      >
                                        <CheckCircle className="w-3 h-3" /> Not Spam
                                      </button>
                                      <button
                                        onClick={() => handleLabelBacklink(b.id, true)}
                                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-semibold border transition cursor-pointer ${labeled === true ? "bg-rose-600 text-white border-rose-600" : "text-rose-700 border-rose-200 hover:bg-rose-50"}`}
                                      >
                                        <XCircle className="w-3 h-3" /> Spam
                                      </button>
                                    </div>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                    <button
                      onClick={() => API.fetchTrainingLabels(activeDomain).then(setTrainingLabels)}
                      className="text-xs text-indigo-600 hover:text-indigo-800 font-medium underline underline-offset-2 cursor-pointer"
                    >
                      Refresh label counts
                    </button>
                  </div>
                )}
              </Panel>
            </div>
          )}

          {/* ── DEEPSEEK AI ───────────────────────────────────────────────── */}
          {page === "ai" && (
            <Panel title="DeepSeek AI SEO Analysis" subtitle="Structured Pydantic-validated JSON reports generated strictly from local crawl evidence">
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  {(["seo_report", "backlink_context", "recommendations"] as const).map((type) => (
                    <button
                      key={type}
                      disabled={!activeDomain || aiLoading}
                      onClick={async () => {
                        setAiLoading(true);
                        try {
                          await API.runAiAnalysis(activeDomain, type);
                          const r = await API.fetchAiReports(activeDomain);
                          setAiReports(r.reports || []);
                        } finally {
                          setAiLoading(false);
                        }
                      }}
                      className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2.5 rounded-xl text-xs font-semibold shadow-sm disabled:opacity-50 transition cursor-pointer"
                    >
                      <Sparkles className="w-4 h-4" />
                      {aiLoading ? "Generating…" : type.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                    </button>
                  ))}
                </div>
                {aiReports.length === 0 ? (
                  <EmptyState title="No AI reports generated yet" msg="Set DEEPSEEK_API_KEY in your .env file, analyze a domain, and click Generate DeepSeek AI Report." />
                ) : (
                  <div className="space-y-4">
                    {aiReports.map((rep) => (
                      <div key={rep.id} className="bg-slate-50 border border-slate-200 rounded-xl p-5 space-y-4">
                        <div className="flex flex-wrap justify-between items-center gap-2 text-xs text-slate-500">
                          <span className="font-semibold text-indigo-700">{rep.domain} • {rep.analysis_type} • {rep.model_used}</span>
                          <span className="font-mono">Tokens: {rep.prompt_tokens} in / {rep.completion_tokens} out</span>
                        </div>

                        {rep.structured_output?.summary && (
                          <p className="text-sm text-slate-800 leading-relaxed">{rep.structured_output.summary}</p>
                        )}

                        <div className="grid sm:grid-cols-2 gap-4">
                          {rep.structured_output?.quality_indicators?.length > 0 && (
                            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-xs space-y-1">
                              <div className="font-semibold text-emerald-800">Quality Indicators</div>
                              {rep.structured_output.quality_indicators.map((q: string, i: number) => (
                                <div key={i} className="text-emerald-700">✓ {q}</div>
                              ))}
                            </div>
                          )}
                          {rep.structured_output?.risk_indicators?.length > 0 && (
                            <div className="bg-rose-50 border border-rose-200 rounded-xl p-3 text-xs space-y-1">
                              <div className="font-semibold text-rose-800">Risk Indicators</div>
                              {rep.structured_output.risk_indicators.map((r: string, i: number) => (
                                <div key={i} className="text-rose-700">⚠ {r}</div>
                              ))}
                            </div>
                          )}
                        </div>

                        {rep.structured_output?.recommendations?.length > 0 && (
                          <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-3 text-xs space-y-1.5">
                            <div className="font-semibold text-indigo-800">Recommendations</div>
                            {rep.structured_output.recommendations.map((r: string, i: number) => (
                              <div key={i} className="flex gap-1.5 text-indigo-700">
                                <ArrowRight className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                                <span>{r}</span>
                              </div>
                            ))}
                          </div>
                        )}

                        {rep.structured_output?.topical_relevance_assessment && (
                          <div className="text-xs text-slate-600 bg-white border border-slate-200 rounded-xl p-3">
                            <span className="font-semibold">Topical Relevance:</span> {rep.structured_output.topical_relevance_assessment}
                          </div>
                        )}
                        {rep.structured_output?.anchor_diversity_observation && (
                          <div className="text-xs text-slate-600 bg-white border border-slate-200 rounded-xl p-3">
                            <span className="font-semibold">Anchor Diversity:</span> {rep.structured_output.anchor_diversity_observation}
                          </div>
                        )}

                        <div className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-1.5">
                          {rep.disclaimer}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </Panel>
          )}

          {/* ── COMPETITOR COMPARISON ─────────────────────────────────────── */}
          {page === "competitors" && (
            <div className="space-y-6">
              <Panel title="Competitor Backlink Comparison" subtitle="Compare up to 5 domains using indexed crawl data">
                <div className="space-y-4">
                  <div className="flex flex-wrap gap-2.5">
                    <input
                      value={compInput}
                      onChange={(e) => setCompInput(e.target.value)}
                      placeholder="domain1.com, domain2.com, domain3.com"
                      className="flex-1 min-w-[260px] bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:bg-white focus:border-indigo-500"
                    />
                    <button
                      onClick={() =>
                        API.compareCompetitors(compInput)
                          .then(setCompData)
                          .catch((e) => setError(e?.response?.data?.detail || "Comparison requires backend API."))
                      }
                      className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-xl text-sm font-semibold shadow-sm cursor-pointer"
                    >
                      Compare Domains
                    </button>
                  </div>
                  {compData?.coverage_warning && (
                    <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded-xl text-xs font-medium">
                      {compData.coverage_warning}
                    </div>
                  )}
                  {compData?.profiles ? (
                    <div className="overflow-x-auto border border-slate-200 rounded-xl">
                      <table className="w-full text-xs text-left">
                        <thead className="bg-slate-50 text-slate-500 uppercase border-b border-slate-200">
                          <tr>
                            <th className="py-3 px-4">Domain</th>
                            <th className="py-3 px-4">Indexed Pages</th>
                            <th className="py-3 px-4">Backlinks</th>
                            <th className="py-3 px-4">Ref Domains</th>
                            <th className="py-3 px-4">LAS</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 bg-white">
                          {compData.profiles.map((p: any) => (
                            <tr key={p.domain} className="hover:bg-slate-50">
                              <td className="py-3 px-4 font-semibold text-indigo-700">{p.domain}</td>
                              <td className="py-3 px-4 tabular-nums">{p.indexed_pages}</td>
                              <td className="py-3 px-4 tabular-nums">{p.total_discovered_backlinks}</td>
                              <td className="py-3 px-4 tabular-nums">{p.unique_referring_domains}</td>
                              <td className="py-3 px-4 font-semibold">{p.local_authority_score?.score ?? "Insufficient Data"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <EmptyState title="Enter 2 to 5 domains to compare" msg="Only indexed local data is compared; coverage discrepancies trigger an automatic warning." />
                  )}
                </div>
              </Panel>

              {/* Competitor bar chart */}
              {compBarData.length >= 2 && (
                <Panel title="Side-by-Side Backlink Volume" subtitle="Backlinks, referring domains, and indexed pages by domain">
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={compBarData} barCategoryGap="25%">
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                        <XAxis dataKey="domain" stroke="#64748b" fontSize={11} tickLine={false} />
                        <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                        <Tooltip contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e2e8f0", borderRadius: "10px", fontSize: "12px" }} />
                        <Legend wrapperStyle={{ fontSize: "12px" }} />
                        <Bar dataKey="backlinks" fill="#4F46E5" radius={[6, 6, 0, 0]} maxBarSize={36} name="Backlinks" />
                        <Bar dataKey="referring" fill="#0D9488" radius={[6, 6, 0, 0]} maxBarSize={36} name="Referring Domains" />
                        <Bar dataKey="indexed" fill="#D97706" radius={[6, 6, 0, 0]} maxBarSize={36} name="Indexed Pages" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </Panel>
              )}
            </div>
          )}

          {/* ── CRAWLER MANAGEMENT ───────────────────────────────────────── */}
          {page === "crawler" && (
            <Panel title="Scrapy BFS Crawler & Seed Manager" subtitle="Crawl permitted external websites to discover outgoing backlinks and build your local index">
              <div className="space-y-5">
                <div className="flex flex-wrap gap-2.5">
                  <input
                    value={seedInput}
                    onChange={(e) => setSeedInput(e.target.value)}
                    placeholder="Add permitted seed website (e.g. https://example.com)"
                    className="flex-1 min-w-[260px] bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:bg-white focus:border-emerald-500"
                  />
                  <button
                    onClick={async () => {
                      if (!seedInput.trim()) return;
                      try {
                        await API.addSeed(seedInput.trim());
                        setSeedInput("");
                        refreshGlobal();
                      } catch (e: any) {
                        setError(e?.response?.data?.detail || "Could not register seed domain.");
                      }
                    }}
                    className="inline-flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-2.5 rounded-xl text-sm font-semibold shadow-sm cursor-pointer"
                  >
                    <Plus className="w-4 h-4" /> Add Seed
                  </button>
                </div>

                <div className="flex flex-wrap gap-4 items-center bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs">
                  <label className="flex items-center gap-2 font-medium text-slate-700">
                    Max Pages
                    <input
                      type="number"
                      value={crawlMaxPages}
                      onChange={(e) => setCrawlMaxPages(Number(e.target.value))}
                      className="w-24 bg-white border border-slate-200 rounded-lg px-2.5 py-1.5"
                    />
                  </label>
                  <label className="flex items-center gap-2 font-medium text-slate-700">
                    Max Depth
                    <input
                      type="number"
                      value={crawlMaxDepth}
                      onChange={(e) => setCrawlMaxDepth(Number(e.target.value))}
                      className="w-20 bg-white border border-slate-200 rounded-lg px-2.5 py-1.5"
                    />
                  </label>
                  <button
                    disabled={seeds.length === 0}
                    onClick={async () => {
                      await API.startCrawlJob(seeds.map((s) => s.seed_url), crawlMaxPages, crawlMaxDepth);
                      refreshGlobal();
                    }}
                    className="inline-flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg font-semibold shadow-sm disabled:opacity-50 cursor-pointer"
                  >
                    <Play className="w-3.5 h-3.5" /> Start BFS Crawl ({seeds.length} Seeds)
                  </button>
                </div>

                <div>
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Registered Seed Domains</div>
                  {seeds.length === 0 ? (
                    <p className="text-xs text-slate-500">No seed domains registered yet.</p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {seeds.map((s) => (
                        <span key={s.id} className="inline-flex items-center gap-1.5 bg-indigo-50 text-indigo-700 border border-indigo-200 pl-3 pr-1.5 py-1 rounded-full text-xs font-medium">
                          {s.domain}
                          <button
                            onClick={async () => {
                              try {
                                await API.deleteSeed(s.id);
                                refreshGlobal();
                              } catch {
                                setError("Could not delete seed domain.");
                              }
                            }}
                            className="text-indigo-400 hover:text-rose-600 transition cursor-pointer"
                            title="Remove seed"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </Panel>
          )}

          {/* ── CRAWL JOB HISTORY ─────────────────────────────────────────── */}
          {page === "jobs" && (
            <Panel title="Crawl Job History" subtitle="Live worker progress and historical crawl logs">
              {jobs.length === 0 ? (
                <EmptyState title="No crawl jobs recorded" msg="Launch your first crawl from Crawler & Seeds to track job execution here." />
              ) : (
                <div className="space-y-6">
                {jobs.length >= 2 && (
                  <div>
                    <p className="text-sm font-semibold text-slate-700 mb-2">Crawl Performance — Pages & Links per Job</p>
                    <div className="h-52">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={jobs.slice(-20).map((j: any) => ({
                          job: `#${j.id}`,
                          pages: j.pages_crawled ?? 0,
                          links: j.links_discovered ?? 0,
                        }))}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                          <XAxis dataKey="job" stroke="#64748b" fontSize={11} tickLine={false} />
                          <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                          <Tooltip contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e2e8f0", borderRadius: "10px", fontSize: "12px" }} />
                          <Legend wrapperStyle={{ fontSize: "12px" }} />
                          <Bar dataKey="pages" fill="#4F46E5" radius={[4, 4, 0, 0]} maxBarSize={28} name="Pages Crawled" />
                          <Bar dataKey="links" fill="#059669" radius={[4, 4, 0, 0]} maxBarSize={28} name="Links Discovered" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}
                <div className="overflow-x-auto border border-slate-200 rounded-xl">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-slate-50 text-slate-500 uppercase border-b border-slate-200">
                      <tr>
                        <th className="py-3 px-4">Job #</th>
                        <th className="py-3 px-4">Target</th>
                        <th className="py-3 px-4">Status</th>
                        <th className="py-3 px-4">Pages</th>
                        <th className="py-3 px-4">Links</th>
                        <th className="py-3 px-4">Started</th>
                        <th className="py-3 px-4 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 bg-white">
                      {jobs.map((j) => (
                        <tr key={j.id} className="hover:bg-slate-50">
                          <td className="py-3 px-4 font-mono">#{j.id}</td>
                          <td className="py-3 px-4 font-medium">{j.target_domain}</td>
                          <td className="py-3 px-4">
                            <Badge tone={j.status === "completed" ? "emerald" : j.status === "running" ? "indigo" : j.status === "failed" ? "rose" : "slate"}>
                              {j.status}
                            </Badge>
                          </td>
                          <td className="py-3 px-4 tabular-nums">{j.pages_crawled}</td>
                          <td className="py-3 px-4 tabular-nums">{j.links_discovered}</td>
                          <td className="py-3 px-4 text-slate-500">{j.started_at ? new Date(j.started_at).toLocaleString() : "—"}</td>
                          <td className="py-3 px-4 text-right">
                            {j.status === "running" && (
                              <button
                                onClick={() => API.stopCrawlJob(j.id).then(refreshGlobal)}
                                className="inline-flex items-center gap-1 text-rose-600 hover:text-rose-800 font-semibold cursor-pointer"
                              >
                                <Square className="w-3 h-3" /> Stop
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                </div>
              )}
            </Panel>
          )}

          {/* ── PROJECT MANAGEMENT ───────────────────────────────────────── */}
          {page === "projects" && (
            <Panel title="Project Workspaces" subtitle="Group domains and track SEO campaigns cleanly">
              <div className="space-y-4">
                <div className="grid md:grid-cols-3 gap-3">
                  <input
                    placeholder="Project Name"
                    value={projForm.name}
                    onChange={(e) => setProjForm({ ...projForm, name: e.target.value })}
                    className="bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:bg-white focus:border-indigo-500"
                  />
                  <input
                    placeholder="Root Domain (e.g. example.com)"
                    value={projForm.root_domain}
                    onChange={(e) => setProjForm({ ...projForm, root_domain: e.target.value })}
                    className="bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:bg-white focus:border-indigo-500"
                  />
                  <button
                    onClick={async () => {
                      if (!projForm.name || !projForm.root_domain) return;
                      await API.createProject(projForm.name, projForm.root_domain, projForm.description);
                      setProjForm({ name: "", root_domain: "", description: "" });
                      refreshGlobal();
                    }}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl px-4 py-2.5 text-sm font-semibold shadow-sm cursor-pointer"
                  >
                    Create Project
                  </button>
                </div>
                {projects.length === 0 ? (
                  <EmptyState title="No projects yet" msg="Create a project workspace above to organize your domains." />
                ) : (
                  <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {projects.map((p) => (
                      <div key={p.id} className="bg-slate-50 border border-slate-200 p-4 rounded-xl flex justify-between items-center">
                        <span className="font-semibold text-sm text-slate-900">{p.name}</span>
                        <span className="text-xs font-medium text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-full">{p.root_domain}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </Panel>
          )}

          {/* ── SETTINGS ──────────────────────────────────────────────────── */}
          {page === "settings" && (
            <div className="space-y-5">
              <Panel title="Runtime Configuration" subtitle="Conservative defaults optimized for Windows 16 GB RAM workstations">
                <div className="grid sm:grid-cols-2 gap-4 text-xs">
                  <SettingRow label="Celery Workers" value="2 concurrent workers (CELERY_WORKER_CONCURRENCY)" />
                  <SettingRow label="Crawler Limits" value="4 concurrent requests • 1.5s delay • robots.txt enforced" />
                  <SettingRow label="SSRF Protection" value="Blocks localhost, LAN, link-local & cloud metadata IPs" />
                  <SettingRow label="AI Integration" value="Official DeepSeek API (configured via .env)" />
                  <SettingRow label="ML Engine" value="CPU-only Scikit-learn + XGBoost (RF/XGB ensemble, Isolation Forest, TF-IDF, K-Means)" />
                  <SettingRow label="Database" value="PostgreSQL 16 (19 normalized tables + Alembic migrations, auto-run on startup)" />
                  <SettingRow label="Beat Schedule" value="Backlink verify: 6h • PageRank: daily 02:00 UTC • Metrics: 12h • Auto-recrawl: 4h" />
                  <SettingRow label="ML Models" value="Persisted to /app/ml_models volume (survives restarts)" />
                  <SettingRow label="Rate Limiter" value="120 req/60s per IP — OrderedDict with 10,000-IP LRU eviction cap" />
                  <SettingRow label="Backlink Verifier" value="Up to 10 parallel HTTP workers via ThreadPoolExecutor (pure, no DB in threads)" />
                  <SettingRow label="JWT Auth" value="Custom HMAC-SHA256 (Python stdlib only) — no third-party auth library" />
                  <SettingRow label="Password Hashing" value="PBKDF2-SHA256 with 260,000 iterations (Python stdlib hashlib)" />
                </div>
              </Panel>
              <Panel title="API Status" subtitle="Live health check from your browser">
                <div className="flex items-center gap-3 text-sm">
                  <span className={`w-3 h-3 rounded-full shrink-0 ${backendOnline ? "bg-emerald-400 animate-pulse" : "bg-amber-400"}`} />
                  <span className="font-medium text-slate-700">FastAPI Backend:</span>
                  <span className={backendOnline ? "text-emerald-600 font-semibold" : "text-amber-600 font-semibold"}>
                    {backendOnline ? "Online — PostgreSQL & Redis connected" : "Offline or starting up"}
                  </span>
                </div>
                <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1.5 text-xs text-indigo-600 hover:text-indigo-800 font-medium">
                  Open Swagger API Docs <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </Panel>
            </div>
          )}
        </main>
      </div>

      {toasts.length > 0 && (
        <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none">
          {toasts.map((t) => (
            <div key={t.id} className={`pointer-events-auto flex items-center gap-2.5 px-4 py-3 rounded-xl shadow-lg text-sm font-medium ${t.type === "success" ? "bg-emerald-600 text-white" : "bg-rose-600 text-white"}`}>
              {t.type === "success" ? <CheckCircle className="w-4 h-4 shrink-0" /> : <AlertTriangle className="w-4 h-4 shrink-0" />}
              <span>{t.message}</span>
              <button onClick={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))} className="ml-1 opacity-70 hover:opacity-100 cursor-pointer">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function KpiCard({ label, value, icon, tone }: { label: string; value: string | number; icon: React.ReactNode; tone: "indigo" | "emerald" | "violet" | "amber" }) {
  const styles = { indigo: "bg-indigo-50 text-indigo-600 border-indigo-100", emerald: "bg-emerald-50 text-emerald-600 border-emerald-100", violet: "bg-violet-50 text-violet-600 border-violet-100", amber: "bg-amber-50 text-amber-600 border-amber-100" }[tone];
  return (
    <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs hover:shadow-md hover:border-slate-300/80 transition">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-500">{label}</span>
        <span className={`w-8 h-8 rounded-xl border flex items-center justify-center ${styles}`}>{icon}</span>
      </div>
      <div className="text-2xl font-bold text-slate-900 mt-3 tracking-tight tabular-nums">{value}</div>
    </div>
  );
}

function CompactStat({ label, value, dot }: { label: string; value: string | number; dot: string }) {
  return (
    <div className="bg-white border border-slate-200/90 rounded-xl px-4 py-3.5 shadow-xs flex items-center justify-between gap-2">
      <div className="flex items-center gap-2 min-w-0">
        <span className={`w-2 h-2 rounded-full shrink-0 ${dot}`} />
        <span className="text-xs font-medium text-slate-500 truncate">{label}</span>
      </div>
      <span className="text-sm font-bold text-slate-900 tabular-nums shrink-0">{value}</span>
    </div>
  );
}

function Panel({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <section className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs">
      <div className="mb-5">
        <h2 className="font-semibold text-base text-slate-900">{title}</h2>
        {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
      {children}
    </section>
  );
}

function EmptyState({ title, msg, actionLabel, onAction }: { title: string; msg: string; actionLabel?: string; onAction?: () => void }) {
  return (
    <div className="bg-slate-50/80 border border-dashed border-slate-300 rounded-xl p-8 text-center flex flex-col items-center justify-center">
      <div className="w-10 h-10 rounded-full bg-white border border-slate-200 flex items-center justify-center text-slate-400 mb-3 shadow-xs">
        <Search className="w-4 h-4" />
      </div>
      <div className="text-sm font-semibold text-slate-800">{title}</div>
      <p className="text-xs text-slate-500 mt-1 max-w-md leading-relaxed">{msg}</p>
      {actionLabel && onAction && (
        <button onClick={onAction} className="mt-4 inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-700 bg-indigo-50 hover:bg-indigo-100 px-3.5 py-2 rounded-lg transition cursor-pointer">
          {actionLabel} <ArrowRight className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}

function Badge({ children, tone }: { children: React.ReactNode; tone: "emerald" | "amber" | "rose" | "indigo" | "slate" }) {
  const cls = { emerald: "bg-emerald-50 text-emerald-700 border-emerald-200", amber: "bg-amber-50 text-amber-700 border-amber-200", rose: "bg-rose-50 text-rose-700 border-rose-200", indigo: "bg-indigo-50 text-indigo-700 border-indigo-200", slate: "bg-slate-100 text-slate-700 border-slate-200" }[tone];
  return <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${cls}`}>{children}</span>;
}

function SettingRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
      <div className="font-semibold text-slate-800">{label}</div>
      <div className="text-slate-500 mt-1">{value}</div>
    </div>
  );
}

function LoginPage({ onLogin }: { onLogin: (token: string) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (mode === "register") await API.registerUser(email, fullName, password);
      const data = await API.loginUser(email, password);
      onLogin(data.access_token);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Authentication failed. Check credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0F1123] flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-teal-400 flex items-center justify-center mx-auto shadow-lg shadow-indigo-500/30 mb-4">
            <ShieldCheck className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">SEO Intelligence</h1>
          <p className="text-sm text-slate-400 mt-1">Enterprise Local Suite</p>
        </div>

        <div className="bg-white/[0.05] border border-white/10 rounded-2xl p-6 backdrop-blur">
          <div className="flex gap-1 mb-6 bg-white/[0.05] p-1 rounded-xl">
            {(["login", "register"] as const).map((m) => (
              <button key={m} onClick={() => { setMode(m); setError(""); }} className={`flex-1 py-2 text-sm font-medium rounded-lg transition cursor-pointer ${mode === m ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-white"}`}>
                {m === "login" ? "Sign In" : "Register"}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "register" && (
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Full Name</label>
                <input value={fullName} onChange={(e) => setFullName(e.target.value)} required className="w-full bg-white/[0.07] border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition" placeholder="Your full name" />
              </div>
            )}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="w-full bg-white/[0.07] border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition" placeholder="admin@seo.local" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Password</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} className="w-full bg-white/[0.07] border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition" placeholder="••••••••" />
            </div>
            {error && <div className="text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-lg px-3 py-2.5">{error}</div>}
            <button type="submit" disabled={loading} className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed text-white py-2.5 rounded-xl text-sm font-semibold transition shadow-md shadow-indigo-900/40 cursor-pointer">
              {loading ? "Please wait…" : mode === "login" ? "Sign In" : "Create Account & Sign In"}
            </button>
          </form>

          <p className="text-center text-xs text-slate-500 mt-5">Local deployment — credentials stored securely in PostgreSQL.</p>
        </div>
      </div>
    </div>
  );
}
