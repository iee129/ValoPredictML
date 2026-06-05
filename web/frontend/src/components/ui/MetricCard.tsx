export default function MetricCard({
  label,
  value,
  tone = "ink",
}: {
  label: string;
  value: React.ReactNode;
  tone?: "ink" | "red" | "green" | "cyan";
}) {
  const toneClass = {
    ink: "text-ink",
    red: "text-red",
    green: "text-green",
    cyan: "text-cyan",
  }[tone];
  return (
    <div className="rounded-lg border border-line bg-panel-2/60 px-4 py-3">
      <div className="text-xs font-bold text-muted">{label}</div>
      <div className={`mt-1 text-2xl font-extrabold tabular-nums ${toneClass}`}>
        {value}
      </div>
    </div>
  );
}
