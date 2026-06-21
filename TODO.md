# TODO — 남은 단계 (순서대로)

완료된 작업은 [HISTORY.md](HISTORY.md)(단계 1~11) 참고. 모든 문서의 단위는 **"단계(Step)"** 하나로 통일한다.
이 문서는 **단계 12부터** 앞으로 할 일을 진행 순서대로 정리한다. 기존 Phase에서 안 끝난 항목도 모두 이
순서 안에 녹였다 (출처는 옛 Phase 번호를 `(P5)`처럼 표기).

> 🎯 **최우선 목표:** 실시간(예: 30분 주기)으로 큰 변동을 감지하고, 레짐/전략에 따라 실시간 매수·매도가
> 동작하게 만든다. **실거래 전에 반드시 페이퍼(paper)로 먼저 검증.** 비트코인(Upbit, BTC)부터 →
> 이후 주식(NYSE: QQQ/SOXL/SOXS)으로 확장.

### 현재 한계 (왜 지금 구조로는 안 되는가)
- 모든 신호가 **일봉 1회**: `strategy/signals.py`는 일봉 CSV 마지막 행으로 SMA200만 판단.
- `scheduler/runner.py`는 **하루 1번(21:30 KST)** 실행 → 장중 급변 대응 불가, 24시간 BTC엔 무의미.
- `strategy/switcher.py`/`regime.py`는 **백테스트용**(전체 시계열 수익률). "지금 BUY/SELL/HOLD"를 뽑는 함수 없음.
- `broker/upbit.py`는 주문 가능하지만 **어떤 전략·스케줄러에도 연결 안 됨**.
- **인트라데이 수집 / 큰 변동 감지 / 실시간 루프 / 페이퍼 포트폴리오 / 안전장치**가 전혀 없음.

---

## 단계 12 — 실시간 신호 함수 (가장 핵심, 나머지의 전제) ✅ → `strategy/live.py`
- [x] `strategy/live.py` 신설: OHLCV 입력 → **현재 시점의** `{regime, strategy, action(BUY/SELL/HOLD), reason}` 반환
- [x] `regime.detect()`의 마지막 값을 실시간 레짐으로 사용 (confirm_days 유지)
- [x] VB/Grid 전략을 "현재 봉 기준 진입/청산 여부"로 변환 (백테스트 함수는 그대로 두고 라이브 전용 로직 추가)

## 단계 13 — 인트라데이 데이터 파이프라인 ✅ → `data/intraday.py`
- [x] Upbit 30분봉 수집기 (`pyupbit.get_ohlcv(interval="minute30")` 래핑)
- [x] 일봉(레짐/SMA200, 400봉) + 30분봉(변동/돌파) 표준 OHLCV 형식 반환
- [x] 일봉 collector와 동일 인터페이스(Open/High/Low/Close/Volume, index=Date) 유지

## 단계 14 — 큰 변동 감지 (이벤트 트리거) ✅ → `strategy/trigger.py`
- [x] 임계치 트리거: 최근 30분/1시간/24시간 수익률이 ±5% 초과 시 트리거
- [x] ATR 대비 최근 봉 변동폭 급등 감지 (정적 % 외 동적)
- [x] 트리거 발생 → 신호 재계산 → 필요 시 매매 → Telegram 알림 (단계 17/18 연동)

## 단계 15 — 페이퍼 포트폴리오 (실거래 전 검증의 핵심) ✅ → `paper/portfolio.py`
- [x] **착수금 1,000만원(10,000,000 KRW)** 으로 시작
- [x] 자산 분류: **BTC / NYSE** 두 그룹으로 구분해 포지션·손익 관리
- [x] **거래 기록**: 매매 발생 시 그 **시점(timestamp)** 으로 전체 거래내역 저장
  - [x] 기록 필드: 일시, 분류, 티커, 방향, 수량, 체결가, 거래금액
  - [x] **예상 수수료** 포함 (BTC=Upbit 0.05%, NYSE=KIS 0.25%)
  - [x] 건별 **손익(PnL)** 및 누적 손익(cum_pnl) 기록
- [x] **TOTAL 집계**: 현금 + 평가액, 분류별/전체 손익, 누적 수익률
- [x] **거래내역 조회**: 최대 **100개**, 초과 시 **페이지네이션** (`trades_page`)
- [x] 상태 저장: `data/paper/portfolio.json` + `data/paper/trades.csv`

## 단계 16 — 주문 실행 계층 (paper ↔ live 토글) ✅ → `broker/executor.py`
- [x] action(BUY/SELL/HOLD) → 체결 매핑 (`TradeExecutor.execute`)
- [x] **paper/live 토글** (`UPBIT_LIVE=false` 기본): paper=가상 체결, live=Upbit 실주문
- [x] 포지션/상태 관리: 보유 추적(`in_position`), 중복 매수·연속 매도 방지
- [ ] 슬리피지 반영 (현재 수수료·수량단위만 반영, 슬리피지 모델 추후)

## 단계 17 — 실시간 루프 스케줄러 ✅ → `scheduler/live_runner.py`
- [x] APScheduler `interval` 30분 job (BTC 24/7), `--daemon` 지원
- [x] 매 주기: 데이터 갱신 → 레짐/신호 계산 → 변동 감지 → 주문 판단 → 기록 → 알림
- [x] 레짐 신호 → 스케줄러 연동 (P11)
- [ ] 상시 구동(launchd/systemd/nohup) 문서화, telegram_agent와 경합 방지

## 단계 18 — Telegram 알림 (트레이딩 발생 시) ✅ → `scheduler/notify.py`
- [x] **트레이딩(페이퍼 포함) 발생 시 즉시 Telegram** (`format_trade`: 분류/티커/방향/수량/체결가/수수료/손익/TOTAL)
- [x] 큰 변동 트리거 발생 시 알림 (`format_spike`, 단계 14 연동)
- [ ] 실시간 레짐 전환 감지 시 알림 (전환 시점 비교 로직 추후)

## 단계 19 — 매일 08:30 결과 보고서 ✅ → `scheduler/daily_report.py`
- [x] 페이퍼 현황(당일/누적 손익·TOTAL)+레짐/신호를 Claude로 보고서화 → Telegram
- [x] 포함: 손익 요약 / 부적합 사유 / 오버피팅 안전 개선 / 전략 유지 vs 변경 판단
- [ ] 08:30 launchd/cron 트리거 등록 (기존 09:00 코드점검과 별개 잡)

## 단계 20 — 안전장치 (실거래 전 필수) ✅ → `broker/safety.py`
- [x] 모의/실거래 토글 (`UPBIT_LIVE=false` 기본)
- [x] 일일 최대 주문 수(10) / 일일 손실 한도(신규 매수 차단)
- [x] Kill switch (`data/paper/KILL` 파일 / `TRADING_HALT=true`)
- [x] 차단 사유 콘솔 로깅 + 체결 시 Telegram 알림 (단계 18)

## 단계 21 — BTC paper 검증 → 소액 실거래 (진행 중)
- [x] **대시보드에 페이퍼 포트폴리오 반영**: BTC/NYSE 분류, 거래내역(100개+페이지네이션), 수수료·손익·TOTAL ("Paper Portfolio (Live)" 탭)
- [ ] BTC paper 모드 **1~2주 실시간 검증** (`live_runner --daemon` 상시 구동, 라이브 ↔ 백테스트 신호 일치 확인)
- [ ] 검증 통과 → BTC 소액 실거래 전환 (`UPBIT_LIVE=true`)

---

## 단계 22 — 전략 고도화 (BTC 검증과 병행 가능)
- [ ] 거래량 필터 (P5)
- [ ] 변동성 필터 (P5)

## 단계 23 — 주식(NYSE: QQQ/SOXL/SOXS) 확장
- [ ] KIS 개발자 계정 생성 / API Key 발급 / 모의투자 계좌 연결 (P6)
- [ ] 주문 가능 금액 조회 (P6)
- [ ] 동일 레짐/실시간 전략을 QQQ/SOXL/SOXS에 적용 (P11) — **장 시간 제약 반영** (BTC와 달리 24h 아님)

## 단계 24 — 모멘텀 전략 확장
- [ ] 월간 리밸런싱 (P9)
- [ ] 분기 리밸런싱 (P9)

## 단계 25 — 운영
- [ ] 성과 리포트 자동 생성 (P10)
- [ ] 실거래 운영 (P10)
- [ ] 1년 이상 운영 데이터 축적 (P10)

---

## 전체 진행 현황

- ✅ **단계 1~11** — 데이터/백테스트/레짐 전략/WFA/대시보드/Telegram 자동화 ([HISTORY.md](HISTORY.md))
- ✅ **단계 12~20** — BTC 실시간 레짐 자동매매 파이프라인 **구현 완료** (paper 모드)
- ⏳ **단계 21** — BTC paper 실시간 검증(1~2주 상시 구동) → 소액 실거래 ← **현재 단계**
- ⬜ **단계 22~23** — 전략 고도화 + 주식(NYSE) 확장
- ⬜ **단계 24~25** — 모멘텀 확장 + 장기 운영

> 🚀 **지금 바로 실시간 페이퍼 트레이딩 시작:**
> ```bash
> uv run python -m scheduler.live_runner            # 1회 점검
> uv run python -m scheduler.live_runner --daemon   # 30분 주기 상시 구동 (paper)
> uv run streamlit run dashboard/app.py             # 대시보드 "Paper Portfolio (Live)" 탭
> ```
> 실거래 전환: `.env`에 `UPBIT_LIVE=true` + Upbit 키 설정. 중단: `touch data/paper/KILL`.
