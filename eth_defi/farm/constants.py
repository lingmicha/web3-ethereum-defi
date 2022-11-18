
from typing import NamedTuple
from eth_typing import ChecksumAddress
from web3 import Web3
from decimal import Decimal


class Pool(NamedTuple):
    name: str
    address: ChecksumAddress
    decimal: Decimal
    pid: int


class Farm(NamedTuple):
    network: str
    protocol: str
    address: ChecksumAddress
    abi: str
    pools: dict[str, Pool]


FARMS = {
    'bsc-pancakeswap': Farm(
        network='bsc',
        protocol='pancakeswap',
        address=Web3.toChecksumAddress("0xa5f8C5Dbd5F286960b9d90548680aE5ebFf07652"),
        abi="pancakeswap/MasterChefV2.json",
        pools={
            "BUSD-WBNB": Pool(name="BUSD-WBNB",
                             address=Web3.toChecksumAddress("0x58F876857a02D6762E0101bb5C46A8c1ED44Dc16"),
                             decimal=Decimal(10**18),
                             pid=3),
            "CAKE-WBNB": Pool(name="CAKE-WBNB",
                             address=Web3.toChecksumAddress("0x0eD7e52944161450477ee417DE9Cd3a859b14fD0"),
                             decimal=Decimal(10**18),
                             pid=2),
            "CAKE-BUSD": Pool(name="CAKE-BUSD",
                              address=Web3.toChecksumAddress("0x804678fa97d91B974ec2af3c843270886528a9E6"),
                              decimal=Decimal(10**18),
                              pid=39),
            "CAKE-USDT": Pool(name="CAKE-USDT",
                              address=Web3.toChecksumAddress("0xA39Af17CE4a8eb807E076805Da1e2B8EA7D0755b"),
                              decimal=Decimal(10**18),
                              pid=47),
            "USDT-BUSD": Pool(name="USDT-BUSD",
                              address=Web3.toChecksumAddress("0x7EFaEf62fDdCCa950418312c6C91Aef321375A00"),
                              decimal=Decimal(10**18),
                              pid=7),
            "LINK-WBNB": Pool(name="LINK-WBNB",
                             address=Web3.toChecksumAddress("0x824eb9faDFb377394430d2744fa7C42916DE3eCe"),
                             decimal=Decimal(10**18),
                             pid=6),
            "ETH-USDC": Pool(name="ETH-USDC",
                             address=Web3.toChecksumAddress("0x2E8135bE71230c6B1B4045696d41C09Db0414226"),
                             decimal=Decimal(10**18),
                             pid=124),
            "ETH-USDT": Pool(name="ETH-USDT",
                             address=Web3.toChecksumAddress("0x17C1Ae82D99379240059940093762c5e4539aba5"),
                             decimal=Decimal(10**18),
                             pid=125),
            "WBTC-ETH": Pool(name="WBTC-ETH",
                             address=Web3.toChecksumAddress("0x4AB6702B3Ed3877e9b1f203f90cbEF13d663B0e8"),
                             decimal=Decimal(10**18),
                             pid=126),
        },
    )
}

FARM_MARKET_CHAINS: dict[int, str] = {
    56: 'bsc',
    66: 'oec',
}


def get_farm(chain_id: int, protocol: str) -> Farm:
    if chain_id not in FARM_MARKET_CHAINS:
        raise ValueError(f'Unsupported chain id: {chain_id}')
    network_slug = FARM_MARKET_CHAINS[chain_id]
    farm = FARMS[network_slug + '-' + protocol.lower()]
    return farm


