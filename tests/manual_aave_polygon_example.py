"""A sample script to manually operate aave on polygon.

"""

from web3 import Web3, HTTPProvider
from eth_defi.abi import get_deployed_contract
from eth_defi.aave_v3.balances import aave_v3_get_deposit_balance, aave_v3_get_variable_borrow_balance, aave_v3_get_stable_borrow_balance
from eth_defi.aave_v3.constants import AaveNetwork, AaveToken, aave_v3_get_network_by_chain_id

node = "https://polygon-mainnet.g.alchemy.com/v2/H3E99oH7XymptRueBxkO4OXXazhFb7_c"


web3 = Web3(HTTPProvider(node))
print(f"{node} current block is {web3.eth.block_number:,}")

aave_network = aave_v3_get_network_by_chain_id(137)
aave_token = aave_network.token_contracts['DAI']

address_does_not_exist = Web3.toChecksumAddress("0x6564b5053C381a8D840B40d78bA229e2d8e912ed")

# ValueError: {'code': -32000, 'message': 'exceed maximum block range: 5000'}
balances = aave_v3_get_deposit_balance(web3,  aave_token.deposit_address, address_does_not_exist)
print("Empty", balances)

# https://polygonscan.com/address/0x5b8effbdae5941b938c1a79616d185cc3c79d4ff
some_large_holder = Web3.toChecksumAddress("0x5b8effbdae5941b938c1a79616d185cc3c79d4ff")
balances = aave_v3_get_deposit_balance(web3, aave_token.deposit_address, some_large_holder)
print("Large ADAI holder", balances)

# https://polygonscan.com/address/0x2f74bd41940a188eb8d0fd0d5a6e92e93ec7a4a8
some_large_holder = Web3.toChecksumAddress("0x2f74bd41940a188eb8d0fd0d5a6e92e93ec7a4a8")
aave_token = aave_network.token_contracts['DAI']
balances = aave_v3_get_stable_borrow_balance(web3, Web3.toChecksumAddress(aave_token.stable_borrow_address), some_large_holder)
print("Large stableDebtPolDAI holder", balances)

some_large_holder = Web3.toChecksumAddress("0x5b8effbdae5941b938c1a79616d185cc3c79d4ff")
aave_token = aave_network.token_contracts['EURS']
balances = aave_v3_get_variable_borrow_balance(web3, Web3.toChecksumAddress(aave_token.variable_borrow_address), some_large_holder)
print("Large variableDebtPolEURS holder", balances)

# https://polygonscan.com/address/0xd1802c153fa2ae751ac7526419c4500fa8025c1e
some_large_holder = Web3.toChecksumAddress("0xd1802c153fa2ae751ac7526419c4500fa8025c1e")
aave_token = aave_network.token_contracts['EURS']
balances = aave_v3_get_stable_borrow_balance(web3, Web3.toChecksumAddress(aave_token.stable_borrow_address), some_large_holder)
print("Large stableDebtPolEURS holder", balances)

# grab balance for a particular block number
some_large_holder = Web3.toChecksumAddress("0x5b8effbdae5941b938c1a79616d185cc3c79d4ff")
aave_token = aave_network.token_contracts['DAI']
AToken = get_deployed_contract(web3, "aave_v3/AToken.json", aave_token.deposit_address)
balances = AToken.functions.balanceOf(some_large_holder).call(block_identifier=34581440)
decimals = AToken.functions.decimals().call(block_identifier=34581440)
print("Large ADAI holder at block '{}':{}".format(34581440, balances * pow(10, -decimals)))
