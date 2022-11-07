'''
    Venus Rates Calculation
'''

import os
import logging
import datetime
from decimal import Decimal
from typing import NamedTuple, Tuple, Union

import pandas
from tqdm.auto import tqdm
from requests.adapters import HTTPAdapter
from pandas import DataFrame, Timedelta

from eth_defi.abi import get_contract
from eth_defi.event_reader.state import ScanState
from eth_defi.event_reader.web3factory import TunedWeb3Factory
from eth_defi.event_reader.web3worker import create_thread_pool_executor
from eth_defi.event_reader.reader import prepare_filter, read_events_concurrent, extract_timestamps_json_rpc
from eth_defi.venus.events import TokenCache

from eth_defi.venus.events import get_event_mapping
from eth_defi.venus.constants import VENUS_NETWORKS
from eth_defi.venus.events import decode_accrue_interest_events

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


# Response from venus_v3_calculate_accrued_interests functions with all different interests calculated
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


def venus_calculate_apr_apy_rates(df: DataFrame) -> DataFrame:
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
            lambda value: float((Decimal(value) / ulyToken_decimals) * blocks_per_year) * 100),
        deposit_apr=df['supply_rate_per_block'].apply(
            lambda value: float((Decimal(value) / ulyToken_decimals) * blocks_per_year) * 100),

        borrow_apy=df['borrow_rate_per_block'].apply(
            lambda value: (float(((Decimal(value) / ulyToken_decimals) * blocks_per_day + 1) ** Decimal(days_per_year)) -1) * 100),
        deposit_apy=df['supply_rate_per_block'].apply(
            lambda value: (float(((Decimal(value) / ulyToken_decimals) * blocks_per_day + 1) ** Decimal(days_per_year)) -1) * 100),

        total_borrow_float=df['total_borrow'].apply(lambda value: float(Decimal(value) / ulyToken_decimals)),
        total_supply_float=df['total_supply'].apply(lambda value: float(Decimal(value) / ulyToken_decimals)),

        utilization=df.apply(
            lambda value: (
                (Decimal(value["total_borrows"]) - Decimal(value["interest_accumulated"])) /
                (Decimal(value["cash_prior"]) + Decimal(value["total_borrows"]) - Decimal(value["interest_accumulated"]))
            ), axis=1),

    )

    return df


def venus_filter_by_token(df: DataFrame, token: str = '') -> DataFrame:
    """
    Filter the DataFrame by token. If token is empty, return the entire DataFrame.
    """
    if not token:
        # Return everything
        return df
    else:
        # Filter by token
        return df.loc[df['token'] == token]


def venus_calculate_mean(df: DataFrame, time_bucket: Timedelta, attribute: Union[str , Tuple], token: str = '') -> Union[DataFrame , Tuple]:
    """
    Calculate mean values for a given time bucket (e.g. 1 day) and given attribute.
    Attribute can be e.g. deposit_apr, borrow_apr, deposit_apy, borrow_apy.
    The dataframe must be indexed by timestamp.
    Returns a new DataFrame, or a tuple of DataFrames if a tuple of attributes was specified.
    """
    assert token, "需要录入token计算收益"

    df = venus_filter_by_token(df, token)
    if isinstance(attribute, str):
        # Single attribute
        # 先upsample至3秒，然后fillna，再downsample去1天，求平均APR
        return df[attribute].resample('3S').mean().ffill().resample(time_bucket).mean()
    else:
        # Multiple attributes
        return pandas.concat(
            [df[attr].resample('3S').mean().ffill().resample(time_bucket).mean() for attr in attribute],
            axis=1)


def venus_filter_by_date_range(df: DataFrame, start_time: datetime, end_time: datetime = None, token: str = '') -> DataFrame:
    """
    Filter the DataFrame by date range suitable for interest calculation (loan start to loan end time)
    The DataFrame must be indexed by timestamp.
    If token is specified, also filters by token.
    """
    if end_time:
        return venus_filter_by_token(df, token).query('timestamp >= @start_time and timestamp <= @end_time')
    else:
        return venus_filter_by_token(df, token).query('timestamp >= @start_time')


def venus_calculate_accrued_interests(df: DataFrame, start_time: datetime, end_time: datetime, amount: Decimal, token: str = '') -> VenusAccruedInterest:
    """
    Calculate total interest accrued for a given time period. The dataframe must be indexed by timestamp.
    Returns a tuple with actual start time, actual end time, and total interest accrued for a deposit, variable borrow debt, and stable borrow debt.
    Actual start time and actual end time are the first and last timestamp in the time period in the DataFrame.
    """
    assert token, "需要录入token名称进行计算"

    df = venus_filter_by_token(df, token)
    df = venus_calculate_apr_apy_rates(df)

    assert start_time >= df.index[0], "DataFrame应包含计算的起始时间"
    assert end_time <= df.index[-1], "DataFrame应包含计算的结束时间"

    df = venus_filter_by_date_range(df, start_time, end_time, token)
    if len(df) <= 0:
        raise ValueError('No data found in date range %s - %s' % (start_time, end_time))

    # 计算区间内的deposit_index
    df['deposit_index_delta'] = df['borrow_index'] - df['borrow_index'].shift(periods=1).fillna(Decimal(0))
    df['deposit_index_delta'] = df.apply(
        lambda value: Decimal(value['deposit_index_delta']) * Decimal(value['utilization']),
        axis=1)
    df['deposit_index'] = df['deposit_index_delta'].cumsum()

    # Loan starts on first row of the DataFrame
    actual_start_time = df.index[0]
    start_borrow_index = Decimal(int(df['borrow_index'][0]))
    start_deposit_index = Decimal(df['deposit_index'][0])

    # Loan ends on last row of the DataFrame
    actual_end_time = df.index[-1]
    end_borrow_index = Decimal(int(df['borrow_index'][-1]))
    end_deposit_index = Decimal(df['deposit_index'][-1])

    # Calculate interest for deposit.
    deposit_scaled_amount = amount / start_deposit_index
    deposit_final_amount = deposit_scaled_amount * end_deposit_index
    deposit_interest = deposit_final_amount - amount

    borrow_scaled_amount = amount / start_borrow_index
    borrow_final_amount = borrow_scaled_amount * end_borrow_index
    borrow_interest = borrow_final_amount - amount

    return VenusAccruedInterest(
        actual_start_time=actual_start_time,
        actual_end_time=actual_end_time,
        deposit_interest=deposit_interest,
        borrow_interest=borrow_interest,
    )

