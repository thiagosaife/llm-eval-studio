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
}

export interface EvaluateRequest {
  metrics: string[]
  cases: TestCase[]
  dataset_id?: string | null
  dataset_name?: string | null
  judge?: JudgeConfig | null
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
}

export interface GenerateRequest {
  cases: TestCase[]
  model?: string | null
  system?: string | null
  max_tokens?: number
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
