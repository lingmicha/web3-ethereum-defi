"""Fast event reading.

For manual tests see `scripts/read-uniswap-v2-pairs-and-swaps.py`.

.. code-block:: shell

    # Ethereum JSON-RPC
    export JSON_RPC_URL=
    pytest -k test_revert_reason

"""

import os
import logging
import pytest
import requests
import datetime
from requests.adapters import HTTPAdapter
from web3 import HTTPProvider, Web3
from pandas import DataFrame

from eth_defi.abi import get_contract
from eth_defi.event_reader.fast_json_rpc import patch_web3
from eth_defi.event_reader.logresult import LogContext, LogResult
from eth_defi.event_reader.reader import read_events, read_events_concurrent, extract_timestamps_json_rpc
from eth_defi.event_reader.web3factory import TunedWeb3Factory
from eth_defi.event_reader.web3worker import create_thread_pool_executor
from eth_defi.event_reader.json_state import JSONFileScanState

from eth_defi.venus.constants import VenusToken, VenusNetwork, venus_get_network_by_chain_id, VENUS_NETWORKS
from eth_defi.venus.events import TokenCache, decode_accrue_interest_events, fetch_events_to_dataframe, fetch_events_to_csv
from eth_defi.event_reader.reader import prepare_filter


logger = logging.getLogger(__name__)


pytestmark = pytest.mark.skipif(
    os.environ.get("BNB_CHAIN_JSON_RPC") is None,
    reason="Set BNB_CHAIN_JSON_RPC environment variable to BSC mainnet node to run this test",
)


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


def test_read_events():
    """Read events quickly over JSON-RPC API."""

    # HTTP 1.1 keep-alive
    session = requests.Session()

    json_rpc_url = os.environ["BNB_CHAIN_JSON_RPC"]
    web3 = Web3(HTTPProvider(json_rpc_url, session=session))

    # Enable faster ujson reads
    patch_web3(web3)

    web3.middleware_onion.clear()

    # Get contracts
    venus_token = get_contract(web3, 'venus/VBep20.json')

    events = [
        venus_token.events.AccrueInterest,
    ]

    addresses = [t.deposit_address for t in VENUS_NETWORKS['bsc'].token_contracts.values()]
    flter = prepare_filter(events)
    flter.contract_address = addresses

    token_cache = TokenCache()

    start_block = 22629320
    end_block = 22629330  # 22631473  #

    # Read through the blog ran
    out = []
    for log_result in read_events(
        web3,
        start_block,
        end_block,
        events,
        None,
        chunk_size=1000,
        context=token_cache,
        extract_timestamps=extract_timestamps_json_rpc,
        filter=flter,
    ):
        out.append(decode_accrue_interest_events(log_result))

    assert len(out) == 2

    e = out[0]
    assert e["block_number"] == 22629321
    assert e['timestamp'] == datetime.datetime(2022, 10, 30, 17, 43, 9)
    assert e["tx_hash"] == "0xc409991514aff4ae68f94dbce4496b0dcaac70741c23c2f1cb53f51cd23fc97d"
    assert e["log_index"] == 197
    assert e['token'] == 'WBNB'
    assert e['deposit_address'] == '0xA07c5b74C9B40447a954e1466938b865b6BBea36'
    assert e['cash_prior'] == 1197764111486000889186443
    assert e['interest_accumulated'] == 62298090010179021
    assert e['borrow_index'] == 1174708111983875926
    assert e['total_borrows'] == 228555595581217444474727

    e = out[1]
    assert e["block_number"] == 22629324
    assert e['timestamp'] == datetime.datetime(2022, 10, 30, 17, 43, 18)
    assert e["tx_hash"] == "0x19f46db89417848ad21127c073db0debe4ef6dc821d0e9b6f82cdb555a02f3d8"
    assert e["log_index"] == 126
    assert e['token'] == 'WBNB'
    assert e['deposit_address'] == '0xA07c5b74C9B40447a954e1466938b865b6BBea36'
    assert e['cash_prior'] == 1197764356612419934198694
    assert e['interest_accumulated'] == 1254321908867940
    assert e['borrow_index'] == 1174708118430726189
    assert e['total_borrows'] == 228555351709120308330416

def test_read_events_failed_case_1():
    """Read events quickly over JSON-RPC API."""

    # HTTP 1.1 keep-alive
    session = requests.Session()

    json_rpc_url = os.environ["BNB_CHAIN_JSON_RPC"]
    web3 = Web3(HTTPProvider(json_rpc_url, session=session))

    # Enable faster ujson reads
    patch_web3(web3)

    web3.middleware_onion.clear()

    # Get contracts
    venus_token = get_contract(web3, 'venus/VBep20.json')

    events = [
        venus_token.events.AccrueInterest,
    ]

    addresses = [t.deposit_address for t in VENUS_NETWORKS['bsc'].token_contracts.values()]
    flter = prepare_filter(events)
    flter.contract_address = addresses

    token_cache = TokenCache()

    start_block = 22159164
    end_block = 22159164  # 22631473  #

    # Read through the blog ran
    out = []
    for log_result in read_events(
        web3,
        start_block,
        end_block,
        events,
        None,
        chunk_size=1000,
        context=token_cache,
        extract_timestamps=extract_timestamps_json_rpc,
        filter=flter,
    ):
        out.append(decode_accrue_interest_events(log_result))

    assert len(out) == 1

    e = out[0]
    assert e["block_number"] == 22159164
    assert e['timestamp'] == datetime.datetime(2022, 10, 14, 4, 44, 3)
    assert e["tx_hash"] == "0x7d7a9a94f8ccce775724f7dd25fbedb4c039841b0d491b5dcada808c98e7ae2a"
    assert e["log_index"] == 155
    assert e['token'] == 'USDC'
    assert e['deposit_address'] == '0xecA88125a5ADbe82614ffC12D0DB554E2e2867C8'
    assert e['cash_prior'] == 14779694531549214423178220
    assert e['interest_accumulated'] == 106412221786647640933
    assert e['borrow_index'] == 1122880921630450768
    assert e['total_borrows'] == 65064505765622195623511139


def test_read_events_concurrent():
    """Read events quickly over JSON-RPC API using a thread pool."""

    json_rpc_url = os.environ["BNB_CHAIN_JSON_RPC"]
    token_cache = TokenCache()
    threads = 16
    http_adapter = HTTPAdapter(pool_connections=threads, pool_maxsize=threads)
    web3_factory = TunedWeb3Factory(json_rpc_url, http_adapter)
    web3 = web3_factory(token_cache)
    executor = create_thread_pool_executor(web3_factory, token_cache, max_workers=threads)

    # Get contracts
    venus_token = get_contract(web3, 'venus/VBep20.json')

    events = [
        venus_token.events.AccrueInterest,
    ]

    addresses = [t.deposit_address for t in VENUS_NETWORKS['bsc'].token_contracts.values()]
    flter = prepare_filter(events)
    flter.contract_address = addresses

    start_block = 22629320
    end_block = 22652473  #

    # Read through the blog ran
    out = []
    for log_result in read_events_concurrent(
        executor,
        start_block,
        end_block,
        events,
        None,
        chunk_size=200,
        context=token_cache,
        extract_timestamps=extract_timestamps_json_rpc,
        filter=flter,
    ):
        out.append(decode_accrue_interest_events(log_result))

    assert len(out) == 1883

    e = out[0]
    assert e["block_number"] == 22629321
    assert e['timestamp'] == datetime.datetime(2022, 10, 30, 17, 43, 9)
    assert e["tx_hash"] == "0xc409991514aff4ae68f94dbce4496b0dcaac70741c23c2f1cb53f51cd23fc97d"
    assert e["log_index"] == 197
    assert e['token'] == 'WBNB'
    assert e['deposit_address'] == '0xA07c5b74C9B40447a954e1466938b865b6BBea36'
    assert e['cash_prior'] == 1197764111486000889186443
    assert e['interest_accumulated'] == 62298090010179021
    assert e['borrow_index'] == 1174708111983875926
    assert e['total_borrows'] == 228555595581217444474727

    e = out[1]
    assert e["block_number"] == 22629324
    assert e['timestamp'] == datetime.datetime(2022, 10, 30, 17, 43, 18)
    assert e["tx_hash"] == "0x19f46db89417848ad21127c073db0debe4ef6dc821d0e9b6f82cdb555a02f3d8"
    assert e["log_index"] == 126
    assert e['token'] == 'WBNB'
    assert e['deposit_address'] == '0xA07c5b74C9B40447a954e1466938b865b6BBea36'
    assert e['cash_prior'] == 1197764356612419934198694
    assert e['interest_accumulated'] == 1254321908867940
    assert e['borrow_index'] == 1174708118430726189
    assert e['total_borrows'] == 228555351709120308330416

    e = out[1883]
    assert e["block_number"] == 22652462
    assert e["tx_hash"] == "0xf9bdb09e2ba28af8baecda74b94795306633d25275650949a2c9dbd665480897"
    assert e["log_index"] == 281
    assert e['token'] == 'ETH'
    assert e["deposit_address"] == Web3.toChecksumAddress("0xf508fcd89b8bd15579dc79a6827cb4686a3592c8")
    assert e['cash_prior'] == 44299213003303609094185
    assert e['interest_accumulated'] == 6472712823055175
    assert e['borrow_index'] == 1082487156484500726
    assert e['total_borrows'] == 18024473191124053920154


def test_fetch_events_to_dataframe():
    json_rpc_url = os.environ["BNB_CHAIN_JSON_RPC"]
    df = fetch_events_to_dataframe(
            json_rpc_url,
            JSONFileScanState("rate_state.log"),
            start_block = 12_766_328,  # TRX created
            end_block = 12_766_328 + 1_000,
            output_folder = "/tmp",
            max_workers = 50,
            log_info = print
    )
    #df.to_csv("rates.csv")

    assert len(df) == 238
    assert df.iloc[0]["token"] == "USDT"
    assert df.iloc[0]["block_number"] == 12766331
    assert df.iloc[0]["log_index"] == 832
    assert df.iloc[0]["total_supply"] == 1103972950685788682
    assert df.iloc[0]["total_borrow"] == 213420616265651700878749776
    assert df.iloc[0]["supply_rate_per_block"] == 12140067034
    assert df.iloc[0]["borrow_rate_per_block"] == 14875896119

    assert df.iloc[237]["token"] == "ETH"
    assert df.iloc[237]["block_number"] == 12767327
    assert df.iloc[237]["log_index"] == 1312
    assert df.iloc[237]["total_supply"] == 773943888684807
    assert df.iloc[237]["total_borrow"] == 26403775314519717108191
    assert df.iloc[237]["supply_rate_per_block"] == 474553026
    assert df.iloc[237]["borrow_rate_per_block"] == 3510190293





