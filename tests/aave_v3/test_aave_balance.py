"""Token tax module test examples on the BSC Chain for the ELEPHANT token

To run tests in this module:

.. code-block:: shell

    export BNB_CHAIN_JSON_RPC="https://bsc-dataseed.binance.org/"
    pytest -k test_token_tax

    current block is 34,581,439
    Large ADAI holder 229496.483194811632175501
    Large stableDebtPolDAI holder 15161.687076820887075569
    Large variableDebtPolEURS holder 21060.34
    Large stableDebtPolEURS holder 20.1


"""
import os

import flaky
import pytest
from eth_typing import HexAddress, HexStr
from web3 import HTTPProvider, Web3

from eth_defi.ganache import fork_network
from eth_defi.aave_v3.constants import AaveToken, AaveNetwork, aave_v3_get_network_by_chain_id
from eth_defi.aave_v3.balances import aave_v3_get_deposit_balance, aave_v3_get_variable_borrow_balance

# https://docs.pytest.org/en/latest/how-to/skipping.html#skip-all-test-functions-of-a-class-or-module
pytestmark = pytest.mark.skipif(
    os.environ.get("POLYGON_CHAIN_JSON_RPC") is None,
    reason="Set POLYGON_CHAIN_JSON_RPC environment variable to Polygon node to run this test",
)


@pytest.fixture(scope="module")
def aave_token_holder() -> HexAddress:
    """A random account picked from polygon that holds a lot of aDAI token.

    This account is unlocked on Ganache, so you have access to good aDAI stash.

    `To find large holder accounts, use polygonscan <https://polygonscan.com/address/0x5b8effbdae5941b938c1a79616d185cc3c79d4ff>`_.
    """
    # Binance Hot Wallet 6
    return Web3.toChecksumAddress("0x5b8effbdae5941b938c1a79616d185cc3c79d4ff")

@pytest.fixture(scope="module")
def aave_token() -> AaveToken:
    aave_network = aave_v3_get_network_by_chain_id(137)
    aave_token = aave_network.token_contracts['DAI']
    return aave_token


@pytest.fixture(scope="module")
def ganache_polygon_chain_fork(aave_token_holder) -> str:
    """Create a testable fork of live Polygon chain.

    :return: JSON-RPC URL for Web3
    """
    mainnet_rpc = os.environ["POLYGON_CHAIN_JSON_RPC"]
    launch = fork_network(mainnet_rpc + "@34581438", unlocked_addresses=[aave_token_holder])
    yield launch.json_rpc_url
    # Wind down Ganache process after the test is complete
    launch.close()


@pytest.fixture
def web3(ganache_polygon_chain_fork: str):
    """Set up a local unit testing blockchain."""
    # https://web3py.readthedocs.io/en/stable/examples.html#contract-unit-tests-in-python
    return Web3(HTTPProvider(ganache_polygon_chain_fork))


def test_get_deposit_balance(web3: Web3, aave_token: AaveToken, aave_token_holder: HexAddress):

    balance = aave_v3_get_deposit_balance(web3, aave_token.deposit_address, aave_token_holder)
    assert balance == 229496.483194811632175501, "账户中AAVE DAI应等于229496.483194811632175501"

