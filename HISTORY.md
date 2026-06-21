# History — 완료된 단계

quant-trading 프로젝트에서 완료된 작업을 **단계(Step)** 기준으로 정리한 기록.
모든 문서는 단위를 "단계" 하나로 통일한다. 남은 작업은 [TODO.md](TODO.md)(단계 12~)를 참고.

---

## 2026-06-14 — 기반 구축 (단계 1~4, 일부 5~10)

### 단계 1. 개발환경 구축
- Python 3.14 + uv + pyenv 환경 구성
- Git / GitHub 연결
- 라이브러리: pandas, numpy, matplotlib, yfinance, vectorbt, jupyter
- 디렉터리 구조: `data/`, `data/raw/`, `strategy/`, `backtest/`, `report/`, `notebook/`

### 단계 2. 데이터 수집
- Universe 구성: QQQ, SOXL, SOXS, BTC-USD (`data/universe.py`)
- yfinance 멀티 티커 collector (`data/collector.py`), 2005년 이후 일봉 → `data/raw/*.csv`
- 데이터 검증: 결측치 / 거래일 / 종가 정제

### 단계 3. 이동평균선
- SMA20 / 50 / 100 / 200 계산 (`strategy/ma.py`)
- 가격 + SMA 시각화 차트 저장

### 단계 4. 백테스트 엔진
- 매수: 종가 > SMA200 / 매도: 종가 < SMA200 (`backtest/engine.py`)
- 성과지표: 누적수익률·CAGR·MDD·Sharpe (`backtest/metrics.py`)
- Buy & Hold 대비 비교 리포트

**백테스트 결과 (SMA200 전략):**

| Ticker | Strategy CAGR | B&H CAGR | Strategy MDD | B&H MDD |
|--------|:---:|:---:|:---:|:---:|
| QQQ | 12.1% | 15.4% | **-26.5%** | -53.4% |
| SOXL | 31.3% | 44.4% | **-69.6%** | -90.5% |
| SOXS | -25.2% | -71.3% | -99.4% | -100% |
| BTC-USD | 58.2% | 59.2% | **-69.9%** | -83.4% |

> SMA200 전략은 수익률을 일부 희생하는 대신 MDD를 절반 수준으로 낮춤.

### 단계 5~10. 전략 개선 ~ 대시보드 (1차 일괄 구현)
- **단계 5 크로스오버 전략** (`strategy/crossover.py`): SMA50/200, SMA20/100, SMA100/200 골든크로스
- **단계 9 모멘텀 전략** (`strategy/momentum.py`): NASDAQ100 상대모멘텀 3·6·12개월, 상위 종목 선정
- **단계 6 브로커 클라이언트** (`broker/kis.py`): 계좌·잔고 조회, 해외주식 주문
- **단계 7 가상매매** (`backtest/paper_trade.py`): 일별 신호 → 가상 포트폴리오/매매 로그 (`paper_portfolio.json`, `paper_trades.csv`)
- **단계 8 스케줄러** (`scheduler/runner.py`): APScheduler 일 1회(21:30 KST) → 데이터 수집 → 신호 → 가상매매 → 알림
- **단계 8 알림** (`scheduler/notify.py`): Discord / Telegram
- **단계 10 API** (`api/main.py`): FastAPI REST
- **단계 10 대시보드** (`dashboard/app.py`): Streamlit — 수익률/MDD/현재 신호 시각화

---

## 2026-06-15 — 설정 정리 · KIS 전환 · Upbit · 레짐 전략 · WFA · 대시보드 개편

### 설정 / 브로커
- `.env` + `config.py`로 환경설정 중앙화 (KIS / Upbit / Discord / Telegram)
- 증권사를 미래에셋 → **한국투자증권(KIS)** 으로 전환
- **Upbit API 클라이언트** (`broker/upbit.py`): 잔고·현재가·OHLCV 조회, 시장가 매수/매도 (BTC 거래용)

### 단계 11. 시장 레짐 적응 전략 + Walk-Forward 검증 ⭐
- **레짐 탐지** (`strategy/regime.py`): ADX(14, Wilder smoothing 수동 구현) + SMA200 기준으로 BULL / SIDEWAYS_UP / BEAR / SIDEWAYS_DOWN 4종 분류, `confirm_days=3` whipsaw 방지
- **레짐별 전략**:
  - Volatility Breakout (Larry Williams, k=0.5) — BULL (`strategy/volatility_breakout.py`)
  - Grid / Mean-Reversion (Bollinger Band) — SIDEWAYS_UP (`strategy/grid.py`)
  - CASH — BEAR / SIDEWAYS_DOWN
- **자동 전략 스위처** (`strategy/switcher.py`): 레짐별 전략 자동 전환 백테스트
  - 결과: **CAGR 93%, MDD -32%, Sharpe 2.04** (vs B&H Sharpe 0.86)
- **Walk-Forward Analysis** (`backtest/wfa.py`):
  - 단순 분할(2015–2021 학습 / 2022–2026 테스트): 테스트 CAGR 32.1% (B&H 6.9%)
  - 롤링 WFA(3년 학습 / 1년 테스트, 9 folds): OOS 스티치 CAGR 18.3%, MDD -15.2%, Sharpe 1.18
  - 차트 저장 (`report/btc_usd_wfa.png`)
- **대시보드 개편**: 레짐 백테스트 / WFA 탭, Datadog 스타일 시간범위 피커, 프리셋 버튼, % 분할 슬라이더 (`docs/dashboard-design.md`)

---

## 2026-06-22 — Telegram 자동화

- **`scheduler/daily_review.py`**: Claude Code를 headless로 호출해 저장소를 점검하고, 한국어 요약(≤300자)을 Telegram으로 발송 (09:00 launchd 트리거 의도)
- **`scheduler/telegram_agent.py`**: Telegram 메시지를 long-poll 해서 각 메시지를 Claude Code 작업으로 실행(코드 수정·테스트·커밋)하고 결과를 회신하는 브리지

---

## 진행 현황

- ✅ **단계 1~11 완료** — 데이터/백테스트/레짐 전략/WFA/대시보드/Telegram 자동화
- ⏳ **단계 12~ 진행 예정** — BTC 실시간 레짐 자동매매 (paper 먼저) → 실거래 → 확장. [TODO.md](TODO.md) 참고.
