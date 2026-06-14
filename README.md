# Quant Trading

NASDAQ 자동매매 시스템 — 이동평균선 기반 전략으로 QQQ, SOXL, SOXS, BTC-USD를 거래하고, 한국투자증권 (KIS) Open API로 실거래를 자동화하는 프로젝트.

## Goal

| 항목 | 내용 |
|------|------|
| 시장 | NASDAQ |
| 증권사 | 한국투자증권 (KIS) |
| 투자 대상 | QQQ, SOXL, SOXS, BTC-USD |
| 1차 전략 | SMA200 돌파 매수/매도 |
| 최종 목표 | 모멘텀 기반 자동매매 |
| 성공 기준 | Buy & Hold 대비 낮은 MDD, 유사하거나 더 높은 CAGR |

---

## Project Structure

```
quant-trading/
├── data/
│   ├── universe.py        # ticker registry (QQQ, SOXL, SOXS, BTC-USD)
│   ├── collector.py       # yfinance data fetcher (multi-ticker)
│   └── raw/               # downloaded CSVs (gitignored)
├── strategy/
│   ├── ma.py              # SMA calculation and chart export
│   ├── signals.py         # current day signal generator
│   ├── crossover.py       # golden cross strategy (SMA50/200 etc.)
│   └── momentum.py        # NASDAQ-100 relative momentum (3m/6m/12m)
├── backtest/
│   ├── metrics.py         # CAGR, MDD, Sharpe Ratio
│   ├── engine.py          # SMA200 backtest vs Buy & Hold
│   └── paper_trade.py     # virtual portfolio & trade log
├── broker/
│   └── kis.py             # Korea Investment & Securities Open API client
├── scheduler/
│   ├── runner.py          # APScheduler daily job (21:30 KST)
│   └── notify.py          # Discord & Telegram notifications
├── api/
│   └── main.py            # FastAPI REST endpoints
├── dashboard/
│   └── app.py             # Streamlit dashboard
├── report/                # generated charts (gitignored PNGs)
└── notebook/              # Jupyter notebooks
```

---

## Setup

**Requirements:** Python 3.14+, pyenv, uv

```bash
# install dependencies
uv sync

# fetch all ticker data
python -m data.collector
```

---

## Usage

### Data

```bash
# fetch / refresh all universe tickers
python -m data.collector
```

### Backtest

```bash
# SMA200 strategy vs Buy & Hold
python -m backtest.engine

# crossover strategy comparison (SMA50/200, SMA20/100, SMA100/200)
python -m strategy.crossover
```

### Signals

```bash
# print today's signal for each ticker
python -m strategy.signals
```

### Paper Trading

```bash
# run one cycle: generate signals → execute virtual trades
python -m backtest.paper_trade
```

### Momentum

```bash
# rank NASDAQ-100 by 3m/6m/12m momentum → top 10
python -m strategy.momentum
```

### Scheduler

```bash
# run job once (fetch data + signals + paper trade + notify)
python -m scheduler.runner

# run as daily daemon (21:30 KST)
python -m scheduler.runner --daemon
```

### Dashboard

```bash
streamlit run dashboard/app.py
# → http://localhost:8501/
```

### API

```bash
uvicorn api.main:app --reload
# → http://localhost:8000/docs
```

---

## Backtest Results (SMA200 Strategy)

| Ticker | Strategy CAGR | B&H CAGR | Strategy MDD | B&H MDD |
|--------|:------------:|:-------:|:-----------:|:------:|
| QQQ | 12.1% | 15.4% | **-26.5%** | -53.4% |
| SOXL | 31.3% | 44.4% | **-69.6%** | -90.5% |
| SOXS | -25.2% | -71.3% | -99.4% | -100% |
| BTC-USD | 58.2% | 59.2% | **-69.9%** | -83.4% |

> SMA200 전략은 수익률을 일부 희생하는 대신 MDD를 절반 수준으로 낮춥니다.

---

## Broker (KIS Open API)

`broker/kis.py`는 한국투자증권 (KIS) Open API 클라이언트입니다.  
신청: https://apiportal.koreainvestment.com

`.env`에 아래 값을 입력하세요:

```bash
APP_KEY=your_app_key
APP_SECRET=your_app_secret
ACCOUNT_NO=your_account_number  # 계좌번호 (숫자만, 하이픈 제외)
USE_MOCK=true                   # 모의투자: true / 실거래: false
```

---

## Notifications

Discord와 Telegram 알림은 환경변수로 설정합니다:

```bash
export DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
export TELEGRAM_BOT_TOKEN=your_bot_token
export TELEGRAM_CHAT_ID=your_chat_id
```

---

## Milestones

- [x] **M1** — QQQ 데이터 수집, SMA200 계산, 백테스트
- [x] **M2** — Buy & Hold 대비 성과 검증, 전략 개선
- [ ] **M3** — 한국투자증권 KIS API 연동, 모의투자 자동매매
- [ ] **M4** — 실거래 자동매매 운영
- [ ] **M5** — 모멘텀 전략 확장
