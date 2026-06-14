// Mirror of backend/app/models.py. Keep the two in lockstep — that one-to-one
// correspondence is what keeps the app type-safe end to end (doc §6).

export type MetricFamily =
  | 'lexical'
  | 'semantic'
  | 'classification'
  | 'model_judge'
  | 'rag'
  | 'operational'

export interface MetricInfo {
  id: string
  name: string
  family: string
  description: string
  requires_reference: boolean
  range: number[] // [min, max]
  how_to_read: string
  caveat: string
  available: boolean
  unavailable_reason?: string | null
  // Selectable for a pre-run cost estimate even when not runnable now (e.g. an
  // LLM metric with the SDK present but no API key).
  estimable: boolean
  // Set-level metrics (precision/recall/F1): summary card only, no per-case column.
  aggregate_only: boolean
  // RAG metrics need context; LLM-judge produces a written rationale.
  requires_context: boolean
  produces_rationale: boolean
}

export interface TestCase {
  id: string
  input?: string | null
  prediction?: string | null
  reference?: string | null
  context?: string | null
}

export interface JudgeConfig {
  model?: string | null
  rubric?: string | null
  // "Bring your own key" map (provider id -> API key), sent per-request. A key
  // here wins over the backend env; the backend never persists it.
  keys?: Record<string, string> | null
}

export interface EvaluateRequest {
  metrics: string[]
  cases: TestCase[]
  dataset_id?: string | null
  dataset_name?: string | null
  judge?: JudgeConfig | null
}

export interface EstimateRequest {
  metrics: string[]
  cases: TestCase[]
  judge?: JudgeConfig | null
  // Use the free count_tokens endpoint for exact input tokens (needs a key).
  exact?: boolean
}

export interface MetricEstimate {
  metric_id: string
  calls: number
  tokens_in: number
}

export interface EstimateResponse {
  model: string
  llm_calls: number
  tokens_in: number
  expected_tokens_out: number
  max_tokens_out: number
  expected_cost: number
  // Worst-case ceiling (every judge reply hits the 1024-token cap).
  max_cost: number
  // True only when count_tokens produced the input counts (else heuristic).
  exact: boolean
  per_metric: MetricEstimate[]
}

export interface CaseResult {
  id: string
  input?: string | null
  prediction?: string | null
  reference?: string | null
  context?: string | null
  // null means "not applicable" (rendered as a dash, never a zero).
  scores: Record<string, number | null>
  // metricId -> the judge's written rationale (LLM-judge / RAG metrics).
  rationales: Record<string, string>
}

export interface Operational {
  latency_ms: number
  tokens_in: number
  tokens_out: number
  cost: number
}

export interface OperationalSummary {
  calls: number
  latency_p50_ms: number
  latency_p95_ms: number
  tokens_in: number
  tokens_out: number
  cost: number
}

export interface ModelInfo {
  id: string
  name: string
  provider: string // which provider owns this model (anthropic | openai | gemini)
}

export interface ProviderInfo {
  id: string // anthropic | openai | gemini
  name: string
  env_var: string // canonical env var name (shown as a hint in Settings)
  env_available: boolean // a usable key is present in the backend env
  sdk_installed: boolean // the provider's SDK is importable on the backend
  models: ModelInfo[]
}

export interface GenerateRequest {
  cases: TestCase[]
  model?: string | null
  system?: string | null
  max_tokens?: number
  // Per-request provider keys (provider id -> key); env is the fallback.
  keys?: Record<string, string> | null
}

export interface GeneratedCase {
  id: string
  prediction: string
  operational: Operational
}

export interface GenerateResponse {
  model: string
  cases: GeneratedCase[]
  summary: OperationalSummary
}

export interface RunSummary {
  run_id: string
  created_at: string
  dataset_name?: string | null
  metrics: string[]
  aggregate: Record<string, number | null>
}

export interface ConfusionMatrix {
  labels: string[]
  matrix: number[][] // matrix[trueIdx][predIdx]
}

export interface RunResponse {
  run_id: string
  created_at: string
  dataset_name?: string | null
  metrics: string[]
  per_case: CaseResult[]
  aggregate: Record<string, number | null>
  confusion_matrix?: ConfusionMatrix | null
  operational?: OperationalSummary | null
}

// --- dimensionality-reduction explorer (mirrors models.py) -----------------

export interface ProjectionParamSpec {
  key: string
  label: string
  kind: 'int' | 'float'
  default: number
  min: number
  max: number
  step: number
  help: string
}

export interface ProjectionAlgorithmInfo {
  id: string // pca | tsne | umap
  name: string
  description: string
  params: ProjectionParamSpec[]
  available: boolean
  unavailable_reason?: string | null
}

export interface SampleDatasetInfo {
  id: string
  name: string
  description: string
  n_samples: number
  n_features: number
}

export interface ProjectRequest {
  source: 'dataset' | 'sample'
  algorithms: string[]
  field?: string | null // dataset source: which case field to embed
  cases?: TestCase[]
  sample_id?: string | null // sample source
  params?: Record<string, Record<string, number>> // { tsne: { perplexity: 30 } }
}

export interface ProjectedPoint {
  id: string
  x: number
  y: number
  label?: string | null // category for coloring
  text?: string | null // hover preview
}

export interface ProjectionMeta {
  variance_explained?: number[] | null // PCA
  perplexity?: number | null // t-SNE
  n_neighbors?: number | null // UMAP
  min_dist?: number | null // UMAP
  preprocessed_dims?: number | null
}

export interface ProjectionResult {
  algorithm: string
  points: ProjectedPoint[]
  meta: ProjectionMeta
}

export interface ProjectResponse {
  source: string
  n_points: number
  dims_in: number
  label_kind: 'category' | 'none'
  results: ProjectionResult[]
}
