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
from pandas import DataFrame
from decimal import Decimal

from eth_defi.abi import get_deployed_contract
from eth_defi.event_reader.fast_json_rpc import patch_web3
from eth_defi.venus.constants import (
    VENUS_NETWORKS,
    VenusToken, VenusNetwork,
    venus_get_network_by_chain_id,
    VenusInterestModelParameters,
    venus_get_token_name_by_deposit_address
)
from eth_defi.venus.rates import venus_get_interest_model_parameters

logger = logging.getLogger(__name__)


pytestmark = pytest.mark.skipif(
    os.environ.get("BNB_CHAIN_JSON_RPC") is None,
    reason="Set BNB_CHAIN_JSON_RPC environment variable to BSC mainnet node to run this test",
)


def test_model_parameters_equality():
    """测试VenusInterestModelParameters __eq__ override
    """
    params_1 = VenusInterestModelParameters(
        reserve_factor=Decimal(0.2),
        kink=Decimal(600000000000000000),
        base_rate_per_block=Decimal(1902587519),
        multiplier_per_block=Decimal(14269406392),
        jump_multiplier_per_block=Decimal(285388127853)
    )

    params_2 = VenusInterestModelParameters(
        reserve_factor=Decimal(0.200000001),
        kink=Decimal(600000000000000000),
        base_rate_per_block=Decimal(1902587519),
        multiplier_per_block=Decimal(14269406392),
        jump_multiplier_per_block=Decimal(285388127853)
    )

    params_3 = VenusInterestModelParameters(
        reserve_factor=Decimal(0.200001),
        kink=Decimal(600000000000000000),
        base_rate_per_block=Decimal(1902587519),
        multiplier_per_block=Decimal(14269406392),
        jump_multiplier_per_block=Decimal(285388127853)
    )

    assert params_1 == params_2, "等于符号无作用"
    assert params_1 != params_3, "等于符号无作用"


def test_model_parameters():
    """Read events quickly over JSON-RPC API."""

    # HTTP 1.1 keep-alive
    session = requests.Session()

    json_rpc_url = os.environ["BNB_CHAIN_JSON_RPC"]
    web3 = Web3(HTTPProvider(json_rpc_url, session=session))

    # Enable faster ujson reads
    patch_web3(web3)

    web3.middleware_onion.clear()

    network = venus_get_network_by_chain_id(56)

    for venus_token in network.token_contracts.values():#[network.token_contracts["XVS"]]
        model_parameters_on_chain = venus_get_interest_model_parameters(web3, venus_token)
        logger.info("{}:{}".format(venus_get_token_name_by_deposit_address(venus_token.deposit_address), model_parameters_on_chain))
        assert model_parameters_on_chain == venus_token.model.params, \
             "{}:链上和配置文件的参数不同".format(venus_get_token_name_by_deposit_address(venus_token.deposit_address))


def test_model_rate_calculation():
    # HTTP 1.1 keep-alive
    session = requests.Session()

    json_rpc_url = os.environ["BNB_CHAIN_JSON_RPC"]
    web3 = Web3(HTTPProvider(json_rpc_url, session=session))

    # Enable faster ujson reads
    patch_web3(web3)

    web3.middleware_onion.clear()
    block_number = web3.eth.get_block_number()
    logger.info("Current Block Number: {}".format(block_number))

    network = venus_get_network_by_chain_id(56)
    venus_token = network.token_contracts['BUSD'] # JumpRateModel
    model = venus_token.model
    contract = get_deployed_contract(web3, "venus/VBep20.json", venus_token.deposit_address)

    # 监控的事件发生时，都会引起利率变化，所以要记录此区块的利率、借款、存款利息等信息
    borrow_rate_per_block = contract.functions.borrowRatePerBlock().call(block_identifier=block_number) # 2957813543
    borrow_rate = Decimal(borrow_rate_per_block) / Decimal(10**18)
    supply_rate_per_block = contract.functions.supplyRatePerBlock().call(block_identifier=block_number) # 174984816
    supply_rate = Decimal(supply_rate_per_block) / Decimal(10**18)

    total_supply = contract.functions.totalSupply().call(block_identifier=block_number)  # 209539053430583173
    supply = Decimal(total_supply) / Decimal(10**8)
    exchange_rate = contract.functions.exchangeRateStored().call(block_identifier=block_number)
    exchange_rate = Decimal(exchange_rate) / Decimal(10**28)
    supply = exchange_rate * supply

    total_borrow = contract.functions.totalBorrows().call(block_identifier=block_number)  # 3124653038953932474258414
    borrows = Decimal(total_borrow) / Decimal(10**18)
    total_reserve = contract.functions.totalReserves().call(block_identifier=block_number)  # 1951135653323763085666
    reserves = Decimal(total_reserve) / Decimal(10**18)
    cash = contract.functions.getCash().call(block_identifier=block_number) # 39130751880398368732080648
    cash = Decimal(cash) / Decimal(10**18)

    utilization = model.utilization_rate(cash, borrows, reserves)
    borrow_rate_model = model.borrow_rate_per_block(cash, borrows, reserves)
    supply_rate_model = model.supply_rate_per_block(cash, borrows, reserves)

    logger.info("Current Utilization:{:.4f}".format(utilization))
    logger.info("Exchange Rate():{:.4f}".format(exchange_rate))
    logger.info("Supply:{:.4f}, Borrow:{:.4f}, Reserve:{:.4f}, Cash:{:.4f}".format(supply, borrows, reserves, cash))
    logger.info("Model Return: Borrow Rate:{:.4e}, Supply Rate:{:.4e}".format(borrow_rate_model, supply_rate_model))
    logger.info("On Chain Data: Borrow Rate:{:.4e}, Supply Rate:{:.4e}".format(borrow_rate, supply_rate))

    assert borrow_rate_model == pytest.approx(borrow_rate, rel=Decimal(1e-6))
    assert supply_rate_model == pytest.approx(supply_rate, rel=Decimal(1e-6))




