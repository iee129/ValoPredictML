interface Series {
  key: string;
  color: string;
  label: string;
}
interface Row {
  name: string;
  values: Record<string, number>;
}

interface Props {
  rows: Row[];
  series: Series[];
  width?: number;
  height?: number;
  yLabel?: string;
}

export default function GroupedColumns({
  rows,
  series,
  width = 340,
  height = 200,
  yLabel,
}: Props) {
  const pad = { t: 20, r: 12, b: 40, l: 42 };
  const W = width - pad.l - pad.r;
  const H = height - pad.t - pad.b;

  const allVals = rows.flatMap((r) => series.map((s) => r.values[s.key] ?? 0));
  const maxVal = Math.max(...allVals, 0.01);

  const groupW = W / rows.length;
  const barW = Math.min((groupW / series.length) * 0.78, 28);
  const gap = (groupW - barW * series.length) / 2;

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((t) => t * maxVal);

  return (
    <svg width={width} height={height} className="overflow-visible">
      {/* Y 격자 + 레이블 */}
      {yTicks.map((v) => {
        const y = pad.t + H - (v / maxVal) * H;
        return (
          <g key={v}>
            <line
              x1={pad.l}
              y1={y}
              x2={pad.l + W}
              y2={y}
              stroke="rgba(255,255,255,0.06)"
              strokeWidth={1}
            />
            <text
              x={pad.l - 5}
              y={y + 3}
              textAnchor="end"
              fontSize={9}
              fill="var(--color-muted)"
            >
              {v >= 1 ? v.toFixed(0) : v.toFixed(2)}
            </text>
          </g>
        );
      })}
      {/* Y축 레이블 */}
      {yLabel && (
        <text
          x={10}
          y={pad.t + H / 2}
          textAnchor="middle"
          fontSize={9}
          fill="var(--color-muted)"
          transform={`rotate(-90,10,${pad.t + H / 2})`}
        >
          {yLabel}
        </text>
      )}
      {/* 막대 */}
      {rows.map((row, ri) => {
        const gx = pad.l + ri * groupW + gap;
        return (
          <g key={row.name}>
            {series.map((s, si) => {
              const v = row.values[s.key] ?? 0;
              const bh = (v / maxVal) * H;
              const bx = gx + si * barW;
              const by = pad.t + H - bh;
              return (
                <g key={s.key}>
                  <rect
                    x={bx}
                    y={by}
                    width={barW - 1}
                    height={bh}
                    fill={s.color}
                    rx={2}
                  />
                  {bh > 16 && (
                    <text
                      x={bx + barW / 2 - 0.5}
                      y={by + 10}
                      textAnchor="middle"
                      fontSize={8}
                      fill="var(--color-ink)"
                    >
                      {v.toFixed(3)}
                    </text>
                  )}
                </g>
              );
            })}
            <text
              x={gx + (groupW - gap * 2) / 2}
              y={pad.t + H + 14}
              textAnchor="middle"
              fontSize={9}
              fill="var(--color-muted)"
            >
              {row.name}
            </text>
          </g>
        );
      })}
      {/* 범례 */}
      <g transform={`translate(${pad.l},${height - 10})`}>
        {series.map((s, i) => (
          <g key={s.key} transform={`translate(${i * 90},0)`}>
            <rect x={0} y={-6} width={8} height={8} fill={s.color} rx={1} />
            <text x={11} y={2} fontSize={9} fill="var(--color-muted)">
              {s.label}
            </text>
          </g>
        ))}
      </g>
    </svg>
  );
}
