"""
    支持异步请求
"""
import asyncio
from web3 import Web3
from typing import Union
from eth_typing import HexAddress

from eth_defi.abi import get_deployed_contract
from eth_defi.token_async import fetch_erc20_details
from eth_defi.event_reader.logresult import LogContext
from eth_defi.uniswap_v2.pair import PairDetails


class PairCache(LogContext):
    """ 避免重复获取币对信息
    """

    def __init__(self):
        self.cache = {}

    async def get_pair_info(self, web3: Web3, pair_contact_address: Union[str, HexAddress]) -> PairDetails:
        pair_contact_address = Web3.to_checksum_address(pair_contact_address)

        if pair_contact_address in self.cache:
            return self.cache[pair_contact_address]

        pair = await fetch_pair_details(web3, pair_contact_address)
        self.cache[pair_contact_address] = pair
        return pair


async def fetch_pair_details(web3: Web3, pair_contact_address: Union[str, HexAddress]) -> PairDetails:
    """Get pair info for PancakeSwap, others.

    :param web3:
        async Web3 instance

    :param pair_contact_address:
        Smart contract address of trading pair

    """
    assert web3.eth.is_async, "只支持异步RPC"
    pair_contact_address = Web3.to_checksum_address(pair_contact_address)
    pool = get_deployed_contract(web3, "UniswapV2Pair.json", pair_contact_address)

    (token0_address, token1_address) = await asyncio.gather(
        *[pool.functions.token0().call(), pool.functions.token1().call()]
    )

    (token0, token1) = await asyncio.gather(
        fetch_erc20_details(web3, token0_address),
        fetch_erc20_details(web3, token1_address))

    return PairDetails(pool.address, token0, token1)



