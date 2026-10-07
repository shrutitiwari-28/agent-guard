export default function JsonView({ value }: { value: unknown }) {
  const text = JSON.stringify(value, null, 2);
  const parts = text.split(/("(?:\\.|[^"\\])*"\s*:?|\b(?:true|false|null)\b|-?\d+(?:\.\d+)?)/g);
  return (
    <pre className="thin max-h-72 overflow-auto rounded-xl bg-white/70 p-3 font-mono text-[11.5px] leading-relaxed">
      {parts.map((p, i) => {
        if (!p) return null;
        let c = "text-ink";
        if (p.startsWith('"')) c = /:\s*$/.test(p) ? "text-stain" : "text-ok";
        else if (/^(true|false|null)$/.test(p)) c = "text-hold";
        else if (/^-?\d/.test(p)) c = "text-bad";
        return <span key={i} className={c}>{p}</span>;
      })}
    </pre>
  );
}
