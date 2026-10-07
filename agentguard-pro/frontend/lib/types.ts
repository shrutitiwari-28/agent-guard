export type Decision = "ALLOW" | "HOLD" | "BLOCK";
export type Mode = "none" | "text" | "flow" | "full";
export interface Control { control: string; action: string; reason: string }
export interface EvidenceItem { rule: string; weight: number; match: string }
export interface Ev {
  call_id: string; session: string; step: number; tool: string; args: Record<string, unknown>; decision: Decision; score: number;
  rationale: string[]; layers: string[]; controls: Control[]; evidence: EvidenceItem[]; policy_version: string; executed: boolean; tainted: boolean;
  state: "ACTIVE" | "CONTAINED"; output: string | null; latency_ms: number; hash?: string; harmful?: boolean; approves?: string;
}
export interface EpisodeMeta { id: string; kind: "attack" | "benign"; title: string; trick: string; task: string; limit: boolean; source: string }
export interface Demo { episode: { id: string; kind: "attack" | "benign"; title: string; trick: string; task: string; limit: boolean }; session: string; unguarded: Ev[]; guarded: Ev[] }
export interface ModeStats { attacks_succeeded: number; benign_completed: number; benign_quarantined: number; benign_holds: number; p50_ms: number; p95_ms: number }
export interface EvalResult {
  modes: Record<Mode, ModeStats>; n_attacks: number; n_benign: number;
  per_attack: Record<string, { title: string; trick: string } & Record<Mode, boolean>>;
  ingress_filter: { classifier_loaded: boolean; attacks_flagged: number; attacks: number; benign_flagged: number; benign: number };
}
export interface LedgerRow { id: number; ts: number; session: string; tool: string; args: string; score: number; decision: Decision; rationale: string[]; hash: string }
export interface Verify { ok: boolean; broken_at: number | null; checked: number; head?: string }
export interface Health { service: string; demo_mode: boolean; demo_token: string | null }
