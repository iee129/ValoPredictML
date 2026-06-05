interface Props {
  fpr: number[];
  tpr: number[];
  auc?: number;
  width?: number;
  height?: number;
}

export default function RocCurve({
  fpr,
  tpr,
  auc,
  width = 260,
  height = 220,
}: Props) {
  const pad = { t: 34, r: 18, b: 42, l: 46 };
  const W = width - pad.l - pad.r;
  const H = height - pad.t - pad.b;

  const pts = fpr
    .map((x, i) => `${pad.l + x * W},${pad.t + (1 - tpr[i]) * H}`)
    .join(" ");
  const diagPts = `${pad.l},${pad.t + H} ${pad.l + W},${pad.t}`;

  const xTicks = [0, 0.25, 0.5, 0.75, 1];
  const yTicks = [0, 0.25, 0.5, 0.75, 1];

  return (
    <svg width={width} height={height} className="overflow-visible">
      {auc !== undefined && (
        <g>
          <rect
            x={width - pad.r - 82}
            y={4}
            width={82}
            height={22}
            rx={5}
            fill="rgba(255,70,85,0.16)"
            stroke="rgba(255,70,85,0.42)"
          />
          <text
            x={width - pad.r - 41}
            y={19}
            textAnchor="middle"
            fontSize={11}
            fontWeight="bold"
            fill="var(--color-ink)"
          >
            AUC {auc.toFixed(3)}
          </text>
        </g>
      )}
      {/* 격자 */}
      {xTicks.map((v) => (
        <line
          key={`xg${v}`}
          x1={pad.l + v * W}
          y1={pad.t}
          x2={pad.l + v * W}
          y2={pad.t + H}
          stroke="rgba(255,255,255,0.07)"
          strokeWidth={1}
        />
      ))}
      {yTicks.map((v) => (
        <line
          key={`yg${v}`}
          x1={pad.l}
          y1={pad.t + v * H}
          x2={pad.l + W}
          y2={pad.t + v * H}
          stroke="rgba(255,255,255,0.07)"
          strokeWidth={1}
        />
      ))}
      {/* 대각선(랜덤) */}
      <polyline
        points={diagPts}
        fill="none"
        stroke="rgba(255,255,255,0.2)"
        strokeDasharray="4 4"
        strokeWidth={1}
      />
      {/* ROC 곡선 */}
      <polyline
        points={pts}
        fill="none"
        stroke="var(--color-red)"
        strokeWidth={2}
        strokeLinejoin="round"
      />
      {/* 채우기 */}
      <polygon
        points={`${pad.l},${pad.t + H} ${pts} ${pad.l + W},${pad.t + H}`}
        fill="rgba(255,70,85,0.12)"
      />
      {/* X 축 레이블 */}
      {xTicks.map((v) => (
        <text
          key={`xl${v}`}
          x={pad.l + v * W}
          y={height - 4}
          textAnchor="middle"
          fontSize={9}
          fill="var(--color-muted)"
        >
          {v}
        </text>
      ))}
      {/* Y 축 레이블 */}
      {yTicks.map((v) => (
        <text
          key={`yl${v}`}
          x={pad.l - 6}
          y={pad.t + (1 - v) * H + 3}
          textAnchor="end"
          fontSize={9}
          fill="var(--color-muted)"
        >
          {v}
        </text>
      ))}
    </svg>
  );
}
