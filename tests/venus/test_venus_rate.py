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
from eth_defi.venus.events import (
    TokenCache,
    decode_accrue_interest_events,
    fetch_events_to_dataframe
)
from eth_defi.venus.rates import (
    venus_calculate_mean_return,
    venus_calculate_per_block_return,
    venus_calculate_accrued_interests,
)

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


def test_calc_rates_using_index(web3:Web3, venus_wbnb_token: VenusToken):
    '''使用index来计算区块间的利率    
    '''
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

    vbnb = get_deployed_contract(web3, "venus/VBep20.json",
                                 Web3.toChecksumAddress(venus_wbnb_token.deposit_address))

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


def test_rates_between_events(web3:Web3, venus_busd_token: VenusToken):
    """测试events之间应该保持稳定的量：
        borrowRatePerBlock
        supplyRatePerBlock
        borrowIndex: 是在操作前 accrueInterest时改变
        totalReserves
        getCash
        totalSupply : vtoken的发行量不变
        totalBorrows: 不包含未清算的利息，只包含从上一次event结算后的借款总额

       测试events之间应该逐渐增加的量：
        totalBorrowsCurrent： 根据区块累积的借款总额
    """

    # start_block ~ end_block -1 的rates_per_block应该保持不变
    # event1: 22874730  https://bscscan.com/tx/0x42a56b081ec2891a96997a9d53d4ad2348cf1e6d154af08ef974964488199585
    # event2: 22874909  https://bscscan.com/tx/0x40e1d4981e9229611cb03cb7f2e07e9b3fcf28013a2bc45ccfdffd2e52116a15
    start_block = 22874730
    end_block = 22874909

    vbusd = get_deployed_contract(web3, "venus/VBep20.json", Web3.toChecksumAddress(venus_busd_token.deposit_address))

    expected_borrow_rate_per_block = 3526766426
    expected_supply_rate_per_block = 2353484014
    expected_borrow_index = 1125635097345409073
    expected_reserves = 50722071475979816838305
    expected_cash = 42458063558393209309333572
    expected_total_supply = 755417266606227251
    expected_total_borrows = 121623566598004872301632790
    for block_num in range(start_block, end_block+1):
        logger.info("开始测试events之间保持不变的量。block number:{} ".format(block_num))
        borrow_rate_per_blcok = vbusd.functions.borrowRatePerBlock().call(block_identifier=block_num)
        supply_rate_per_block = vbusd.functions.supplyRatePerBlock().call(block_identifier=block_num)
        borrow_index = vbusd.functions.borrowIndex().call(block_identifier=block_num)
        reserves = vbusd.functions.totalReserves().call(block_identifier=block_num)
        total_supply = vbusd.functions.totalSupply().call(block_identifier=block_num)
        total_borrows = vbusd.functions.totalBorrows().call(block_identifier=block_num)
        cash = vbusd.functions.getCash().call(block_identifier=block_num)
        if block_num != end_block:
            assert borrow_rate_per_blcok == expected_borrow_rate_per_block
            assert supply_rate_per_block == expected_supply_rate_per_block
            assert borrow_index == expected_borrow_index
            assert reserves == expected_reserves
            assert total_supply == expected_total_supply
            assert total_borrows == expected_total_borrows
            assert cash == expected_cash
        else:
            assert borrow_rate_per_blcok != expected_borrow_rate_per_block
            assert supply_rate_per_block != expected_supply_rate_per_block
            assert borrow_index != expected_borrow_index
            assert reserves != expected_reserves
            assert total_supply != expected_total_supply
            assert total_borrows != expected_total_borrows
            assert cash != expected_cash

    expected_total_borrows_current = 0
    for block_num in range(start_block-1, end_block):
        logger.info("开始测试events直接逐渐增加的量。block number:{} ".format(block_num))
        total_borrows_current = vbusd.functions.totalBorrowsCurrent().call(block_identifier=block_num)
        #logger.info("total_borrows_current:{}".format(total_borrows_current))
        assert total_borrows_current > expected_total_borrows_current
        expected_total_borrows_current = total_borrows_current


def test_venus_calculate_mean_return(web3:Web3, venus_wbnb_token: VenusToken):
    json_rpc_url = os.environ["BNB_CHAIN_JSON_RPC"]

    start_block = 22629320 #
    end_block = 22639420 #

    df = fetch_events_to_dataframe(json_rpc_url,
                        JSONFileScanState("/tmp/test_venus_calculate_mean_return/scanstate.log"),
                        start_block=start_block,
                        end_block=end_block,
                        output_folder="/tmp/test_venus_calculate_mean_return")

    assert len(df) == 680
    assert df.iloc[0]['block_number'] == 22629321
    assert df.iloc[0]['tx_hash'] == "0xc409991514aff4ae68f94dbce4496b0dcaac70741c23c2f1cb53f51cd23fc97d"
    assert df.iloc[0]['token'] == "WBNB"

    assert df.iloc[-1]['block_number'] == 22639411
    assert df.iloc[-1]['tx_hash']== "0xb2711a8c7285cb684ca39ad8ddd8e2b5ecaea1d6362595b1ae6a7dab182f1608"
    assert df.iloc[-1]['token']== "USDT"

    mean_rates_df = venus_calculate_mean_return(df, '1D', ['deposit_apr', 'borrow_apr'], token='WBNB')
    assert mean_rates_df.loc['2022-10-30', 'borrow_apr'] == pytest.approx(1.9210414834638212, rel=1e-6)

    mean_rates_df = venus_calculate_mean_return(df, '1D', 'borrow_apr', token='WBNB')
    assert mean_rates_df.loc['2022-10-30', 'borrow_apr'] == pytest.approx(1.9210414834638212, rel=1e-6)


def test_venus_calculate_accrued_interests(venus_wbnb_token: VenusToken):

    json_rpc_url = os.environ["BNB_CHAIN_JSON_RPC"]

    start_block = 22629320  #
    end_block = 22639420  #
    amount = Decimal(100)

    df = fetch_events_to_dataframe(json_rpc_url,
                                   JSONFileScanState("/tmp/test_venus_calculate_mean_return/scanstate.log"),
                                   start_block=start_block,
                                   end_block=end_block,
                                   output_folder="/tmp/test_venus_calculate_mean_return")

    interest = venus_calculate_accrued_interests(df,
                                                 datetime.datetime(2022,10,30,17,43,9),
                                                 datetime.datetime(2022,10,31,1,28,45),
                                                 amount,
                                                 'WBNB')

    ## 把平均利率的计算结果和使用borrowIndex计算结果相比较
    # 起始：block_number:22629321  block_time:2022-10-30 17:43:09  borrow_index:1174708111983875926
    # 结束：block_number:22638543  block_time:2022-10-31 01:28:45  borrow_index:1174727930902663238
    start_borrow_index = Decimal(1174708111983875926)
    end_borrow_index = Decimal(1174727930902663238)
    borrow_scaled_amount = amount / start_borrow_index
    borrow_final_amount = borrow_scaled_amount * end_borrow_index
    expected_borrow_interest = borrow_final_amount - amount

    assert interest.borrow_interest == \
           pytest.approx(expected_borrow_interest, rel=Decimal(1e-2))
