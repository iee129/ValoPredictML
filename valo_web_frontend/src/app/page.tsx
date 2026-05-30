"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getModel } from "@/lib/api";
import type { ModelInfo } from "@/types/api";
import MetricCard from "@/components/ui/MetricCard";

const STEPS = [
  { href: "/model", title: "1. 모델 근거", desc: "125피처 앙상블 · Test AUC · 검증 PASS 확인" },
  { href: "/replay", title: "2. 경기 다시보기", desc: "실제 경기 예측 vs 결과 (적중 확인)" },
  { href: "/predict", title: "3. 승률 예측", desc: "임의 5v5 라인업으로 라이브 예측 + 근거" },
];

export default function Home() {
  const [m, setM] = useState<ModelInfo | null>(null);
  useEffect(() => {
    getModel().then(setM).catch(() => setM(null));
  }, []);

  const auc = m?.metrics?.test_auc;
  const verdict = m?.validation?.final_verdict;

  return (
    <div className="flex flex-col gap-6">
      <section className="tactical-cut rounded-lg border border-line border-l-[5px] border-l-vred bg-panel2/60 p-6">
        <div className="text-xs font-extrabold text-vred uppercase">Match Control</div>
        <h1 className="text-3xl md:text-4xl font-extrabold mt-1">
          발로란트 5v5 승률 예측 시뮬레이터
        </h1>
        <p className="text-muted mt-2">
          맵과 양 팀 선수·요원 5명을 입력하면, advanced 앙상블 모델이 승률과 근거를 계산합니다.
        </p>
      </section>

      {m && (
        <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard label="입력 피처" value={m.n_features} />
          <MetricCard
            label="Test AUC"
            value={typeof auc === "number" ? auc.toFixed(4) : "-"}
            tone="vgreen"
          />
          <MetricCard label="알고리즘" value={<span className="text-lg">{m.contract}</span>} />
          <MetricCard
            label="검증"
            value={<span className="text-lg">{verdict ? "PASS ✅" : "-"}</span>}
            tone="vgreen"
          />
        </section>
      )}

      <section className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {STEPS.map((s) => (
          <Link
            key={s.href}
            href={s.href}
            className="rounded-lg border border-line bg-panel2/60 p-4 hover:border-vred/50 transition-colors"
          >
            <div className="font-extrabold text-lg">{s.title}</div>
            <p className="text-sm text-muted mt-1">{s.desc}</p>
          </Link>
        ))}
      </section>
    </div>
  );
}
