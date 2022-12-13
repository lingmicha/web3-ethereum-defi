
from typing import NamedTuple, Union
from eth_typing import ChecksumAddress, HexAddress
from web3 import Web3
from decimal import Decimal


class Pool(NamedTuple):
    name: str
    address: ChecksumAddress
    decimals: Decimal
    pid: int


class Reward(NamedTuple):
    name: str
    address: ChecksumAddress
    decimals: Decimal


class Farm(NamedTuple):
    network: str
    chain_id: int
    protocol: str
    address: ChecksumAddress
    abi: str
    reward: Reward
    pools: dict[str, Pool]


FARMS = {
    'bsc-pancake_farm': Farm(
        network='bsc',
        chain_id=56,
        protocol='pancake_farm',
        address=Web3.to_checksum_address("0xa5f8C5Dbd5F286960b9d90548680aE5ebFf07652"),
        abi="pancakeswap/MasterChefV2.json",
        reward=Reward(
            name='CAKE',
            address=Web3.to_checksum_address("0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82"),
            decimals=18,
        ),
        pools={
            "CAKE": Pool(name="CAKE", #Cake池是单币质押，但是cake pool需要处理boost等复杂情况
                         address=Web3.to_checksum_address("0x45c54210128a065de780c4b0df3d16664f7f859e"),
                         decimals=18,
                         pid=0),
            "WBNB-BUSD": Pool(name="WBNB-BUSD",
                             address=Web3.to_checksum_address("0x58F876857a02D6762E0101bb5C46A8c1ED44Dc16"),
                             decimals=18,
                             pid=3),
            "CAKE-WBNB": Pool(name="CAKE-WBNB",
                             address=Web3.to_checksum_address("0x0eD7e52944161450477ee417DE9Cd3a859b14fD0"),
                             decimals=18,
                             pid=2),
            "CAKE-BUSD": Pool(name="CAKE-BUSD",
                              address=Web3.to_checksum_address("0x804678fa97d91B974ec2af3c843270886528a9E6"),
                              decimals=18,
                              pid=39),
            "CAKE-USDT": Pool(name="CAKE-USDT",
                              address=Web3.to_checksum_address("0xA39Af17CE4a8eb807E076805Da1e2B8EA7D0755b"),
                              decimals=18,
                              pid=47),
            "USDT-BUSD": Pool(name="USDT-BUSD",
                              address=Web3.to_checksum_address("0x7EFaEf62fDdCCa950418312c6C91Aef321375A00"),
                              decimals=18,
                              pid=7),
            "LINK-WBNB": Pool(name="LINK-WBNB",
                             address=Web3.to_checksum_address("0x824eb9faDFb377394430d2744fa7C42916DE3eCe"),
                             decimals=18,
                             pid=6),
            "ETH-USDC": Pool(name="ETH-USDC",
                             address=Web3.to_checksum_address("0x2E8135bE71230c6B1B4045696d41C09Db0414226"),
                             decimals=18,
                             pid=124),
            "ETH-USDT": Pool(name="ETH-USDT",
                             address=Web3.to_checksum_address("0x17C1Ae82D99379240059940093762c5e4539aba5"),
                             decimals=18,
                             pid=125),
            "WBTC-ETH": Pool(name="WBTC-ETH",
                             address=Web3.to_checksum_address("0x4AB6702B3Ed3877e9b1f203f90cbEF13d663B0e8"),
                             decimals=18,
                             pid=126),
        },
    )
}

FARM_MARKET_CHAINS: dict[int, str] = {
    56: 'bsc',
    66: 'oec',
}

POOL_BY_POOL_ADDRESS: dict[HexAddress, Pool] = {}


def get_farm(chain_id: int, protocol: str) -> Farm:
    if chain_id not in FARM_MARKET_CHAINS:
        raise ValueError(f'Unsupported chain id: {chain_id}')
    network_slug = FARM_MARKET_CHAINS[chain_id]
    farm = FARMS[network_slug + '-' + protocol.lower()]
    return farm


def get_farm_by_staking_contract_address(address: HexAddress) -> Union[None, Farm]:

    for (name, farm) in FARMS.items():
        if farm.address == Web3.to_checksum_address(address):
            return farm

    return None

def get_pool_by_pool_address(address: HexAddress) -> Union[None, Pool]:

    return POOL_BY_POOL_ADDRESS.get(Web3.to_checksum_address(address))



def get_pool_by_id(farm: Farm, pid: int) -> Union[None, Pool]:
    pools = farm.pools
    for pool in pools.values():
        if pool.pid == pid:
            return pool
    return None


def _init_pool_by_pool_address():
    for (farm_name, farm) in FARMS.items():
        for (pool_name, pool) in farm.pools.items():
            POOL_BY_POOL_ADDRESS[pool.address] = pool


_init_pool_by_pool_address()