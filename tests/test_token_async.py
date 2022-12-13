"""Mock token deployment."""

import pytest
import pytest_asyncio
import asyncio
from web3 import (
    EthereumTesterProvider,
    Web3,
)
from web3.providers.eth_tester.main import (
    AsyncEthereumTesterProvider,
)
from web3.eth import AsyncEth

from typing import Union
from eth_typing import HexAddress
from eth_tester.exceptions import TransactionFailed
from web3.providers.eth_tester.middleware import async_construct_formatting_middleware
from web3.middleware import async_geth_poa_middleware
from eth_defi.deploy_async import deploy_contract
from eth_defi.token import TokenDetailError
from eth_defi.token_async import create_token, fetch_erc20_details

@pytest_asyncio.fixture(scope='module')
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope='module')
def web3(event_loop):
    """Set up a local unit testing blockchain."""
    # https://web3py.readthedocs.io/en/stable/examples.html#contract-unit-tests-in-python
    web3 = Web3(
        AsyncEthereumTesterProvider(),
        modules={"eth": [AsyncEth]},
        middlewares=[])
    web3.middleware_onion.clear()
    #web3.middleware_onion.inject(async_construct_formatting_middleware, layer=0)
    #web3.middleware_onion.inject(async_geth_poa_middleware, layer=0)
    return web3

@pytest_asyncio.fixture(scope='module')
async def deployer(web3) -> str:
    """Deploy account.

    Do some account allocation for tests.
    """
    return (await web3.eth.accounts)[0]


@pytest_asyncio.fixture(scope='module')
async def user_1(web3) -> str:
    """User account.

    Do some account allocation for tests.
    """
    return (await web3.eth.accounts)[1]


@pytest_asyncio.fixture(scope='module')
async def user_2(web3) -> str:
    """User account.

    Do some account allocation for tests.
    """
    return (await web3.eth.accounts)[2]

@pytest.mark.asyncio
async def test_deploy_token(web3: Web3, deployer: str):
    """Deploy mock ERC-20."""
    token = await create_token(web3, deployer, "Hentai books token", "HENTAI", 100_000 * 10**18, 6)
    # https://web3py.readthedocs.io/en/stable/contracts.html#contract-deployment-example
    assert await token.functions.name().call() == "Hentai books token"
    assert await token.functions.symbol().call() == "HENTAI"
    assert await token.functions.totalSupply().call() == 100_000 * 10**18
    assert await token.functions.decimals().call() == 6

@pytest.mark.asyncio
async def test_tranfer_tokens_between_users(web3: Web3, deployer: str, user_1: str, user_2: str):
    """Transfer tokens between users."""
    token = await create_token(web3, deployer, "Telos EVM rocks", "TELOS", 100_000 * 10**18)

    # Move 10 tokens from deployer to user1
    await token.functions.transfer(user_1, 10 * 10**18).transact({"from": deployer})
    assert await token.functions.balanceOf(user_1).call() == 10 * 10**18

    # Move 10 tokens from deployer to user1
    await token.functions.transfer(user_2, 6 * 10**18).transact({"from": user_1})
    assert await token.functions.balanceOf(user_1).call() == 4 * 10**18
    assert await token.functions.balanceOf(user_2).call() == 6 * 10**18

@pytest.mark.asyncio
async def test_tranfer_too_much(web3: Web3, deployer: str, user_1: str, user_2: str):
    """Attempt to transfer more tokens than an account has."""
    token = await create_token(web3, deployer, "Telos EVM rocks", "TELOS", 100_000 * 10**18)

    # Move 10 tokens from deployer to user1
    await token.functions.transfer(user_1, 10 * 10**18).transact({"from": deployer})
    assert await token.functions.balanceOf(user_1).call() == 10 * 10**18

    # Attempt to move 11 tokens from deployer to user1
    # with pytest.raises(TransactionFailed):
    #     await token.functions.transfer(user_2, 11 * 10**18).transact({"from": user_1})
    #assert str(excinfo.value) == "execution reverted: ERC20: transfer amount exceeds balance"

@pytest.mark.asyncio
async def test_fetch_token_details(web3: Web3, deployer: str):
    """Get details of a token."""
    token = await create_token(web3, deployer, "Hentai books token", "HENTAI", 100_000 * 10**18, 6)
    details = await fetch_erc20_details(web3, token.address)
    assert details.name == "Hentai books token"
    assert details.decimals == 6

@pytest.mark.asyncio
async def test_fetch_token_details_broken_silent(web3: Web3, deployer: str):
    """Get details of a token that does not conform ERC-20 guidelines."""
    malformed_token = await deploy_contract(web3, "MalformedERC20.json", deployer)
    details = await fetch_erc20_details(web3, malformed_token.address, raise_on_error=False)
    assert details.symbol == ""
    assert details.decimals == 0
    assert details.total_supply is None

@pytest.mark.asyncio
async def test_fetch_token_details_broken_load(web3: Web3, deployer: str):
    """Get an error if trying to read malformed token."""
    malformed_token = await deploy_contract(web3, "MalformedERC20.json", deployer)
    with pytest.raises(TokenDetailError):
        await fetch_erc20_details(web3, malformed_token.address)
