"""A sample script to manually operate venus on bsc.

"""

from web3 import Web3, HTTPProvider
from eth_defi.venus.balances import venus_get_deposit_balance, venus_get_borrow_balance
from eth_defi.venus.constants import venus_get_network_by_chain_id

node = "https://bsc-dataseed.binance.org"

web3 = Web3(HTTPProvider(node))
print(f"{node} current block is {web3.eth.block_number:,}")

venus_network = venus_get_network_by_chain_id(56)
venus_busd_token = venus_network.token_contracts['BUSD']
venus_usdt_token = venus_network.token_contracts['USDT']
venus_wbnb_token = venus_network.token_contracts['WBNB']


address_does_not_exist = Web3.toChecksumAddress("0x6564b5053C381a8D840B40d78bA229e2d8e912ed")
balances = venus_get_deposit_balance(web3,  venus_busd_token, Web3.toChecksumAddress(address_does_not_exist))
print("Empty BUSD Deposit", balances)

balances = venus_get_borrow_balance(web3, venus_busd_token, Web3.toChecksumAddress(address_does_not_exist))
print("Empty Borrow", balances)


holder = Web3.toChecksumAddress("0xded08eFB71AbCc782A86D53a43731C77CA1250Cf")
balances = venus_get_deposit_balance(web3,  venus_busd_token, Web3.toChecksumAddress(holder))
print("Large BUSD Deposit", balances)

balances = venus_get_borrow_balance(web3, venus_usdt_token, Web3.toChecksumAddress(holder))
print("Large USDT Borrow", balances)

holder = Web3.toChecksumAddress("0xfde64760370ad58805900a3e23a1ebeeae9fba2c")
balances = venus_get_deposit_balance(web3, venus_wbnb_token, Web3.toChecksumAddress(holder))
print("Large WBNB Deposit", balances)


