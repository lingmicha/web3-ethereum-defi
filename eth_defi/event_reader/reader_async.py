"""
    利用asyncio,异步监听链上事件
"""
import logging
import asyncio
from typing import Callable, Dict, AsyncIterable, List, Optional, Protocol
from web3 import Web3
from web3.contract import ContractEvent

from eth_defi.event_reader.filter import Filter
from eth_defi.event_reader.logresult import LogContext, LogResult
from eth_defi.event_reader.reader import (
    prepare_filter,
    ProgressUpdate
)


logger = logging.getLogger(__name__)


async def extract_timestamps_json_rpc(
        web3: Web3,
        start_block: int,
        end_block: int,
) -> Dict[str, int]:
    """Get block timestamps from block headers.

    Use slow JSON-RPC block headers call to get this information.

    :return:
        block hash -> UNIX timestamp mapping
    """
    timestamps = {}

    logging.debug("Extracting timestamps for logs %d - %d", start_block, end_block)

    tasks = [web3.manager.coro_request("eth_getBlockByNumber", (hex(block_num), False)) for block_num in range(start_block, end_block + 1)]
    raw_results = await asyncio.gather(*tasks)

    # Collect block timestamps from the headers
    for (raw_result, block_num) in zip(raw_results, range(start_block, end_block + 1)):
        #raw_result = await web3.eth.get_block(block_num, False)
        #raw_result = await web3.manager.coro_request("eth_getBlockByNumber", (hex(block_num), False))
        data_block_number = raw_result["number"]
        assert type(data_block_number) == str, "Some automatic data conversion occured from JSON-RPC data. Make sure that you have cleared middleware onion for web3"
        assert int(raw_result["number"], 16) == block_num
        timestamps[raw_result["hash"]] = int(raw_result["timestamp"], 16)

    return timestamps


async def extract_events(
    web3: Web3,
    start_block: int,
    end_block: int,
    filter: Filter,
    context: Optional[LogContext] = None,
    extract_timestamps: Optional[Callable] = extract_timestamps_json_rpc,
) -> AsyncIterable[LogResult]:
    """Perform eth_getLogs call over a block range.

    :param start_block:
        First block to process (inclusive)

    :param end_block:
        Last block to process (inclusive)

    :param filter:
        Internal filter used to match logs

    :param extract_timestamps:
        Method to get the block timestamps

    :param context:
        Passed to the all generated logs

    :return:
        Iterable for the raw event data
    """

    topics = list(filter.topics.keys())

    # https://www.quicknode.com/docs/ethereum/eth_getLogs
    # https://docs.alchemy.com/alchemy/guides/eth_getlogs
    filter_params = {
        "topics": [topics],  # JSON-RPC has totally braindead API to say how to do OR event lookup
        "fromBlock": hex(start_block),
        "toBlock": hex(end_block),
    }

    if filter.contract_address:
        filter_params["address"] = filter.contract_address

    # logging.debug("Extracting logs %s", filter_params)
    # logging.info("Log range %d - %d", start_block, end_block)
    #logs = await web3.eth.get_logs(filter_params)
    logs = await web3.manager.coro_request("eth_getLogs", (filter_params,))

    if logs:

        if extract_timestamps is not None:
            timestamps = await extract_timestamps(web3, start_block, end_block)

        for log in logs:
            block_hash = log["blockHash"]
            block_number = log["blockNumber"]
            # Retrofit our information to the dict
            event_signature = log["topics"][0]
            log["context"] = context
            log["event"] = filter.topics[event_signature]
            try:
                log["timestamp"] = timestamps[block_hash] if extract_timestamps else None
            except KeyError as e:
                raise RuntimeError(f"Timestamp missing for block number {block_number:,}, hash {block_hash}, our timestamp table has {len(timestamps)} blocks") from e
            yield log


async def read_events(
    web3: Web3,
    start_block: int,
    end_block: int,
    events: List[ContractEvent],
    notify: Optional[ProgressUpdate],
    chunk_size: int = 100,
    context: Optional[LogContext] = None,
    extract_timestamps: Optional[Callable] = extract_timestamps_json_rpc,
    filter: Optional[Filter] = None,
) -> AsyncIterable[LogResult]:
    """Reads multiple events from the blockchain.

    Optimized to read multiple events fast.

    - Scans chains block by block

    - Returns events as a dict for optimal performance

    - Supports interactive progress bar

    - Reads all the events matching signature - any filtering must be done
      by the reader

    See `scripts/read-uniswap-v2-pairs-and-swaps.py` for a full example.

    Example:

    .. code-block:: python

        # HTTP 1.1 keep-alive
        session = requests.Session()

        json_rpc_url = os.environ["JSON_RPC_URL"]
        web3 = Web3(HTTPProvider(json_rpc_url, session=session))

        # Enable faster ujson reads
        patch_web3(web3)

        web3.middleware_onion.clear()

        # Get contracts
        Factory = get_contract(web3, "UniswapV2Factory.json")

        events = [
            Factory.events.PairCreated, # https://etherscan.io/txs?ea=0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f&topic0=0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9
        ]

        token_cache = TokenCache()

        start_block = 10_000_835  # Uni deployed
        end_block = 10_009_000  # The first pair created before this block

        # Read through the blog ran
        out = []
        for log_result in read_events(
            web3,
            start_block,
            end_block,
            events,
            None,
            chunk_size=1000,
            context=token_cache,
            extract_timestamps=None,
        ):
            out.append(decode_pair_created(log_result))

    :param web3:
        Web3 instance

    :param events:
        List of Web3.py contract event classes to scan for

    :param notify:
        Optional callback to be called before starting to scan each chunk

    :param start_block:
        First block to process (inclusive)

    :param end_block:
        Last block to process (inclusive)

    :param extract_timestamps:
        Override for different block timestamp extraction methods

    :param chunk_size:
        How many blocks to scan in one eth_getLogs call

    :param context:
        Passed to the all generated logs

    :param filter:
        Pass a custom event filter for the readers
    """

    assert type(start_block) == int
    assert type(end_block) == int

    total_events = 0

    # TODO: retry middleware makes an exception
    # assert len(web3.middleware_onion) == 0, f"Must not have any Web3 middleware installed to slow down scan, has {web3.middleware_onion.middlewares}"

    # Construct our bloom filter
    if filter is None:
        filter = prepare_filter(events)

    last_timestamp = None

    for block_num in range(start_block, end_block + 1, chunk_size):

        # Ping our master
        if notify is not None:
            notify(block_num, start_block, end_block, chunk_size, total_events, last_timestamp, context)

        last_of_chunk = min(end_block, block_num + chunk_size - 1)

        # logger.info("Extracting %d - %d", block_num, last_of_chunk)

        # Stream the events
        async for event in extract_events(web3, block_num, last_of_chunk, filter, context, extract_timestamps):
            last_timestamp = event.get("timestamp")
            total_events += 1
            yield event

