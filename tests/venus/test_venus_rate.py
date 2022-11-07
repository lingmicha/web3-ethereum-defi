'''
Test Venus Rate Calculation
'''

import os
import logging
import pytest
import requests
import datetime
from decimal import Decimal

from web3 import HTTPProvider, Web3
from web3.middleware import geth_poa_middleware

from eth_defi.abi import get_contract, get_deployed_contract

from eth_defi.event_reader.fast_json_rpc import patch_web3
from eth_defi.event_reader.web3factory import TunedWeb3Factory
from eth_defi.event_reader.reader import prepare_filter, read_events, extract_timestamps_json_rpc
from eth_defi.event_reader.json_state import JSONFileScanState

from eth_defi.venus.constants import VenusToken, venus_get_network_by_chain_id, VENUS_NETWORKS
from eth_defi.venus.events import TokenCache, decode_accrue_interest_events, fetch_events_to_csv
from eth_defi.venus.rates import load_accrue_interest_event_dataframe, venus_calculate_mean, \
    venus_calculate_apr_apy_rates,venus_calculate_accrued_interests

logger = logging.getLogger(__name__)


pytestmark = pytest.mark.skipif(
    os.environ.get("BNB_CHAIN_JSON_RPC") is None,
    reason="Set BNB_CHAIN_JSON_RPC environment variable to BSC mainnet node to run this test",
)


@pytest.fixture
def web3_factory() -> TunedWeb3Factory:
    """Set up a Web3 connection generation factury """
    # https://web3py.readthedocs.io/en/latest/web3.eth.account.html#read-a-private-key-from-an-environment-variable
    return TunedWeb3Factory(os.environ["BNB_CHAIN_JSON_RPC"])


@pytest.fixture
def web3() -> Web3:
    """Set up a Web3 connection generation factury """
    # https://web3py.readthedocs.io/en/latest/web3.eth.account.html#read-a-private-key-from-an-environment-variable
    web3 = Web3(HTTPProvider(os.environ["BNB_CHAIN_JSON_RPC"]))
    web3.middleware_onion.clear()
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return web3


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


def test_calc_rates_using_index(venus_wbnb_token: VenusToken):
    '''使用index来计算区块间的利率    
    '''
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

    start_block = 22629321
    end_block = 22629324    #

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

    # 对比链上数据和计算值

    ''' 链上计算方式：
         * Calculate the interest accumulated into borrows and reserves and the new index:
         *  simpleInterestFactor = borrowRate * blockDelta
         *  interestAccumulated = simpleInterestFactor * totalBorrows
         *  totalBorrowsNew = interestAccumulated + totalBorrows
         *  totalReservesNew = interestAccumulated * reserveFactor + totalReserves
         *  borrowIndexNew = simpleInterestFactor * borrowIndex + borrowIndex
    '''

    vbnb = get_deployed_contract(web3, Web3.toChecksumAddress(venus_wbnb_token.deposit_address))

    block_number_start = out[0]['block_number']
    block_number_end = out[1]['block_number']
    block_delta = block_number_end - block_number_start

    borrow_index_start = out[0]['borrow_index']
    borrow_index_end = out[1]['borrow_index']
    simple_interest_factor = borrow_index_end / borrow_index_start - 1
    borrow_rate_calculated = simple_interest_factor / block_delta

    # borrow rate per block
    borrow_rate_on_chain = vbnb.functions.borrowRatePerBlock().call(block_identifier=22629320) / 1e18
    assert borrow_rate_calculated == pytest.approx(borrow_rate_on_chain, 1e-10)


def test_rates_between_events(venus_wbnb_token: VenusToken):
    # HTTP 1.1 keep-alive
    session = requests.Session()

    json_rpc_url = os.environ["BNB_CHAIN_JSON_RPC"]
    web3 = Web3(HTTPProvider(json_rpc_url, session=session))

    # Enable faster ujson reads
    patch_web3(web3)

    web3.middleware_onion.clear()

    # start_block ~ end_block -1 的rates_per_block应该保持不变
    start_block = 22629321
    end_block = 22629324    #

    vbnb = get_deployed_contract(web3, "venus/VBep20.json", Web3.toChecksumAddress(venus_wbnb_token.deposit_address))

    expected_rate_per_block = 1829348130
    for block_num in range(start_block, end_block):
        borrow_rate_per_blcok = vbnb.functions.borrowRatePerBlock().call(block_identifier=block_num)
        assert borrow_rate_per_blcok == expected_rate_per_block


def test_venus_calculate_mean(venus_wbnb_token: VenusToken):
    json_rpc_url = os.environ["BNB_CHAIN_JSON_RPC"]
    session = requests.Session()

    start_block = 22629320
    end_block =   22639420

    fetch_events_to_csv(json_rpc_url,
                        JSONFileScanState("/tmp/test_venus_calculate_mean.log"),
                        start_block=start_block,
                        end_block=end_block,
                        output_folder="/tmp")

    df = load_accrue_interest_event_dataframe(dirname="/tmp", filename="venus-accrueinterest.csv")
    assert len(df) == 680
    assert df.iloc[0]['block_number'] == 22629321
    assert df.iloc[0]['tx_hash'] == "0xc409991514aff4ae68f94dbce4496b0dcaac70741c23c2f1cb53f51cd23fc97d"
    assert df.iloc[0]['token'] == "WBNB"

    assert df.iloc[-1]['block_number'] == 22639411
    assert df.iloc[-1]['tx_hash']== "0xb2711a8c7285cb684ca39ad8ddd8e2b5ecaea1d6362595b1ae6a7dab182f1608"
    assert df.iloc[-1]['token']== "USDT"

    rates_df = venus_calculate_apr_apy_rates(df)

    mean_rates_df = venus_calculate_mean(rates_df, '1D', ['deposit_apr', 'borrow_apr'], token='WBNB')
    assert mean_rates_df.loc['2022-10-30','borrow_apr'] == pytest.approx(1.9210414834638212, rel=1e-6)

    mean_rates_df = venus_calculate_mean(rates_df, '1D', 'borrow_apr', token='WBNB')
    assert mean_rates_df.loc['2022-10-30'] == pytest.approx(1.9210414834638212, rel=1e-6)

    interest = venus_calculate_accrued_interests(df, datetime.datetime(2022,10,30,18,0,0), datetime.datetime(2022,10,31,1,0,0), Decimal(1), 'WBNB')
    assert interest.deposit_interest == pytest.approx(Decimal(0.000014251501809496980583061), rel=Decimal(1e-2))
