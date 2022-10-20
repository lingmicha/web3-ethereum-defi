# Compile all of Sushiswap fiels
sushi:
	# Get our mock up contracts to the compiler bundle
	@cp contracts/inhouse/* contracts/sushiswap/contracts
	@(cd contracts/sushiswap && yarn install && yarn build) > /dev/null
	@echo "Sushi is ready"

# Extract all compilation artifacts from Sushi to our abi/ dump
copy-sushi-abi: sushi
	@find contracts/sushiswap/artifacts/contracts -iname "*.json" -not -iname "*.dbg.json" -exec cp {} eth_defi/abi \;

# Compile v3 core and periphery
uniswapv3:
	@(cd contracts/uniswap-v3-core && yarn install && yarn compile) > /dev/null
	@(cd contracts/uniswap-v3-periphery && yarn install && yarn compile) > /dev/null

# Extract ABI and copied over to our abi/uniswap_v3/ folder
copy-uniswapv3-abi: uniswapv3
	@find contracts/uniswap-v3-core/artifacts/contracts -iname "*.json" -not -iname "*.dbg.json" -exec cp {} eth_defi/abi/uniswap_v3 \;
	@find contracts/uniswap-v3-periphery/artifacts/contracts -iname "*.json" -not -iname "*.dbg.json" -exec cp {} eth_defi/abi/uniswap_v3 \;

# Copy Aave V3 contract ABIs from their NPM package, remove library placeholders (__$ $__)
aavev3:
	@(cd contracts/aave-v3 && npm install)
	@mkdir -p eth_defi/abi/aave_v3
	@find contracts/aave-v3/node_modules/@aave/core-v3/artifacts -iname "*.json" -not -iname "*.dbg.json" -exec cp {} eth_defi/abi/aave_v3 \;
	@find eth_defi/abi/aave_v3 -iname "*.json" -exec sed -e 's/\$$__\|__\$$//g' -i {} \;

# Copy Compound V2 contract ABIs from their NPM package, remove library placeholders (__$ $__)
compoundv2:
#	#@export SADDLE_CONTRACTS="contracts/*.sol"
	@(cd contracts/compound-protocol && npm install && npm run compile)
#	@(export SADDLE_CONTRACTS="contracts/*.sol" && cd contracts/compound-protocol && npm run compile)
	@mkdir -p eth_defi/abi/compound_v2
#	@find contracts/compound-protocol/abi/ -iname "*.json" -not -iname "*.dbg.json" -exec cp {} eth_defi/abi/compound_v2 \;

# Compile all of Venues files
venus:
	@(cd contracts/venus-protocol && yarn install --lock-file && yarn compile) > /dev/null

# Extract ABI and copied over to our abi/venues/ folder
copy-venus-abi: venus
	@mkdir -p eth_defi/abi/venus
	@find contracts/venus-protocol/artifacts/contracts -iname "*.json" -not -iname "*.dbg.json" -exec cp {} eth_defi/abi/venus \;
#	@find eth_defi/abi/venus -iname "*.json" -exec sed -e 's/\$$__\|__\$$//g' -i {} \;

clean:
	@rm -rf contracts/sushiswap/artifacts/*
	@rm -rf contracts/uniswap-v3-core/artifacts/*
	@rm -rf contracts/uniswap-v3-periphery/artifacts/*

all: clean-docs copy-sushi-abi copy-uniswapv3-abi aavev3 compoundv2 copy-venus-abi build-docs

# Export the dependencies, so that Read the docs can build our API docs
# See: https://github.com/readthedocs/readthedocs.org/issues/4912
rtd-dep-export:
	poetry export --without-hashes --dev -f requirements.txt --output requirements-dev.txt

# Build docs locally
build-docs:
	@poetry install -E docs
	@(cd docs && make html)

# Nuke the old docs build to ensure all pages are regenerated
clean-docs:
	@rm -rf docs/source/api/_autosummary*
	@rm -rf docs/build/html

docs-all: clean-docs build-docs

# Manually generate table of contents for Github README
toc:
	cat README.md | scripts/gh-md-toc -

# Open web browser on docs on macOS
browse-docs-macos:
	@open docs/build/html/index.html
