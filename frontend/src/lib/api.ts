import type {
  ApiError,
  PaletteComponent,
  ProblemDetail,
  ProblemSummary,
  ReviewResponse,
  SerializedEdge,
  SerializedNode,
  Workspace,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiRequestError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiRequestError";
  }

  /** Distinguishes a paywall from a generic failure so the UI can show an
   *  upgrade path rather than an error toast. */
  get isPremiumRequired() {
    return this.status === 402;
  }

  /** A concurrent save from another tab — recoverable, not fatal. */
  get isConflict() {
    return this.status === 409;
  }
}

function authHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = window.localStorage.getItem("if_access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init?.headers ?? {}),
    },
  });

  if (response.status === 204) return undefined as T;

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const err = body as ApiError | null;
    throw new ApiRequestError(
      response.status,
      err?.error?.code ?? "unknown_error",
      err?.error?.message ?? `Request failed (${response.status})`,
      err?.error?.details ?? {},
    );
  }

  return body as T;
}

export const api = {
  listComponents: () => request<PaletteComponent[]>("/system-design/components"),

  listProblems: (params: { sheet_tier?: number; search?: string; difficulty?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.sheet_tier) q.set("sheet_tier", String(params.sheet_tier));
    if (params.search) q.set("search", params.search);
    if (params.difficulty) q.set("difficulty", params.difficulty);
    return request<{ items: ProblemSummary[]; total: number }>(
      `/system-design/problems?${q.toString()}`,
    );
  },

  getProblem: (slug: string) =>
    request<ProblemDetail>(`/system-design/problems/${slug}`),

  openWorkspace: (slug: string) =>
    request<Workspace>(`/system-design/problems/${slug}/workspace`, { method: "POST" }),

  saveWorkspace: (
    id: string,
    payload: {
      nodes: SerializedNode[];
      edges: SerializedEdge[];
      candidate_notes_md: string | null;
      expected_version: number | null;
    },
  ) =>
    request<Workspace>(`/system-design/workspaces/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  reviewWorkspace: (id: string) =>
    request<ReviewResponse>(`/system-design/workspaces/${id}/review`, { method: "POST" }),

  shareWorkspace: (id: string) =>
    request<{ share_slug: string }>(`/system-design/workspaces/${id}/share`, {
      method: "POST",
    }),
};
