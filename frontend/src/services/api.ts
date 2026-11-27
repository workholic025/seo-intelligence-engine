import axios from "axios";

export const api = axios.create({
  baseURL: "http://localhost:8000/api",
  timeout: 30000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("seo_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("seo_token");
      window.location.reload();
    }
    return Promise.reject(error);
  }
);

export const loginUser = (email: string, password: string) =>
  api.post("/auth/login", { email, password }).then((r) => r.data);

export const registerUser = (email: string, full_name: string, password: string) =>
  api.post("/auth/register", { email, full_name, password }).then((r) => r.data);

export const fetchDashboardStats = () => api.get("/dashboard/stats").then((r) => r.data);
export const analyzeDomain = (target: string) => api.post("/domains/analyze", { target }).then((r) => r.data);
export const fetchOverview = (domain: string) => api.get(`/domains/${domain}/overview`).then((r) => r.data);
export const fetchBacklinks = (domain: string, params: Record<string, any>) =>
  api.get(`/domains/${domain}/backlinks`, { params }).then((r) => r.data);
export const fetchBacklinkDetail = (id: number) => api.get(`/backlinks/${id}`).then((r) => r.data);
export const fetchReferringDomains = (domain: string, params: Record<string, any> = {}) =>
  api.get(`/domains/${domain}/referring-domains`, { params }).then((r) => r.data);
export const fetchAuthority = (domain: string) => api.get(`/domains/${domain}/authority`).then((r) => r.data);
export const fetchPageRank = (domain: string, recalculate = false) =>
  api.get(`/domains/${domain}/pagerank`, { params: { recalculate } }).then((r) => r.data);
export const fetchQualityAndAnchors = (domain: string) => api.get(`/domains/${domain}/quality`).then((r) => r.data);
export const fetchSpamAnalysis = (domain: string) => api.get(`/domains/${domain}/spam-analysis`).then((r) => r.data);
export const compareCompetitors = (domains: string) =>
  api.get("/competitors/compare", { params: { domains } }).then((r) => r.data);
export const startCrawlJob = (seed_domains: string[], max_pages: number, max_depth: number) =>
  api.post("/crawler/start", { seed_domains, max_pages, max_depth }).then((r) => r.data);
export const stopCrawlJob = (job_id: number) => api.post("/crawler/stop", { job_id }).then((r) => r.data);
export const fetchCrawlJobs = () => api.get("/crawler/jobs").then((r) => r.data);
export const fetchSeeds = () => api.get("/crawler/seeds").then((r) => r.data);
export const addSeed = (domain: string) => api.post("/crawler/seeds", { domain }).then((r) => r.data);
export const runAiAnalysis = (domain: string, analysis_type: string) =>
  api.post("/ai/analyze", { domain, analysis_type }).then((r) => r.data);
export const fetchAiReports = (domain?: string) =>
  api.get("/ai/reports", { params: domain ? { domain } : {} }).then((r) => r.data);
export const fetchProjects = () => api.get("/projects").then((r) => r.data);
export const createProject = (name: string, root_domain: string, description: string) =>
  api.post("/projects", { name, root_domain, description }).then((r) => r.data);

export const fetchMetricsHistory = (domain: string, limit = 30) =>
  api.get(`/domains/${domain}/metrics-history`, { params: { limit } }).then((r) => r.data);

export const addTrainingLabel = (backlink_id: number, is_spam: boolean, reviewer_note = "") =>
  api.post("/ml/labels", { backlink_id, is_spam, reviewer_note }).then((r) => r.data);
export const fetchTrainingLabels = (domain?: string, page = 1, page_size = 25) =>
  api.get("/ml/labels", { params: { domain, page, page_size } }).then((r) => r.data);
export const deleteTrainingLabel = (label_id: number) =>
  api.delete(`/ml/labels/${label_id}`).then((r) => r.data);

export const deleteSeed = (id: number) => api.delete(`/crawler/seeds/${id}`).then((r) => r.data);

export const fetchAuthorityHistory = (domain: string, limit = 30) =>
  api.get(`/domains/${domain}/authority-history`, { params: { limit } }).then((r) => r.data);

export const fetchContentRelevance = (domain: string, source_url: string) =>
  api.get(`/domains/${domain}/content-relevance`, { params: { source_url } }).then((r) => r.data);
