"""
Functions for reading Venus account status.
"""
import logging
from decimal import Decimal
from typing import Union

from web3 import Web3
from eth_defi.abi import get_deployed_contract
from eth_defi.defi_lending.rates import ulyToken_decimals, lending_token_decimals, WAD, unlimited
from eth_defi.defi_lending.constants import get_token_name_by_deposit_address, LendingToken
from eth_defi.hotwallet import HotWallet
from eth_defi.gas import estimate_gas_fees, apply_gas
from eth_defi.confirmation import broadcast_and_wait_transactions_to_complete

logger = logging.getLogger(__name__)


def get_exchange_rate(web3: Web3, lending_token: LendingToken) -> Decimal:
    """Check current exchange rate:
            uly token = vtoken * exchange_rate

    :param web3:
    :param lending_token:
    """

    contract = get_deployed_contract(web3, lending_token.abi, lending_token.deposit_address)
    result = contract.functions.exchangeRateCurrent().call()
    return Decimal(result) / WAD


def get_lending_token_balance(web3: Web3, lending_token: LendingToken, account_address: str) -> Decimal:

    contract = get_deployed_contract(web3, lending_token.abi, lending_token.deposit_address)
    result = contract.functions.balanceOf(account_address).call()
    return Decimal(result) / lending_token_decimals


async def get_deposit_balance(web3: Web3, lending_token: LendingToken, account_address: str, block_number:Union[str, int]='latest') -> Decimal:
    """Check the underlying depositing token balance

    :param web3:
    :param lending_token:
    :param account_address:
    :return:
    """
    # Use the vToken contract to read the account's current deposit balance in the specified currency reserve
    contract = get_deployed_contract(web3, lending_token.abi, lending_token.deposit_address)
    result = await contract.functions.balanceOfUnderlying(account_address).call(block_identifier=block_number)
    return Decimal(result) / ulyToken_decimals


async def get_borrow_balance(web3: Web3, lending_token: LendingToken, account_address: str, block_number:Union[str, int]='latest') -> Decimal:
    """Check the underlying borrowing token balance

    :param web3:
    :param venus_token:
    :param account_address:
    :return:
    """
    # Use the vToken contract to read the account's current borrow balance in the specified currency reserve
    deposit_address = Web3.to_checksum_address(lending_token.deposit_address)
    contract = get_deployed_contract(web3, lending_token.abi, deposit_address)
    result = await contract.functions.borrowBalanceCurrent(account_address).call(block_identifier=block_number)
    return Decimal(result) / ulyToken_decimals


def deposit(web3: Web3, hot_wallet: HotWallet, lending_token: LendingToken, deposit_amount: Decimal) -> bool:

    venus_contract = get_deployed_contract(web3, lending_token.abi, lending_token.deposit_address)
    gas_fees = estimate_gas_fees(web3)

    # 区分是否是wbnb
    # 1. 检查balance是否足够
    token_name = get_token_name_by_deposit_address(lending_token.deposit_address)
    if token_name == 'WBNB':

        underlying_balance = web3.eth.get_balance(hot_wallet.address)
        underlying_balance = web3.fromWei(underlying_balance, 'ether')

        # 检查balance是否足够
        if deposit_amount > underlying_balance:
            logger.warning("待存入的{}数量：{}，大于实际账户结余数量：{}，存入失败".format(token_name, deposit_amount, underlying_balance))
            return False

        # deposit
        tx = venus_contract.functions.mint(int(deposit_amount * ulyToken_decimals)).buildTransaction(
            {
                "from": hot_wallet.address,
                "chainId": web3.eth.chain_id,
                # "gas": 150_000,  # 150k gas should be more than enough for ERC20.transfer(),
            }
        )
        apply_gas(tx, gas_fees)
        signed_tx = hot_wallet.sign_transaction_with_new_nonce(tx)
        complete = broadcast_and_wait_transactions_to_complete(web3, [signed_tx])
        for receipt in complete.values():
            assert receipt.status == 1  # tx success

    else: # 非WBNB
        token_address = Web3.toChecksumAddress(lending_token.token_address)
        underlying_contract = get_deployed_contract(web3, "ERC20Mock.json", token_address)
        underlying_balance = underlying_contract.functions.balanceOf(hot_wallet.address).call()
        underlying_balance = underlying_balance / ulyToken_decimals

        # 检查balance是否足够
        if deposit_amount > underlying_balance:
            logger.warning("待存入的{}数量：{}，大于实际账户结余数量：{}，存入失败".format(token_name, deposit_amount, underlying_balance))
            return False

        # 检查授权是否足够，如果未授权，则自动授权
        allowance = underlying_contract.functions.allowance(hot_wallet.address, lending_token.deposit_address).call() / ulyToken_decimals
        if deposit_amount > allowance:
            logger.warning("授权{}的数量：{}，小于待存入的数量：{}".format(token_name, allowance, deposit_amount))

            tx = underlying_contract.functions.approve(lending_token.deposit_address, unlimited).buildTransaction(
                {
                    "from": hot_wallet.address,
                    "chainId": web3.eth.chain_id,
                    #"gas": 150_000,  # 150k gas should be more than enough for ERC20.transfer(),
                }
            )
            apply_gas(tx, gas_fees)
            signed_tx = hot_wallet.sign_transaction_with_new_nonce(tx)
            complete = broadcast_and_wait_transactions_to_complete(web3, [signed_tx])
            for receipt in complete.values():
                assert receipt.status == 1  # tx success

        # deposit
        tx = venus_contract.functions.mint(int(deposit_amount * ulyToken_decimals)).buildTransaction(
            {
                "from": hot_wallet.address,
                "chainId": web3.eth.chain_id,
                #"gas": 150_000,  # 150k gas should be more than enough for ERC20.transfer(),
            }
        )
        apply_gas(tx, gas_fees)
        signed_tx = hot_wallet.sign_transaction_with_new_nonce(tx)
        complete = broadcast_and_wait_transactions_to_complete(web3, [signed_tx])
        for receipt in complete.values():
            assert receipt.status == 1  # tx success

    return True


def withdraw(web3: Web3, lending_token: LendingToken, account_address: str, withdraw_amount: float) -> bool:
    pass
