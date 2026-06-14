# Quant Trading Project

## 목표

- 시장: NASDAQ
- 증권사: 한국투자증권 (KIS)
- 언어: Python
- 1차 전략: 이동평균선(Moving Average)
- 최종 목표: 모멘텀 기반 자동매매
- 투자 대상: QQQ, SOXL, SOXS, Bitcoin (BTC-USD)
- 성공 기준
  - Buy & Hold 대비 낮은 MDD
  - 유사하거나 더 높은 CAGR
  - 자동매매 가능한 구조 확보

---

# Phase 1. 개발환경 구축

## Python 환경 구성

- [x] Python 3.14 설치
- [x] uv 설치
- [x] Git Repository 생성
- [x] GitHub 연결

## 필수 라이브러리

- [x] pandas
- [x] numpy
- [x] matplotlib
- [x] yfinance
- [x] vectorbt
- [x] jupyter

## 프로젝트 구조

- [x] data/
- [x] data/raw/
- [x] strategy/
- [x] backtest/
- [x] report/
- [x] notebook/

---

# Phase 2. 데이터 수집

## Universe 구성

- [x] QQQ (NASDAQ 100 ETF)
- [x] SOXL (Semiconductor 3x Bull ETF)
- [x] SOXS (Semiconductor 3x Bear ETF)
- [x] BTC-USD (Bitcoin)
- [x] universe.py 티커 등록 및 관리

## 데이터 확보

- [x] yfinance 연동
- [x] 멀티 티커 지원 collector
- [x] 2005년 이후 데이터 수집
- [x] data/raw/ 에 티커별 CSV 저장

## 데이터 검증

- [x] 결측치 확인
- [x] 거래일 확인
- [x] 종가 데이터 정제

---

# Phase 3. 이동평균선 구현

## SMA 계산

- [x] SMA20
- [x] SMA50
- [x] SMA100
- [x] SMA200

## 시각화

- [x] 가격 + SMA20
- [x] 가격 + SMA50
- [x] 가격 + SMA200

---

# Phase 4. 백테스트 엔진

## 매수 조건

- [x] 종가 > SMA200

## 매도 조건

- [x] 종가 < SMA200

## 성과 분석

- [x] 누적 수익률
- [x] CAGR
- [x] MDD
- [x] Sharpe Ratio

## 비교 분석

- [x] Buy & Hold 수익률 계산
- [x] 전략 수익률 계산
- [x] 결과 리포트 생성

---

# Phase 5. 전략 개선

## 이동평균 조합

- [x] SMA50 / SMA200 골든크로스
- [x] SMA20 / SMA100
- [x] SMA100 / SMA200

## 필터 추가

- [ ] 거래량 필터
- [ ] 변동성 필터

## 결과 비교

- [x] 전략별 CAGR 비교
- [x] 전략별 MDD 비교

---

# Phase 6. 한국투자증권 (KIS) API 연동

## Open API 준비

- [ ] 개발자 계정 생성
- [ ] API Key 발급
- [ ] 모의투자 계좌 연결

## 기능 구현

- [x] 계좌 조회
- [x] 잔고 조회
- [ ] 주문 가능 금액 조회
- [x] 해외주식 주문

---

# Phase 7. 가상매매

## 신호 생성

- [x] 일별 매수/매도 신호 생성

## 주문 시뮬레이션

- [x] 매수 로그 저장
- [x] 매도 로그 저장
- [x] 포트폴리오 추적

---

# Phase 8. 자동매매

## Scheduler

- [x] 장 마감 후 데이터 수집
- [x] 전략 계산
- [x] 신호 생성

## 주문 자동화

- [x] 매수 주문
- [x] 매도 주문

## 알림

- [x] Discord 알림
- [x] Telegram 알림

---

# Phase 9. 모멘텀 전략

## 상대 모멘텀

- [x] 최근 3개월 수익률
- [x] 최근 6개월 수익률
- [x] 최근 12개월 수익률

## 종목 선정

- [x] NASDAQ100 종목 수집
- [x] 상위 종목 선정

## 리밸런싱

- [ ] 월간 리밸런싱
- [ ] 분기 리밸런싱

---

# Phase 10. 운영 및 대시보드

## API

- [x] FastAPI 구성

## Dashboard

- [x] Streamlit 구성
- [x] 수익률 시각화
- [x] MDD 시각화
- [x] 현재 매매 신호 표시

## 운영

- [ ] 실거래 운영
- [ ] 성과 리포트 자동 생성
- [ ] 1년 이상 운영 데이터 축적

---

# Milestone

## M1

- [x] QQQ 데이터 수집 완료
- [x] SMA200 계산 완료
- [x] 백테스트 완료

## M2

- [x] Buy & Hold 대비 성과 검증
- [x] 전략 개선 완료

## M3

- [ ] KIS API 연동
- [ ] 모의투자 자동매매 완료

## M4

- [ ] 실거래 자동매매 운영

## M5

- [ ] 모멘텀 전략 확장

---

# Phase 11. 시장 레짐 적응 전략 + Walk-Forward 검증

## 레짐 탐지

- [x] ADX(14) 계산 (Wilder smoothing 수동 구현)
- [x] SMA200 기준 상승장/하락장 판단
- [x] confirm_days=3 whipsaw 방지 로직
- [x] BULL / SIDEWAYS_UP / BEAR / SIDEWAYS_DOWN 4가지 레짐

## 전략별 구현

- [x] Volatility Breakout (Larry Williams, BULL 레짐)
- [x] Grid / Mean-Reversion (Bollinger Band, SIDEWAYS 레짐)
- [x] CASH (BEAR / SIDEWAYS_DOWN 레짐)

## 자동 전략 스위처

- [x] strategy/switcher.py — 레짐별 전략 자동 전환
- [x] 백테스트 결과: CAGR 93%, MDD -32%, Sharpe 2.04 vs B&H Sharpe 0.86

## Walk-Forward Analysis (WFA)

- [x] backtest/wfa.py 구현
- [x] 단순 분할 (2015-2021 학습 / 2022-2026 테스트)
  - [x] 학습 CAGR 139.7%, 테스트 CAGR 32.1% (B&H 6.9%)
- [x] 롤링 WFA (3년 학습 / 1년 테스트, 9 folds)
  - [x] OOS 스티치 CAGR 18.3%, MDD -15.2%, Sharpe 1.18
- [x] WFA 차트 저장 (report/btc_usd_wfa.png)

## 다음 단계

- [ ] 레짐 신호 → scheduler/runner.py 연동
- [ ] QQQ / SOXL / SOXS에 동일 전략 적용
- [ ] 실시간 레짐 감지 → Telegram 알림
