'''
    Venus 概念：参见README.md
'''

import os
import logging
import datetime
from decimal import Decimal
from typing import NamedTuple, Tuple, Union, List, Optional
from retry import retry

import numpy as np
from pandas import (DataFrame, Timedelta, pandas)
from web3 import Web3,exceptions
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

DAYS_PER_YEAR = Decimal(365)
BLOCKS_PER_DAY = Decimal(20 * 60 * 24)  # BSC block rate
BLOCKS_PER_YEAR = Decimal(20 * 60 * 24 * 365)

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


def venus_calculate_per_block_return(df: DataFrame) -> DataFrame:
    """
    Calculate APR and APY columns for Venus DataFrame previously generated from the blockchain events.
    Also add converted float versions of rate columns for easier calculation operations.
    """
    # https://docs.venus.io/docs/getstarted#protocol-math
    # BNB APR = (Rate Per Block / BNB Mantissa * Blocks Per Year) * 100
    # BNB APY = (((Rate Per Block / BNB Mantissa * Blocks Per Day + 1) ^ Days Per Year - 1)) * 100


    df = df.assign(
        borrow_apr =df['borrow_rate_per_block'].apply(
            lambda value: ((Decimal(value) / ulyToken_decimals) * BLOCKS_PER_YEAR) ),
        deposit_apr=df['supply_rate_per_block'].apply(
            lambda value: ((Decimal(value) / ulyToken_decimals) * BLOCKS_PER_YEAR) ),

        borrow_apy=df['borrow_rate_per_block'].apply(
            lambda value: ((((Decimal(value) / ulyToken_decimals) * BLOCKS_PER_DAY + 1) ** DAYS_PER_YEAR) -1) ),
        deposit_apy=df['supply_rate_per_block'].apply(
            lambda value: ((((Decimal(value) / ulyToken_decimals) * BLOCKS_PER_DAY + 1) ** DAYS_PER_YEAR) -1) ),
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

    actual_start_time = df.index[0]
    actual_end_time = df.index[-1]
    delta_time = actual_end_time - actual_start_time
    full_year = datetime.timedelta(days=365)

    if delta_time < datetime.timedelta(days=3):
        time_bucket = '3S'
    elif delta_time < datetime.timedelta(days=90):
        time_bucket = '1min'
    else:
        time_bucket = '1D'

    df = venus_calculate_mean_return(df, time_bucket, ["deposit_apr", "borrow_apr"], token)
    df = df.loc[start_time:end_time]
    if len(df) <= 0:
        raise ValueError('No data found in date range %s - %s' % (start_time, end_time))

    # 使用平均APR计算利息
    average_deposit_apr = df["deposit_apr"].mean()
    average_borrow_apr = df["borrow_apr"].mean()

    deposit_interest = Decimal(float(amount) * average_deposit_apr * (delta_time / full_year) )
    borrow_interest = Decimal(float(amount) * average_borrow_apr * (delta_time / full_year) )

    return VenusAccruedInterest(
        actual_start_time=actual_start_time,
        actual_end_time=actual_end_time,
        deposit_interest=deposit_interest,
        borrow_interest=borrow_interest,
    )


class VenusInterestParameters(NamedTuple):
    total_borrows: Decimal
    total_reserves: Decimal
    cash: Decimal
    borrow_rate_per_block: Decimal
    supply_rate_per_block: Decimal


class VenusDepthAnalysis(NamedTuple):

    borrow_apr: Decimal
    # delta borrow amount from current level
    plus_one_pct_borrow_apr: Decimal    # Rate+1%
    plus_five_pct_borrow_apr: Decimal    # Rate+5%
    plus_ten_pct_borrow_apr: Decimal     # Rate+10%
    plus_fifteen_pct_borrow_apr: Decimal  # Rate+15%
    plus_twenty_pct_borrow_apr: Decimal  # Rate+20%

    supply_apr: Decimal
    # delta supply amount from current level
    minus_one_pct_supply_apr: Decimal  ## Rate-1%
    minus_five_pct_supply_apr: Decimal  ## Rate-5%
    minus_ten_pct_supply_apr: Decimal   ## Rate-10%
    minus_fifteen_pct_supply_apr: Decimal ## Rate-15%
    minus_twenty_pct_supply_apr: Decimal ## Rate-20%


@retry(exceptions.BadFunctionCallOutput, tries=5, delay=2)
def venus_get_current_interest_parameters(web3: Web3, venus_token: VenusToken) -> VenusInterestParameters:

    contract = get_deployed_contract(web3, "venus/VBep20.json", venus_token.deposit_address)

    # 监控的事件发生时，都会引起利率变化，所以要记录此区块的利率、借款、存款利息等信息
    borrow_rate_per_block = contract.functions.borrowRatePerBlock().call()
    borrow_rate_per_block = Decimal(borrow_rate_per_block) / ulyToken_decimals

    supply_rate_per_block = contract.functions.supplyRatePerBlock().call()
    supply_rate_per_block = Decimal(supply_rate_per_block) / ulyToken_decimals

    total_borrows = contract.functions.totalBorrows().call()
    total_borrows = Decimal(total_borrows)/ulyToken_decimals

    total_reserves = contract.functions.totalReserves().call()
    total_reserves = Decimal(total_reserves)/ulyToken_decimals

    cash = contract.functions.getCash().call()
    cash = Decimal(cash)/ulyToken_decimals

    return VenusInterestParameters(
        total_borrows=total_borrows,
        total_reserves=total_reserves,
        cash=cash,
        borrow_rate_per_block=borrow_rate_per_block,
        supply_rate_per_block=supply_rate_per_block,
    )


def venus_deposit_depth_analysis(interest_params: VenusInterestParameters, venus_token: VenusToken) -> VenusDepthAnalysis:
    """ 在现有的利率水平和参数(cash/reserves/borrows)下，
        计算存取利率下降1%/5%/10%/15%/20%时额外需存入的token数量；
        计算借款利率上升1%/5%/10%/15%/20%时额外借出的token数量；
    """

    interest_model = venus_token.model
    target_borrow_changes = np.array([Decimal(0.01), Decimal(0.05), Decimal(0.1), Decimal(0.15), Decimal(0.2)])
    target_supply_changes = np.array([Decimal(-0.01), Decimal(-0.05), Decimal(-0.1), Decimal(-0.15), Decimal(-0.2)])
    delta_borrow = np.zeros(len(target_borrow_changes))
    delta_supply = np.zeros(len(target_supply_changes))

    # 利用二分法查找： 借款利息增加时，对应增加的借款数量
    target_borrow_rates = target_borrow_changes/BLOCKS_PER_YEAR + interest_params.borrow_rate_per_block

    # TODO: 防止利率过大无法达成：目前来看好像利率都可以超过100%，故不太成为问题

    for i, target_borrow_rate in enumerate(target_borrow_rates):
        def f(delta_borrow):
            new_rate = interest_model.borrow_rate_per_block(
                interest_params.cash - Decimal(delta_borrow), # cash
                interest_params.total_borrows + Decimal(delta_borrow), # borrow
                interest_params.total_reserves)
            return float(new_rate - target_borrow_rate)

        root = bisect(f, 0, float(interest_params.cash))
        delta_borrow[i] = Decimal(root)

    # 利用二分法查找： 存款利息减少时，对应增加的存款数量
    target_supply_rates = target_supply_changes/BLOCKS_PER_YEAR + interest_params.supply_rate_per_block

    # 给定一个极小的利率，防止不能converge
    # BaseRatePerBlock有可能为零，故额外加一个很小的利率(年化0.1%)
    target_supply_rates[target_supply_rates < Decimal(0)] = \
        interest_model.params.base_rate_per_block + Decimal(0.001)/BLOCKS_PER_YEAR

    for i, target_supply_rate in enumerate(target_supply_rates):
        def f(delta_supply):
            new_rate = interest_model.supply_rate_per_block(
                interest_params.cash + Decimal(delta_supply), # cash
                interest_params.total_borrows, # borrow
                interest_params.total_reserves)
            return float(target_supply_rate - new_rate)

        root = bisect(f, 0, float(interest_params.cash + interest_params.total_borrows) * 100)
        delta_supply[i] = Decimal(root)

    return VenusDepthAnalysis(
        borrow_apr=interest_params.borrow_rate_per_block * BLOCKS_PER_YEAR,
        # delta borrow amount from current level
        plus_one_pct_borrow_apr=delta_borrow[0],  # Rate+1%
        plus_five_pct_borrow_apr=delta_borrow[1],  # Rate+5%
        plus_ten_pct_borrow_apr=delta_borrow[2],  # Rate+10%
        plus_fifteen_pct_borrow_apr=delta_borrow[3],  # Rate+15%
        plus_twenty_pct_borrow_apr=delta_borrow[4],  # Rate+20%

        supply_apr=interest_params.supply_rate_per_block * BLOCKS_PER_YEAR,
        # delta supply amount from current level
        minus_one_pct_supply_apr=delta_supply[0],  ## Rate-1%
        minus_five_pct_supply_apr=delta_supply[1],  ## Rate-5%
        minus_ten_pct_supply_apr=delta_supply[2],  ## Rate-10%
        minus_fifteen_pct_supply_apr=delta_supply[3],  ## Rate-15%
        minus_twenty_pct_supply_apr=delta_supply[4],  ## Rate-20%
    )




