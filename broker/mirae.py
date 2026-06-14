"""
Mirae Asset Open API client (Phase 6).
Requires APP_KEY, APP_SECRET, ACCOUNT_NO environment variables.
Set USE_MOCK=true to run against the paper-trading endpoint.
"""

import os


class MiraeClient:
    BASE_URL = "https://openapi.koreainvestment.com:9443"
    MOCK_URL = "https://openapivts.koreainvestment.com:29443"

    def __init__(self) -> None:
        self.app_key = os.environ["APP_KEY"]
        self.app_secret = os.environ["APP_SECRET"]
        self.account_no = os.environ["ACCOUNT_NO"]
        self.use_mock = os.environ.get("USE_MOCK", "true").lower() == "true"
        self.base = self.MOCK_URL if self.use_mock else self.BASE_URL
        self._token: str | None = None

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _get_token(self) -> str:
        import requests

        resp = requests.post(
            f"{self.base}/oauth2/tokenP",
            json={"grant_type": "client_credentials", "appkey": self.app_key, "appsecret": self.app_secret},
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    def _headers(self, tr_id: str) -> dict:
        if not self._token:
            self._get_token()
        return {
            "authorization": f"Bearer {self._token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "content-type": "application/json",
        }

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    def get_balance(self) -> dict:
        import requests

        resp = requests.get(
            f"{self.base}/uapi/overseas-stock/v1/trading/inquire-balance",
            headers=self._headers("JTTT3012R"),
            params={
                "CANO": self.account_no[:8],
                "ACNT_PRDT_CD": self.account_no[8:],
                "OVRS_EXCG_CD": "NASD",
                "TR_CRCY_CD": "USD",
            },
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def buy(self, ticker: str, qty: int) -> dict:
        return self._order(ticker, qty, side="buy")

    def sell(self, ticker: str, qty: int) -> dict:
        return self._order(ticker, qty, side="sell")

    def _order(self, ticker: str, qty: int, side: str) -> dict:
        import requests

        tr_id = "JTTT1002U" if side == "buy" else "JTTT1006U"
        resp = requests.post(
            f"{self.base}/uapi/overseas-stock/v1/trading/order",
            headers=self._headers(tr_id),
            json={
                "CANO": self.account_no[:8],
                "ACNT_PRDT_CD": self.account_no[8:],
                "OVRS_EXCG_CD": "NASD",
                "PDNO": ticker,
                "ORD_DVSN": "00",  # market order
                "ORD_QTY": str(qty),
                "OVRS_ORD_UNPR": "0",
            },
        )
        resp.raise_for_status()
        return resp.json()
