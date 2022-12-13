
import os
import logging
import pytest
import asyncio
import pytz
from datetime import datetime
from decimal import Decimal

import pytest_asyncio
from web3 import HTTPProvider, Web3, AsyncHTTPProvider
from web3.eth import AsyncEth
from web3.middleware import async_geth_poa_middleware
from eth_typing import HexStr
from bson.objectid import ObjectId
from eth_defi.event_reader.reader import (
    prepare_filter,
)
from eth_defi.event_reader.reader_async import (
    extract_timestamps_json_rpc,
    extract_events,
    read_events,
)
from eth_defi.event_reader.logresult import LogContext, LogResult
from eth_defi.abi import get_contract, get_deployed_contract
from eth_defi.token import TokenDetails
from eth_defi.defi_lending.events import (
    MarketCache,
)
from eth_defi.defi_lending.constants import (
    LendingToken,
    get_lending_market,
    LENDING_MARKETS,
    get_token_name_by_deposit_address,
)
from eth_defi.event_reader.conversion import (
    decode_data,
    convert_int256_bytes_to_int,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("BNB_CHAIN_JSON_RPC") is None,
    reason="Set BNB_CHAIN_JSON_RPC environment variable to BSC mainnet node to run this test",
)

async def decode_accrue_interest_events(log: LogResult) -> dict:
    """Process venus event.

    This function does manually optimised high speed decoding of the event.

    The event signature is:

    .. code-block::

        AccrueInterest(uint256,uint256,uint256,uint256)
    """

    # Do additional lookup for the token data
    web3 = log["event"].w3

    market_cache: MarketCache = log["context"]
    block_time = datetime.utcfromtimestamp(log["timestamp"])
    block_number = int(log["blockNumber"], 16)

    # Any indexed Solidity event parameter will be in topics data.
    # The first topics (0) is always the event signature.
    deposit_address = Web3.to_checksum_address(log["address"])
    token_name = get_token_name_by_deposit_address(deposit_address)

    contract = get_deployed_contract(web3, market_cache.get_abi_path(), deposit_address)

    # Chop data blob to byte32 entries
    data_entries = decode_data(log["data"])
    # Wepiggy 和 Venus 参数不同，但是[2]都是borrow index， Wepiggy在最后加了一个totalReserves
    borrow_index = convert_int256_bytes_to_int(data_entries[2])

    # 监控的事件发生时，都会引起利率变化，所以要记录此区块的利率、借款、存款利息等信息
    tasks = [
        contract.functions.borrowRatePerBlock().call(block_identifier=block_number),
        contract.functions.supplyRatePerBlock().call(block_identifier=block_number),
        contract.functions.totalBorrows().call(block_identifier=block_number),
        contract.functions.totalReserves().call(block_identifier=block_number),
        contract.functions.getCash().call(block_identifier=block_number)
    ]

    (borrow_rate_per_block, supply_rate_per_block, total_borrows, total_reserves, cash) = \
    await asyncio.gather(*tasks)

    data = {
        "block_number": block_number,
        "timestamp": block_time,
        "tx_hash": log["transactionHash"],
        "log_index": int(log["logIndex"], 16),
        "token": token_name,
        "deposit_address": deposit_address,

        #"cash_prior": cash_prior,
        #"interest_accumulated": interest_accumulated,
        "borrow_index": borrow_index,

        # below is forward rates read directly from the chain:
        "borrow_rate_per_block": borrow_rate_per_block,
        "supply_rate_per_block": supply_rate_per_block,
        "total_borrows": total_borrows,
        "total_reserves": total_reserves,
        "cash": cash,

    }
    return data


@pytest_asyncio.fixture(scope='module')
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope='module')
def asyncweb3(event_loop) -> Web3:
    """Set up a Web3 connection generation factury """
    json_rpc_url = os.environ["BNB_CHAIN_JSON_RPC"]
    web3 = Web3(AsyncHTTPProvider(json_rpc_url), modules={'eth': (AsyncEth,)}, middlewares=[])

    from eth_defi.rate import async_rate_limiter_middleware

    # Enable faster ujson reads
    web3.middleware_onion.clear()
    web3.middleware_onion.inject(async_geth_poa_middleware, layer=0)
    web3.middleware_onion.add(async_rate_limiter_middleware)
    return web3


@pytest.fixture(scope="module")
def venus_busd_token() -> LendingToken:
    venus_network = get_lending_market(56, 'venus')
    venus_token = venus_network.token_contracts['BUSD']
    return venus_token


@pytest.fixture(scope="module")
def venus_wbnb_token() -> LendingToken:
    venus_network = get_lending_market(56, 'venus')
    venus_token = venus_network.token_contracts['WBNB']
    return venus_token


@pytest.mark.asyncio
async def test_async_extract_timestamps_json_rpc(asyncweb3: Web3):

    start = 23420000
    end =   23420101
    timestamps = await extract_timestamps_json_rpc(asyncweb3, start, end)
    assert len(timestamps) == 23420101 - 23420000 + 1
    # https://bscscan.com/block/23420000
    hash = '0xd254c4e68cda82d9fdc7204d12284a7d36b58fa5463e0ffd56cd79549ac1b348'
    expected_timestamp = datetime(2022,11,27,15,10,32,tzinfo=pytz.utc)
    actual_timestamp = datetime.fromtimestamp(timestamps[hash], tz=pytz.utc)
    assert actual_timestamp == expected_timestamp


@pytest.mark.asyncio
async def test_async_extract_events(asyncweb3: Web3):

    start = 23353768
    end =   23353769
    context = MarketCache(56, 'venus')

    contract = get_contract(asyncweb3, 'venus/VBep20.json')
    events = [contract.events.Borrow]
    flter = prepare_filter(events)

    logs = []
    async for log in extract_events(asyncweb3, start, end, flter, context):
        logs.append(log)

    assert len(logs) == 1
    assert logs[0]["timestamp"] == 1669359454
    assert logs[0]["topics"] == ["0x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80"]

async def test_async_read_events(asyncweb3: Web3):

    # Get contracts
    venus_token = get_contract(asyncweb3, 'venus/VBep20.json')
    venus_market = get_lending_market(56, 'venus')

    events = [
        venus_token.events.AccrueInterest,
    ]

    addresses = [t.deposit_address for t in venus_market.token_contracts.values()]
    flter = prepare_filter(events)
    flter.contract_address = addresses

    token_cache = MarketCache(56, 'venus')

    start_block = 22629320
    end_block = 22629330  # 22631473  #

    # Read through the blog ran
    out = []
    async for log_result in read_events(
        asyncweb3,
        start_block,
        end_block,
        events,
        None,
        chunk_size=1000,
        context=token_cache,
        extract_timestamps=extract_timestamps_json_rpc,
        filter=flter,
    ):
        out.append(await decode_accrue_interest_events(log_result))

    assert len(out) == 2

    e = out[0]
    assert e["block_number"] == 22629321
    assert e['timestamp'] == datetime(2022, 10, 30, 17, 43, 9)
    assert e["tx_hash"] == "0xc409991514aff4ae68f94dbce4496b0dcaac70741c23c2f1cb53f51cd23fc97d"
    assert e["log_index"] == 197
    assert e['token'] == 'WBNB'
    assert e['deposit_address'] == '0xA07c5b74C9B40447a954e1466938b865b6BBea36'
    assert e['borrow_index'] == 1174708111983875926
    assert e['borrow_rate_per_block'] == 1829348130
    assert e['supply_rate_per_block'] == 234523741
    assert e['total_borrows'] == 228555350454798399462476
    assert e['total_reserves'] == 85247367568144551221
    assert e['cash'] == 1197764356612419934198694

    e = out[1]
    assert e["block_number"] == 22629324
    assert e['timestamp'] == datetime(2022, 10, 30, 17, 43, 18)
    assert e["tx_hash"] == "0x19f46db89417848ad21127c073db0debe4ef6dc821d0e9b6f82cdb555a02f3d8"
    assert e["log_index"] == 126
    assert e['token'] == 'WBNB'
    assert e['deposit_address'] == '0xA07c5b74C9B40447a954e1466938b865b6BBea36'
    assert e['borrow_index'] == 1174708118430726189
    assert e['borrow_rate_per_block'] == 1829348126
    assert e['total_borrows'] == 228555351709120308330416
    assert e['total_reserves'] == 85247618432526324809
    assert e['cash'] == 1197764366612419934198694
