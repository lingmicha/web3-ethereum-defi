
import csv
import logging
import datetime
from pathlib import Path

import pandas
from tqdm.auto import tqdm
from pandas import DataFrame
from retry import retry
from web3 import Web3, exceptions
from requests.adapters import HTTPAdapter

from eth_defi.abi import(
    get_contract,
    get_deployed_contract,
)
from eth_defi.event_reader.conversion import (
    decode_data,
    convert_int256_bytes_to_int,
)

from eth_defi.token import TokenDetails, fetch_erc20_details
from eth_defi.event_reader.logresult import LogContext
from eth_defi.event_reader.reader import LogResult, prepare_filter, read_events_concurrent, extract_timestamps_json_rpc
from eth_defi.event_reader.web3factory import TunedWeb3Factory
from eth_defi.event_reader.web3worker import create_thread_pool_executor
from eth_defi.event_reader.state import ScanState

from eth_defi.defi_lending.constants import (
    LENDING_MARKETS,
    get_lending_market,
    get_token_name_by_deposit_address,
)

logger = logging.getLogger(__name__)


class TokenCache(LogContext):
    """Manage cache of token data when doing PairCreated look-up.

    Do not do extra requests for already known tokens.
    """

    def __init__(self):
        self.cache = {}

    def get_token_info(self, web3: Web3, address: str) -> TokenDetails:
        if address not in self.cache:
            self.cache[address] = fetch_erc20_details(web3, address, raise_on_error=False)
        return self.cache[address]


@retry(exceptions.BadFunctionCallOutput, tries=5, delay=2, backoff=2)
def decode_accrue_interest_events(log: LogResult) -> dict:
    """Process venus event.

    This function does manually optimised high speed decoding of the event.

    The event signature is:

    .. code-block::

        AccrueInterest(uint256,uint256,uint256,uint256)
    """

    # Do additional lookup for the token data
    web3 = log["event"].web3
    token_cache: TokenCache = log["context"]
    block_time = datetime.datetime.utcfromtimestamp(log["timestamp"])
    block_number = int(log["blockNumber"], 16)

    # Any indexed Solidity event parameter will be in topics data.
    # The first topics (0) is always the event signature.
    deposit_address = Web3.toChecksumAddress(log["address"])
    token_name = get_token_name_by_deposit_address(deposit_address)

    #TODO: fname according to different protocols
    contract = get_deployed_contract(web3, "venus/VBep20.json", deposit_address)

    # Chop data blob to byte32 entries
    data_entries = decode_data(log["data"])

    #cash_prior = convert_int256_bytes_to_int(data_entries[0])
    #interest_accumulated = convert_int256_bytes_to_int(data_entries[1])
    borrow_index = convert_int256_bytes_to_int(data_entries[2])
    #total_borrows = convert_int256_bytes_to_int(data_entries[3])

    # 监控的事件发生时，都会引起利率变化，所以要记录此区块的利率、借款、存款利息等信息
    borrow_rate_per_block = contract.functions.borrowRatePerBlock().call(block_identifier=block_number)
    supply_rate_per_block = contract.functions.supplyRatePerBlock().call(block_identifier=block_number)

    total_borrows = contract.functions.totalBorrows().call(block_identifier=block_number)
    total_reserves = contract.functions.totalReserves().call(block_identifier=block_number)
    cash = contract.functions.getCash().call(block_identifier=block_number)

    data = {
        "block_number": block_number,
        "timestamp": block_time,
        "tx_hash": log["transactionHash"],
        "log_index": int(log["logIndex"], 16),
        "token": token_name,
        "deposit_address": deposit_address,

        #"cash_prior": cash_prior,
        #"interest_accumulated": interest_accumulated,
        "borrow_index": borrow_index,

        # below is forward rates read directly from the chain:
        "borrow_rate_per_block": borrow_rate_per_block,
        "supply_rate_per_block": supply_rate_per_block,
        "total_borrows": total_borrows,
        "total_reserves": total_reserves,
        "cash": cash,

    }
    return data


def get_event_mapping(web3: Web3, protocol: str ="venus") -> dict:
    """Returns tracked event types and mapping.

    Currently we are tracking these events:
        event AccrueInterest(uint256,uint256,uint256,uint256);
    """

    # Get contracts
    if protocol.lower() == 'venus':
        fname = 'venus/VBep20.json'
    elif protocol.lower() == 'wepiggy':
        fname = 'wepiggy/PToken.json'
    else:
        raise AttributeError("protocol name not valid: {}".format(protocol))

    token = get_contract(web3, fname)

    return {
        "AccrueInterest": {
            "contract_event": token.events.AccrueInterest,
            "field_names": [
                "block_number",
                "timestamp",
                "tx_hash",
                "log_index",
                "token",
                "deposit_address",
                #"cash_prior",
                #"interest_accumulated",
                "borrow_index",
                "borrow_rate_per_block",
                "supply_rate_per_block",
                "total_borrows",
                "total_reserves",
                "cash",
    ],
            "decode_function": decode_accrue_interest_events,
        },
    }


def fetch_events_to_csv(
    json_rpc_url: str,
    chain_id: int,
    protocol: str,
    state: ScanState,
    start_block: int = 12_766_328, # TRX created
    end_block: int = 12_766_328 + 1_000,
    output_folder: str = "/tmp",
    max_workers: int = 16,
    log_info=print,
):
    """Fetch all tracked venus events to CSV files for notebook analysis.

    Creates couple of CSV files with the event data:

    - `/tmp/venus-accrueinterest.csv`

    A progress bar and estimation on the completion is rendered for console / Jupyter notebook using `tqdm`.

    The scan be resumed using `state` storage to retrieve the last scanned block number from the previous round.
    However, the mechanism here is no perfect and only good for notebook use - for advanced
    persistent usage like database backed scans, please write your own scan loop using proper transaction management.

    .. note ::

        Any Ethereum address is lowercased in the resulting dataset and is not checksummed.

    :param json_rpc_url: JSON-RPC URL
    :param start_block: First block to process (inclusive), default is block 12_766_328 (when vTRX was created on mainnet)
    :param end_block: Last block to process (inclusive), default is block 12_767_328 (1000 block after default start block)
    :param state: Store the current scan state, so we can resume
    :param output_folder: Folder to contain output CSV files, default is /tmp folder
    :param max_workers:
        How many threads to allocate for JSON-RPC IO.
        You can increase your EVM node output a bit by making a lot of parallel requests,
        until you exhaust your nodes IO capacity. Experiement with different values
        and see how your node performs.
    :param log_info: Which function to use to output info messages about the progress
    """
    market = get_lending_market(chain_id, protocol)
    token_cache = TokenCache()
    http_adapter = HTTPAdapter(pool_connections=max_workers, pool_maxsize=max_workers)
    web3_factory = TunedWeb3Factory(json_rpc_url, http_adapter)
    web3 = web3_factory(token_cache)
    executor = create_thread_pool_executor(web3_factory, token_cache, max_workers=max_workers)
    event_mapping = get_event_mapping(web3, protocol)
    contract_events = [event_data["contract_event"] for event_data in event_mapping.values()]

    # Make sure output folder exists
    if not Path(output_folder).exists():
        Path(output_folder).mkdir(parents=True, exist_ok=True)

    # Start scanning
    restored, restored_start_block = state.restore_state(start_block)
    original_block_range = end_block - start_block

    if restored:
        log_info(f"Restored previous scan state, data until block {restored_start_block:,}, we are skipping {restored_start_block - start_block:,} blocks out of {original_block_range:,} total")
    else:
        log_info(f"No previous scan done, starting fresh from block {start_block:,}, total {original_block_range:,} blocks", )

    # Prepare local buffers and files.
    # Buffers is a context dictionary that is passed around
    # by the event scanner.
    buffers = {}

    for event_name, mapping in event_mapping.items():
        file_path = f"{output_folder}/{protocol.lower()}-{event_name.lower()}.csv"
        exists_already = Path(file_path).exists()
        file_handler = open(file_path, "a", encoding="utf-8")
        csv_writer = csv.DictWriter(file_handler, fieldnames=mapping["field_names"])
        if not exists_already:
            csv_writer.writeheader()

        # For each event, we have its own
        # counters and handlers in the context dictionary
        buffers[event_name] = {
            "buffer": [],
            "total": 0,
            "file_handler": file_handler,
            "csv_writer": csv_writer,
        }

    log_info(f"Scanning block range {restored_start_block:,} - {end_block:,}")
    with tqdm(total=end_block - restored_start_block) as progress_bar:
        #  1. update the progress bar
        #  2. save any events in the buffer in to a file in one go
        def update_progress(
            current_block,
            start_block,
            end_block,
            chunk_size: int,
            total_events: int,
            last_timestamp: int,
            context: TokenCache,
        ):
            nonlocal buffers

            if last_timestamp:
                # Display progress with the date information
                d = datetime.datetime.utcfromtimestamp(last_timestamp)
                formatted_time = d.strftime("%Y-%m-%d")
                progress_bar.set_description(f"Block: {current_block:,}, events: {total_events:,}, time:{formatted_time}")
            else:
                progress_bar.set_description(f"Block: {current_block:,}, events: {total_events:,}")

            progress_bar.update(chunk_size)

            # Update event specific contexes
            for buffer_data in buffers.values():
                buffer = buffer_data["buffer"]

                # write events to csv
                for entry in buffer:
                    buffer_data["csv_writer"].writerow(entry)
                    buffer_data["total"] += 1

                # then reset buffer
                buffer_data["buffer"] = []

            # Sync the state of updated events
            state.save_state(current_block)

        # Prepare filter so that only vtoken address are monitored
        addresses = [t.deposit_address for t in market.token_contracts.values()]
        flter = prepare_filter(contract_events)
        flter.contract_address = addresses

        # Read specified events in block range
        for log_result in read_events_concurrent(
            executor,
            restored_start_block,
            end_block,
            events=contract_events,
            notify=update_progress,
            chunk_size=100,
            context=token_cache,
            filter=flter,
            extract_timestamps=extract_timestamps_json_rpc,
        ):
            try:
                # write to correct buffer
                event_name = log_result["event"].event_name
                buffer = buffers[event_name]["buffer"]
                decode_function = event_mapping[event_name]["decode_function"]

                buffer.append(decode_function(log_result))
            except Exception as e:
                raise RuntimeError(f"Could not decode {log_result}") from e

    # close files and print stats
    for event_name, buffer in buffers.items():
        buffer["file_handler"].close()
        log_info(f"Wrote {buffer['total']} {event_name} events")


def fetch_events_to_dataframe(
    json_rpc_url: str,
    chain_id: int,
    protocol: str,
    state: ScanState,
    start_block: int = 12_766_328, # TRX created
    end_block: int = 12_766_328 + 1_000,
    output_folder: str = "/tmp",
    max_workers: int = 16,
    log_info=print,
) -> DataFrame:
    '''

    :return:
    '''

    fetch_events_to_csv(json_rpc_url,chain_id, protocol,  state, start_block, end_block, output_folder, max_workers, log_info,)

    restored, restored_block = state.restore_state(start_block)
    assert restored, "ScanState not restored!"
    assert restored_block >= end_block, "Scan not finished"

    event_name = "accrueInterest"
    file_path = f"{output_folder}/{protocol.lower()}-{event_name.lower()}.csv"
    assert Path(file_path).exists(), "Scanned Event CSV file {} not found!".format(file_path)

    df = pandas.read_csv(file_path, parse_dates=True, index_col="timestamp")

    return df


