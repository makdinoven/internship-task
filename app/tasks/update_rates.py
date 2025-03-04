import json
import logging

import httpx
import redis

from app.celery import celery_app
from app.config import COINMARKETCAP_API_URL

BASE_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
HEADERS = {"X-CMC_PRO_API_KEY": COINMARKETCAP_API_URL}
CURRENCIES = ["USD", "EUR", "AUD", "CAD", "ARS", "PLN", "BTC", "ETH", "DOGE", "USDT"]
FIATS = ["USD", "EUR", "AUD", "CAD", "ARS", "PLN"]
CRYPTOS = ["BTC", "ETH", "DOGE", "USDT"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

redis_client = redis.Redis(host="redis", port=6379, db=0)


@celery_app.task
def update_rates():
    """
    Task to update and cache exchange rates for cryptocurrencies and fiat currencies.
    """
    logger.info("Started task for updating rates")
    try:
        # Retrieve crypto prices in USD
        params = {"symbol": ",".join(CRYPTOS)}
        resp = httpx.get(BASE_URL, params=params, headers=HEADERS, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()["data"]
        prices_usd = {sym: data[sym]["quote"]["USD"]["price"] for sym in CRYPTOS}
        logger.info("Crypto prices retrieved: %s", prices_usd)

        # Retrieve fiat conversion rates (via USDT)
        fiat_to_usd = {"USD": 1.0}
        for fiat in FIATS:
            if fiat == "USD":
                continue
            params = {"symbol": "USDT", "convert": fiat}
            resp = httpx.get(BASE_URL, params=params, headers=HEADERS, timeout=10.0)
            resp.raise_for_status()
            price = resp.json()["data"]["USDT"]["quote"][fiat]["price"]
            fiat_to_usd[fiat] = 0 if price == 0 else 1 / price
        logger.info("Fiat rates retrieved: %s", fiat_to_usd)

        # Combine rates and calculate conversions
        value_in_usd = {**fiat_to_usd, **prices_usd}
        logger.info("Combined currency values: %s", value_in_usd)

        for base in CURRENCIES:
            rates = {}
            for target in CURRENCIES:
                if target == base or base not in value_in_usd or target not in value_in_usd:
                    continue
                rate = value_in_usd[base] / value_in_usd[target]
                rates[target] = rate
            # Cache the conversion rates with a TTL of 3600 seconds
            cache_key = f"rates:{base}"
            redis_client.setex(cache_key, 3600, json.dumps(rates))
            logger.info("Rates saved for %s: %s", base, rates)
        logger.info("Rate update task completed successfully.")
        return "Success"
    except Exception as e:
        logger.error("Error while updating rates: %s", e)
        return "Failed"
