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
from web3.middleware import geth_poa_middleware


from eth_defi.abi import get_contract
from eth_defi.event_reader.fast_json_rpc import patch_web3
from eth_defi.event_reader.reader import (
    read_events,
    read_events_concurrent,
    extract_timestamps_json_rpc,
    prepare_filter
)
from eth_defi.event_reader.web3factory import TunedWeb3Factory
from eth_defi.event_reader.web3worker import create_thread_pool_executor
from eth_defi.event_reader.json_state import JSONFileScanState

from eth_defi.defi_lending.constants import(
    LENDING_MARKETS,
    LendingToken,
    LendingMarket,
    get_lending_market,
)

from eth_defi.defi_lending.events import (
    MarketCache,
    decode_accrue_interest_events,
    fetch_events_to_dataframe,
    fetch_events_to_csv,
)


logger = logging.getLogger(__name__)

pytestmark = pytest.mark.skipif(
    os.environ.get("BNB_CHAIN_JSON_RPC") is None,
    reason="Set BNB_CHAIN_JSON_RPC environment variable to BSC mainnet node to run this test",
)

@pytest.fixture
def web3() -> Web3:
    """Set up a Web3 connection generation factury """
    # https://web3py.readthedocs.io/en/latest/web3.eth.account.html#read-a-private-key-from-an-environment-variable
    web3 = Web3(HTTPProvider(os.environ["BNB_CHAIN_JSON_RPC"]))
    web3.middleware_onion.clear()
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)
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


def test_read_events(web3: Web3):

    # Get contracts
    venus_token = get_contract(web3, 'venus/VBep20.json')
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
    assert e['borrow_index'] == 1174708111983875926
    assert e['borrow_rate_per_block'] == 1829348130
    assert e['supply_rate_per_block'] == 234523741
    assert e['total_borrows'] == 228555350454798399462476
    assert e['total_reserves'] == 85247367568144551221
    assert e['cash'] == 1197764356612419934198694

    e = out[1]
    assert e["block_number"] == 22629324
    assert e['timestamp'] == datetime.datetime(2022, 10, 30, 17, 43, 18)
    assert e["tx_hash"] == "0x19f46db89417848ad21127c073db0debe4ef6dc821d0e9b6f82cdb555a02f3d8"
    assert e["log_index"] == 126
    assert e['token'] == 'WBNB'
    assert e['deposit_address'] == '0xA07c5b74C9B40447a954e1466938b865b6BBea36'
    assert e['borrow_index'] == 1174708118430726189
    assert e['borrow_rate_per_block'] == 1829348126
    assert e['total_borrows'] == 228555351709120308330416
    assert e['total_reserves'] == 85247618432526324809
    assert e['cash'] == 1197764366612419934198694


def test_read_wepiggy_events(web3: Web3):
    # Get contracts
    # TODO: use venus events to read wepiggy events
    wepiggy_token = get_contract(web3, 'wepiggy/PToken.json')

    wepiggy_market = get_lending_market(56, 'wepiggy')

    events = [
        wepiggy_token.events.AccrueInterest,
    ]

    addresses = [t.deposit_address for t in wepiggy_market.token_contracts.values()]
    flter = prepare_filter(events)
    flter.contract_address = addresses

    token_cache = MarketCache(56, 'wepiggy')

    start_block = 22958548
    end_block = 22958573

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
    assert e["block_number"] == 22958548
    assert e['timestamp'] == datetime.datetime(2022, 11, 11, 8, 24, 57)
    assert e["tx_hash"] == "0xfbbd438734d86154ea2898207f615950fc9f7e852c55f75c8fe554d79d325195"
    assert e["log_index"] == 406
    assert e['token'] == 'DOT'
    assert e['deposit_address'] == '0x811Cd5CB4cC43F44600Cfa5eE3F37a402C82aec2'
    assert e['borrow_index'] == 1117925744930006963
    assert e['borrow_rate_per_block'] == 54573398028
    assert e['supply_rate_per_block'] == 34610964475
    assert e['total_borrows'] == 1915181603233538321416
    assert e['total_reserves'] == 58420651674954799729
    assert e['cash'] == 408084224942092940046

    e = out[1]
    assert e["block_number"] == 22958573
    assert e['timestamp'] == datetime.datetime(2022, 11, 11, 8, 26, 12)
    assert e["tx_hash"] == '0x9cbb428a2931bd19fcc1a620cb947e19ff146722a6d9958580e9451c93e97c4e'
    assert e["log_index"] == 182
    assert e['token'] == 'USDT'
    assert e['deposit_address'] == '0x2a8Cd78bFb91ACF53f589961D213d87c956e0d7f'
    assert e['borrow_index'] == 1139428702916594951
    assert e['borrow_rate_per_block'] == 3780391922
    assert e['supply_rate_per_block'] == 2704154557
    assert e['total_borrows'] == 377283537762406896666098
    assert e['total_reserves'] == 10407615241136816325631
    assert e['cash'] == 107820196806391617696803

def test_read_events_failed_case_1(web3: Web3):

    # Get contracts
    venus_token = get_contract(web3, 'venus/VBep20.json')
    venus_market = get_lending_market(56, 'venus')
    events = [
        venus_token.events.AccrueInterest,
    ]

    addresses = [t.deposit_address for t in venus_market.token_contracts.values()]
    flter = prepare_filter(events)
    flter.contract_address = addresses

    token_cache = MarketCache(56, 'venus')

    start_block = 20500372#22159164
    end_block = 20500372#22159164  # 22631473  #

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
    assert e['borrow_rate_per_block'] == 5352776277
    assert e['supply_rate_per_block'] == 3925900679
    assert e['total_borrows'] == 65064505765622195623511139
    assert e['total_reserves'] == 12114617303311774371055
    assert e['cash'] == 14788693531549214423178220


def test_read_events_concurrent():
    """Read events quickly over JSON-RPC API using a thread pool."""

    json_rpc_url = os.environ["BNB_CHAIN_JSON_RPC"]
    token_cache = MarketCache(56, 'venus')
    threads = 2
    http_adapter = HTTPAdapter(pool_connections=threads, pool_maxsize=threads)
    web3_factory = TunedWeb3Factory(json_rpc_url, http_adapter)
    web3 = web3_factory(token_cache)
    executor = create_thread_pool_executor(web3_factory, token_cache, max_workers=threads)

    # Get contracts
    venus_token = get_contract(web3, 'venus/VBep20.json')
    venus_market = get_lending_market(56, 'venus')

    events = [
        venus_token.events.AccrueInterest,
    ]

    addresses = [t.deposit_address for t in venus_market.token_contracts.values()]
    flter = prepare_filter(events)
    flter.contract_address = addresses

    start_block = 12_766_328
    end_block = 12_766_328 + 1_000  #

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

    assert len(out) == 238

    e = out[0]
    assert e["block_number"] == 12766331
    assert e['timestamp'] == datetime.datetime(2021, 11, 19, 2, 4, 14)
    assert e["tx_hash"] == "0x2b62b3edab76e223137c77dd6723011b6c6c4174744a8cc785daf5e66362ba21"
    assert e["log_index"] == 832
    assert e['token'] == 'USDT'
    assert e['deposit_address'] == '0xfD5840Cd36d94D7229439859C0112a4185BC0255'
    assert e['borrow_index'] == 1090134621168291647
    assert e['borrow_rate_per_block'] == 14875896119
    assert e['supply_rate_per_block'] == 12140067034
    assert e['total_borrows'] == 213420616265651700878749776
    assert e['total_reserves'] == 2134785769793988071396465
    assert e['cash'] == 24078654513750731053762012

    e = out[237]
    assert e["block_number"] == 12767327
    assert e['timestamp'] == datetime.datetime(2021, 11, 19, 2, 55, 38)
    assert e["tx_hash"] == "0x12193c1b1c37849b780b314cffd1094cd580bf4475850bdc2307fb21981a2dea"
    assert e["log_index"] == 1312
    assert e['token'] == 'ETH'
    assert e['deposit_address'] == '0xf508fCD89b8bd15579dc79A6827cB4686A3592c8'
    assert e['borrow_index'] == 1043938861499949016
    assert e['borrow_rate_per_block'] == 3510190293
    assert e['supply_rate_per_block'] == 474553026
    assert e['total_borrows'] == 26403775314519717108191
    assert e['total_reserves'] == 505873000910622841823
    assert e['cash'] == 130345586971338864337358


def test_fetch_events_to_dataframe():
    json_rpc_url = os.environ["BNB_CHAIN_JSON_RPC"]
    file_path = os.path.realpath(os.path.dirname(__file__))
    sub_path = "events"
    full_path = f"{file_path}/{sub_path}"
    scanstate = f"{full_path}/venus_scanstate.log"

    df = fetch_events_to_dataframe(
            json_rpc_url,
            56,
            'venus',
            JSONFileScanState(scanstate),
            start_block = 12_766_328,  # TRX created
            end_block = 12_766_328 + 1_000,
            output_folder = full_path,
            max_workers = 2,
            log_info = logger.info
    )

    assert len(df) == 238
    assert df.index[0] == datetime.datetime(2021, 11, 19, 2, 4, 14)

    assert df.iloc[0]["block_number"] == 12766331
    assert df.iloc[0]["tx_hash"] == "0x2b62b3edab76e223137c77dd6723011b6c6c4174744a8cc785daf5e66362ba21"
    assert df.iloc[0]["log_index"] == 832
    assert df.iloc[0]['token'] == 'USDT'
    assert df.iloc[0]['deposit_address'] == '0xfD5840Cd36d94D7229439859C0112a4185BC0255'
    assert df.iloc[0]['borrow_index'] == 1090134621168291647
    assert df.iloc[0]['borrow_rate_per_block'] == 14875896119
    assert df.iloc[0]['supply_rate_per_block'] == 12140067034
    assert int(df.iloc[0]['total_borrows']) == 213420616265651700878749776
    assert int(df.iloc[0]['total_reserves']) == 2134785769793988071396465
    assert int(df.iloc[0]['cash']) == 24078654513750731053762012

    assert df.index[237] == datetime.datetime(2021, 11, 19, 2, 55, 38)
    assert df.iloc[237]["block_number"] == 12767327
    assert df.iloc[237]["tx_hash"] == "0x12193c1b1c37849b780b314cffd1094cd580bf4475850bdc2307fb21981a2dea"
    assert df.iloc[237]["log_index"] == 1312
    assert df.iloc[237]['token'] == 'ETH'
    assert df.iloc[237]['deposit_address'] == '0xf508fCD89b8bd15579dc79A6827cB4686A3592c8'
    assert df.iloc[237]['borrow_index'] == 1043938861499949016
    assert df.iloc[237]['borrow_rate_per_block'] == 3510190293
    assert df.iloc[237]['supply_rate_per_block'] == 474553026
    assert int(df.iloc[237]['total_borrows']) == 26403775314519717108191
    assert int(df.iloc[237]['total_reserves']) == 505873000910622841823
    assert int(df.iloc[237]['cash']) == 130345586971338864337358


def test_fetch_wepiggy_events_to_dataframe():
    json_rpc_url = os.environ["BNB_CHAIN_JSON_RPC"]
    file_path = os.path.realpath(os.path.dirname(__file__))
    sub_path = "events"
    full_path = f"{file_path}/{sub_path}"
    scanstate = f"{full_path}/wepiggy_scanstate.log"

    df = fetch_events_to_dataframe(
            json_rpc_url,
            56,
            'wepiggy',
            JSONFileScanState(scanstate),
            start_block = 12_766_328,  # TRX created
            end_block = 12_766_328 + 1000,
            output_folder = full_path,
            max_workers = 2,
            log_info = logger.info
    )

    assert len(df) == 2

    assert df.index[0] == datetime.datetime(2021, 11, 19, 2, 25, 53)
    assert df.iloc[0]["block_number"] == 12766756
    assert df.iloc[0]["tx_hash"] == "0xbd6a1a5d8012c2a8305f6741768cdd7d6e1339262d0022cb5e2f40bd9e0b96e8"
    assert df.iloc[0]["log_index"] == 1474
    assert df.iloc[0]['token'] == 'USDT'
    assert df.iloc[0]['deposit_address'] == '0x2a8Cd78bFb91ACF53f589961D213d87c956e0d7f'
    assert df.iloc[0]['borrow_index'] == 1042860734322971115
    assert df.iloc[0]['borrow_rate_per_block'] == 13376086923
    assert df.iloc[0]['supply_rate_per_block'] == 9953765085
    assert int(df.iloc[0]['total_borrows']) == 446498644338914066316065
    assert int(df.iloc[0]['total_reserves']) == 2477889538599204420264
    assert int(df.iloc[0]['cash']) == 95992412407343823570439

    assert df.index[1] == datetime.datetime(2021, 11, 19, 2, 55, 24)
    assert df.iloc[1]["block_number"] == 12767323
    assert df.iloc[1]["tx_hash"] == "0xc11c1230fb984bee068c8caac9b4b9e20b6a4963ff44874c918e96b8d1cd0337"
    assert df.iloc[1]["log_index"] == 481
    assert df.iloc[1]['token'] == 'WBNB'
    assert df.iloc[1]['deposit_address'] == '0x33A32f0ad4AA704e28C93eD8Ffa61d50d51622a7'
    assert df.iloc[1]['borrow_index'] == 1095153214647240679
    assert df.iloc[1]['borrow_rate_per_block'] == 6836680054
    assert df.iloc[1]['supply_rate_per_block'] == 759855685
    assert int(df.iloc[1]['total_borrows']) == 173664968309257428890
    assert int(df.iloc[1]['total_reserves']) == 31969157701741437663
    assert int(df.iloc[1]['cash']) == 1030196280790570627983



