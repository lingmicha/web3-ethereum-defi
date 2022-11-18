
from typing import NamedTuple
from eth_typing import ChecksumAddress
from web3 import Web3
from decimal import Decimal
from eth_defi.abi import get_deployed_contract
from eth_defi.farm.constants import Farm


class FarmReward(NamedTuple):
    name: str
    pool_address: ChecksumAddress
    lp_balance: Decimal
    pending_reward: Decimal


def get_farm_reward(web3: Web3, farm: Farm, pool_name: str, account_address: str) -> FarmReward:

    pool = farm.pools[pool_name]
    contract = get_deployed_contract(web3, farm.abi, farm.address)

    if farm.protocol == 'pancakeswap':
        pending_reward = contract.functions.pendingCake(pool.pid, account_address).call()
        pending_reward = Decimal(pending_reward) / Decimal(10**18) # Cake
    else:
        raise NotImplementedError("{} reward call not supported".format(farm.protocol))

    (amount, reward_debt, boost_multiplier) = contract.functions.userInfo(pool.pid, account_address).call()
    lp_balance = Decimal(amount) / pool.decimal

    # (acc_cake_per_share, _, alloc_point, _, _,) = contract.functions.poolInfo(pool.pid).call()
    # assert pending_reward == (acc_cake_per_share * lp_balance - reward_debt)/pool.decimal

    return FarmReward(
        name=pool.name,
        pool_address=pool.address,
        lp_balance=lp_balance,
        pending_reward=pending_reward,
    )

