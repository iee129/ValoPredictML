"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getModel } from "@/lib/api";

const LINKS = [
  { href: "/", label: "예측" },
  { href: "/replay", label: "다시보기" },
  { href: "/model", label: "모델" },
];

export default function Navbar() {
  const path = usePathname();
  const [auc, setAuc] = useState<string | null>(null);

  useEffect(() => {
    getModel()
      .then((m) => {
        const val = m.eval?.primary_auc ?? m.metrics?.test_auc;
        if (val != null) setAuc(val.toFixed(3));
      })
      .catch(() => {});
  }, []);

  return (
    <header className="sticky top-0 z-20 border-b border-line bg-bg/80 backdrop-blur">
      <div className="relative max-w-[1280px] mx-auto px-4 sm:px-6 h-[52px] flex items-center">
        {/* 좌측 로고 */}
        <Link href="/" className="flex items-center gap-2 shrink-0 mr-2 sm:mr-4">
          <span className="inline-block w-1.5 h-5 bg-red" />
          <span className="font-display text-[15px] tracking-[0.14em] text-[#ece8e1] whitespace-nowrap sm:text-lg sm:tracking-widest">
            VALOPREDICT<span className="text-red">ML</span>
          </span>
        </Link>

        {/* 가운데 정렬 네비 */}
        <nav className="ml-auto flex items-center gap-0.5 text-xs sm:absolute sm:left-1/2 sm:ml-0 sm:-translate-x-1/2 sm:gap-1 sm:text-sm">
          {LINKS.map((l) => {
            const active =
              l.href === "/" ? path === "/" : path.startsWith(l.href);
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`px-2 py-1.5 font-bold whitespace-nowrap transition-colors relative sm:px-3 ${
                  active
                    ? "text-ink after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[2px] after:bg-red"
                    : "text-muted hover:text-ink"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>

        {/* 우측 AUC 배지 */}
        <div className="ml-auto hidden shrink-0 sm:block">
          <div
            className="border rounded-[6px] px-4 py-1.5 text-[13px] font-medium text-[#f5f7fb] whitespace-nowrap"
            style={{
              background: "rgba(255,255,255,0.05)",
              borderColor: "rgba(255,255,255,0.14)",
            }}
          >
            심화 앙상블 · AUC {auc ?? "..."}
          </div>
        </div>
      </div>
    </header>
  );
}
