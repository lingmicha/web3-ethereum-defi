
import csv
import logging
import datetime
from pathlib import Path
from tqdm.auto import tqdm

from web3 import Web3
from requests.adapters import HTTPAdapter

from eth_defi.event_reader.conversion import (
    convert_uint256_bytes_to_address,
    convert_uint256_string_to_address,
    convert_uint256_string_to_int,
    decode_data,
    convert_int256_bytes_to_int,
)
from eth_defi.event_reader.logresult import LogContext
from eth_defi.event_reader.reader import LogResult, read_events_concurrent
from eth_defi.token import TokenDetails, fetch_erc20_details
from eth_defi.venus.constants import venus_get_token_name_by_deposit_address, VenusToken, VenusNetwork, VENUS_NETWORKS
from eth_defi.abi import get_contract
from eth_defi.event_reader.reader import prepare_filter,read_events, read_events_concurrent
from eth_defi.event_reader.web3factory import TunedWeb3Factory
from eth_defi.event_reader.web3worker import create_thread_pool_executor
from eth_defi.event_reader.state import ScanState


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


def decode_events(log: LogResult) -> dict:
    """Process venus event.

    This function does manually optimised high speed decoding of the event.

    The event signature is:

    .. code-block::

        event Mint(address,uint256,uint256);
        event Redeem(address,uint256,uint256);

        event Borrow(address,uint256,uint256,uint256);
        event LiquidateBorrow(address,address,uint256,address,uint256);
        event RepayBorrow(address,address,uint256,uint256,uint256);

    """

    '''The raw log result looks like：
    {'address': '0x95c78222b3d6e262426483d42cfa53685a67ab9d',
     'topics': ['0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f'],
     'data': '0x000000000000000000000000ded08efb71abcc782a86d53a43731c77ca1250cf000000000000000000000000000000000000000000000035f057d41869acc0000000000000000000000000000000000000000000000000000000042d49347f25',
     'blockNumber': '0x1502408',
     'transactionHash': '0x5a5ac368ec989338bcde6956cc393eb545903dc1c31f686f98c0435c31217f69',
     'transactionIndex': '0x58',
     'blockHash': '0x404d7158ce7baea438eaf2461ed4881379a903eacf1b791f979314d1e8740512',
     'logIndex': '0xd4',
     'removed': False,
     'context': <eth_defi.venus.events.TokenCache at 0x7f8d4253fcd0>,
     'event': web3._utils.datatypes.Mint,
     'timestamp': None}
    '''

    # Do additional lookup for the token data
    web3 = log["event"].web3
    token_cache: TokenCache = log["context"]

    # Any indexed Solidity event parameter will be in topics data.
    # The first topics (0) is always the event signature.
    deposit_address = Web3.toChecksumAddress(log["address"])
    token_name = venus_get_token_name_by_deposit_address(deposit_address)

    # Chop data blob to byte32 entries
    data_entries = decode_data(log["data"])

    minter_address = Web3.toChecksumAddress(convert_uint256_bytes_to_address(data_entries[0]))

    data = {
        "block_number": int(log["blockNumber"], 16),
        "tx_hash": log["transactionHash"],
        "log_index": int(log["logIndex"], 16),

        "token_name": token_name,
        "deposit_address": deposit_address,
        "minter_address": minter_address,

    }
    return data


def get_event_mapping(web3: Web3) -> dict:
    """Returns tracked event types and mapping.

    Currently we are tracking these events:
        event Mint(address,uint256,uint256);
        event Redeem(address,uint256,uint256);
        event Borrow(address,uint256,uint256,uint256);
        event LiquidateBorrow(address,address,uint256,address,uint256);
        event RepayBorrow(address,address,uint256,uint256,uint256);
    """

    # Get contracts
    venus_token = get_contract(web3, 'venus/VBep20.json')

    return {
        "Mint": {
            "contract_event": venus_token.events.Mint,
            "field_names": [
                "block_number",
                "timestamp",
                "tx_hash",
                "log_index",
                "token_name",
                "deposit_address",
                "minter_address",
            ],
            "decode_function": decode_events,
        },
        "Redeem": {
            "contract_event": venus_token.events.Redeem,
            "field_names": [
                "block_number",
                "timestamp",
                "tx_hash",
                "log_index",
                "token_name",
                "deposit_address",
                "minter_address",
            ],
            "decode_function": decode_events,
        },
        "Borrow": {
            "contract_event": venus_token.events.Borrow,
            "field_names": [
                "block_number",
                "timestamp",
                "tx_hash",
                "log_index",
                "token_name",
                "deposit_address",
                "minter_address",
            ],
            "decode_function": decode_events,
        },
        "LiquidateBorrow": {
            "contract_event": venus_token.events.LiquidateBorrow,
            "field_names": [
                "block_number",
                "timestamp",
                "tx_hash",
                "log_index",
                "token_name",
                "deposit_address",
                "minter_address",
            ],
            "decode_function": decode_events,
        },
        "RepayBorrow": {
            "contract_event": venus_token.events.RepayBorrow,
            "field_names": [
                "block_number",
                "timestamp",
                "tx_hash",
                "log_index",
                "token_name",
                "deposit_address",
                "minter_address",
            ],
            "decode_function": decode_events,
        },
    }


def fetch_events_to_csv(
    json_rpc_url: str,
    state: ScanState,
    start_block: int = 12_766_328, # TRX created
    end_block: int = 12_766_328 + 1_000,
    output_folder: str = "/tmp",
    max_workers: int = 16,
    log_info=print,
):
    """Fetch all tracked venus events to CSV files for notebook analysis.

    Creates couple of CSV files with the event data:

    - `/tmp/venus-mint.csv`

    - `/tmp/venus-redeem.csv`

    - `/tmp/venus-borrow.csv`

    - `/tmp/venus-liquidateborrow.csv`

    - `/tmp/venus-repayborrow.csv`

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
    token_cache = TokenCache()
    http_adapter = HTTPAdapter(pool_connections=max_workers, pool_maxsize=max_workers)
    web3_factory = TunedWeb3Factory(json_rpc_url, http_adapter)
    web3 = web3_factory(token_cache)
    executor = create_thread_pool_executor(web3_factory, token_cache, max_workers=max_workers)
    event_mapping = get_event_mapping(web3)
    contract_events = [event_data["contract_event"] for event_data in event_mapping.values()]

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
        file_path = f"{output_folder}/venus-{event_name.lower()}.csv"
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

        # Get contracts
        venus_token = get_contract(web3, 'venus/VBep20.json')

        events = [
            venus_token.events.Mint,
            venus_token.events.Redeem,
            venus_token.events.Borrow,
            venus_token.events.LiquidateBorrow,
            venus_token.events.RepayBorrow,
        ]

        addresses = [t.deposit_address for t in VENUS_NETWORKS['bsc'].token_contracts.values()]
        flter = prepare_filter(events)
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


