"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "홈" },
  { href: "/predict", label: "승률 예측" },
  { href: "/replay", label: "경기 다시보기" },
  { href: "/model", label: "모델 근거" },
];

export default function Navbar() {
  const path = usePathname();
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-base/80 backdrop-blur">
      <div className="max-w-[2200px] mx-auto px-4 sm:px-6 lg:px-8 2xl:px-12 h-14 flex items-center gap-3 sm:gap-6 overflow-x-auto">
        <Link href="/" className="flex items-center gap-2 shrink-0">
          <span className="inline-block w-1.5 h-5 bg-vred" />
          <span className="font-extrabold tracking-wide text-ink whitespace-nowrap">
            VALO<span className="text-vred">PREDICT</span>ML
          </span>
        </Link>
        <nav className="flex items-center gap-1 text-sm shrink-0">
          {LINKS.map((l) => {
            const active = l.href === "/" ? path === "/" : path.startsWith(l.href);
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`px-3 py-1.5 rounded-md font-bold whitespace-nowrap transition-colors ${
                  active ? "bg-vred text-white" : "text-muted hover:text-ink"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
