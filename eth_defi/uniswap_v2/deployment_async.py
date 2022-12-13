from web3 import Web3
from eth_defi.uniswap_v2.deployment import UniswapV2Deployment
from eth_defi.abi import get_contract, get_deployed_contract
from typing import Union
from eth_typing import HexAddress

async def fetch_deployment(
    web3: Web3,
    factory_address: Union[HexAddress, str],
    router_address: Union[HexAddress, str],
    init_code_hash: Optional[Union[HexStr, str]] = None,
) -> UniswapV2Deployment:
    """Construct Uniswap deployment based on on-chain data.

    Fetches init code hash from on-chain.

    Factory does not know about routers, so they must be explicitly given.

    `Read more details here <https://ethereum.stackexchange.com/questions/76334/what-is-the-difference-between-bytecode-init-code-deployed-bytedcode-creation>`_.

    Example how to get PancakeSwap v2 deployment:

    .. code-block:: python

        @pytest.fixture()
        def pancakeswap_v2(web3) -> UniswapV2Deployment:
            deployment = fetch_deployment(
                web3,
                "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73",
                "0x10ED43C718714eb63d5aA57B78B54704E256024E",
                # Taken from https://bscscan.com/address/0xca143ce32fe78f1f7019d7d551a6402fc5350c73#readContract
                init_code_hash="0x00fb7f630766e6a796048ea87d01acd3068e8ff67d078148a3fa3f4a84f69bd5",
                )
            return deployment

    :param init_code_hash: Read init code hash from the caller. If not given call `pairCodeHash` (SushiSwap) on the factory.
    """
    factory = get_deployed_contract(web3, "UniswapV2Factory.json", factory_address)
    # https://github.com/sushiswap/sushiswap/blob/4fdfeb7dafe852e738c56f11a6cae855e2fc0046/contracts/uniswapv2/UniswapV2Factory.sol#L26
    if init_code_hash is None:
        init_code_hash = await factory.functions.pairCodeHash().call().hex()
    router = get_deployed_contract(web3, "UniswapV2Router02.json", router_address)
    # https://github.com/sushiswap/sushiswap/blob/4fdfeb7dafe852e738c56f11a6cae855e2fc0046/contracts/uniswapv2/UniswapV2Router02.sol#L17
    weth_address = await router.functions.WETH().call()
    weth = get_deployed_contract(web3, "WETH9Mock.json", weth_address)
    PairContract = get_contract(web3, "UniswapV2Pair.json")
    return UniswapV2Deployment(
        web3,
        factory,
        weth,
        router,
        init_code_hash,
        PairContract,
    )

