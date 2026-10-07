import type { EpisodeMeta } from "@/lib/types";
interface Props { episodes: EpisodeMeta[]; selected: string | null; busy: boolean; onPick: (e: EpisodeMeta) => void }
export default function EpisodeList({ episodes, selected, busy, onPick }: Props) {
  const group = (kind: "attack" | "benign", title: string) => (
    <div className="mb-6">
      <h4 className="mb-1 text-sm font-semibold text-mute">{title}</h4>
      {episodes.filter((e) => e.kind === kind).map((e) => (
        <button key={e.id} disabled={busy} aria-pressed={selected === e.id} onClick={() => onPick(e)}
          className={`flex w-full items-baseline gap-2.5 border-t border-rule px-2.5 py-2 text-left disabled:opacity-60 ${selected === e.id ? "rounded-xl bg-ink text-paper" : "hover:bg-paper"}`}>
          <i className={`h-[9px] w-[9px] flex-none rounded-full ${kind === "attack" ? "bg-bad" : "bg-ok"}`} />
          <span><b className="block font-semibold leading-tight">{e.title}{e.limit && <span className="ml-1.5 rounded-full border border-current px-1.5 text-[11px] font-medium">known limit</span>}</b>
            <small className={`block text-[13px] leading-snug ${selected === e.id ? "text-[#b9c8cc]" : "text-mute"}`}>{e.trick}</small></span>
        </button>))}
    </div>);
  return <aside aria-label="Episodes" className="thin mb-6 max-h-60 overflow-auto md:mb-0 md:sticky md:top-3 md:max-h-[calc(100vh-24px)] md:self-start">{group("attack", "Attacks")}{group("benign", "Everyday tasks")}</aside>;
}
