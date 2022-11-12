import os
import json
from typing import Optional


# Helper functions for reading JSON-RPC URLs and account addresses from an optional defi_lending.json file.
# If you use it (instead of entering the values interactively), it should look like this:
# {
#   "json_rpc_url": "https://address-to-your-json-rpc-server,
#   "account_address": "address-of-your-account"
# }
def get_json_rpc_url() -> Optional[str]:
    # Allow configuring the JSON-RPC URL via aave.json in current directory
    # If not present, user will be asked to input the URL
    if os.path.exists('./defi_lending.json'):
        _config = json.load(open('./defi_lending.json'))
        return _config['json_rpc_url']


def get_account_address() -> Optional[str]:
    # Allow configuring an account address via aave.json in current directory
    # If not present, user will be asked to input the account
    if os.path.exists('./defi_lending.json'):
        _config = json.load(open('./defi_lending.json'))
        return _config['account_address']
