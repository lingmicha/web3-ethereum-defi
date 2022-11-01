"""A sample script to fetch Uniswap v3 data."""
import os

from eth_defi.venus.events import fetch_events_to_csv
from eth_defi.event_reader.json_state import JSONFileScanState

json_rpc_url = os.environ["BNB_CHAIN_JSON_RPC"]

fetch_events_to_csv(json_rpc_url, JSONFileScanState("./state.log"), output_folder=".")

