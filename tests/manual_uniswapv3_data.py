"""A sample script to fetch Uniswap v3 data."""
import os

from eth_defi.uniswap_v3.events import fetch_events_to_csv
from eth_defi.uniswap_v3.liquidity import create_tick_csv, create_tick_delta_csv
from eth_defi.event_reader.json_state import JSONFileScanState

json_rpc_url = os.environ["JSON_RPC_URL"]

fetch_events_to_csv(json_rpc_url, JSONFileScanState("./state.log"), output_folder=".")

tick_delta_csv = create_tick_delta_csv("./uniswap-v3-mint.csv", "./uniswap-v3-burn.csv", ".")

create_tick_csv("./uniswap-v3-tickdeltas.csv", ".")
