export default function Legend() {
  return (
    <div className="flex items-center gap-3 text-xs text-muted">
      <span className="text-vgreen font-bold">✓ 적합</span>
      <span className="font-bold">△ 보통</span>
      <span className="text-vred font-bold">✗ 비추천</span>
    </div>
  );
}
