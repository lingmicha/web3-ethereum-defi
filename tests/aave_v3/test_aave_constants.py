import pytest
from eth_defi.aave_v3.constants import aave_v3_get_network_by_chain_id, aave_v3_get_token_name_by_deposit_address


def test_aave_v3_get_network_by_chain_id():
    aave_network = aave_v3_get_network_by_chain_id(137) # polygon
    assert aave_network.name == 'Polygon', "错误的网络名称"
    assert aave_network.pool_address == '0x794a61358D6845594F94dc1DB02A252b5b4814aD', "错误的pool address"

def test_aave_v3_get_token_name_by_deposit_address():
    deposit_address = "0xf329e36C7bF6E5E86ce2150875a84Ce77f477375"
    token_name = aave_v3_get_token_name_by_deposit_address(deposit_address)
    assert token_name == "AAVE", "错误的代币名称查找"
