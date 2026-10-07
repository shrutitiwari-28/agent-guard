export const API = process.env.NEXT_PUBLIC_API ?? "";
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(API + path, init);
  if (!r.ok) throw new Error((await r.text()).slice(0, 200) || `HTTP ${r.status}`);
  return (await r.json()) as T;
}
export const operator = (token: string): RequestInit => ({ method: "POST", headers: { "X-Operator-Token": token } });
export const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));
export const hostOf = (u: string) => { try { return new URL(u).hostname; } catch { return u; } };
export const destOf = (a: Record<string, unknown>): string => String(a.to ?? (a.url ? hostOf(String(a.url)) : "") ?? "") || String(a.path ?? a.sql ?? a.id ?? "");
export const errMsg = (e: unknown) => (e instanceof Error ? e.message : "Request failed");
