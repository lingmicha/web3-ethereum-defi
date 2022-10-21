"""Venus constants."""
import json
import os
from typing import NamedTuple, Optional

# Deployed Contracts on BSC:
# https://github.com/VenusProtocol/venus-config/blob/master/networks/mainnet.json

class VenusNetwork(NamedTuple):
    # Network name
    name: str

    # Address of the Unitroller (risk management) contract
    unitroller_address: str

    # Token contract information
    token_contracts: dict[str, 'VenusToken']


class VenusToken(NamedTuple):
    # Address of the token contract
    token_address: str

    # Address of the vToken (deposit) contract
    deposit_address: str

    # Block number when the token was created
    token_created_at_block: int


# Map chain identifiers to Venus network parameters - autodetect parameters based on the Web3 provider's chain id
# Note that the pool addresses are proxy addresses, not the actual contract addresses (but you can use them with the contract ABI)

VENUS_NETWORK_CHAINS: dict[int, str] = {
    56: 'bsc',
}

# Note that in Polygon, Aave v2 sends identical ReserveDataUpdated events from contract 0x8dff5e27ea6b7ac08ebfdf9eb090f32ee9a30fcf,
# while we are watching v3 events from contract 0x794a61358D6845594F94dc1DB02A252b5b4814aD only. So we need to filter events by
# the pool_address configured here.

VENUS_NETWORKS: dict[str, VenusNetwork] = {
    # bsc Mainnet
    'bsc': VenusNetwork(
        name='bsc',
        unitroller_address='0xfD36E2c2a6789Db23113685031d7F16329158384',
        #pool_address='0x794a61358D6845594F94dc1DB02A252b5b4814aD',
        #pool_created_at_block=25826028,
        token_contracts={
            # Venus token contracts defined in the BSC network
            'SXP': VenusToken(
                token_address='0x47BEAd2563dCBf3bF2c9407fEa4dC236fAbA485A',
                deposit_address='0x2fF3d0F6990a40261c66E1ff2017aCBc282EB6d0',
                token_created_at_block=2472901),
            'USDC': VenusToken(
                token_address='0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d',
                deposit_address='0xecA88125a5ADbe82614ffC12D0DB554E2e2867C8',
                token_created_at_block=2472670),
            'USDT': VenusToken(
                token_address='0x55d398326f99059fF775485246999027B3197955',
                deposit_address='0xfD5840Cd36d94D7229439859C0112a4185BC0255',
                token_created_at_block=2472804),
            'BUSD': VenusToken(
                token_address='0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56',
                deposit_address='0x95c78222B3D6e262426483D42CfA53685A67Ab9D',
                token_created_at_block=2472859),
            'XVS': VenusToken(
                token_address='0xcF6BB5389c92Bdda8a3747Ddb454cB7a64626C63',
                deposit_address='0x151B1e2635A717bcDc836ECd6FbB62B674FE3E1D',
                token_created_at_block=2472959),
            'BTC': VenusToken(
                token_address='0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c',
                deposit_address='0x882C173bC7Ff3b7786CA16dfeD3DFFfb9Ee7847B',
                token_created_at_block=2795150),
            'ETH': VenusToken(
                token_address='0x2170Ed0880ac9A755fd29B2688956BD959F933F8',
                deposit_address='0xf508fCD89b8bd15579dc79A6827cB4686A3592c8',
                token_created_at_block=2795451),
            'LTC': VenusToken(
                token_address='0x4338665CBB7B2485A8855A139b75D5e34AB0DB94',
                deposit_address='0x57A5297F2cB2c0AaC9D554660acd6D385Ab50c6B',
                token_created_at_block=2795531),
            'XRP': VenusToken(
                token_address='0x1D2F0da169ceB9fC7B3144628dB156f3F6c60dBE',
                deposit_address='0xB248a295732e0225acd3337607cc01068e3b9c10',
                token_created_at_block=2795586),
            'WBNB': VenusToken(
                token_address='',
                deposit_address='0xA07c5b74C9B40447a954e1466938b865b6BBea36',
                token_created_at_block=2473058),
            # TUSD TRX MATIC LINK FIL DOT DOGE DAI CAKE BETH BCH ADA AAVE
            'BCH': VenusToken(
                token_address='0x8ff795a6f4d97e7887c79bea79aba5cc76444adf',
                deposit_address='0x5f0388ebc2b94fa8e123f404b79ccf5f40b29176',
                token_created_at_block=3081065),
            'DOT': VenusToken(
                token_address='0x7083609fce4d1d8dc0c979aab8c869ea2c873402',
                deposit_address='0x1610bc33319e9398de5f57b33a5b184c806ad217',
                token_created_at_block=3081164),
            'LINK': VenusToken(
                token_address='0xf8a0bf9cf54bb92f17374d9e9a321e6a111a51bd',
                deposit_address='0x650b940a1033b8a1b1873f78730fcfc73ec11f1f',
                token_created_at_block=3081198),
            'DAI': VenusToken(
                token_address='0x1af3f329e8be154074d8769d1ffa4ee058b1dbc3',
                deposit_address='0x334b3ecb4dca3593bccc3c7ebd1a1c1d1780fbf1',
                token_created_at_block=3744996),
            'FIL': VenusToken(
                token_address='0x0d8ce2a99bb6e3b7db580ed848240e4a0f9ae153',
                deposit_address='0xf91d58b5ae142dacc749f58a49fcbac340cb0343',
                token_created_at_block=3745901),
            'BETH': VenusToken(
                token_address='0x250632378e573c6be1ac2f97fcdf00515d0aa91b',
                deposit_address='0x972207a639cc1b374b893cc33fa251b55ceb7c07',
                token_created_at_block=3883997),
            'CAN': VenusToken(
                token_address='0x20bff4bbeda07536ff00e073bd8359e5d80d733d',
                deposit_address='0xebd0070237a0713e8d94fef1b728d3d993d290ef',
                token_created_at_block=3966503),
            'ADA': VenusToken(
                token_address='0x3ee2200efb3400fabb9aacf31297cbdd1d435d47',
                deposit_address='0x9a0af7fdb2065ce470d72664de73cae409da28ec',
                token_created_at_block=4976416),
            'DOGE': VenusToken(
                token_address='0xba2ae424d960c26247dd6c32edc70b295c744c43',
                deposit_address='0xec3422ef92b2fb59e84c8b02ba73f1fe84ed8d71',
                token_created_at_block=6773712),
            'MATIC': VenusToken(
                token_address='0xcc42724c6683b7e57334c4e856f4c9965ed682bd',
                deposit_address='0x5c9476fcd6a4f9a3654139721c949c2233bbbbc8',
                token_created_at_block=8996895),
            'CAKE': VenusToken(
                token_address='0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82',
                deposit_address='0x86ac3974e2bd0d60825230fa6f355ff11409df5c',
                token_created_at_block=9505961),
            'AAVE': VenusToken(
                token_address='0xfb6115445bff7b52feb98650c87f44907e58f802',
                deposit_address='0x26da28954763b92139ed49283625cecaf52c6f94',
                token_created_at_block=10562515),
            'TUSD': VenusToken(
                token_address='0x14016e85a25aeb13065688cafb43044c2ef86784',
                deposit_address='0x08ceb3f4a7ed3500ca0982bcd0fc7816688084c3',
                token_created_at_block=10865315),
            'TRX': VenusToken(
                token_address='0x85eac5ac2f758618dfa09bdbe0cf174e7d574d5b',
                deposit_address='0x61edcfe8dd6ba3c891cb9bec2dc7657b3b422e93',
                token_created_at_block=12766328),
        },
    ),
}

VENUS_DEPOSIT_ADDRESS_TOKENS: dict[str, str] = {}  # autofill later


# Helper functions for reading JSON-RPC URLs and account addresses from an optional aave.json file.
# If you use it (instead of entering the values interactively), it should look like this:
# {
#   "json_rpc_url": "https://address-to-your-json-rpc-server,
#   "account_address": "address-of-your-account"
# }


def venus_get_json_rpc_url() -> Optional[str]:
    # Allow configuring the JSON-RPC URL via aave.json in current directory
    # If not present, user will be asked to input the URL
    if os.path.exists('./aave.json'):
        aave_config = json.load(open('./aave.json'))
        return aave_config['json_rpc_url']


def venus_get_account_address() -> Optional[str]:
    # Allow configuring an account address via aave.json in current directory
    # If not present, user will be asked to input the account
    if os.path.exists('./aave.json'):
        aave_config = json.load(open('./aave.json'))
        return aave_config['account_address']


def venus_get_network_by_chain_id(chain_id: int) -> VenusNetwork:
    # Auto-detect the network based on the chain id
    if chain_id not in VENUS_NETWORK_CHAINS:
        raise ValueError(f'Unsupported chain id: {chain_id}')
    network_slug = VENUS_NETWORK_CHAINS[chain_id]
    venus_network = VENUS_NETWORKS[network_slug]
    return venus_network


def venus_get_token_name_by_deposit_address(deposit_address: str) -> Optional[str]:
    # Get a token name by the AToken deposit contract address
    return VENUS_DEPOSIT_ADDRESS_TOKENS.get(deposit_address, None)


def _autofill_token_addresses():
    for network in VENUS_NETWORKS.values():
        for token_name, token in network.token_contracts.items():
            VENUS_DEPOSIT_ADDRESS_TOKENS[token.deposit_address] = token_name


# Initialization
_autofill_token_addresses()
