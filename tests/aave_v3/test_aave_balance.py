"""balance module test examples on the Polygon Chain for DAI/EURS token

To run tests in this module:

.. code-block:: shell

    export POLYGON_CHAIN_JSON_RPC="https://polygon-mainnet.g.alchemy.com/v2/H3E99oH7XymptRueBxkO4OXXazhFb7_c"
    pytest -k test_aave_balance

    Fork Block Number: 34581439

    holder_1: 0x6564b5053C381a8D840B40d78bA229e2d8e912ed
    ADAI balance == 0.0

    holder_2: 0x5b8effbdae5941b938c1a79616d185cc3c79d4ff
    ADAI balance == 229496.483194811632175501
    variableDebtPolEURS balance == 21060.34

    holder_3: 0x2f74bd41940a188eb8d0fd0d5a6e92e93ec7a4a8
    stableDebtPolDAI balance == 15161.687076820887075569

    holder_4: 0xd1802c153fa2ae751ac7526419c4500fa8025c1e
    stableDebtPolEURS balance == 20.1

"""
import os

import flaky
import pytest
from eth_typing import HexAddress, HexStr
from web3 import HTTPProvider, Web3

from eth_defi.ganache import fork_network
from eth_defi.aave_v3.constants import AaveToken, AaveNetwork, aave_v3_get_network_by_chain_id
from eth_defi.aave_v3.balances import aave_v3_get_deposit_balance, aave_v3_get_variable_borrow_balance, aave_v3_get_stable_borrow_balance

# https://docs.pytest.org/en/latest/how-to/skipping.html#skip-all-test-functions-of-a-class-or-module
pytestmark = pytest.mark.skipif(
    os.environ.get("POLYGON_CHAIN_JSON_RPC") is None,
    reason="Set POLYGON_CHAIN_JSON_RPC environment variable to Polygon node to run this test",
)


@pytest.fixture(scope="module")
def holder_1() -> HexAddress:
    """A random account picked from polygon that holds 0 of aDAI token.
    `To find large holder accounts, use polygonscan <https://polygonscan.com/address/0x6564b5053C381a8D840B40d78bA229e2d8e912ed>`_.
    """
    return Web3.toChecksumAddress("0x6564b5053C381a8D840B40d78bA229e2d8e912ed")


@pytest.fixture(scope="module")
def holder_2() -> HexAddress:
    """A random account picked from polygon that holds large aDAI and variableDebtPolEURS token.
    `To find large holder accounts, use polygonscan <https://polygonscan.com/address/0x5b8effbdae5941b938c1a79616d185cc3c79d4ff>`_.
    """
    return Web3.toChecksumAddress("0x5b8effbdae5941b938c1a79616d185cc3c79d4ff")


@pytest.fixture(scope="module")
def holder_3() -> HexAddress:
    """A random account picked from polygon that holds large aDAI and variableDebtPolEURS token.
    `To find large holder accounts, use polygonscan <https://polygonscan.com/address/0x2f74bd41940a188eb8d0fd0d5a6e92e93ec7a4a8>`_.
    """
    return Web3.toChecksumAddress("0x2f74bd41940a188eb8d0fd0d5a6e92e93ec7a4a8")


@pytest.fixture(scope="module")
def holder_4() -> HexAddress:
    """A random account picked from polygon that holds large aDAI and variableDebtPolEURS token.
    `To find large holder accounts, use polygonscan <https://polygonscan.com/address/0xd1802c153fa2ae751ac7526419c4500fa8025c1e>`_.
    """
    return Web3.toChecksumAddress("0xd1802c153fa2ae751ac7526419c4500fa8025c1e")


@pytest.fixture(scope="module")
def aave_dai_token() -> AaveToken:
    aave_network = aave_v3_get_network_by_chain_id(137)
    aave_token = aave_network.token_contracts['DAI']
    return aave_token


@pytest.fixture(scope="module")
def aave_eurs_token() -> AaveToken:
    aave_network = aave_v3_get_network_by_chain_id(137)
    aave_token = aave_network.token_contracts['EURS']
    return aave_token


@pytest.fixture(scope="module")
def ganache_polygon_chain_fork() -> str:
    """Create a testable fork of live Polygon chain.

    :return: JSON-RPC URL for Web3
    """
    mainnet_rpc = os.environ["POLYGON_CHAIN_JSON_RPC"]
    launch = fork_network(mainnet_rpc + "@34581439")
    yield launch.json_rpc_url
    # Wind down Ganache process after the test is complete
    launch.close()


@pytest.fixture
def web3(ganache_polygon_chain_fork: str):
    """Set up a local unit testing blockchain."""
    # https://web3py.readthedocs.io/en/stable/examples.html#contract-unit-tests-in-python
    return Web3(HTTPProvider(ganache_polygon_chain_fork))


def test_get_deposit_balance(web3: Web3, aave_dai_token: AaveToken,  holder_1: HexAddress, holder_2: HexAddress ):

    # 0 balance
    balance = aave_v3_get_deposit_balance(web3, Web3.toChecksumAddress(aave_dai_token.deposit_address), holder_1)
    assert balance == 0, "账户中AAVE DAI 应为 0"

    # large balance
    expected_balance = 229496.483194811632175501
    balance = float(aave_v3_get_deposit_balance(web3, Web3.toChecksumAddress(aave_dai_token.deposit_address), holder_2))
    assert balance == pytest.approx(expected_balance, rel=1e-1), "账户中AAVE DAI应约等于 229496.483194811632175501"
#
# def test_get_variable_borrow_balance(web3: Web3, aave_eurs_token: AaveToken, holder_2: HexAddress):
#
#     # non-zero balance
#     expected_balance = 21060.34
#     balance = aave_v3_get_variable_borrow_balance(web3, Web3.toChecksumAddress(aave_eurs_token.variable_borrow_address), holder_2)
#     assert balance * 1.0 == pytest.approx(expected_balance, rel=1e0), "账户中 variableDebtPolEURS 应等于 21060.34"
#
# def test_get_stable_borrow_balance_1(web3: Web3, aave_dai_token: AaveToken, holder_3: HexAddress):
#
#     # non-zero  balance
#     balance = aave_v3_get_stable_borrow_balance(web3, Web3.toChecksumAddress(aave_dai_token.stable_borrow_address), holder_3)
#     assert balance > 1.0, "账户中 stableDebtPolDAI 应等于 15161.687076820887075569"
#
# def test_get_stable_borrow_balance_2(web3: Web3, aave_eurs_token: AaveToken, holder_4: HexAddress):
#
#     # non-zero  balance
#     balance = aave_v3_get_stable_borrow_balance(web3, Web3.toChecksumAddress(aave_eurs_token.stable_borrow_address), holder_4)
#     assert balance > 1.0, "账户中 stableDebtPolEURS 应等于 15161.687076820887075569"
