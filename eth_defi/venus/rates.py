'''
    Venus 概念：参见README.md
'''

import os
import logging
import datetime
from decimal import Decimal
from typing import NamedTuple, Tuple, Union, List

import numpy as np
from pandas import (DataFrame, Timedelta, pandas)
from web3 import Web3
from scipy.optimize import bisect

from eth_defi.abi import get_deployed_contract
from eth_defi.venus.constants import (
    VenusToken,
    venus_get_token_name_by_deposit_address
)
from eth_defi.venus.interest_model import (
    VenusInterestModelParameters,
    VenusInterestModel,
    VenusWhitePaperInterestModel,
    VenusJumpInterestModel,
)


logger = logging.getLogger(__name__)

# Constants for APY and APR calculation
RAY = Decimal(10**27)  # 10 to the power 27
WAD = Decimal(10**18)  # 10 to the power 18

# Constants for
venus_token_decimals = Decimal(10**8)
ulyToken_decimals = Decimal(10**18)

# Constants
unlimited = 0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff # 2^256-1

SECONDS_PER_YEAR_INT = 31_536_000
SECONDS_PER_YEAR = Decimal(SECONDS_PER_YEAR_INT)


def venus_get_interest_model_parameters(web3: Web3, venus_token: VenusToken) -> VenusInterestModelParameters:

    contract = get_deployed_contract(web3, "venus/VBep20.json", venus_token.deposit_address)

    reserve_factor = contract.functions.reserveFactorMantissa().call()
    reserve_factor = Decimal(reserve_factor) / WAD

    model_address = contract.functions.interestRateModel().call()
    logger.info("model address: {}".format(model_address))

    if isinstance(venus_token.model, VenusWhitePaperInterestModel):
        fname = "venus/WhitePaperInterestRateModel.json"
    else:
        fname = "venus/JumpRateModel.json"
    model_contract = get_deployed_contract(web3, fname, Web3.toChecksumAddress(model_address))

    base_rate_per_block = model_contract.functions.baseRatePerBlock().call()
    base_rate_per_block = Decimal(base_rate_per_block) / WAD

    multiplier_per_block = model_contract.functions.multiplierPerBlock().call()
    multiplier_per_block = Decimal(multiplier_per_block) / WAD

    if isinstance(venus_token.model, VenusJumpInterestModel):
        kink = model_contract.functions.kink().call()
        kink = Decimal(kink) / WAD

        jump_multiplier_per_block = model_contract.functions.jumpMultiplierPerBlock().call()
        jump_multiplier_per_block = Decimal(jump_multiplier_per_block) / WAD
    else:
        kink = Decimal(0)
        jump_multiplier_per_block = Decimal(0)

    return VenusInterestModelParameters(
        reserve_factor=reserve_factor,
        kink=kink,
        base_rate_per_block=base_rate_per_block,
        multiplier_per_block=multiplier_per_block,
        jump_multiplier_per_block=jump_multiplier_per_block,
    )


# Response from venus_calculate_accrued_interests functions with all different interests calculated
class VenusAccruedInterest(NamedTuple):
    # The first interest event found in the given date range
    actual_start_time: datetime.datetime

    # The last interest event found in the given date range
    actual_end_time: datetime.datetime

    # Calculated interest for deposit of specified amount
    deposit_interest: Decimal

    # Calculated interest for a borrow loan of specified amount
    borrow_interest: Decimal


def load_accrue_interest_event_dataframe(
    dirname: str = ".",
    filename: str = "venus-accrueinterest.csv",
) -> DataFrame:
    """Load accrue interest event csv"""

    fullpath = os.path.join(dirname, filename)
    if os.path.exists(fullpath):
        df = pandas.read_csv(fullpath, parse_dates=True, index_col="timestamp")
        return df
    else:
        raise FileNotFoundError("{} not found".format(fullpath))


def venus_filter_by_token(df: DataFrame, token: str) -> DataFrame:
    """
    Filter the DataFrame by token. If token is empty, fail.
    """
    assert token, "传入正确的token字符串"
    return df.loc[df['token'] == token]


# def venus_filter_by_date_range(df: DataFrame, start_time: datetime, end_time: datetime = None, token: str = '') -> DataFrame:
#     """
#     Filter the DataFrame by date range suitable for interest calculation (loan start to loan end time)
#     The DataFrame must be indexed by timestamp.
#     If token is specified, also filters by token.
#     """
#     if end_time:
#         return venus_filter_by_token(df, token).query('timestamp >= @start_time and timestamp <= @end_time')
#     else:
#         return venus_filter_by_token(df, token).query('timestamp >= @start_time')


def venus_calculate_per_block_return(df: DataFrame) -> DataFrame:
    """
    Calculate APR and APY columns for Venus DataFrame previously generated from the blockchain events.
    Also add converted float versions of rate columns for easier calculation operations.
    """
    # https://docs.venus.io/docs/getstarted#protocol-math
    # BNB APR = (Rate Per Block / BNB Mantissa * Blocks Per Year) * 100
    # BNB APY = (((Rate Per Block / BNB Mantissa * Blocks Per Day + 1) ^ Days Per Year - 1)) * 100

    days_per_year = 365
    blocks_per_day = 20 * 60 * 24 # BSC block rate
    blocks_per_year = blocks_per_day * days_per_year

    df = df.assign(
        borrow_apr =df['borrow_rate_per_block'].apply(
            lambda value: ((Decimal(value) / ulyToken_decimals) * Decimal(blocks_per_year)) * 100),
        deposit_apr=df['supply_rate_per_block'].apply(
            lambda value: ((Decimal(value) / ulyToken_decimals) * Decimal(blocks_per_year)) * 100),

        borrow_apy=df['borrow_rate_per_block'].apply(
            lambda value: ((((Decimal(value) / ulyToken_decimals) * Decimal(blocks_per_day) + 1) ** Decimal(days_per_year)) -1) * 100),
        deposit_apy=df['supply_rate_per_block'].apply(
            lambda value: ((((Decimal(value) / ulyToken_decimals) * Decimal(blocks_per_day) + 1) ** Decimal(days_per_year)) -1) * 100),
    )

    return df


def venus_calculate_mean_return(df: DataFrame, time_bucket: Timedelta, attribute: Union[str , List], token: str) -> Union[DataFrame , Tuple]:
    """
    Calculate mean values for a given time bucket (e.g. 1 day) and given attribute.
    Attribute can be e.g. deposit_apr, borrow_apr, deposit_apy, borrow_apy.
    The dataframe must be indexed by timestamp.
    Returns a new DataFrame, or a tuple of DataFrames if a tuple of attributes was specified.
    """
    assert token, "需要录入token计算收益"
    df = venus_filter_by_token(df, token)
    df = venus_calculate_per_block_return(df)

    valid_attributes = ["deposit_apr", "borrow_apr", "deposit_apy", "borrow_apy"]
    target_attributes = []

    if isinstance(attribute, str):
        assert attribute in valid_attributes, "attribute '{}' 不在合格的列表{}".format(attribute, valid_attributes)
        target_attributes.append(attribute)
    else:
        invalid = np.setdiff1d(attribute, valid_attributes)
        assert len(invalid) == 0, "发现非法attribute字段：'{}'".format(invalid)
        target_attributes = attribute

    # Multiple attributes
    return pandas.concat(
        [
            df[attr].resample('1S').mean().ffill().resample(time_bucket).mean()
            for attr in target_attributes
        ],
        axis=1)


def venus_calculate_accrued_interests(df: DataFrame, start_time: datetime, end_time: datetime, amount: Decimal, token: str = '') -> VenusAccruedInterest:
    """
    Calculate total interest accrued for a given time period. The dataframe must be indexed by timestamp.
    Returns a tuple with actual start time, actual end time, and total interest accrued for a deposit, variable borrow debt, and stable borrow debt.
    Actual start time and actual end time are the first and last timestamp in the time period in the DataFrame.
    """
    assert token, "需要录入token名称进行计算"

    df = venus_filter_by_token(df, token)
    df = venus_calculate_per_block_return(df)

    assert start_time >= df.index[0], "DataFrame应包含计算的起始时间"
    assert end_time <= df.index[-1], "DataFrame应包含计算的结束时间"
    assert start_time <= end_time, "DataFrame应包含计算的结束时间"

    df = venus_calculate_mean_return(df, '1S', ["deposit_apr", "borrow_apr"], token)
    df = df.loc[start_time:end_time]
    if len(df) <= 0:
        raise ValueError('No data found in date range %s - %s' % (start_time, end_time))

    # 使用平均APR计算利息
    average_deposit_apr = df["deposit_apr"].mean()
    average_borrow_apr = df["borrow_apr"].mean()

    actual_start_time = df.index[0]
    actual_end_time = df.index[-1]
    delta_time = actual_end_time - actual_start_time
    full_year = datetime.timedelta(days=365)

    deposit_interest = Decimal(float(amount) * average_deposit_apr * delta_time / full_year / 100)
    borrow_interest = Decimal(float(amount) * average_borrow_apr * delta_time / full_year / 100)

    # 计算区间内的deposit_index
    # df['deposit_index_delta'] = df['borrow_index'] - df['borrow_index'].shift(periods=1).fillna(Decimal(0))
    # df['deposit_index_delta'] = df.apply(
    #     lambda value: Decimal(value['deposit_index_delta']) * Decimal(value['utilization']),
    #     axis=1)
    # df['deposit_index'] = df['deposit_index_delta'].cumsum()
    #
    # # Loan starts on first row of the DataFrame
    # actual_start_time = df.index[0]
    # start_borrow_index = Decimal(int(df['borrow_index'][0]))
    # start_deposit_index = Decimal(df['deposit_index'][0])
    #
    # # Loan ends on last row of the DataFrame
    # actual_end_time = df.index[-1]
    # end_borrow_index = Decimal(int(df['borrow_index'][-1]))
    # end_deposit_index = Decimal(df['deposit_index'][-1])
    #
    # # Calculate interest for deposit.
    # deposit_scaled_amount = amount / start_deposit_index
    # deposit_final_amount = deposit_scaled_amount * end_deposit_index
    # deposit_interest = deposit_final_amount - amount
    #
    # borrow_scaled_amount = amount / start_borrow_index
    # borrow_final_amount = borrow_scaled_amount * end_borrow_index
    # borrow_interest = borrow_final_amount - amount

    return VenusAccruedInterest(
        actual_start_time=actual_start_time,
        actual_end_time=actual_end_time,
        deposit_interest=deposit_interest,
        borrow_interest=borrow_interest,
    )


class VenusDepthAnalysis(NamedTuple):
    # The first interest event found in the given date range
    actual_start_time: datetime.datetime

    # The last interest event found in the given date range
    actual_end_time: datetime.datetime

    # Calculated interest for deposit of specified amount
    deposit_interest: Decimal

    # Calculated interest for a borrow loan of specified amount
    borrow_interest: Decimal


def venus_deposit_depth_analysis(web3: Web3, venus_token: VenusToken, target_amount: Decimal) -> VenusDepthAnalysis:
    """给定存取或者借出的token数量，计算存取/借出后的利率
        同时计算现有利率下，5%，10%，20%，50%，100%利率变动所承载的存取/借出金额
    """
    contract = get_deployed_contract(web3, "VBep20.json", venus_token.deposit_address)

    # 监控的事件发生时，都会引起利率变化，所以要记录此区块的利率、借款、存款利息等信息
    borrow_rate_per_block = contract.functions.borrowRatePerBlock().call() # 2957813543
    supply_rate_per_block = contract.functions.supplyRatePerBlock().call() # 174984816

    total_borrow = contract.functions.totalBorrowsCurrent().call()  # 3124653038953932474258414
    total_supply = contract.functions.totalSupply().call()  # 209539053430583173
    total_reserve = contract.functions.totalReserves().call()  # 1951135653323763085666
    cash = contract.functions.getCash().call()  # 39130751880398368732080648

    model = venus_token.model




