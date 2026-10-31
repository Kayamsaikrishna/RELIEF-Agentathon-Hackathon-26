const KEY = "relief.token";
let token: string | null = null;
try { token = localStorage.getItem(KEY); } catch { /* storage blocked: stay signed in for this tab only */ }

export const setToken = (t: string | null) => {
  token = t;
  try { t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY); } catch { /* ignore */ }
};
export const hasToken = () => !!token;

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
let onUnauthorized: () => void = () => {};
export const setUnauthorizedHandler = (fn: () => void) => { onUnauthorized = fn; };

function detailText(d: unknown): string {
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => (x && typeof x === "object" && "msg" in x ? `${(x as { loc?: unknown[] }).loc?.slice(1).join(".") ?? ""} ${(x as { msg: string }).msg}`.trim() : String(x))).join("; ");
  return "Something went wrong.";
}

export async function api<T>(path: string, opts: { method?: string; body?: unknown; form?: FormData } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetch("/api" + path, { method: opts.method ?? (opts.body || opts.form ? "POST" : "GET"), headers, body: opts.form ?? (opts.body !== undefined ? JSON.stringify(opts.body) : undefined) });
  } catch {
    throw new ApiError(0, "Cannot reach the RELIEF service. Check that the backend is running.");
  }
  if (res.status === 401 && path !== "/auth/login") { setToken(null); onUnauthorized(); }
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = detailText((await res.json()).detail); } catch { /* not json */ }
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}
