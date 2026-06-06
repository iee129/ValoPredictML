const cls =
  "bg-bg-2 border border-line rounded-md px-3 py-2 text-ink text-sm font-semibold focus:outline-none focus:border-red";

export default function YearSelect({
  years,
  value,
  onChange,
}: {
  years: number[];
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="text-muted font-bold">기준 연도</span>
      <select
        className={cls}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      >
        {years.map((y) => (
          <option key={y} value={y}>
            {y}
          </option>
        ))}
      </select>
    </label>
  );
}
