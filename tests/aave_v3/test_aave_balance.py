"""Token tax module test examples on the BSC Chain for the ELEPHANT token

To run tests in this module:

.. code-block:: shell

    export BNB_CHAIN_JSON_RPC="https://bsc-dataseed.binance.org/"
    pytest -k test_token_tax

"""
import os

import flaky
import pytest
from eth_typing import HexAddress, HexStr
from web3 import HTTPProvider, Web3

from eth_defi.ganache import fork_network
from eth_defi.aave_v3.balances import aave_v3_get_deposit_balance, aave_v3_get_variable_borrow_balance

# https://docs.pytest.org/en/latest/how-to/skipping.html#skip-all-test-functions-of-a-class-or-module
pytestmark = pytest.mark.skipif(
    os.environ.get("POLYGON_CHAIN_JSON_RPC") is None,
    reason="Set POLYGON_CHAIN_JSON_RPC environment variable to Polygon node to run this test",
)


@pytest.fixture(scope="module")
def aDai_holder() -> HexAddress:
    """A random account picked from polygon that holds a lot of aDAI token.

    This account is unlocked on Ganache, so you have access to good aDAI stash.

    `To find large holder accounts, use bscscan <https://polygonscan.com/address/0x29ad16353b0bebd3bbefee58d9f72887ebf4621e>`_.
    """
    # Binance Hot Wallet 6
    return HexAddress(HexStr("0x29ad16353b0bebd3bbefee58d9f72887ebf4621e"))


@pytest.fixture(scope="module")
def ganache_polygon_chain_fork(aDai_holder) -> str:
    """Create a testable fork of live Polygon chain.

    :return: JSON-RPC URL for Web3
    """
    mainnet_rpc = os.environ["POLYGON_CHAIN_JSON_RPC"]
    launch = fork_network(mainnet_rpc, unlocked_addresses=[aDai_holder]) #"@34571963"
    yield launch.json_rpc_url
    # Wind down Ganache process after the test is complete
    launch.close()


@pytest.fixture
def web3(ganache_polygon_chain_fork: str):
    """Set up a local unit testing blockchain."""
    # https://web3py.readthedocs.io/en/stable/examples.html#contract-unit-tests-in-python
    return Web3(HTTPProvider(ganache_polygon_chain_fork))


def test_get_deposit_balance(web3: Web3, aDai_holder: HexAddress):

    # polygon aDAI: 0x82E64f49Ed5EC1bC6e43DAD4FC8Af9bb3A2312EE
    aDai = HexAddress(HexStr("0x82E64f49Ed5EC1bC6e43DAD4FC8Af9bb3A2312EE"))
    balance = aave_v3_get_deposit_balance(web3, aDai, aDai_holder)
    print("balance:", balance)
    assert balance > 0, "账户中aDai应大于0"

