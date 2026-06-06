"use client";

// 페이지 전체에 깔리는 맵 사진 배경 — 시안의 BG_IMG(맵 사진) + BG_OVL(단색 딤).
// 맵 사진을 또렷하게 깔되, 어두운 딤으로 콘텐츠 가독성을 지킨다.
import { mapSplash } from "@/lib/valorantImages";

// 맵 컨텍스트가 없는 페이지(모델 등)의 기본 배경
const DEFAULT_MAP = "Ascent";

export default function PageBackdrop({
  map,
  dim = 0.6,
}: {
  map?: string | null;
  // 0(맵 그대로) ~ 1(완전히 검정). 데이터가 빽빽한 페이지는 높게.
  dim?: number;
}) {
  const url = mapSplash(map) ?? mapSplash(DEFAULT_MAP);
  if (!url) return null;
  const a = Math.max(0, Math.min(1, dim));
  return (
    <div aria-hidden className="fixed inset-0 -z-10 pointer-events-none">
      {/* BG_IMG — 맵 사진 */}
      <div
        className="absolute inset-0 bg-cover bg-center"
        style={{ backgroundImage: `url(${url})` }}
      />
      {/* BG_OVL — 단색 딤 + 상하 비네팅 */}
      <div
        className="absolute inset-0"
        style={{
          background: `linear-gradient(180deg, rgba(7,8,12,${(a + 0.06).toFixed(
            2,
          )}) 0%, rgba(7,8,12,${a.toFixed(2)}) 42%, rgba(5,6,9,${Math.min(
            a + 0.22,
            0.96,
          ).toFixed(2)}) 100%)`,
        }}
      />
    </div>
  );
}
