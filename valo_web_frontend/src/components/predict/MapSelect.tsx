import type { MapInfo } from "@/types/api";

const cls =
  "bg-base2 border border-line rounded-md px-3 py-2 text-ink text-sm font-semibold focus:outline-none focus:border-vred";

export default function MapSelect({
  maps,
  value,
  onChange,
}: {
  maps: MapInfo[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="text-muted font-bold">맵</span>
      <select className={cls} value={value} onChange={(e) => onChange(e.target.value)}>
        {maps.map((m) => (
          <option key={m.name} value={m.name}>
            {m.ko} ({m.name})
          </option>
        ))}
      </select>
    </label>
  );
}
