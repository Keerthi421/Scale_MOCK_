/** Mirrors the backend Pydantic schemas in app/schemas/system_design.py. */

export type NodeKind =
  | "client" | "mobile_app" | "web_app" | "dns" | "cdn"
  | "load_balancer" | "api_gateway" | "reverse_proxy" | "rate_limiter"
  | "app_server" | "microservice" | "worker" | "cron"
  | "sql_database" | "nosql_database" | "read_replica" | "cache"
  | "object_storage" | "search_index" | "data_warehouse"
  | "message_queue" | "event_stream" | "pub_sub"
  | "monitoring" | "logging" | "auth_service" | "config_service"
  | "custom";

export type Difficulty = "easy" | "medium" | "hard";

export interface PaletteComponent {
  kind: NodeKind;
  label: string;
  category: string;
  description: string;
  icon: string;
}

export interface CanvasNodeData {
  kind: NodeKind;
  label: string;
  notes?: string | null;
}

export interface ProblemSummary {
  id: string;
  slug: string;
  title: string;
  summary: string;
  difficulty: Difficulty;
  tags: string[];
  companies: string[];
  estimated_minutes: number;
  sheet_tier: number;
  is_premium: boolean;
  is_solved: boolean;
  is_locked: boolean;
}

export interface CapacityRow {
  metric: string;
  assumption: string;
  working: string;
  result: string;
}

export interface ProblemDetail {
  id: string;
  slug: string;
  title: string;
  difficulty: Difficulty;
  description_md: string;
  functional_requirements: string[];
  non_functional_requirements: string[];
  estimated_minutes: number;
  tags: string[];
  companies: string[];
  is_locked: boolean;
  study_guide_md?: string | null;
  capacity_estimation?: CapacityRow[] | null;
}

export interface Workspace {
  id: string;
  problem_id: string;
  title: string;
  nodes: SerializedNode[];
  edges: SerializedEdge[];
  candidate_notes_md: string | null;
  version: number;
  share_slug: string | null;
  updated_at: string;
}

/** The wire shape — flat, matching the backend's JSONB columns. React Flow's
 *  nested `data` shape is converted at the boundary, not stored. */
export interface SerializedNode {
  id: string;
  kind: NodeKind;
  label: string;
  x: number;
  y: number;
  notes?: string | null;
}

export interface SerializedEdge {
  id: string;
  source: string;
  target: string;
  label?: string | null;
}

export interface DesignIssue {
  severity: "critical" | "major" | "minor";
  title: string;
  component?: string | null;
  explanation: string;
  recommendation: string;
}

export interface DimensionScore {
  dimension: string;
  score: number;
  rationale: string;
}

export interface DesignReviewPayload {
  overall_score: number;
  summary_md: string;
  dimension_scores: DimensionScore[];
  issues: DesignIssue[];
  tradeoffs: { decision: string; benefit: string; cost: string; alternative: string }[];
  capacity_checks: { metric: string; candidate_estimate?: string | null; assessment: string }[];
  missing_components: string[];
  bottlenecks: string[];
  single_points_of_failure: string[];
  strengths: string[];
  next_steps: string[];
}

export interface ReviewResponse {
  id: string;
  workspace_id: string;
  workspace_version: number;
  overall_score: number;
  payload: DesignReviewPayload;
  model_id: string;
  prompt_version: string;
  created_at: string;
}

export interface ApiError {
  error: { code: string; message: string; details: Record<string, unknown> };
}
