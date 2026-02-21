"""CLI entry point for xrt-classic-miner."""

import click
import yaml
from eth_account import Account
from web3 import Web3

from .abi import FACTORY_ADDRESS
from .miner import XRTMiner


def load_config(path: str | None) -> dict:
    if path is None:
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def make_miner(rpc_url: str, private_key: str, factory: str,
               lighthouse: str | None,
               priority_gwei: float = 1.0) -> XRTMiner:
    if rpc_url.startswith("ws://") or rpc_url.startswith("wss://"):
        from web3 import Web3 as _W3
        w3 = _W3(Web3.LegacyWebSocketProvider(rpc_url))
    else:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise click.ClickException(f"Cannot connect to RPC: {rpc_url}")
    account = Account.from_key(private_key)
    return XRTMiner(w3, account, factory, lighthouse, priority_gwei=priority_gwei)


@click.group()
@click.option("--rpc", envvar="RPC_URL", default=None, help="Ethereum RPC URL")
@click.option("--key", envvar="PRIVATE_KEY", default=None, help="Private key (hex) or path to keyfile")
@click.option("--config", "config_path", default=None, type=click.Path(exists=True), help="Path to config.yaml")
@click.option("--lighthouse", default=None, help="Lighthouse contract address")
@click.option("--priority-fee", "priority_gwei", default=1.0, type=float, help="Priority fee in gwei (default: 1.0)")
@click.pass_context
def cli(ctx, rpc, key, config_path, lighthouse, priority_gwei):
    """XRT Classic Miner — mine XRT via Robonomics liability emission."""
    cfg = load_config(config_path)
    ctx.ensure_object(dict)

    ctx.obj["rpc_url"] = rpc or cfg.get("rpc_url")
    ctx.obj["lighthouse"] = lighthouse or cfg.get("lighthouse") or None
    ctx.obj["factory"] = cfg.get("factory", FACTORY_ADDRESS)
    ctx.obj["priority_gwei"] = priority_gwei
    ctx.obj["config"] = cfg

    raw_key = key or cfg.get("private_key")
    if raw_key and not raw_key.startswith("0x"):
        # Could be a hex key without prefix or a file path
        if len(raw_key) == 64 and all(c in "0123456789abcdefABCDEF" for c in raw_key):
            raw_key = "0x" + raw_key
        else:
            with open(raw_key) as f:
                raw_key = f.read().strip()
    ctx.obj["private_key"] = raw_key


def get_miner(ctx) -> XRTMiner:
    obj = ctx.obj
    if not obj.get("rpc_url"):
        raise click.ClickException("RPC URL required (--rpc or config rpc_url)")
    if not obj.get("private_key"):
        raise click.ClickException("Private key required (--key or config private_key)")
    return make_miner(
        obj["rpc_url"], obj["private_key"], obj["factory"],
        obj.get("lighthouse"),
        priority_gwei=obj.get("priority_gwei", 1.0),
    )


@cli.command()
@click.option("--name", required=True, help="Lighthouse name (ENS subdomain)")
@click.option("--stake", "stake_amount", required=True, type=int, help="XRT to stake (in wn, 1 XRT = 1e9 wn)")
@click.option("--min-stake", "minimal_stake", default=1, type=int, help="Lighthouse minimal stake requirement in wn (default: 1)")
@click.option("--timeout", "timeout_blocks", default=1, type=int, help="Timeout in blocks (default: 1)")
@click.pass_context
def setup(ctx, name, stake_amount, minimal_stake, timeout_blocks):
    """Create a new lighthouse and stake XRT."""
    miner = get_miner(ctx)
    lh_address = miner.create_lighthouse(name, minimal_stake, timeout_blocks)
    miner.stake(stake_amount)
    click.echo(f"\nSetup complete. Lighthouse: {lh_address}")
    click.echo("You can now run: xrt-miner mine")


@cli.command()
@click.option("--count", default=None, type=int, help="Number of liabilities to mine (default: infinite)")
@click.option("--model", default=None, help="Model bytes (hex)")
@click.option("--objective", default=None, help="Objective bytes (hex)")
@click.option("--min-margin", default=0.0, type=float, help="Minimum profit margin %% to mine (default: 0 = break-even)")
@click.option("--force", is_flag=True, default=False, help="Skip profitability check")
@click.pass_context
def mine(ctx, count, model, objective, min_margin, force):
    """Start mining XRT via liability creation & finalization."""
    miner = get_miner(ctx)
    if not miner.lighthouse:
        raise click.ClickException("Lighthouse address required (--lighthouse or config)")

    model_bytes = bytes.fromhex(model) if model else None
    objective_bytes = bytes.fromhex(objective) if objective else None

    click.echo(f"Mining on lighthouse {miner.lighthouse_address}")
    click.echo(f"Account: {miner.address}")
    if min_margin > 0:
        click.echo(f"Min margin: {min_margin}%")
    if count:
        click.echo(f"Count: {count}")
    else:
        click.echo("Count: infinite (Ctrl+C to stop)")

    miner.mine_loop(count=count, model=model_bytes, objective=objective_bytes,
                    min_margin=min_margin, force=force)


@cli.command()
@click.option("--batch-size", default=20, type=int, help="Liabilities per batch (default: 20)")
@click.option("--budget", default=1.0, type=float, help="ETH budget to spend on gas (default: 1.0)")
@click.option("--sell-every", default=1000.0, type=float, help="Sell XRT every N XRT minted (default: 1000)")
@click.option("--slippage", default=5.0, type=float, help="Slippage tolerance %% for sells (default: 5)")
@click.pass_context
def batch(ctx, batch_size, budget, sell_every, slippage):
    """Batch mine: create+finalize N liabilities per round, auto-sell XRT."""
    miner = get_miner(ctx)
    if not miner.lighthouse:
        raise click.ClickException("Lighthouse address required (--lighthouse or config)")
    miner.mine_batch_loop(
        batch_size=batch_size,
        eth_budget=budget,
        sell_every_xrt=sell_every,
        slippage=slippage / 100,
    )


@cli.command()
@click.option("--batch-size", default=20, type=int, help="Liabilities per batch (default: 20)")
@click.option("--budget", default=1.0, type=float, help="ETH budget to spend on gas (default: 1.0)")
@click.option("--sell-every", default=1000.0, type=float, help="Sell XRT every N XRT minted (default: 1000)")
@click.option("--slippage", default=5.0, type=float, help="Slippage tolerance %% (default: 5)")
@click.option("--max-cost", default=0.0, type=float, help="Max cost per liability in USD (0 = no limit)")
@click.pass_context
def pipeline(ctx, batch_size, budget, sell_every, slippage, max_cost):
    """Pipeline mine: finalize(prev)+create(next) in same block for 2x speed."""
    miner = get_miner(ctx)
    if not miner.lighthouse:
        raise click.ClickException("Lighthouse address required (--lighthouse or config)")
    miner.mine_pipeline_loop(
        batch_size=batch_size,
        eth_budget=budget,
        sell_every_xrt=sell_every,
        slippage=slippage / 100,
        max_cost_usd=max_cost,
    )


@cli.command()
@click.pass_context
def status(ctx):
    """Show XRT balance, stake, lighthouse info, emission estimate."""
    miner = get_miner(ctx)
    info = miner.status()

    click.echo(f"Account:             {info['address']}")
    click.echo(f"ETH balance:         {Web3.from_wei(info['eth_balance'], 'ether')} ETH")
    click.echo(f"XRT token:           {info['xrt_address']}")
    click.echo(f"XRT balance:         {info['xrt_balance']} wn ({info['xrt_balance'] / 1e9:.4f} XRT)")
    click.echo(f"Factory:             {info['factory']}")
    click.echo(f"Factory gas price:   {info['factory_gas_price']}")
    click.echo(f"Total gas consumed:  {info['total_gas_consumed']}")
    click.echo(f"Est. XRT per cycle:  {info['estimated_xrt_per_cycle']} wn")

    prof = info["profitability"]
    click.echo(f"\nProfitability (est. {prof['gas_estimate']} gas/cycle):")
    click.echo(f"  Gas price:         {prof['gas_price_gwei']:.2f} gwei")
    click.echo(f"  Gas cost:          {prof['gas_cost_eth']:.6f} ETH")
    click.echo(f"  XRT minted:        {prof['xrt_minted']} wn")
    click.echo(f"  XRT sell value:    {prof['xrt_value_eth']:.6f} ETH")
    click.echo(f"  Profit:            {prof['profit_eth']:.6f} ETH")
    click.echo(f"  Margin:            {prof['margin']:.1f}%")
    click.echo(f"  Verdict:           {'PROFITABLE' if prof['profitable'] else 'UNPROFITABLE'}")

    if "lighthouse" in info:
        click.echo(f"\nLighthouse:          {info['lighthouse']}")
        click.echo(f"  Is valid:          {info['is_lighthouse']}")
        click.echo(f"  Minimal stake:     {info['minimal_stake']} wn")
        click.echo(f"  Timeout:           {info['timeout_blocks']} blocks")
        click.echo(f"  My stake:          {info['my_stake']} wn")
        click.echo(f"  My index:          {info['my_index']}")
        click.echo(f"  Current marker:    {info['marker']}")
        click.echo(f"  Quota:             {info['quota']}")
        click.echo(f"  Keep-alive block:  {info['keep_alive_block']}")
    else:
        click.echo("\nNo lighthouse configured.")


@cli.command("stake")
@click.argument("amount", type=int)
@click.pass_context
def stake_cmd(ctx, amount):
    """Add stake to lighthouse."""
    miner = get_miner(ctx)
    if not miner.lighthouse:
        raise click.ClickException("Lighthouse address required")
    miner.stake(amount)


@cli.command("buy")
@click.argument("amount", type=float)
@click.option("--slippage", default=5.0, type=float, help="Slippage tolerance %% (default: 5)")
@click.pass_context
def buy_cmd(ctx, amount, slippage):
    """Buy XRT with ETH via Uniswap V2. Amount in XRT (e.g. 3.0)."""
    miner = get_miner(ctx)
    wn_amount = int(amount * 1e9)
    click.echo(f"Buying {amount} XRT ({wn_amount} wn)")
    miner.swap_eth_to_xrt(wn_amount, slippage=slippage / 100)
    xrt_bal = miner.xrt.functions.balanceOf(miner.address).call()
    click.echo(f"XRT balance: {xrt_bal} wn ({xrt_bal/1e9:.4f} XRT)")


@cli.command("swap")
@click.option("--amount", default=None, type=int, help="XRT amount in wn to swap (default: all)")
@click.option("--slippage", default=5.0, type=float, help="Slippage tolerance %% (default: 5)")
@click.pass_context
def swap_cmd(ctx, amount, slippage):
    """Swap XRT → ETH via Uniswap V2."""
    miner = get_miner(ctx)
    if amount is None:
        amount = miner.xrt.functions.balanceOf(miner.address).call()
        if amount == 0:
            raise click.ClickException("No XRT to swap")
    click.echo(f"Swapping {amount} wn ({amount/1e9:.4f} XRT)")
    miner.swap_xrt_to_eth(amount, slippage=slippage / 100)


@cli.command("withdraw")
@click.argument("amount", type=int)
@click.pass_context
def withdraw_cmd(ctx, amount):
    """Withdraw stake from lighthouse."""
    miner = get_miner(ctx)
    if not miner.lighthouse:
        raise click.ClickException("Lighthouse address required")
    miner.unstake(amount)


if __name__ == "__main__":
    cli()
