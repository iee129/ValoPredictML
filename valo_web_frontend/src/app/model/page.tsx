"use client";

import { useEffect, useState } from "react";
import { getModel } from "@/lib/api";
import type { ModelInfo } from "@/types/api";
import MetricCard from "@/components/ui/MetricCard";
import ErrorBanner from "@/components/ui/ErrorBanner";
import Spinner from "@/components/ui/Spinner";

export default function ModelPage() {
  const [m, setM] = useState<ModelInfo | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getModel().then(setM).catch((e) => setErr((e as Error).message));
  }, []);

  if (err) return <ErrorBanner message={err} />;
  if (!m) return <Spinner label="모델 정보를 불러오는 중…" />;

  const metric = (k: string) =>
    typeof m.metrics?.[k] === "number" ? m.metrics[k].toFixed(4) : "-";
  const maxImp = Math.max(...m.global_importance.map((g) => g.importance), 1e-9);

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-2xl font-extrabold border-l-[3px] border-vred pl-2">모델 근거</h1>

      <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="입력 피처" value={m.n_features} />
        <MetricCard label="Test AUC" value={metric("test_auc")} tone="vgreen" />
        <MetricCard label="Test 정확도" value={metric("test_acc")} />
        <MetricCard
          label="검증"
          value={
            <span className="text-lg">
              {m.validation?.final_verdict ? "PASS ✅" : "-"}
            </span>
          }
          tone="vgreen"
        />
      </section>

      <section className="rounded-lg border border-line bg-panel2/60 p-4">
        <div className="text-sm font-bold text-muted mb-1">알고리즘</div>
        <div className="font-extrabold">{m.algorithm}</div>
        {m.validation?.final_verdict && (
          <div className="text-xs text-muted mt-1">
            검증 결과: {String(m.validation.final_verdict)}
          </div>
        )}
      </section>

      <section className="rounded-lg border border-line bg-panel2/60 p-4">
        <div className="text-sm font-bold text-muted mb-3">전역 피처 중요도 (상위 20)</div>
        <div className="flex flex-col gap-1.5">
          {m.global_importance.map((g) => (
            <div key={g.feature} className="text-xs">
              <div className="flex justify-between gap-2">
                <span className="text-muted truncate">{g.feature}</span>
                <span className="tabular-nums text-ink shrink-0">
                  {g.importance.toFixed(4)}
                </span>
              </div>
              <div className="h-1.5 bg-white/10 rounded mt-0.5">
                <div
                  className="h-full rounded bg-vred"
                  style={{ width: `${(g.importance / maxImp) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
