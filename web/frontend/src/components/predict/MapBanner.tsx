// 상단 맵 배너 — 대형 디스플레이 폰트(영문 맵명) + 기준연도 + 맵/연도 드롭다운 통합
import type { MapInfo } from "@/types/api";
import { CornerAccent, SectionKicker } from "@/components/ui/Tactical";

interface Props {
  map: string;
  ko: string;
  year: number;
  maps: MapInfo[];
  years: number[];
  onMapChange: (v: string) => void;
  onYearChange: (v: number) => void;
}

const dropdownCls =
  "bg-black/40 border border-white/[0.16] rounded-[6px] h-[30px] px-3 text-[13px] text-[#f5f7fb] focus:outline-none focus:border-red cursor-pointer";

export default function MapBanner({
  map,
  ko,
  year,
  maps,
  years,
  onMapChange,
  onYearChange,
}: Props) {
  return (
    <div className="tactical-card tactical-depth relative min-h-[84px] overflow-hidden rounded-[var(--radius)] border border-line border-l-[5px] border-l-red bg-panel-2/70 px-5 py-3 shadow-[var(--shadow-card)] sm:h-[84px]">
      <CornerAccent />
      <div className="relative h-full">
        {/* 상단 행: // MAP 레이블(좌) + 드롭다운(우) */}
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <SectionKicker>MAP</SectionKicker>
          <div className="flex items-center gap-2">
            <select
              value={map}
              onChange={(e) => onMapChange(e.target.value)}
              aria-label="맵 선택"
              className={dropdownCls}
            >
              {maps.map((m) => (
                <option key={m.name} value={m.name}>
                  {m.ko} ({m.name})
                </option>
              ))}
            </select>
            <select
              value={year}
              onChange={(e) => onYearChange(Number(e.target.value))}
              aria-label="기준 연도 선택"
              className={dropdownCls}
            >
              {years.map((y) => (
                <option key={y} value={y}>
                  기준연도 {y}
                </option>
              ))}
            </select>
          </div>
        </div>
        {/* 하단 행: 큰 맵명 + 기준연도 설명 */}
        <div className="mt-1 flex items-baseline gap-3 flex-wrap sm:absolute sm:bottom-0 sm:left-0">
          <span className="font-display text-4xl leading-none tracking-wide text-ink sm:text-[46px]">
            {map || "—"}
          </span>
          {ko && <span className="text-sm font-bold text-muted">{ko}</span>}
          <span className="text-sm text-muted ml-2">
            기준연도{" "}
            <span className="font-bold text-ink tabular-nums">
              {year || "—"}
            </span>
            <span className="ml-2 text-muted">· 픽창 단계 예측</span>
          </span>
        </div>
      </div>
    </div>
  );
}
