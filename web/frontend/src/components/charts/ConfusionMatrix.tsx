interface Props {
  matrix: [[number, number], [number, number]];
  labels?: [string, string];
}

export default function ConfusionMatrix({
  matrix,
  labels = ["패배", "승리"],
}: Props) {
  const total = matrix.flat().reduce((a, b) => a + b, 0) || 1;
  const cells = [
    { r: 0, c: 0, v: matrix[0][0], label: "TN", color: "var(--color-panel-2)" },
    { r: 0, c: 1, v: matrix[0][1], label: "FP", color: "rgba(255,70,85,0.18)" },
    { r: 1, c: 0, v: matrix[1][0], label: "FN", color: "rgba(255,70,85,0.18)" },
    {
      r: 1,
      c: 1,
      v: matrix[1][1],
      label: "TP",
      color: "rgba(48,208,140,0.22)",
    },
  ];
  const cellW = 80;
  const cellH = 64;
  const off = 32;

  return (
    <svg
      width={cellW * 2 + off + 8}
      height={cellH * 2 + off + 8}
      className="overflow-visible"
    >
      {/* 축 레이블 */}
      <text
        x={off + cellW}
        y={14}
        textAnchor="middle"
        fontSize={10}
        fill="var(--color-muted)"
      >
        예측 →
      </text>
      <text
        x={14}
        y={off + cellH}
        textAnchor="middle"
        fontSize={10}
        fill="var(--color-muted)"
        transform={`rotate(-90,14,${off + cellH})`}
      >
        실제 →
      </text>
      {labels.map((l, i) => (
        <text
          key={`col${i}`}
          x={off + cellW * i + cellW / 2}
          y={off - 6}
          textAnchor="middle"
          fontSize={9}
          fill="var(--color-muted)"
        >
          {l}
        </text>
      ))}
      {labels.map((l, i) => (
        <text
          key={`row${i}`}
          x={off - 6}
          y={off + cellH * i + cellH / 2 + 4}
          textAnchor="end"
          fontSize={9}
          fill="var(--color-muted)"
        >
          {l}
        </text>
      ))}
      {cells.map(({ r, c, v, label, color }) => {
        const x = off + c * cellW;
        const y = off + r * cellH;
        return (
          <g key={label}>
            <rect
              x={x}
              y={y}
              width={cellW}
              height={cellH}
              fill={color}
              stroke="rgba(255,255,255,0.08)"
              strokeWidth={1}
            />
            <text
              x={x + cellW / 2}
              y={y + cellH / 2 - 6}
              textAnchor="middle"
              fontSize={18}
              fontWeight="bold"
              fill="var(--color-ink)"
            >
              {v.toLocaleString()}
            </text>
            <text
              x={x + cellW / 2}
              y={y + cellH / 2 + 10}
              textAnchor="middle"
              fontSize={9}
              fill="var(--color-muted)"
            >
              {label} · {((v / total) * 100).toFixed(1)}%
            </text>
          </g>
        );
      })}
    </svg>
  );
}
