# XRT Classic Miner

Automated XRT token emission mining tool for [Robonomics Network](https://robonomics.network/) v5 contracts on Ethereum mainnet. Exploits the gas-proportional token emission mechanism built into Robonomics Factory: each liability creation and finalization triggers XRT minting proportional to gas consumed, scaled by the Factory's internal SMMA (Smoothed Moving Average) gas price.

For the full analysis, see the accompanying paper: [XRT Emission as Proof-of-Work Mining: An Experimental Analysis of Robonomics Network Token Economics](paper/xrt_emission_experiment.pdf).

## Requirements

- Python 3.10+
- Ethereum account funded with ETH (for gas)
- Ethereum RPC endpoint (HTTP or WebSocket)

## Installation

```bash
git clone https://github.com/ensrationis/xrt-classic-miner.git
cd xrt-classic-miner
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Configuration

Copy the example config and fill in your values:

```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml`:
```yaml
rpc_url: "https://your-rpc-endpoint"
private_key: "0x..."
lighthouse: "0x..."   # after setup
factory: "0x7e384AD1FE06747594a6102EE5b377b273DC1225"
xrt: "0x7dE91B204C1c737bcEe6F000AAA6569Cf7061cb7"
```

All options can also be passed via CLI flags (`--rpc`, `--key`) or environment variables (`RPC_URL`, `PRIVATE_KEY`).

## Usage

### 1. Check status and profitability

```bash
xrt-miner --config config.yaml status
```

Shows ETH/XRT balances, Factory SMMA, estimated emission per cycle, and profitability verdict. Mining is profitable when SMMA is significantly higher than the current gas price (ratio > 3x is the sweet spot).

### 2. Buy XRT for staking

You need at least 1 XRT staked on a lighthouse to mine. Buy via the built-in Uniswap V2 integration:

```bash
xrt-miner --config config.yaml buy 1.0
```

### 3. Create lighthouse and stake

```bash
xrt-miner --config config.yaml setup \
  --name "my-lighthouse" \
  --stake 1000000000 \
  --min-stake 1 \
  --timeout 1
```

The stake amount is in wn (1 XRT = 10^9 wn). Add the resulting lighthouse address to your `config.yaml`.

### 4. Mine

**Sequential** (one liability at a time):
```bash
xrt-miner --config config.yaml mine
```

**Batch** (N liabilities per round, auto-sell):
```bash
xrt-miner --config config.yaml batch --batch-size 20 --budget 0.5 --sell-every 1000
```

**Pipeline** (finalize previous + create next in same block, 2x throughput):
```bash
xrt-miner --config config.yaml pipeline --batch-size 20 --budget 0.5 --sell-every 1000
```

Use `--priority-fee` (global option, in gwei) to control transaction priority. For mining, 0.001 gwei is sufficient; for Uniswap swaps, use 0.1+ gwei.

### 5. Sell XRT

```bash
xrt-miner --config config.yaml swap --slippage 5
```

Sells entire XRT balance to ETH via Uniswap V2.

### 6. Withdraw stake

```bash
xrt-miner --config config.yaml withdraw 1000000000
```

## Contract Addresses (Ethereum Mainnet)

| Contract | Address |
|----------|---------|
| Factory (v5) | `0x7e384AD1FE06747594a6102EE5b377b273DC1225` |
| XRT Token | `0x7dE91B204C1c737bcEe6F000AAA6569Cf7061cb7` |
| Uniswap V2 Router | `0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D` |

## How It Works

The Robonomics Factory contract mints XRT tokens as emission when liabilities are created and finalized. The emission amount is calculated as:

```
emission = gasUsed * SMMA / 1e9
```

Where SMMA is the Factory's internal gas price tracker, updated with each transaction:

```
SMMA[n+1] = (SMMA[n] * 999 + tx.gasprice) / 1000
```

When the SMMA is much higher than the actual network gas price, each liability cycle produces XRT worth more than the gas cost to create it. The miner automates the full cycle: demand/offer signing, liability creation, finalization, and optional Uniswap selling.

## Links

- [Experiment Report](EXPERIMENT_REPORT.md) (Russian)
- [Paper: XRT Emission as Proof-of-Work Mining](paper/xrt_emission_experiment.pdf)
- [Robonomics Network](https://robonomics.network/)
- [XRT on Etherscan](https://etherscan.io/token/0x7dE91B204C1c737bcEe6F000AAA6569Cf7061cb7)
