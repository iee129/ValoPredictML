import type { Role, BalanceWarning } from "@/types/api";

// docs/08_web/06_insights/03_balance_warning.md — 프론트 즉시 룰(백엔드 룰과 동일)
export function balanceCheck(roles: Role[]): BalanceWarning[] {
  const c: Record<Role, number> = {
    duelist: 0,
    initiator: 0,
    controller: 0,
    sentinel: 0,
  };
  roles.forEach((r) => {
    if (r in c) c[r]++;
  });

  const w: BalanceWarning[] = [];
  if (c.controller === 0)
    w.push({
      code: "no_controller",
      severity: "high",
      message: "전략가 부재 — 스모크로 시야 차단·지역 통제가 약합니다.",
    });
  if (c.sentinel >= 3)
    w.push({
      code: "too_many_sentinel",
      severity: "high",
      message: "감시자 과다 — 진입력이 부족해 공격 라운드가 어렵습니다.",
    });
  if (c.duelist === 0)
    w.push({
      code: "no_duelist",
      severity: "medium",
      message: "타격대 부재 — 진입·킬 창출 주체가 없습니다.",
    });
  if (c.initiator === 0)
    w.push({
      code: "no_initiator",
      severity: "medium",
      message: "척후대 부재 — 정보 수집·진입 보조가 약합니다.",
    });
  if (c.duelist >= 4)
    w.push({
      code: "too_many_duelist",
      severity: "low",
      message: "타격대 과다 — 유틸·지역 통제가 부족합니다.",
    });
  return w;
}
