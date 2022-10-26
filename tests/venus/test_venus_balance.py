"""balance module test examples on the BSC Chain for  token

To run tests in this module:

.. code-block:: shell

    export BNB_CHAIN_JSON_RPC=https://bsc-dataseed.binance.org
    pytest -k test_venus_balance

    Fork Block Number: 22503000

    holder_1: 0x6564b5053C381a8D840B40d78bA229e2d8e912ed
    vBUSD balance == 0.0

    holder_2: 0x74dc8ab767982958f0fd162a9b9a71a32d5fa775
    vBUSD quantity == 389,464,062.80620444
          balance == $8,457,374.88

    holder_3: 0xfde64760370ad58805900a3e23a1ebeeae9fba2c
    vWBNB quantity == 3,685,389.27906611
            balance == $34,798,602.93

    holder_4: 0xded08efb71abcc782a86d53a43731c77ca1250cf
    vUSDT borrow quantity
            balance ==

"""
import os

import flaky
import pytest
import logging
from eth_typing import HexAddress, HexStr
from decimal import Decimal
from web3 import HTTPProvider, Web3

from eth_defi.ganache import fork_network
from eth_defi.venus.constants import VenusToken, VENUS_NETWORKS, venus_get_network_by_chain_id
from eth_defi.venus.balances import venus_get_deposit_balance, venus_get_borrow_balance, venus_get_exchange_rate, venus_get_venus_token_balance

logger = logging.getLogger(__name__)

# https://docs.pytest.org/en/latest/how-to/skipping.html#skip-all-test-functions-of-a-class-or-module
pytestmark = pytest.mark.skipif(
    os.environ.get("BNB_CHAIN_JSON_RPC") is None,
    reason="Set BNB_CHAIN_JSON_RPC environment variable to Polygon node to run this test",
)


@pytest.fixture(scope="module")
def holder_1() -> HexAddress:
    """A random account picked from bsc that holds 0 of vBUSD token.
    `To find large holder accounts, use bscscan <https://bscscan.com/address/0x6564b5053C381a8D840B40d78bA229e2d8e912ed>`_.
    """
    return Web3.toChecksumAddress("0x6564b5053C381a8D840B40d78bA229e2d8e912ed")


@pytest.fixture(scope="module")
def holder_2() -> HexAddress:
    """A random account picked from bsc that holds large vBUSD token.
    `To find large holder accounts, use bscscan <https://bscscan.com/address/0x74dc8ab767982958f0fd162a9b9a71a32d5fa775>`_.
    """
    return Web3.toChecksumAddress("0x74dc8ab767982958f0fd162a9b9a71a32d5fa775")


@pytest.fixture(scope="module")
def holder_3() -> HexAddress:
    """A random account picked from polygon that holds large vWBNB token.
    `To find large holder accounts, use bscscan <https://bscscan.com/address/0xfde64760370ad58805900a3e23a1ebeeae9fba2c>`_.
    """
    return Web3.toChecksumAddress("0xfde64760370ad58805900a3e23a1ebeeae9fba2c")


@pytest.fixture(scope="module")
def holder_4() -> HexAddress:
    """A random account picked from bsc that holds usdt borrow token.
    `To find large holder accounts, use bscscan <https://bscscan.com/address/0xded08efb71abcc782a86d53a43731c77ca1250cf>`_.
    """
    return Web3.toChecksumAddress("0xded08efb71abcc782a86d53a43731c77ca1250cf")


@pytest.fixture(scope="module")
def venus_busd_token() -> VenusToken:
    venus_network = venus_get_network_by_chain_id(56)
    venus_token = venus_network.token_contracts['BUSD']
    return venus_token


@pytest.fixture(scope="module")
def venus_wbnb_token() -> VenusToken:
    venus_network = venus_get_network_by_chain_id(56)
    venus_token = venus_network.token_contracts['WBNB']
    return venus_token


@pytest.fixture(scope="module")
def venus_usdt_token() -> VenusToken:
    venus_network = venus_get_network_by_chain_id(56)
    venus_token = venus_network.token_contracts['USDT']
    return venus_token


@pytest.fixture(scope="module")
def ganache_bnb_chain_fork() -> str:
    """Create a testable fork of live bnb chain.

    :return: JSON-RPC URL for Web3
    """
    mainnet_rpc = os.environ["BNB_CHAIN_JSON_RPC"]
    launch = fork_network(mainnet_rpc + "@22503000", port=19998)
    yield launch.json_rpc_url
    # Wind down Ganache process after the test is complete
    launch.close()


@pytest.fixture
def web3(ganache_bnb_chain_fork: str):
    """Set up a local unit testing blockchain."""
    # https://web3py.readthedocs.io/en/stable/examples.html#contract-unit-tests-in-python
    return Web3(HTTPProvider(ganache_bnb_chain_fork))


def test_get_busd_exchange_rate(web3: Web3, venus_busd_token: VenusToken):
    expected_exchange_rate = Decimal(216984931.17271517901891039)
    exchange_rate = venus_get_exchange_rate(web3, venus_busd_token)
    logger.debug("vBUSD exchange rate: {}".format(exchange_rate))
    assert exchange_rate == pytest.approx(expected_exchange_rate, rel=Decimal(1e-3)), "VBUSD的exchange rate应为 216984931.17271517901891039"


def test_zero_busd_deposit_balance(web3: Web3, venus_busd_token: VenusToken, holder_1: HexAddress):
    # 0 balance
    balance = venus_get_deposit_balance(web3, venus_busd_token, holder_1)
    logger.debug("0 vBUSD holder balance: {}".format(balance))
    assert balance == Decimal(0), "账户中VBUSD价值应为 0"


def test_large_busd_deposit_balance(web3: Web3, venus_busd_token: VenusToken, holder_2: HexAddress):
    # large busd balance
    expected_busd_balance = Decimal(8450783.286225)
    balance = venus_get_deposit_balance(web3, venus_busd_token, holder_2)
    logger.debug("Large vBUSD holder balance: {}, expected balance: {}".format(balance, expected_busd_balance))
    assert balance == pytest.approx(expected_busd_balance, rel=Decimal(1e-3)), "账户中VBUSD价值应为 8450783.286225"


def test_large_wbnb_deposit_balance(web3: Web3, venus_wbnb_token: VenusToken, holder_3: HexAddress):
    # large wbnb balance
    expected_wbnb_balance = Decimal(80354.860453789838412348)
    balance = venus_get_deposit_balance(web3, venus_wbnb_token, holder_3)
    logger.debug("Large WBNB holder balance: {}, expected balance: {}".format(balance, expected_wbnb_balance))
    assert balance == pytest.approx(expected_wbnb_balance, rel=Decimal(1e-3)), "账户中VBUSD价值应为 80354.860453789838412348"

    # 用exchange rate重新计算balance
    exchange_rate = venus_get_exchange_rate(web3, venus_wbnb_token)
    vwbnb_balance = venus_get_venus_token_balance(web3, venus_wbnb_token, holder_3)
    assert exchange_rate * vwbnb_balance / Decimal(10**10) == pytest.approx(expected_wbnb_balance, rel=Decimal(1e-3))


def test_zero_busd_borrow_balance(web3: Web3, venus_busd_token: VenusToken, holder_1: HexAddress):
    # 0 balance
    balance = venus_get_borrow_balance(web3, venus_busd_token, holder_1)
    logger.debug("0 BUSD borrow balance: {}".format(balance))
    assert balance == Decimal(0), "账户中BUSD借款价值应为 0"


def test_non_zero_usdt_borrow_balance(web3: Web3, venus_usdt_token: VenusToken, holder_4: HexAddress):
    # non-zero usdt borrow balance
    expected_usdt_balance = Decimal(2202.89)
    balance = venus_get_borrow_balance(web3, venus_usdt_token, holder_4)
    logger.debug("non-zero USDT borrow balance: {}, expected balance: {}".format(balance, expected_usdt_balance))
    assert balance == pytest.approx(expected_usdt_balance, rel=Decimal(1e-3)), "账户中USDT价值应为 2202.89"


def test_deposit_busd_not_enough_balance():
    pass


def test_deposit_busd_not_enough_allowance():
    pass


def test_deposit_busd():
    pass


def test_deposit_bnb_not_enough_balance():
    pass


def test_deposit_bnb_not_enough_allowance():
    pass


def test_deposit_bnb():
    pass
