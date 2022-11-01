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
import secrets

import flaky
import pytest
import logging
from eth_typing import HexAddress, HexStr
from eth_account import Account
from hexbytes import HexBytes
from decimal import Decimal
from web3 import HTTPProvider, Web3
from eth_defi.hotwallet import HotWallet
from eth_defi.token import fetch_erc20_details
from eth_defi.ganache import fork_network
from eth_defi.confirmation import wait_transactions_to_complete
from eth_defi.venus.constants import VenusToken, VENUS_NETWORKS, venus_get_network_by_chain_id
from eth_defi.venus.balances import venus_get_deposit_balance, \
    venus_get_borrow_balance, venus_get_exchange_rate, venus_get_venus_token_balance,\
    venus_deposit

from web3.middleware import construct_sign_and_send_raw_middleware


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
def large_busd_holder() -> HexAddress:
    """A random account picked from BNB Smart chain that holds a lot of BUSD.

    This account is unlocked on Ganache, so you have access to good BUSD stash.

    `To find large holder accounts, use bscscan <https://bscscan.com/token/0xe9e7cea3dedca5984780bafc599bd69add087d56#balances>`_.
    """
    # Binance Hot Wallet 6
    return HexAddress(HexStr("0x8894E0a0c962CB723c1976a4421c95949bE2D4E3"))


@pytest.fixture(scope="module")
def large_bnb_holder() -> HexAddress:
    """A random account picked from BNB Smart chain that holds a lot of BNB.

    This account is unlocked on Ganache, so you have access to good BUSD stash.

    `To find large holder accounts, use bscscan <https://bscscan.com/token/0xF977814e90dA44bFA03b6295A0616a897441aceC#balances>`_.
    """
    # Binance Hot Wallet 6
    return HexAddress(HexStr("0xF977814e90dA44bFA03b6295A0616a897441aceC"))

@pytest.fixture()
def hot_wallet_private_key(web3) -> HexBytes:
    """Generate a private key"""
    return HexBytes(secrets.token_bytes(32))


@pytest.fixture()
def hot_wallet(web3, hot_wallet_private_key) -> HotWallet:
    """User account.

    Do some account allocation for tests.
    """
    account = Account.from_key(hot_wallet_private_key)
    hot_wallet = HotWallet(account)
    hot_wallet.sync_nonce(web3)
    return hot_wallet


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
def ganache_bnb_chain_fork(large_busd_holder:HexAddress, large_bnb_holder: HexAddress) -> str:
    """Create a testable fork of live bnb chain.

    :return: JSON-RPC URL for Web3
    """
    mainnet_rpc = os.environ["BNB_CHAIN_JSON_RPC"]
    launch = fork_network(mainnet_rpc + "@22503000", port=19998, unlocked_addresses=[large_busd_holder, large_bnb_holder], block_time=1)
    yield launch.json_rpc_url
    # Wind down Ganache process after the test is complete
    launch.close()


@pytest.fixture
def web3(ganache_bnb_chain_fork: str):
    """Set up a local unit testing blockchain."""
    # https://web3py.readthedocs.io/en/latest/web3.eth.account.html#read-a-private-key-from-an-environment-variable
    web3 = Web3(HTTPProvider(ganache_bnb_chain_fork))
    return web3


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


def test_deposit_busd_not_enough_balance(web3: Web3, venus_busd_token: VenusToken, hot_wallet: HotWallet, large_bnb_holder: HexAddress, large_busd_holder: HexAddress):

    # 先转入一些1 BNB做GAS
    bnb_tx_hash = web3.eth.send_transaction(
        {
            "from": large_bnb_holder,
            "to": hot_wallet.address,
            "value": 1_000_000_000_000_000_000 # 1BNB
        }
    )
    receipts = wait_transactions_to_complete(web3, [bnb_tx_hash])
    for receipt in receipts.values():
        assert receipt.status == 1  # tx success
    assert web3.eth.get_balance(hot_wallet.address) == 1_000_000_000_000_000_000, "转入的BNB数量不正确"

    # 1.测试结余不够
    ret = venus_deposit(web3, hot_wallet, venus_busd_token, 1)
    assert ret == False, "账户BUSD结余不够时应失败"


def test_deposit_busd_not_enough_allowance(web3: Web3, venus_busd_token: VenusToken, hot_wallet: HotWallet, large_bnb_holder: HexAddress, large_busd_holder: HexAddress):

    # 先转入一些1 BNB做GAS
    bnb_tx_hash = web3.eth.send_transaction(
        {
            "from": large_bnb_holder,
            "to": hot_wallet.address,
            "value": 1_000_000_000_000_000_000  # 1BNB
        }
    )
    receipts = wait_transactions_to_complete(web3, [bnb_tx_hash])
    for receipt in receipts.values():
        assert receipt.status == 1  # tx success
    assert web3.eth.get_balance(hot_wallet.address) == 1_000_000_000_000_000_000, "转入的BNB数量不正确"

    # 检查allowance不足
    busd_details = fetch_erc20_details(web3, "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56")
    busd = busd_details.contract
    allowance = busd.functions.allowance(hot_wallet.address,  venus_busd_token.deposit_address).call()
    assert allowance == 0, "allowance应为0"

    # 转入 50 BUSD 再测试
    busd_tx_hash = busd.functions.transfer(hot_wallet.address, 50 * 10 ** 18).transact({"from": large_busd_holder})
    receipts = wait_transactions_to_complete(web3, [busd_tx_hash])
    for receipt in receipts.values():
        assert receipt.status == 1  # tx success

    busd_balance = busd.functions.balanceOf(hot_wallet.address).call()
    assert busd_balance == 50 * 10 ** 18, "BUSD 余额应等于转入的数量50"

    ret = venus_deposit(web3, hot_wallet, venus_busd_token, 1)
    assert ret == True, "成功存入时应返回True"

    vbusd_balance = venus_get_deposit_balance(web3, venus_busd_token, hot_wallet.address)
    assert vbusd_balance == pytest.approx(Decimal(1), rel=Decimal(1e-5)), "存入的BUSD余额应等于50"


def test_deposit_busd(web3: Web3, venus_busd_token: VenusToken, hot_wallet: HotWallet, large_bnb_holder: HexAddress, large_busd_holder: HexAddress):
    # 先转入一些1 BNB做GAS
    bnb_tx_hash = web3.eth.send_transaction(
        {
            "from": large_bnb_holder,
            "to": hot_wallet.address,
            "value": 1_000_000_000_000_000_000  # 1BNB
        }
    )
    receipts = wait_transactions_to_complete(web3, [bnb_tx_hash])
    for receipt in receipts.values():
        assert receipt.status == 1  # tx success
    assert web3.eth.get_balance(hot_wallet.address) == 1_000_000_000_000_000_000, "转入的BNB数量不正确"

    # 转入 50 BUSD 再测试
    busd_details = fetch_erc20_details(web3, "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56")
    busd = busd_details.contract
    busd_tx_hash = busd.functions.transfer(hot_wallet.address, 50 * 10 ** 18).transact({"from": large_busd_holder})
    receipts = wait_transactions_to_complete(web3, [busd_tx_hash])
    for receipt in receipts.values():
        assert receipt.status == 1  # tx success

    busd_balance = busd.functions.balanceOf(hot_wallet.address).call()
    assert busd_balance == 50 * 10 ** 18, "BUSD 余额应等于转入的数量50"

    ret = venus_deposit(web3, hot_wallet, venus_busd_token, 1)
    assert ret == True, "成功存入时应返回True"

    vbusd_balance = venus_get_deposit_balance(web3, venus_busd_token, hot_wallet.address)
    assert vbusd_balance == pytest.approx(Decimal(1), rel=Decimal(1e-5)), "存入的BUSD余额应等于50"


def test_deposit_bnb_not_enough_balance(web3: Web3, venus_wbnb_token: VenusToken, hot_wallet: HotWallet, large_bnb_holder: HexAddress):
    # 先转入一些1 BNB做GAS
    bnb_tx_hash = web3.eth.send_transaction(
        {
            "from": large_bnb_holder,
            "to": hot_wallet.address,
            "value": 1_000_000_000_000_000_000  # 1BNB
        }
    )
    receipts = wait_transactions_to_complete(web3, [bnb_tx_hash])
    for receipt in receipts.values():
        assert receipt.status == 1  # tx success
    assert web3.eth.get_balance(hot_wallet.address) == 1_000_000_000_000_000_000, "转入的BNB数量不正确"

    ret = venus_deposit(web3, hot_wallet, venus_wbnb_token, 2) # BNB不足
    assert ret == False, "余额不足应返回False"


def test_deposit_bnb(web3: Web3, venus_wbnb_token: VenusToken, hot_wallet: HotWallet, large_bnb_holder: HexAddress):
    # 先转入一些2 BNB做GAS
    bnb_tx_hash = web3.eth.send_transaction(
        {
            "from": large_bnb_holder,
            "to": hot_wallet.address,
            "value": 2_000_000_000_000_000_000  # 1BNB
        }
    )
    receipts = wait_transactions_to_complete(web3, [bnb_tx_hash])
    for receipt in receipts.values():
        assert receipt.status == 1  # tx success
    assert web3.eth.get_balance(hot_wallet.address) == 2_000_000_000_000_000_000, "转入的BNB数量不正确"

    ret = venus_deposit(web3, hot_wallet, venus_wbnb_token, 1)
    assert ret == True, "存入成功应返回Ture"

