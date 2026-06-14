# Dashboard Design Spec

Reference: https://www.quantus.kr/

---

## Design Concept

**"데이터 중심, 군더더기 없음"**

수치와 차트가 중심이 되도록 UI는 최대한 빠져있어야 한다.
Quantus처럼 흰 배경 + 짙은 텍스트 + 절제된 색상으로 신뢰감을 준다.

---

## Color

| 용도 | 값 |
|------|----|
| Background | `#FFFFFF` |
| Surface (카드/패널) | `#F8F9FA` |
| Border | `#E5E7EB` |
| Text primary | `#111827` |
| Text secondary | `#6B7280` |
| Accent (버튼, 하이라이트) | `#1B5E8B` |
| Positive (수익/BUY) | `#16A34A` |
| Negative (손실/SELL) | `#DC2626` |
| Neutral | `#9CA3AF` |

---

## Typography

- Font: 시스템 sans-serif (별도 로딩 없음)
- 제목: `font-weight: 700`, `font-size: 1.25rem`
- 부제목: `font-weight: 600`, `font-size: 1rem`
- 본문: `font-weight: 400`, `font-size: 0.875rem`
- Caption: `font-size: 0.75rem`, color `#6B7280`

---

## Layout

### 전체 구조

```
┌─────────────────────────────────────────────────────────┐
│  📈 Quant Trading Dashboard              [종목▼] [기간▼] │  ← header row
├─────────────────────────────────────────────────────────┤
│  [Signals & Portfolio] [Regime Backtest] [Walk-Forward] [Data]  │  ← tabs
├─────────────────────────────────────────────────────────┤
│  (탭 설명 한 줄, ~100자)                                │
│  ─────────────────────────────────────────────────────  │
│  [파라미터 패널 1/4]  │  [결과 영역 3/4]               │
└─────────────────────────────────────────────────────────┘
```

### Header

- 타이틀: 왼쪽 정렬, 크게
- 종목/기간 컨트롤: 오른쪽 정렬, 같은 행 또는 타이틀 바로 아래 행
- `st.columns([3, 1, 1])` 비율 사용

### 컨트롤 (종목 / 기간)

- 둘 다 `st.selectbox` — 동일한 컴포넌트, 동일한 너비
- 레이블: "종목 (Stock)", "기간 (Period)"
- 기간 옵션:
  ```
  Past 1 Month
  Past 3 Months
  Past 6 Months
  Past 1 Year      ← default
  Past 2 Years
  Past 3 Years
  Custom range
  ```
- `Custom range` 선택 시: `st.date_input(value=(start, end))` 달력 출력
  - 첫 번째 클릭 = 시작일, 두 번째 클릭 = 종료일

### Tab

- 이모지 없음
- 탭 이름: `Signals & Portfolio`, `Regime Backtest`, `Walk-Forward`, `Data`
- 탭 선택 시 최상단에 해당 탭 역할 설명 (~100자) — `st.caption` 사용

### 파라미터 패널

- 위치: 왼쪽 (`col[0]`, 비율 1)
- 스타일: `st.container(border=True)` — 단순 경계선
- 내부: 슬라이더/셀렉트 등 입력값만
- 불필요한 spacing 없음 — Streamlit 기본 gap 사용

### 결과 영역

- 위치: 오른쪽 (`col[1]`, 비율 3)
- 상단: `st.metric` 4개 가로 배열
- 중단: `st.line_chart`
- 하단: `st.dataframe`

---

## Components

### Metric card

```
CAGR          MDD          Sharpe       Total Return
12.04%        -8.35%       0.875        18.2%
+19.38% vs B&H  +23.80% vs B&H  +0.852 vs B&H
```

- `st.metric(label, value, delta)`
- delta: B&H 대비 차이, 양수=green, 음수=red

### Chart

- `st.line_chart` 사용 (Streamlit 기본)
- 범례: Strategy / Buy & Hold
- x축: 날짜, y축: Growth of $1

### Table

- `st.dataframe(hide_index=True, use_container_width=True)`
- 숫자 컬럼 우측 정렬 (Streamlit 기본 동작)

### Button

- Primary: `st.button(type="primary")` — 실행 버튼 하나만
- 라벨: `Run Backtest`, `Run WFA`, `Refresh Data`

---

## Tabs Detail

### Signals & Portfolio
> 현재 시장 신호(SMA 기반 매수/매도)와 페이퍼 포트폴리오 잔고를 확인합니다.

### Regime Backtest
> 시장 레짐(BULL/SIDEWAYS/BEAR)을 자동 감지하고, 레짐별 전략을 적용한 백테스트 결과를 보여줍니다.

### Walk-Forward
> 과거 데이터를 Train/Test로 나누어 파라미터를 최적화하고, 미래 데이터에서 실제 성과를 검증합니다.

### Data
> 종목별 가격 데이터 현황을 확인하고 최신 데이터로 갱신합니다.

---

## Rules

1. 이모지는 사용하지 않는다 (탭, 버튼, 제목 모두)
2. 컨테이너/컬럼에 불필요한 margin/padding을 넣지 않는다
3. 레이아웃 비율은 `[1, 3]` (파라미터:결과) 고정
4. 색상은 Streamlit 기본 테마 + 위 Color 표 준수
5. 설명 텍스트는 `st.caption` 사용, 100자 이내
6. 에러/경고는 `st.error` / `st.warning` 사용
7. 로딩은 `st.spinner` 사용
