"""A sample script to fetch Venus data."""
import os

from eth_defi.defi_lending.events import fetch_events_to_csv, fetch_events_to_dataframe
from eth_defi.event_reader.json_state import JSONFileScanState


json_rpc_url = os.environ["BNB_CHAIN_JSON_RPC"]

# start_block = 22629320
# end_block = 22639320   #2286905201  #

start_block = 22837829 - 864000 * 3
end_block = 22837829 - 864000 * 2 #2286905201

fetch_events_to_csv(
    json_rpc_url,
    56,
    'venus',
    JSONFileScanState("venus_events_state.log"),
    max_workers=2,
    start_block=start_block,
    end_block=end_block,
    output_folder=".")
