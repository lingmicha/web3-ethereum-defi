"""Fast event reading.

For manual tests see `scripts/read-uniswap-v2-pairs-and-swaps.py`.

.. code-block:: shell

    # Ethereum JSON-RPC
    export JSON_RPC_URL=
    pytest -k test_revert_reason

"""

import os

import pytest
import requests
from requests.adapters import HTTPAdapter
from web3 import HTTPProvider, Web3

from eth_defi.abi import get_contract
from eth_defi.event_reader.fast_json_rpc import patch_web3
from eth_defi.event_reader.logresult import LogContext, LogResult
from eth_defi.event_reader.reader import read_events, read_events_concurrent
from eth_defi.event_reader.web3factory import TunedWeb3Factory
from eth_defi.event_reader.web3worker import create_thread_pool_executor
from eth_defi.token import TokenDetails, fetch_erc20_details

from eth_defi.venus.balances import get_venus_deployed_contract
from eth_defi.venus.constants import VenusToken,VenusNetwork, venus_get_network_by_chain_id, VENUS_NETWORKS
from eth_defi.venus.events import TokenCache, decode_events
from eth_defi.event_reader.reader import prepare_filter

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
        venus_token.events.Mint,
        venus_token.events.Redeem,
        venus_token.events.Borrow,
        venus_token.events.LiquidateBorrow,
        venus_token.events.RepayBorrow,
    ]

    addresses = [t.deposit_address for t in VENUS_NETWORKS['bsc'].token_contracts.values()]
    flter = prepare_filter(events)
    flter.contract_address = addresses

    token_cache = TokenCache()

    start_block = 22629320
    end_block = 22652473  #

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
        extract_timestamps=None,
        filter=flter,
    ):
        out.append(decode_events(log_result))

    assert len(out) == 1890

    e = out[0]
    assert e["block_number"] == 22629321
    assert e["tx_hash"] == "0xc409991514aff4ae68f94dbce4496b0dcaac70741c23c2f1cb53f51cd23fc97d"
    assert e["log_index"] == 199
    assert e['token_name'] == 'WBNB'
    assert e["deposit_address"] == Web3.toChecksumAddress("0xa07c5b74c9b40447a954e1466938b865b6bbea36")
    assert e["minter_address"] == Web3.toChecksumAddress("0x5efA1e46F4Fd738FF721F5AebC895b970F13E8A1")

    e = out[1]
    assert e["block_number"] == 22629324
    assert e["tx_hash"] == "0x19f46db89417848ad21127c073db0debe4ef6dc821d0e9b6f82cdb555a02f3d8"
    assert e["log_index"] == 128
    assert e['token_name'] == 'WBNB'
    assert e["deposit_address"] == Web3.toChecksumAddress("0xa07c5b74c9b40447a954e1466938b865b6bbea36")
    assert e["minter_address"] == Web3.toChecksumAddress("0x340d2d57941C213B7B97EE2DdDc6dAFeB73c4672")

    e = out[1889]
    assert e["block_number"] == 22652462
    assert e["tx_hash"] == "0xf9bdb09e2ba28af8baecda74b94795306633d25275650949a2c9dbd665480897"
    assert e["log_index"] == 285
    assert e['token_name'] == 'ETH'
    assert e["deposit_address"] == Web3.toChecksumAddress("0xf508fcd89b8bd15579dc79a6827cb4686a3592c8")
    assert e["minter_address"] == Web3.toChecksumAddress("0x30cc8552FAD6a705bbf543744746bEC4B2FdE2dd")

# def test_read_events_concurrent():
#     """Read events quickly over JSON-RPC API using a thread pool."""
#
#     json_rpc_url = os.environ["JSON_RPC_URL"]
#     token_cache = TokenCache()
#     threads = 16
#     http_adapter = HTTPAdapter(pool_connections=threads, pool_maxsize=threads)
#     web3_factory = TunedWeb3Factory(json_rpc_url, http_adapter)
#     web3 = web3_factory(token_cache)
#     executor = create_thread_pool_executor(web3_factory, token_cache, max_workers=threads)
#
#     # Get contracts
#     Factory = get_contract(web3, "UniswapV2Factory.json")
#
#     events = [
#         Factory.events.PairCreated,  # https://etherscan.io/txs?ea=0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f&topic0=0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9
#     ]
#
#     start_block = 10_000_835  # Uni deployed
#     end_block = 10_009_000  # The first pair created before this block
#
#     # Read through the blog ran
#     out = []
#     for log_result in read_events_concurrent(
#         executor,
#         start_block,
#         end_block,
#         events,
#         None,
#         chunk_size=100,
#         context=token_cache,
#         extract_timestamps=None,
#     ):
#         out.append(decode_pair_created(log_result))
#
#     assert len(out) == 2
#
#     e = out[0]
#     assert e["pair_count_index"] == 1
#     assert e["pair_contract_address"] == "0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc"
#     assert e["token1_symbol"] == "WETH"
#     assert e["token0_symbol"] == "USDC"
#     assert e["tx_hash"] == "0xd07cbde817318492092cc7a27b3064a69bd893c01cb593d6029683ffd290ab3a"
#
#     e = out[1]
#     assert e["pair_count_index"] == 2
#     assert e["token1_symbol"] == "USDC"
#     assert e["token0_symbol"] == "USDP"
#     assert e["tx_hash"] == "0xb0621ca74cee9f540dda6d575f6a7b876133b42684c1259aaeb59c831410ccb2"
