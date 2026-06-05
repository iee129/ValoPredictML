interface CVFold {
  name: string;
  auc: number;
}

interface Props {
  folds: CVFold[];
  mean: number;
  width?: number;
  height?: number;
}

export default function CVStrip({
  folds,
  mean,
  width = 320,
  height = 80,
}: Props) {
  const pad = { t: 10, r: 16, b: 28, l: 16 };
  const W = width - pad.l - pad.r;
  const H = height - pad.t - pad.b;

  const vals = folds.map((f) => f.auc);
  const minV = Math.min(...vals, mean) - 0.03;
  const maxV = Math.max(...vals, mean) + 0.03;
  const range = maxV - minV || 0.01;

  const xOf = (i: number) => pad.l + ((i + 0.5) / folds.length) * W;
  const yOf = (v: number) => pad.t + H - ((v - minV) / range) * H;
  const meanY = yOf(mean);

  return (
    <svg width={width} height={height} className="overflow-visible">
      {/* 평균선 */}
      <line
        x1={pad.l}
        y1={meanY}
        x2={pad.l + W}
        y2={meanY}
        stroke="var(--color-red)"
        strokeDasharray="5 3"
        strokeWidth={1.5}
      />
      <text
        x={pad.l + W + 4}
        y={meanY + 4}
        fontSize={9}
        fill="var(--color-red)"
      >
        μ={mean.toFixed(3)}
      </text>
      {/* 점 + 라벨 */}
      {folds.map((f, i) => {
        const cx = xOf(i);
        const cy = yOf(f.auc);
        return (
          <g key={f.name}>
            <circle cx={cx} cy={cy} r={5} fill="var(--color-cyan)" />
            <text
              x={cx}
              y={cy - 8}
              textAnchor="middle"
              fontSize={8}
              fill="var(--color-ink)"
            >
              {f.auc.toFixed(3)}
            </text>
            <text
              x={cx}
              y={pad.t + H + 14}
              textAnchor="middle"
              fontSize={9}
              fill="var(--color-muted)"
            >
              {f.name}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
