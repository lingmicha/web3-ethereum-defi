"""
    定义compound v2的常量，目前支持
        1. Venus ( BSC )
        2. Wepiggy ( BSC, OEC )

    Venus Deployed Contracts on BSC:
    https://github.com/VenusProtocol/venus-config/blob/master/networks/mainnet.json

"""
from decimal import Decimal
from typing import NamedTuple, Optional
from web3 import Web3
from eth_typing import ChecksumAddress, HexAddress
from web3.contract import Contract

from eth_defi.defi_lending.interest_model import (
    InterestModelParameters,
    InterestModel,
    SimpleInterestModel,
    JumpInterestModel,
)


class LendingMarket(NamedTuple):
    # Chain name
    network: str

    # Protocol name
    protocol: str

    abi: str

    # Address of the Unitroller (risk management) contract
    #unitroller_address: ChecksumAddress

    # Token contract information
    token_contracts: dict[str, 'LendingToken']


class LendingToken(NamedTuple):

    # Token Name
    name: str

    # Address of the token contract
    token_address: ChecksumAddress

    # Address of the vToken (deposit) contract
    deposit_address: ChecksumAddress

    # Interest Model Address
    model_address: ChecksumAddress

    # Interst Model Parameters
    model: InterestModel

    # Block number when the token was created
    token_created_at_block: int


class VenusToken(LendingToken):
    # default VenusToken ABI file
    abi = 'venus/VBep20.json'


class WepiggyToken(LendingToken):
    # default VenusToken ABI file
    abi = 'wepiggy/PERC20.json'


LENDING_NETWORK_CHAINS: dict[int, str] = {
    56: 'bsc',
    66: 'oec',
    57: 'bsc', # 测试用途
}


LENDING_MARKETS: dict[str, LendingMarket] = {
    # Venus on bsc Mainnet
    'bsc-venus': LendingMarket(
        network='bsc',
        protocol='venus',
        abi='venus/VBep20.json',
        #unitroller_address=Web3.to_checksum_address('0xfD36E2c2a6789Db23113685031d7F16329158384'),
        token_contracts={
            # Venus token contracts defined in the BSC network
            'SXP': VenusToken(
                name="SXP",
                token_address=Web3.to_checksum_address('0x47BEAd2563dCBf3bF2c9407fEa4dC236fAbA485A'),
                deposit_address=Web3.to_checksum_address('0x2fF3d0F6990a40261c66E1ff2017aCBc282EB6d0'),
                model_address=Web3.to_checksum_address('0x32450305D6c692269B3cBf9730d99104f80fce23'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.2'),
                                                              kink=Decimal('0.6'),
                                                              base_rate_per_block=Decimal('1.902587519E-9'),
                                                              multiplier_per_block=Decimal('1.4269406392E-8'),
                                                              jump_multiplier_per_block=Decimal('2.85388127853E-7'))),
                token_created_at_block=2472901),
            'USDC': VenusToken(
                name="USDC",
                token_address=Web3.to_checksum_address('0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d'),
                deposit_address=Web3.to_checksum_address('0xecA88125a5ADbe82614ffC12D0DB554E2e2867C8'),
                model_address=Web3.to_checksum_address('0x9E47C4F8654EDFb45bc81E7E320c8fC1AD0aCB73'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.1'),
                                                              kink=Decimal('0.8'),
                                                              base_rate_per_block=Decimal('0'),
                                                              multiplier_per_block=Decimal('4.756468797E-9'),
                                                              jump_multiplier_per_block=Decimal('1.03691019786E-7'))),
                token_created_at_block=2472670),
            'USDT': VenusToken(
                name="USDT",
                token_address=Web3.to_checksum_address('0x55d398326f99059fF775485246999027B3197955'),
                deposit_address=Web3.to_checksum_address('0xfD5840Cd36d94D7229439859C0112a4185BC0255'),
                model_address=Web3.to_checksum_address('0x9E47C4F8654EDFb45bc81E7E320c8fC1AD0aCB73'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.1'),
                                                              kink=Decimal('0.8'),
                                                              base_rate_per_block=Decimal('0'),
                                                              multiplier_per_block=Decimal('4.756468797E-9'),
                                                              jump_multiplier_per_block=Decimal('1.03691019786E-7'))),
                token_created_at_block=2472804),
            'BUSD': VenusToken(
                name="BUSD",
                token_address=Web3.to_checksum_address('0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56'),
                deposit_address=Web3.to_checksum_address('0x95c78222B3D6e262426483D42CfA53685A67Ab9D'),
                model_address=Web3.to_checksum_address('0x9E47C4F8654EDFb45bc81E7E320c8fC1AD0aCB73'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.1'),
                                                              kink=Decimal('0.8'),
                                                              base_rate_per_block=Decimal('0'),
                                                              multiplier_per_block=Decimal('4.756468797E-9'),
                                                              jump_multiplier_per_block=Decimal('1.03691019786E-7'))),
                token_created_at_block=2472859),
            'XVS': VenusToken(
                name="XVS",
                token_address=Web3.to_checksum_address('0xcF6BB5389c92Bdda8a3747Ddb454cB7a64626C63'),
                deposit_address=Web3.to_checksum_address('0x151B1e2635A717bcDc836ECd6FbB62B674FE3E1D'),
                model_address=Web3.to_checksum_address('0xa166Ca91a570747708a318A771F0C9AB84DD984b'),
                model=SimpleInterestModel(InterestModelParameters(reserve_factor=Decimal('0.25'),
                                                                                kink=Decimal('0'),
                                                                                base_rate_per_block=Decimal('0'),
                                                                                multiplier_per_block=Decimal('2.28310502283E-7'),
                                                                                jump_multiplier_per_block=Decimal('0'))),
                token_created_at_block=2472959),
            'BTC': VenusToken(
                name="BTC",
                token_address=Web3.to_checksum_address('0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c'),
                deposit_address=Web3.to_checksum_address('0x882C173bC7Ff3b7786CA16dfeD3DFFfb9Ee7847B'),
                model_address=Web3.to_checksum_address('0x8683B97aA8eA1f5a0d65CDBA6FA78782Aa77C193'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.2'),
                                                                          kink=Decimal('0.75'),
                                                                          base_rate_per_block=Decimal('0'),
                                                                          multiplier_per_block=Decimal('1.2052891933E-8'),
                                                                          jump_multiplier_per_block=Decimal('1.90258751902E-7'))),
                token_created_at_block=2795150),
            'ETH': VenusToken(
                name='ETH',
                token_address=Web3.to_checksum_address('0x2170Ed0880ac9A755fd29B2688956BD959F933F8'),
                deposit_address=Web3.to_checksum_address('0xf508fCD89b8bd15579dc79A6827cB4686A3592c8'),
                model_address=Web3.to_checksum_address('0x8683B97aA8eA1f5a0d65CDBA6FA78782Aa77C193'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.2'),
                                                                          kink=Decimal('0.75'),
                                                                          base_rate_per_block=Decimal('0'),
                                                                          multiplier_per_block=Decimal('1.2052891933E-8'),
                                                                          jump_multiplier_per_block=Decimal('1.90258751902E-7'))),
                token_created_at_block=2795451),
            'LTC': VenusToken(
                name='LTC',
                token_address=Web3.to_checksum_address('0x4338665CBB7B2485A8855A139b75D5e34AB0DB94'),
                deposit_address=Web3.to_checksum_address('0x57A5297F2cB2c0AaC9D554660acd6D385Ab50c6B'),
                model_address=Web3.to_checksum_address('0x32450305D6c692269B3cBf9730d99104f80fce23'),
                model=JumpInterestModel(InterestModelParameters(
                    reserve_factor=Decimal(0.2),
                    kink=Decimal(600000000000000000) / Decimal(10 ** 18),
                    base_rate_per_block=Decimal(1902587519) / Decimal(10 ** 18),
                    multiplier_per_block=Decimal(14269406392) / Decimal(10 ** 18),
                    jump_multiplier_per_block=Decimal(285388127853) / Decimal(10 ** 18),
                )),
                token_created_at_block=2795531),
            'XRP': VenusToken(
                name='XRP',
                token_address=Web3.to_checksum_address('0x1D2F0da169ceB9fC7B3144628dB156f3F6c60dBE'),
                deposit_address=Web3.to_checksum_address('0xB248a295732e0225acd3337607cc01068e3b9c10'),
                model_address=Web3.to_checksum_address('0x32450305D6c692269B3cBf9730d99104f80fce23'),
                model=JumpInterestModel(InterestModelParameters(
                    reserve_factor=Decimal(0.2),
                    kink=Decimal(600000000000000000) / Decimal(10 ** 18),
                    base_rate_per_block=Decimal(1902587519) / Decimal(10 ** 18),
                    multiplier_per_block=Decimal(14269406392) / Decimal(10 ** 18),
                    jump_multiplier_per_block=Decimal(285388127853) / Decimal(10 ** 18),
                )),
                token_created_at_block=2795586),
            'WBNB': VenusToken(
                name='WBNB',
                token_address=Web3.to_checksum_address('0xA000000000000000000000000000000000000000'),
                deposit_address=Web3.to_checksum_address('0xA07c5b74C9B40447a954e1466938b865b6BBea36'),
                model_address=Web3.to_checksum_address('0x1ba3cc62DEe8556433EFB23F946Ab7d6482BBB57'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.2'),
                                                                          kink=Decimal('0.75'),
                                                                          base_rate_per_block=Decimal('0'),
                                                                          multiplier_per_block=Decimal('1.1415525114E-8'),
                                                                          jump_multiplier_per_block=Decimal('1.90258751902E-7'))),
                token_created_at_block=2473058),
            'BCH': VenusToken(
                name='BCH',
                token_address=Web3.to_checksum_address('0x8ff795a6f4d97e7887c79bea79aba5cc76444adf'),
                deposit_address=Web3.to_checksum_address('0x5f0388ebc2b94fa8e123f404b79ccf5f40b29176'),
                model_address=Web3.to_checksum_address('0x32450305D6c692269B3cBf9730d99104f80fce23'),
                model=JumpInterestModel(InterestModelParameters(
                    reserve_factor=Decimal(0.2),
                    kink=Decimal(600000000000000000) / Decimal(10 ** 18),
                    base_rate_per_block=Decimal(1902587519) / Decimal(10 ** 18),
                    multiplier_per_block=Decimal(14269406392) / Decimal(10 ** 18),
                    jump_multiplier_per_block=Decimal(285388127853) / Decimal(10 ** 18),
                )),
                token_created_at_block=3081065),
            'DOT': VenusToken(
                name='DOT',
                token_address=Web3.to_checksum_address('0x7083609fce4d1d8dc0c979aab8c869ea2c873402'),
                deposit_address=Web3.to_checksum_address('0x1610bc33319e9398de5f57b33a5b184c806ad217'),
                model_address=Web3.to_checksum_address('0x89fb915EaFf2D449Cb1Bd0Ea7963142481D16652'),
                model=JumpInterestModel(InterestModelParameters(
                    reserve_factor=Decimal(0.2),
                    kink=Decimal(600000000000000000) / Decimal(10 ** 18),
                    base_rate_per_block=Decimal(1902587519) / Decimal(10 ** 18),
                    multiplier_per_block=Decimal(14269406392) / Decimal(10 ** 18),
                    jump_multiplier_per_block=Decimal(285388127853) / Decimal(10 ** 18),
                )),
                token_created_at_block=3081164),
            'LINK': VenusToken(
                name='LINK',
                token_address=Web3.to_checksum_address('0xf8a0bf9cf54bb92f17374d9e9a321e6a111a51bd'),
                deposit_address=Web3.to_checksum_address('0x650b940a1033b8a1b1873f78730fcfc73ec11f1f'),
                model_address=Web3.to_checksum_address('0x32450305D6c692269B3cBf9730d99104f80fce23'),
                model=JumpInterestModel(InterestModelParameters(
                    reserve_factor=Decimal(0.2),
                    kink=Decimal(600000000000000000) / Decimal(10 ** 18),
                    base_rate_per_block=Decimal(1902587519) / Decimal(10 ** 18),
                    multiplier_per_block=Decimal(14269406392) / Decimal(10 ** 18),
                    jump_multiplier_per_block=Decimal(285388127853) / Decimal(10 ** 18),
                )),
                token_created_at_block=3081198),
            'DAI': VenusToken(
                name='DAI',
                token_address=Web3.to_checksum_address('0x1af3f329e8be154074d8769d1ffa4ee058b1dbc3'),
                deposit_address=Web3.to_checksum_address('0x334b3ecb4dca3593bccc3c7ebd1a1c1d1780fbf1'),
                model_address=Web3.to_checksum_address('0x9E47C4F8654EDFb45bc81E7E320c8fC1AD0aCB73'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.1'),
                                                                          kink=Decimal('0.8'),
                                                                          base_rate_per_block=Decimal('0'),
                                                                          multiplier_per_block=Decimal('4.756468797E-9'),
                                                                          jump_multiplier_per_block=Decimal('1.03691019786E-7'))),
                token_created_at_block=3744996),
            'FIL': VenusToken(
                name='FIL',
                token_address=Web3.to_checksum_address('0x0d8ce2a99bb6e3b7db580ed848240e4a0f9ae153'),
                deposit_address=Web3.to_checksum_address('0xf91d58b5ae142dacc749f58a49fcbac340cb0343'),
                model_address=Web3.to_checksum_address('0xB8760Bc1391ab0E729cff04871DA131ba2949d41'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.2'),
                                                                          kink=Decimal('0.5'),
                                                                          base_rate_per_block=Decimal('1.902587519E-9'),
                                                                          multiplier_per_block=Decimal('1.902587519E-8'),
                                                                          jump_multiplier_per_block=Decimal('2.85388127853E-7'))),
                token_created_at_block=3745901),
            'BETH': VenusToken(
                name='BETH',
                token_address=Web3.to_checksum_address('0x250632378e573c6be1ac2f97fcdf00515d0aa91b'),
                deposit_address=Web3.to_checksum_address('0x972207a639cc1b374b893cc33fa251b55ceb7c07'),
                model_address=Web3.to_checksum_address('0xEa464DfB1B0BB8964c250427bb5B0DD4f315141A'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal(0.2),
                                                                kink=Decimal(600000000000000000) / Decimal(10 ** 18),
                                                                base_rate_per_block=Decimal(0) / Decimal(10 ** 18),
                                                                multiplier_per_block=Decimal(14269406392) / Decimal(10 ** 18),
                                                                jump_multiplier_per_block=Decimal(285388127853) / Decimal(10 ** 18),
                )),
                token_created_at_block=3883997),
            'CAN': VenusToken(
                name='CAN',
                token_address=Web3.to_checksum_address('0x20bff4bbeda07536ff00e073bd8359e5d80d733d'),
                deposit_address=Web3.to_checksum_address('0xebd0070237a0713e8d94fef1b728d3d993d290ef'),
                model_address=Web3.to_checksum_address('0x49fADE95f94e5EC7C1f4AE13a6d6f9ca18B2F430'),
                model=SimpleInterestModel(InterestModelParameters(reserve_factor=Decimal('0'),
                                                                                kink=Decimal('0'),
                                                                                base_rate_per_block=Decimal('1.902587519E-9'),
                                                                                multiplier_per_block=Decimal('9.512937595E-9'),
                                                                                jump_multiplier_per_block=Decimal('0'))),
                token_created_at_block=3966503),
            'ADA': VenusToken(
                name='ADA',
                token_address=Web3.to_checksum_address('0x3ee2200efb3400fabb9aacf31297cbdd1d435d47'),
                deposit_address=Web3.to_checksum_address('0x9a0af7fdb2065ce470d72664de73cae409da28ec'),
                model_address=Web3.to_checksum_address('0x32450305d6c692269b3cbf9730d99104f80fce23'),
                model=JumpInterestModel(InterestModelParameters(
                    reserve_factor=Decimal(0.2),
                    kink=Decimal(600000000000000000) / Decimal(10 ** 18),
                    base_rate_per_block=Decimal(1902587519) / Decimal(10 ** 18),
                    multiplier_per_block=Decimal(14269406392) / Decimal(10 ** 18),
                    jump_multiplier_per_block=Decimal(285388127853) / Decimal(10 ** 18),
                )),
                token_created_at_block=4976416),
            'DOGE': VenusToken(
                name='DOGE',
                token_address=Web3.to_checksum_address('0xba2ae424d960c26247dd6c32edc70b295c744c43'),
                deposit_address=Web3.to_checksum_address('0xec3422ef92b2fb59e84c8b02ba73f1fe84ed8d71'),
                model_address=Web3.to_checksum_address('0xB8760Bc1391ab0E729cff04871DA131ba2949d41'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.2'),
                                                                          kink=Decimal('0.5'),
                                                                          base_rate_per_block=Decimal('1.902587519E-9'),
                                                                          multiplier_per_block=Decimal('1.902587519E-8'),
                                                                          jump_multiplier_per_block=Decimal('2.85388127853E-7'))),
                token_created_at_block=6773712),
            'MATIC': VenusToken(
                name='MATIC',
                token_address=Web3.to_checksum_address('0xcc42724c6683b7e57334c4e856f4c9965ed682bd'),
                deposit_address=Web3.to_checksum_address('0x5c9476fcd6a4f9a3654139721c949c2233bbbbc8'),
                model_address=Web3.to_checksum_address('0xC6F3f4D5421E70CB6C32C7402E51C8894A40F29a'),
                model=JumpInterestModel(InterestModelParameters(
                    reserve_factor=Decimal(0.2),
                    kink=Decimal(600000000000000000) / Decimal(10 ** 18),
                    base_rate_per_block=Decimal(1902587519) / Decimal(10 ** 18),
                    multiplier_per_block=Decimal(14269406392) / Decimal(10 ** 18),
                    jump_multiplier_per_block=Decimal(285388127853) / Decimal(10 ** 18),
                )),
                token_created_at_block=8996895),
            'CAKE': VenusToken(
                name='CAKE',
                token_address=Web3.to_checksum_address('0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82'),
                deposit_address=Web3.to_checksum_address('0x86ac3974e2bd0d60825230fa6f355ff11409df5c'),
                model_address=Web3.to_checksum_address('0xC6F3f4D5421E70CB6C32C7402E51C8894A40F29a'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.25'),
                                                                          kink=Decimal('0.6'),
                                                                          base_rate_per_block=Decimal('1.902587519E-9'),
                                                                          multiplier_per_block=Decimal('1.4269406392E-8'),
                                                                          jump_multiplier_per_block=Decimal('2.85388127853E-7'))),
                token_created_at_block=9505961),
            'AAVE': VenusToken(
                name='AAVE',
                token_address=Web3.to_checksum_address('0xfb6115445bff7b52feb98650c87f44907e58f802'),
                deposit_address=Web3.to_checksum_address('0x26da28954763b92139ed49283625cecaf52c6f94'),
                model_address=Web3.to_checksum_address('0x637e19b6EE87758506d6eA34bF11BE8F43AD8d61'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.25'),
                                                                          kink=Decimal('0.5'),
                                                                          base_rate_per_block=Decimal('0'),
                                                                          multiplier_per_block=Decimal('1.902587519E-8'),
                                                                          jump_multiplier_per_block=Decimal('2.85388127853E-7'))),
                token_created_at_block=10562515),
            'TUSD': VenusToken(
                name='TUSD',
                token_address=Web3.to_checksum_address('0x14016e85a25aeb13065688cafb43044c2ef86784'),
                deposit_address=Web3.to_checksum_address('0x08ceb3f4a7ed3500ca0982bcd0fc7816688084c3'),
                model_address=Web3.to_checksum_address('0x1ee6f0F68A2D028230d4609Ee58D77f521dFf3c9'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.2'),
                                                                          kink=Decimal('0.8'),
                                                                          base_rate_per_block=Decimal('0'),
                                                                          multiplier_per_block=Decimal('4.756468797E-9'),
                                                                          jump_multiplier_per_block=Decimal('1.03691019786E-7'))),
                token_created_at_block=10865315),
            'TRX': VenusToken(
                name='TRX',
                token_address=Web3.to_checksum_address('0x85eac5ac2f758618dfa09bdbe0cf174e7d574d5b'),
                deposit_address=Web3.to_checksum_address('0x61edcfe8dd6ba3c891cb9bec2dc7657b3b422e93'),
                model_address=Web3.to_checksum_address('0x8B831e2c6f184F552Fb4c2CB7c01Ff76FeC93881'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.2'),
                                                                          kink=Decimal('0.6'),
                                                                          base_rate_per_block=Decimal('1.902587519E-9'),
                                                                          multiplier_per_block=Decimal('1.4269406392E-8'),
                                                                          jump_multiplier_per_block=Decimal('2.85388127853E-7'))),
                token_created_at_block=12766328),
        },
    ),

    # Wepiggy on bsc Mainnet
    'bsc-wepiggy': LendingMarket(
        network='bsc',
        protocol='wepiggy',
        abi='wepiggy/IPToken.json',
        token_contracts={
            # WePiggy BSC 合约地址： https://www.yuque.com/zgryhn/kgrqd1/fcf9ag
            'WBNB': WepiggyToken(
                name='WBNB',
                token_address=Web3.to_checksum_address('0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c'),
                deposit_address=Web3.to_checksum_address('0x33A32f0ad4AA704e28C93eD8Ffa61d50d51622a7'),
                model_address=Web3.to_checksum_address('0x621ce6596e0b9ccf635316bfe7fdbc80c3029bec'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.25'),
                                                                kink=Decimal('0.8'),
                                                                base_rate_per_block=Decimal('1.902587519E-9'),
                                                                multiplier_per_block=Decimal('3.3295281582E-8'),
                                                                jump_multiplier_per_block=Decimal('5.70776255707E-7'))),
                token_created_at_block=7533478),
            'ETH': WepiggyToken(
                name='ETH',
                token_address=Web3.to_checksum_address('0x2170Ed0880ac9A755fd29B2688956BD959F933F8'),
                deposit_address=Web3.to_checksum_address('0x849C37A029B38D3826562697Ccc40c34477C6293'),
                model_address=Web3.to_checksum_address('0xd1121ade04ee215524aefbf7f8d45029214d668d'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.2'),
                                                                kink=Decimal('0.65'),
                                                                base_rate_per_block=Decimal('0'),
                                                                multiplier_per_block=Decimal('1.1708230886E-8'),
                                                                jump_multiplier_per_block=Decimal('2.71798217003E-7'))),
                token_created_at_block=7533491),
            'BTC': WepiggyToken(
                name='BTC',
                token_address=Web3.to_checksum_address('0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c'),
                deposit_address=Web3.to_checksum_address('0x311aEA58Ca127B955890647413846E351df32554'),
                model_address=Web3.to_checksum_address('0xd1121ade04ee215524aefbf7f8d45029214d668d'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.2'),
                                                                kink=Decimal('0.65'),
                                                                base_rate_per_block=Decimal('0'),
                                                                multiplier_per_block=Decimal('1.1708230886E-8'),
                                                                jump_multiplier_per_block=Decimal('2.71798217003E-7'))),
                token_created_at_block=7533500),
            'DAI': WepiggyToken(
                name='DAI',
                token_address=Web3.to_checksum_address('0x1AF3F329e8BE154074D8769D1FFa4eE058B1DBc3'),
                deposit_address=Web3.to_checksum_address('0x12D803497D1e58dD4D4A4F455D754f1d0F937C8b'),
                model_address=Web3.to_checksum_address('0xc1b02e52e9512519edf99671931772e452fb4399'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.1'),
                                                                kink=Decimal('0.8'),
                                                                base_rate_per_block=Decimal('0'),
                                                                multiplier_per_block=Decimal('4.756468797E-9'),
                                                                jump_multiplier_per_block=Decimal('3.56735159817E-7'))),
                token_created_at_block=7533507),
            'USDT': WepiggyToken(
                name='USDT',
                token_address=Web3.to_checksum_address('0x55d398326f99059fF775485246999027B3197955'),
                deposit_address=Web3.to_checksum_address('0x2a8Cd78bFb91ACF53f589961D213d87c956e0d7f'),
                model_address=Web3.to_checksum_address('0xc1b02e52e9512519edf99671931772e452fb4399'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.1'),
                                                               kink=Decimal('0.8'),
                                                               base_rate_per_block=Decimal('0'),
                                                               multiplier_per_block=Decimal('4.756468797E-9'),
                                                               jump_multiplier_per_block=Decimal('3.56735159817E-7'))),
                token_created_at_block=7533514),
            'USDC': WepiggyToken(
                name='USDC',
                token_address=Web3.to_checksum_address('0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d'),
                deposit_address=Web3.to_checksum_address('0x2B7F68170a598E507B19Bca41ED745eABc936B3F'),
                model_address=Web3.to_checksum_address('0xc1b02e52e9512519edf99671931772e452fb4399'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.1'),
                                                               kink=Decimal('0.8'),
                                                               base_rate_per_block=Decimal('0'),
                                                               multiplier_per_block=Decimal('4.756468797E-9'),
                                                               jump_multiplier_per_block=Decimal('3.56735159817E-7'))),
                token_created_at_block=7533522),
            'BUSD': WepiggyToken(
                name='BUSD',
                token_address=Web3.to_checksum_address('0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56'),
                deposit_address=Web3.to_checksum_address('0x2dd8FFA7923a17739F70C34759Af7650e44EA3BE'),
                model_address=Web3.to_checksum_address('0xc1b02e52e9512519edf99671931772e452fb4399'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.1'),
                                                               kink=Decimal('0.8'),
                                                               base_rate_per_block=Decimal('0'),
                                                               multiplier_per_block=Decimal('4.756468797E-9'),
                                                               jump_multiplier_per_block=Decimal('3.56735159817E-7'))),
                token_created_at_block=7533528),
            'DOT': WepiggyToken(
                name='DOT',
                token_address=Web3.to_checksum_address('0x7083609fCE4d1d8Dc0C979AAb8c869Ea2C873402'),
                deposit_address=Web3.to_checksum_address('0x811Cd5CB4cC43F44600Cfa5eE3F37a402C82aec2'),
                model_address=Web3.to_checksum_address('0x621ce6596e0b9ccf635316bfe7fdbc80c3029bec'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.25'),
                                                                kink=Decimal('0.8'),
                                                                base_rate_per_block=Decimal('1.902587519E-9'),
                                                                multiplier_per_block=Decimal('3.3295281582E-8'),
                                                                jump_multiplier_per_block=Decimal('5.70776255707E-7'))),
                token_created_at_block=7533535),
            'UNI': WepiggyToken(
                name='UNI',
                token_address=Web3.to_checksum_address('0xBf5140A22578168FD562DCcF235E5D43A02ce9B1'),
                deposit_address=Web3.to_checksum_address('0x17933112E9780aBd0F27f2B7d9ddA9E840D43159'),
                model_address=Web3.to_checksum_address('0x621ce6596e0b9ccf635316bfe7fdbc80c3029bec'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('1'),
                                                                kink=Decimal('0.8'),
                                                                base_rate_per_block=Decimal('1.902587519E-9'),
                                                                multiplier_per_block=Decimal('3.3295281582E-8'),
                                                                jump_multiplier_per_block=Decimal('5.70776255707E-7'))),
                token_created_at_block=7533543),
            'CAKE': WepiggyToken(
                name='CAKE',
                token_address=Web3.to_checksum_address('0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82'),
                deposit_address=Web3.to_checksum_address('0x417FDfC74503d8008AeEB53248E5C0f1960c2C1d'),
                model_address=Web3.to_checksum_address('0x621ce6596e0b9ccf635316bfe7fdbc80c3029bec'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.25'),
                                                                kink=Decimal('0.8'),
                                                                base_rate_per_block=Decimal('1.902587519E-9'),
                                                                multiplier_per_block=Decimal('3.3295281582E-8'),
                                                                jump_multiplier_per_block=Decimal('5.70776255707E-7'))),
                token_created_at_block=7533550),
            'LTC': WepiggyToken(
                name='LTC',
                token_address=Web3.to_checksum_address('0x4338665CBB7B2485A8855A139b75D5e34AB0DB94'),
                deposit_address=Web3.to_checksum_address('0x6a05BD123d780055c38526cC05d3c9B90D0E471c'),
                model_address=Web3.to_checksum_address('0x621ce6596e0b9ccf635316bfe7fdbc80c3029bec'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.25'),
                                                                kink=Decimal('0.8'),
                                                                base_rate_per_block=Decimal('1.902587519E-9'),
                                                                multiplier_per_block=Decimal('3.3295281582E-8'),
                                                                jump_multiplier_per_block=Decimal('5.70776255707E-7'))),
                token_created_at_block=8196853),
            'LINK': WepiggyToken(
                name='LINK',
                token_address=Web3.to_checksum_address('0xF8A0BF9cF54Bb92F17374d9e9A321E6a111a51bD'),
                deposit_address=Web3.to_checksum_address('0x00FF07204C3b27D72cF83Ef521Adb7066167561a'),
                model_address=Web3.to_checksum_address('0x621ce6596e0b9ccf635316bfe7fdbc80c3029bec'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.25'),
                                                                kink=Decimal('0.8'),
                                                                base_rate_per_block=Decimal('1.902587519E-9'),
                                                                multiplier_per_block=Decimal('3.3295281582E-8'),
                                                                jump_multiplier_per_block=Decimal('5.70776255707E-7'))),
                token_created_at_block=7533522),
            'ADA': WepiggyToken(
                name='ADA',
                token_address=Web3.to_checksum_address('0x3EE2200Efb3400fAbB9AacF31297cBdD1d435D47'),
                deposit_address=Web3.to_checksum_address('0xBc52BCE2C73Fec358ABBf047c50377183B9EAd0d'),
                model_address=Web3.to_checksum_address('0x621ce6596e0b9ccf635316bfe7fdbc80c3029bec'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.25'),
                                                                kink=Decimal('0.8'),
                                                                base_rate_per_block=Decimal('1.902587519E-9'),
                                                                multiplier_per_block=Decimal('3.3295281582E-8'),
                                                                jump_multiplier_per_block=Decimal('5.70776255707E-7'))),
                token_created_at_block=8196871),
            'FIL': WepiggyToken(
                name='FIL',
                token_address=Web3.to_checksum_address('0x0D8Ce2A99Bb6e3B7Db580eD848240e4a0F9aE153'),
                deposit_address=Web3.to_checksum_address('0xDF21D42a0fC6746718F2CFe2798F91C9d7277F32'),
                model_address=Web3.to_checksum_address('0x621ce6596e0b9ccf635316bfe7fdbc80c3029bec'),
                model=JumpInterestModel(InterestModelParameters(reserve_factor=Decimal('0.25'),
                                                                kink=Decimal('0.8'),
                                                                base_rate_per_block=Decimal('1.902587519E-9'),
                                                                multiplier_per_block=Decimal('3.3295281582E-8'),
                                                                jump_multiplier_per_block=Decimal('5.70776255707E-7'))),
                token_created_at_block=8196880),
        }
    ),
}


def get_lending_market(chain_id: int, protocol: str) -> LendingMarket:
    # Auto-detect the network based on the chain id
    if chain_id not in LENDING_NETWORK_CHAINS:
        raise ValueError(f'Unsupported chain id: {chain_id}')
    network_slug = LENDING_NETWORK_CHAINS[chain_id]
    lending_market = LENDING_MARKETS[network_slug + '-' + protocol.lower()]
    return lending_market


DEPOSIT_ADDRESS_TO_TOKEN: dict[ChecksumAddress, LendingToken] = {}  # autofill later

def get_token_by_deposit_address(deposit_address: ChecksumAddress) -> Optional[LendingToken]:
    # Get a token name by the AToken deposit contract address
    return DEPOSIT_ADDRESS_TO_TOKEN.get(Web3.to_checksum_address(deposit_address), None)


def get_token_name_by_deposit_address(deposit_address: ChecksumAddress) -> Optional[str]:
    # Get a token name by the AToken deposit contract address
    return get_token_by_deposit_address(deposit_address).name


def _autofill_token_addresses():
    for network in LENDING_MARKETS.values():
        for token_name, token in network.token_contracts.items():
            assert token.deposit_address not in DEPOSIT_ADDRESS_TO_TOKEN, \
                "出现重复的deposit address:{}".format(token.deposit_address)
            DEPOSIT_ADDRESS_TO_TOKEN[token.deposit_address] = token


# Initialization
_autofill_token_addresses()


