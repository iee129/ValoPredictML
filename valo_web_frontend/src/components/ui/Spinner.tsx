export default function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-muted py-4">
      <span className="inline-block w-5 h-5 border-2 border-line border-t-vred rounded-full animate-spin" />
      {label && <span className="text-sm">{label}</span>}
    </div>
  );
}
