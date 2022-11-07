"""A sample script to fetch Uniswap v3 data."""
import os

from eth_defi.venus.events import fetch_events_to_csv, fetch_events_to_dataframe
from eth_defi.event_reader.json_state import JSONFileScanState


json_rpc_url = os.environ["BNB_CHAIN_JSON_RPC"]

# start_block = 22629320
# end_block = 22639320   #2286905201  #

start_block = 22837829 - 864000
end_block = 22837829   #2286905201

fetch_events_to_csv(json_rpc_url, JSONFileScanState("venus_events_state.log"), start_block=start_block, end_block=end_block, output_folder=".")
