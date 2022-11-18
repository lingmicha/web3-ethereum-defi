import logging
import pytest
import os
from web3 import HTTPProvider, Web3
from decimal import Decimal
from eth_defi.event_reader.web3factory import TunedWeb3Factory
from eth_defi.farm.rewards import get_farm_reward, FarmReward
from eth_defi.farm.constants import Pool, get_farm, Farm
from eth_defi.ganache import fork_network
from eth_defi.abi import get_deployed_contract

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.skipif(
    os.environ.get("BNB_CHAIN_JSON_RPC") is None,
    reason="Set BNB_CHAIN_JSON_RPC environment variable to BSC mainnet node to run this test",
)

@pytest.fixture(scope="module")
def ganache_bnb_chain_fork() -> str:
    """Create a testable fork of live BNB chain.

    :return: JSON-RPC URL for Web3
    """
    mainnet_rpc = os.environ["BNB_CHAIN_JSON_RPC"]
    launch = fork_network(mainnet_rpc+ "@23018713", port=19997)
    yield launch.json_rpc_url
    # Wind down Ganache process after the test is complete
    launch.close()


@pytest.fixture
def web3(ganache_bnb_chain_fork: str):
    """Set up a local unit testing blockchain."""
    # https://web3py.readthedocs.io/en/stable/examples.html#contract-unit-tests-in-python
    return Web3(HTTPProvider(ganache_bnb_chain_fork))


@pytest.fixture(scope="module")
def pancake_farm() -> Farm:
    farm = get_farm(56, 'pancakeswap')
    return farm


@pytest.fixture(scope="module")
def pancake_wbnb_busd_pool(pancake_farm: Farm) -> Pool:
    pool = pancake_farm.pools['BUSD-WBNB']
    return pool


def test_pending_rewards_calculation(web3: Web3, pancake_farm: Farm, pancake_wbnb_busd_pool: Pool):
    account = Web3.toChecksumAddress("0xded08eFB71AbCc782A86D53a43731C77CA1250Cf")
    contract = get_deployed_contract(web3, pancake_farm.abi, pancake_farm.address)

    pending_rewards = contract.functions.pendingCake(pancake_wbnb_busd_pool.pid, account).call()
    pending_rewards = pending_rewards/Decimal(10**18)

    (amount, reward_debt, boost_multiplier) = contract.functions.userInfo(pancake_wbnb_busd_pool.pid, account).call()
    lp_balance = Decimal(amount) / pancake_wbnb_busd_pool.decimal

    (acc_cake_per_share, _, alloc_point, _, _,) = contract.functions.poolInfo(pancake_wbnb_busd_pool.pid).call()
    calc_rewards = (Decimal(acc_cake_per_share) * lp_balance - Decimal(reward_debt))/pancake_wbnb_busd_pool.decimal
    assert pending_rewards == pytest.approx(calc_rewards, rel=Decimal(1e-3))


def test_get_farm_reward(web3: Web3, pancake_farm: Farm, pancake_wbnb_busd_pool: Pool):
    account = Web3.toChecksumAddress("0xded08eFB71AbCc782A86D53a43731C77CA1250Cf")
    reward = get_farm_reward(web3, pancake_farm, 'BUSD-WBNB', account)
    expected_reward = FarmReward(
        name='BUSD-WBNB',
        pool_address=Web3.toChecksumAddress('0x58F876857a02D6762E0101bb5C46A8c1ED44Dc16'),
        lp_balance=Decimal('123.979989960873820619'),
        pending_reward=Decimal('5.625266848109961534'),
    )
    assert reward == expected_reward

