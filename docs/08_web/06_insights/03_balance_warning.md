# 03. 구성 결함 알림 — 차별점 G

전략가가 없거나 감시자가 너무 많은 등 한쪽으로 치우친 팀을 자동 감지해 경고한다. **순수 룰**이며 데이터·모델 불필요 → 입력 즉시(프론트) 표시 가능.

---

## 1. 입력

요원 5개의 역할 카운트만 있으면 된다. 역할은 `src/domain/agent_roles.py`의 `AGENT_ROLE_MAP`(`/agents` 응답의 `role`) 사용. `(duelist, initiator, controller, sentinel)`, 합 5.

---

## 2. 룰 (5종, 튜닝 가능)

| code | 조건 | severity | 메시지 |
|------|------|:---:|--------|
| `no_controller` | controller == 0 | high | "전략가 부재 — 스모크로 시야 차단·지역 통제가 약합니다." |
| `too_many_sentinel` | sentinel >= 3 | high | "감시자 과다 — 진입력이 부족해 공격 라운드가 어렵습니다." |
| `no_duelist` | duelist == 0 | medium | "타격대 부재 — 진입·킬 창출 주체가 없습니다." |
| `no_initiator` | initiator == 0 | medium | "척후대 부재 — 정보 수집·진입 보조가 약합니다." |
| `too_many_duelist` | duelist >= 4 | low | "타격대 과다 — 유틸·지역 통제가 부족합니다." |

> 임계값은 도메인 통념 기준. 데이터로 보정하려면 `meta_comps.json`의 역할 분포에서 하위 분위 구성을 결함으로 정의할 수도 있으나, 본 기능은 **설명 가능성**을 위해 고정 룰을 유지한다(차별점 G "룰 5개 코드 내장").

---

## 3. 권장 구현 — 프론트 즉시 룰

서버 왕복 없이 슬롯이 채워질 때마다 즉시 평가:

```ts
// lib/balance.ts
import type { Role } from "@/types/api";

export interface BalanceWarning { code: string; severity: "high"|"medium"|"low"; message: string }

export function balanceCheck(roles: Role[]): BalanceWarning[] {
  const c = { duelist:0, initiator:0, controller:0, sentinel:0 } as Record<Role, number>;
  roles.forEach(r => { c[r]++; });
  const w: BalanceWarning[] = [];
  if (c.controller === 0) w.push({ code:"no_controller", severity:"high",
    message:"전략가 부재 — 스모크로 시야 차단·지역 통제가 약합니다." });
  if (c.sentinel >= 3)    w.push({ code:"too_many_sentinel", severity:"high",
    message:"감시자 과다 — 진입력이 부족해 공격 라운드가 어렵습니다." });
  if (c.duelist === 0)    w.push({ code:"no_duelist", severity:"medium",
    message:"타격대 부재 — 진입·킬 창출 주체가 없습니다." });
  if (c.initiator === 0)  w.push({ code:"no_initiator", severity:"medium",
    message:"척후대 부재 — 정보 수집·진입 보조가 약합니다." });
  if (c.duelist >= 4)     w.push({ code:"too_many_duelist", severity:"low",
    message:"타격대 과다 — 유틸·지역 통제가 부족합니다." });
  return w;
}
```

요원→역할은 `/agents` 응답(`Map<agentName, role>`)으로 변환:
```ts
const roleOf = new Map(agents.map(a => [a.name, a.role]));
const teamRoles = slots.map(s => roleOf.get(s.agent)).filter(Boolean) as Role[];
const warnings = balanceCheck(teamRoles);
```

---

## 4. (선택) 백엔드 노출

예측 결과 카드에도 함께 싣고 싶으면 `/predict` 응답에 추가한다. `PredictionResult.role_counts`가 이미 역할 카운트를 주므로 서버에서 동일 룰을 적용해 직렬화한다:

```python
# serializers.py
def balance_warnings(role_counts: dict) -> list[dict]:
    c = {k: role_counts.get(k, 0) for k in ("duelist","initiator","controller","sentinel")}
    out = []
    if c["controller"] == 0: out.append({"code":"no_controller","severity":"high","message":"전략가 부재 — ..."})
    # ... 동일 5룰
    return out
```

응답 확장(선택):
```jsonc
// PredictResponse 에 추가
"balance": { "team_a": [ {code,severity,message} ], "team_b": [ ... ] }
```

> 프론트 룰과 백엔드 룰은 **메시지·임계값을 한 곳**(예: 공유 상수 표)에서 관리해 불일치를 막는다. 권장: 프론트 즉시 표시를 기본으로, 백엔드는 결과 카드용 보조.

---

## 5. 프론트 표시

```tsx
{warnings.map(w => (
  <Alert key={w.code} tone={w.severity}>{w.message}</Alert>
))}
```
- severity별 색(high=red, medium=amber, low=gray)
- 슬롯 입력 영역 하단에 실시간 표시 → 사용자가 즉시 구성을 고칠 수 있게

---

## 6. 관련 문서

- 메타 매칭률(보완 지표) → [02_comp_match.md](02_comp_match.md)
- 자연어 근거 → [04_nl_explanation.md](04_nl_explanation.md)
