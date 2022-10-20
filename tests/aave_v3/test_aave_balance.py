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
def holder() -> HexAddress:
    """A random account picked from polygon that holds a lot of aDAI token.

    This account is unlocked on Ganache, so you have access to good aDAI stash.

    `To find large holder accounts, use bscscan <https://polygonscan.com/address/0x29ad16353b0bebd3bbefee58d9f72887ebf4621e>`_.
    """
    # Binance Hot Wallet 6
    return HexAddress(HexStr("0x29ad16353b0bebd3bbefee58d9f72887ebf4621e"))


@pytest.fixture(scope="module")
def ganache_polygon_chain_fork(holder) -> str:
    """Create a testable fork of live Polygon chain.

    :return: JSON-RPC URL for Web3
    """
    mainnet_rpc = os.environ["POLYGON_CHAIN_JSON_RPC"]
    launch = fork_network(mainnet_rpc, unlocked_addresses=[holder])
    yield launch.json_rpc_url
    # Wind down Ganache process after the test is complete
    launch.close()


@pytest.fixture
def web3(ganache_polygon_chain_fork: str):
    """Set up a local unit testing blockchain."""
    # https://web3py.readthedocs.io/en/stable/examples.html#contract-unit-tests-in-python
    return Web3(HTTPProvider(ganache_polygon_chain_fork))


@pytest.fixture
def seller(web3: Web3) -> HexAddress:
    """return a random account as seller"""
    return web3.eth.accounts[5]


#
# @pytest.fixture(scope="module")
# def sushiswap_factory_v2() -> HexAddress:
#     """returns the uniswapfactoryV2 address for sushiswap on bsc"""
#     return HexAddress(HexStr("0xc35DADB65012eC5796536bD9864eD8773aBc74C4"))
#
#
# @pytest.fixture(scope="module")
# def pancakeswap_factory_v2() -> HexAddress:
#     """returns the uniswapfactoryV2 address for pancakeswap on bsc"""
#     return HexAddress(HexStr("0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73"))
#
#
# @pytest.fixture(scope="module")
# def pancake_router() -> HexAddress:
#     """returns the uniswaprouterV2 address for pancakeswap in bsc"""
#     return HexAddress(HexStr("0x10ED43C718714eb63d5aA57B78B54704E256024E"))
#
#
# @pytest.fixture(scope="module")
# def pancake_code_hash() -> str:
#     """The init code hash for pancakeswap. needed while fetching deployment"""
#     return "0x00fb7f630766e6a796048ea87d01acd3068e8ff67d078148a3fa3f4a84f69bd5"
#
#
# @pytest.fixture(scope="module")
# def elephant() -> HexAddress:
#     """return hex address of the elephant token"""
#     return HexAddress(HexStr("0xE283D0e3B8c102BAdF5E8166B73E02D96d92F688"))
#
#
# @pytest.fixture(scope="module")
# def busd() -> HexAddress:
#     """return hex address of busd token"""
#     return HexAddress(HexStr("0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56"))
#
#
# @pytest.fixture
# def uniswap(web3: Web3, pancakeswap_factory_v2: HexAddress, pancake_router: HexAddress,
#             pancake_code_hash: str) -> UniswapV2Deployment:
#     """returns an instance of the pancakeswap router & factory deployment on bsc"""
#     return fetch_deployment(web3, pancakeswap_factory_v2, pancake_router, pancake_code_hash)
#
#


def test_get_deposit_balance(web3: Web3, holder: HexAddress):

    # polygon aDAI: 0x82E64f49Ed5EC1bC6e43DAD4FC8Af9bb3A2312EE

    aDai = "0x82E64f49Ed5EC1bC6e43DAD4FC8Af9bb3A2312EE"
    balance = aave_v3_get_deposit_balance(web3, aDai, holder)
    print("balance:", balance)
    assert balance > 0, "Not enough BUSD to perform the test"



# @pytest.mark.skip(msg="Find a better low liquidity token to do a test swap")
# def test_low_liquidity_exception(uniswap: UniswapV2Deployment, large_busd_holder: HexAddress, seller: HexAddress,
#                                  elephant: HexAddress, busd: HexAddress):
#     buy_amount: float = 1e30
#
#     with pytest.raises(SwapError):
#         estimate_token_taxes(uniswap, elephant, busd, large_busd_holder, seller, buy_amount)
