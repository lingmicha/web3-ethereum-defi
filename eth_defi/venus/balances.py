"""
Functions for reading Venus account status.
"""
import logging
from decimal import Decimal

from web3 import Web3

from eth_defi.abi import get_deployed_contract
from .rates import ulyToken_decimals

logger = logging.getLogger(__name__)


def venus_get_deposit_balance(web3: Web3, deposit_address: str, account_address: str) -> Decimal:
    # Use the vToken contract to read the account's current deposit balance in the specified currency reserve
    VToken = get_deployed_contract(web3, "venus/VToken.json", deposit_address)
    result = VToken.functions.balanceOfUnderlying(account_address).call()
    return Decimal(result) / ulyToken_decimals


def venus_get_borrow_balance(web3: Web3, borrow_address: str, account_address: str) -> Decimal:
    # Use the vToken contract to read the account's current borrow balance in the specified currency reserve
    VToken = get_deployed_contract(web3, "venus/VToken.json", borrow_address)
    result = VToken.functions.borrowBalanceCurrent(account_address).call()
    return Decimal(result) / ulyToken_decimals

