// A thin, typed wrapper around fetch. Every response is parsed as its declared
// interface, so callers get end-to-end types without sprinkling `any` around.
import type {
  EvaluateRequest,
  GenerateRequest,
  GenerateResponse,
  MetricInfo,
  ModelInfo,
  ProjectionAlgorithmInfo,
  ProjectRequest,
  ProjectResponse,
  RunResponse,
  RunSummary,
  SampleDatasetInfo,
} from './types'

const BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8000/api'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let resp: Response
  try {
    resp = await fetch(`${BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    })
  } catch {
    // Network-level failure (server down, CORS, offline) — fetch rejects with
    // no status, so give the user something actionable.
    throw new ApiError(0, `Can't reach the API at ${BASE}. Is the backend running?`)
  }

  if (!resp.ok) {
    let detail = resp.statusText
    try {
      const body = await resp.json()
      if (body?.detail) detail = body.detail
    } catch {
      /* response had no JSON body */
    }
    throw new ApiError(resp.status, detail)
  }

  return (await resp.json()) as T
}

export const api = {
  listMetrics: () => request<MetricInfo[]>('/metrics'),
  listModels: () => request<ModelInfo[]>('/models'),
  evaluate: (body: EvaluateRequest) =>
    request<RunResponse>('/evaluate', { method: 'POST', body: JSON.stringify(body) }),
  generate: (body: GenerateRequest) =>
    request<GenerateResponse>('/generate', { method: 'POST', body: JSON.stringify(body) }),
  getRun: (runId: string) => request<RunResponse>(`/runs/${encodeURIComponent(runId)}`),
  listRuns: () => request<RunSummary[]>('/runs'),
  listProjectionAlgorithms: () => request<ProjectionAlgorithmInfo[]>('/projection/algorithms'),
  listProjectionSamples: () => request<SampleDatasetInfo[]>('/projection/samples'),
  project: (body: ProjectRequest) =>
    request<ProjectResponse>('/project', { method: 'POST', body: JSON.stringify(body) }),
}
