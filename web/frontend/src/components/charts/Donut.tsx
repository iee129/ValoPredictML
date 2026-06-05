interface Slice {
  label: string;
  value: number;
  color: string;
}

interface Props {
  slices: Slice[];
  size?: number;
  showLegend?: boolean;
}

function polarToXY(cx: number, cy: number, r: number, angle: number) {
  return {
    x: cx + r * Math.cos(angle - Math.PI / 2),
    y: cy + r * Math.sin(angle - Math.PI / 2),
  };
}

function arcPath(
  cx: number,
  cy: number,
  r: number,
  ro: number,
  start: number,
  end: number,
) {
  const s = polarToXY(cx, cy, ro, start);
  const e = polarToXY(cx, cy, ro, end);
  const si = polarToXY(cx, cy, r, start);
  const ei = polarToXY(cx, cy, r, end);
  const large = end - start > Math.PI ? 1 : 0;
  return [
    `M ${s.x} ${s.y}`,
    `A ${ro} ${ro} 0 ${large} 1 ${e.x} ${e.y}`,
    `L ${ei.x} ${ei.y}`,
    `A ${r} ${r} 0 ${large} 0 ${si.x} ${si.y}`,
    "Z",
  ].join(" ");
}

export default function Donut({
  slices,
  size = 140,
  showLegend = true,
}: Props) {
  const cx = size / 2;
  const cy = size / 2;
  const ro = size * 0.42;
  const ri = size * 0.26;
  const total = slices.reduce((a, s) => a + s.value, 0) || 1;

  const paths = slices.reduce<
    ((typeof slices)[0] & { path: string; startAngle: number })[]
  >((acc, s) => {
    const startAngle =
      acc.length > 0
        ? acc[acc.length - 1].startAngle +
          (acc[acc.length - 1].value / total) * 2 * Math.PI
        : 0;
    const sweep = (s.value / total) * 2 * Math.PI;
    const path = arcPath(cx, cy, ri, ro, startAngle, startAngle + sweep);
    return [...acc, { ...s, path, startAngle }];
  }, []);

  return (
    <div className="flex items-center gap-4 flex-wrap">
      <svg width={size} height={size}>
        {paths.map((p) => (
          <path
            key={p.label}
            d={p.path}
            fill={p.color}
            stroke="var(--color-bg-2)"
            strokeWidth={1.5}
          />
        ))}
        <text
          x={cx}
          y={cy + 4}
          textAnchor="middle"
          fontSize={11}
          fontWeight="bold"
          fill="var(--color-ink)"
        >
          {total.toLocaleString()}
        </text>
        <text
          x={cx}
          y={cy + 16}
          textAnchor="middle"
          fontSize={8}
          fill="var(--color-muted)"
        >
          total
        </text>
      </svg>
      {showLegend && (
        <ul className="flex flex-col gap-1">
          {slices.map((s) => (
            <li key={s.label} className="flex items-center gap-2 text-xs">
              <span
                className="inline-block w-2.5 h-2.5 rounded-sm shrink-0"
                style={{ background: s.color }}
              />
              <span className="text-muted">{s.label}</span>
              <span className="tabular-nums font-bold text-ink">
                {s.value.toLocaleString()}
              </span>
              <span className="text-muted">
                ({((s.value / total) * 100).toFixed(1)}%)
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
