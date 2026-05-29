> ⚠️ **범위 외**: Next.js 미사용. UI는 Streamlit 로컬 도구로 대체. 본문은 참고용으로 보존된다.

# 05. 비주얼 무드보드

발로란트 블랙&레드 컨셉의 분위기·레퍼런스·색 계획을 정리한다.  
실제 구현은 `02_valo_theme.md` 토큰 + `00_design_principles.md` 패턴을 따른다.

---

## 핵심 키워드

```
TACTICAL  ·  HIGH-CONTRAST  ·  ANGULAR  ·  CINEMATIC  ·  PRECISE
```

발로란트 공식 UI가 주는 느낌: 전술 지도를 보는 것 같은 **냉정한 정보 밀도**, 레드 포인트가 주는 **긴장감**, 각진 형태가 주는 **기계적 정밀함**.

---

## 레퍼런스

| 출처 | 특징 | URL |
|---|---|---|
| 발로란트 공식 사이트 | 극단적 어둠 배경, 레드 포인트, clip-path UI | https://playvalorant.com |
| 발로란트 에이전트 선택 화면 | 각진 카드, 선택 시 레드 테두리+광원 | — (인게임) |
| 발로란트 클라이언트 HUD | 레드/화이트 타이포, 정보 밀도 높은 패널 | — (인게임) |
| 텍스트 엠블럼 스타일 — Bebas Neue | 콘덴스드 대문자, 게임 UI 광범위 사용 | https://fonts.google.com/specimen/Bebas+Neue |
| Pretendard 폰트 | 한글 UI 표준, SIL OFL 무료 라이선스 | https://github.com/orioncactus/pretendard |

---

## 분위기 — 택티컬 하이콘트라스트

이 UI가 지향하는 두 가지 극단:

**어둠 극단 (배경)**: 색이 없다. 화면 대부분은 거의 순수 블랙에 가깝다. 정보가 어둠 속에서 스스로 빛난다.

**레드 극단 (포인트)**: 레드는 한 번에 한 곳에만 나타난다. 그래서 보는 즉시 시선이 거기 간다. 절제가 강조를 만든다.

---

## 블랙 단계 램프

배경에서 패널, 테두리까지 6단계 밝기 계층. 각 단계는 고유한 역할이 있고 임의 조합하지 않는다.

| 단계 | 토큰 | Hex | 역할 | 색 칩 |
|---|---|---|---|---|
| 0 — 최심부 | `--color-valo-bg` | `#07080c` | 페이지 최상위 배경 | <span style="display:inline-block;width:56px;height:20px;background:#07080c;border:1px solid #444;border-radius:3px;vertical-align:middle;"></span> |
| 1 — 카드 배경 | `--color-valo-panel` | `#11151f` | 카드·사이드바 패널 | <span style="display:inline-block;width:56px;height:20px;background:#11151f;border:1px solid #444;border-radius:3px;vertical-align:middle;"></span> |
| 2 — 중첩 패널 | `--color-valo-panel-alt` | `#171c27` | 패널 안의 패널, 입력 배경 | <span style="display:inline-block;width:56px;height:20px;background:#171c27;border:1px solid #444;border-radius:3px;vertical-align:middle;"></span> |
| 3 — 테두리선 | `--color-valo-border` | `#1f2633` | 구분선·외곽선 | <span style="display:inline-block;width:56px;height:20px;background:#1f2633;border:1px solid #555;border-radius:3px;vertical-align:middle;"></span> |
| 4 — 보조 텍스트 | `--color-valo-muted` | `#9ba3b3` | 레이블·설명 | <span style="display:inline-block;width:56px;height:20px;background:#9ba3b3;border-radius:3px;vertical-align:middle;"></span> |
| 5 — 주 텍스트 | `--color-valo-text` | `#f5f7fb` | 제목·핵심 수치 | <span style="display:inline-block;width:56px;height:20px;background:#f5f7fb;border-radius:3px;vertical-align:middle;"></span> |

> 단계 0-3은 배경 계열. 단계 4-5는 텍스트 계열. 두 계열을 서로의 역할에 쓰지 않는다.

---

## 레드 포인트 & 보조 컬러

| 역할 | 토큰 | Hex | 색 칩 |
|---|---|---|---|
| 브랜드 레드 (기본) | `--color-valo-red` | `#ff4655` | <span style="display:inline-block;width:56px;height:20px;background:#ff4655;border-radius:3px;vertical-align:middle;"></span> |
| 레드 호버 | `--color-valo-red-hover` | `#ff6675` | <span style="display:inline-block;width:56px;height:20px;background:#ff6675;border-radius:3px;vertical-align:middle;"></span> |
| 레드 그라디언트 끝 | `--color-valo-red-end` | `#ff8c9a` | <span style="display:inline-block;width:56px;height:20px;background:#ff8c9a;border-radius:3px;vertical-align:middle;"></span> |
| 골드 포인트 | `--color-valo-gold` | `#ffd166` | <span style="display:inline-block;width:56px;height:20px;background:#ffd166;border-radius:3px;vertical-align:middle;"></span> |
| 팀 B / 척후대 | `--color-valo-cyan` | `#29c5e0` | <span style="display:inline-block;width:56px;height:20px;background:#29c5e0;border-radius:3px;vertical-align:middle;"></span> |

---

## 역할군 & 신뢰도 기능색

정보 구분용. 브랜드 레드와 혼용하지 않는다.

| 의미 | 토큰 | Hex | 색 칩 |
|---|---|---|---|
| 타격대 (Duelist) | `--color-role-duelist` | `#ff4655` | <span style="display:inline-block;width:56px;height:20px;background:#ff4655;border-radius:3px;vertical-align:middle;"></span> |
| 척후대 (Initiator) | `--color-role-initiator` | `#29c5e0` | <span style="display:inline-block;width:56px;height:20px;background:#29c5e0;border-radius:3px;vertical-align:middle;"></span> |
| 전략가 (Controller) | `--color-role-controller` | `#5ccf6f` | <span style="display:inline-block;width:56px;height:20px;background:#5ccf6f;border-radius:3px;vertical-align:middle;"></span> |
| 감시자 (Sentinel) | `--color-role-sentinel` | `#ffb02e` | <span style="display:inline-block;width:56px;height:20px;background:#ffb02e;border-radius:3px;vertical-align:middle;"></span> |
| 신뢰도 HIGH | `--color-confidence-high` | `#5ccf6f` | <span style="display:inline-block;width:56px;height:20px;background:#5ccf6f;border-radius:3px;vertical-align:middle;"></span> |
| 신뢰도 MEDIUM | `--color-confidence-medium` | `#ffb02e` | <span style="display:inline-block;width:56px;height:20px;background:#ffb02e;border-radius:3px;vertical-align:middle;"></span> |
| 신뢰도 LOW | `--color-confidence-low` | `#9aa3b2` | <span style="display:inline-block;width:56px;height:20px;background:#9aa3b2;border-radius:3px;vertical-align:middle;"></span> |

---

## 타이포 무드

| 용도 | 폰트 | 특성 |
|---|---|---|
| 영문 헤드라인, 수치 레이블 | Bebas Neue | 콘덴스드, 대문자, 단일 웨이트, 발로란트 무드 |
| 한글·영문 본문, UI 레이블 | Pretendard Variable | 가변 웨이트(100–900), 한글 최적화, SIL OFL |
| 숫자 테이블, 통계 | Pretendard + `font-variant-numeric: tabular-nums` | 열 정렬용 고정폭 숫자 |

폰트 로딩 순서: Pretendard Variable → Pretendard → system fallback.  
Bebas Neue는 헤드라인 전용 → 본문 폴백은 Pretendard Variable.  
발로란트 공식 폰트(Tungsten, DIN)는 유료 라이선스 — **이 프로젝트에서 사용하지 않는다.**

---

## 레드 사용 규칙 요약

1. 한 화면에서 레드가 적용된 **최강조 포인트는 1개** (CTA 버튼 또는 활성 탭 또는 선택 카드).
2. **좌측 강조 바(3px)**는 섹션 구분용으로만 — 배경 면적이 아님.
3. 레드 틴트(`--color-valo-red-dim`)는 내부 배경 필 용도 OK. 넓은 패널 배경 전체에는 사용하지 않음.
4. 레드 그라디언트(`red → red-end`)는 **데이터 바, 프로그레스** 전용. 버튼 배경 전체에는 단색 레드.
5. 에러·경고 아닌 상태에서 레드를 "위험" 연상으로 사용하지 않음 — 여기서 레드는 브랜드 색.
