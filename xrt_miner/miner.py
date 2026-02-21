"""Lighthouse management and XRT mining loop."""

import os
import time

from web3 import Web3

from . import abi as contract_abi
from . import signer


ESTIMATED_GAS_PER_CYCLE = 1_100_000  # calibrated after first batch
TRANSFER_TOPIC = Web3.keccak(text="Transfer(address,address,uint256)").hex()
# Observed gas per single liability (from pipeline data)
GAS_PER_CREATE = 790_000
GAS_PER_FINALIZE = 268_000
GAS_PER_LIABILITY = GAS_PER_CREATE + GAS_PER_FINALIZE


class XRTMiner:
    def __init__(self, w3: Web3, account, factory_address: str,
                 lighthouse_address: str | None = None,
                 priority_gwei: float = 1.0):
        self.w3 = w3
        self.account = account
        self.address = account.address
        self.private_key = account.key.hex()
        self.priority_gwei = priority_gwei

        self.factory = w3.eth.contract(
            address=Web3.to_checksum_address(factory_address),
            abi=contract_abi.FACTORY_ABI,
        )

        real_xrt = self.factory.functions.xrt().call()
        self.xrt = w3.eth.contract(
            address=Web3.to_checksum_address(real_xrt),
            abi=contract_abi.XRT_ABI,
        )
        click_echo(f"Factory XRT: {self.xrt.address}")

        self.uniswap = w3.eth.contract(
            address=Web3.to_checksum_address(contract_abi.UNISWAP_V2_ROUTER),
            abi=contract_abi.UNISWAP_V2_ROUTER_ABI,
        )
        self.chainlink = w3.eth.contract(
            address=Web3.to_checksum_address(contract_abi.CHAINLINK_ETH_USD),
            abi=contract_abi.CHAINLINK_ABI,
        )

        self.lighthouse = None
        self.lighthouse_address = None
        if lighthouse_address:
            self.set_lighthouse(lighthouse_address)

    def set_lighthouse(self, address: str):
        self.lighthouse_address = Web3.to_checksum_address(address)
        self.lighthouse = self.w3.eth.contract(
            address=self.lighthouse_address,
            abi=contract_abi.LIGHTHOUSE_ABI,
        )

    def xrt_to_eth(self, xrt_amount: int) -> int:
        """Get ETH value of xrt_amount (in wn) via Uniswap V2. Returns wei."""
        if xrt_amount == 0:
            return 0
        path = [
            self.xrt.address,
            Web3.to_checksum_address(contract_abi.WETH_ADDRESS),
        ]
        try:
            amounts = self.uniswap.functions.getAmountsOut(xrt_amount, path).call()
            return amounts[1]
        except Exception:
            return 0

    def get_eth_usd_price(self) -> float:
        """Get ETH/USD price from Chainlink oracle. Returns USD per ETH."""
        answer = self.chainlink.functions.latestAnswer().call()
        return answer / 1e8  # Chainlink ETH/USD has 8 decimals

    def _effective_batch_size(self, max_batch: int, max_cost_usd: float) -> int:
        """Calculate batch size based on current gas price and ETH/USD.
        Scales proportionally: if cost is 2x the limit, batch halves.
        Returns 0 if cost is too high even for a single liability."""
        gas_price = self.w3.eth.gas_price
        eth_usd = self.get_eth_usd_price()
        cost_per_liability_usd = gas_price * GAS_PER_LIABILITY / 1e18 * eth_usd
        if cost_per_liability_usd <= max_cost_usd:
            return max_batch
        effective = int(max_batch * max_cost_usd / cost_per_liability_usd)
        return max(0, effective)

    def check_profitability(self, gas_estimate: int = ESTIMATED_GAS_PER_CYCLE) -> dict:
        """Check if mining is profitable at current gas price and XRT/ETH rate."""
        gas_price = self.w3.eth.gas_price
        gas_cost = gas_price * gas_estimate

        xrt_minted = self.factory.functions.wnFromGas(gas_estimate).call()
        xrt_value = self.xrt_to_eth(xrt_minted)

        profit = xrt_value - gas_cost
        margin = (profit / gas_cost * 100) if gas_cost > 0 else 0

        return {
            "gas_price_gwei": gas_price / 1e9,
            "gas_estimate": gas_estimate,
            "gas_cost_wei": gas_cost,
            "gas_cost_eth": gas_cost / 1e18,
            "xrt_minted": xrt_minted,
            "xrt_value_wei": xrt_value,
            "xrt_value_eth": xrt_value / 1e18,
            "profit_wei": profit,
            "profit_eth": profit / 1e18,
            "profitable": profit > 0,
            "margin": margin,
        }

    def _build_tx(self, tx_func, eth_nonce: int, gas: int = 500_000,
                  value: int = 0) -> bytes:
        """Build and sign a transaction, return raw bytes. Does not send."""
        base_fee = self.w3.eth.gas_price
        prio_wei = self.w3.to_wei(self.priority_gwei, "gwei")
        max_fee = max(base_fee + prio_wei, self.w3.to_wei(1, "gwei"))
        priority_fee = min(prio_wei, max_fee)
        tx_params = {
            "from": self.address,
            "nonce": eth_nonce,
            "gas": gas,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": priority_fee,
        }
        if value > 0:
            tx_params["value"] = value
        tx = tx_func.build_transaction(tx_params)
        signed = self.account.sign_transaction(tx)
        return signed.raw_transaction

    def _send_tx(self, tx_func, **kwargs):
        """Build, sign, send a contract transaction. Raises on revert."""
        raw = self._build_tx(
            tx_func,
            self.w3.eth.get_transaction_count(self.address),
            kwargs.get("gas", 500_000),
            value=kwargs.get("value", 0),
        )
        tx_hash = self.w3.eth.send_raw_transaction(raw)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt["status"] != 1:
            raise RuntimeError(f"Transaction reverted. Hash: {tx_hash.hex()}")
        return receipt

    def create_lighthouse(self, name: str, minimal_stake: int, timeout_blocks: int) -> str:
        """Create new lighthouse via Factory. Returns lighthouse address."""
        click_echo(f"Creating lighthouse '{name}' (stake={minimal_stake}, timeout={timeout_blocks})...")

        receipt = self._send_tx(
            self.factory.functions.createLighthouse(minimal_stake, timeout_blocks, name),
            gas=1_500_000,
        )

        logs = self.factory.events.NewLighthouse().process_receipt(receipt)
        if not logs:
            raise RuntimeError(f"createLighthouse tx succeeded but no NewLighthouse event found. Hash: {receipt['transactionHash'].hex()}")

        lh_address = logs[0]["args"]["lighthouse"]
        click_echo(f"Lighthouse created at {lh_address}")
        self.set_lighthouse(lh_address)
        return lh_address

    def _ensure_allowance(self, spender: str, amount: int):
        """Approve XRT spending if current allowance is insufficient."""
        current = self.xrt.functions.allowance(self.address, spender).call()
        if current < amount:
            click_echo(f"Approving {amount} XRT for {spender}...")
            self._send_tx(
                self.xrt.functions.approve(spender, amount),
                gas=60_000,
            )

    def stake(self, amount: int):
        """Approve XRT and call lighthouse.refill(amount)."""
        if not self.lighthouse:
            raise RuntimeError("No lighthouse set")
        self._ensure_allowance(self.lighthouse_address, amount)
        click_echo(f"Staking {amount} XRT...")
        self._send_tx(self.lighthouse.functions.refill(amount), gas=200_000)
        click_echo("Staked.")

    def unstake(self, amount: int):
        """Call lighthouse.withdraw(amount)."""
        if not self.lighthouse:
            raise RuntimeError("No lighthouse set")
        click_echo(f"Withdrawing {amount} XRT from stake...")
        self._send_tx(self.lighthouse.functions.withdraw(amount), gas=100_000)
        click_echo("Withdrawn.")

    def _wait_for_timeout(self):
        """Wait until lighthouse timeout has passed so quota resets."""
        keep_alive = self.lighthouse.functions.keepAliveBlock().call()
        timeout = self.lighthouse.functions.timeoutInBlocks().call()
        current_block = self.w3.eth.block_number
        target = keep_alive + timeout + 1
        if current_block >= target:
            return
        blocks_to_wait = target - current_block
        wait_seconds = blocks_to_wait * 12
        click_echo(f"  Waiting ~{blocks_to_wait} blocks ({wait_seconds}s) for quota reset...")
        time.sleep(wait_seconds)

    def _ensure_stake(self, needed_quota: int):
        """Make sure we have enough stake for the given quota. Stakes from balance if possible."""
        my_stake = self.lighthouse.functions.stakes(self.address).call()
        min_stake = self.lighthouse.functions.minimalStake().call()
        needed = needed_quota * min_stake
        if my_stake >= needed:
            return
        extra = needed - my_stake
        xrt_bal = self.xrt.functions.balanceOf(self.address).call()
        if xrt_bal < extra:
            click_echo(f"  Need {extra} wn stake but only {xrt_bal} XRT available (have {my_stake} staked)")
            if xrt_bal > 0:
                extra = xrt_bal
            else:
                return
        click_echo(f"  Staking {extra} more wn (total will be {my_stake + extra})...")
        self.stake(extra)

    def mine_batch(self, batch_size: int) -> tuple[int, int]:
        """
        Mine a batch of liabilities. Returns (total_gas_used, total_xrt_minted).
        1. Pre-sign all demand/offer pairs with incrementing factory nonces
        2. Fire all createLiability txs rapidly
        3. Wait for receipts, parse liability addresses
        4. Wait for quota reset
        5. Fire all finalizeLiability txs rapidly
        6. Wait for receipts, sum XRT from Transfer events
        """
        if not self.lighthouse:
            raise RuntimeError("No lighthouse set")

        token = self.xrt.address
        cost = 0
        validator = signer.ZERO_ADDRESS
        validator_fee = 0
        lighthouse_fee = 0

        current_block = self.w3.eth.block_number
        deadline = current_block + 200

        factory_nonce = self.factory.functions.nonceOf(self.address).call()
        eth_nonce = self.w3.eth.get_transaction_count(self.address)

        # --- Phase 1: Build & send all createLiability txs ---
        click_echo(f"  Phase 1: sending {batch_size} createLiability txs...")
        create_hashes = []
        for i in range(batch_size):
            model = os.urandom(34)
            objective = os.urandom(34)

            demand_nonce = factory_nonce + 2 * i
            offer_nonce = factory_nonce + 2 * i + 1

            demand = signer.build_demand(
                model, objective, token, cost,
                self.lighthouse_address, validator, validator_fee,
                deadline, demand_nonce, self.address, self.private_key,
            )
            offer = signer.build_offer(
                model, objective, token, cost,
                validator, self.lighthouse_address, lighthouse_fee,
                deadline, offer_nonce, self.address, self.private_key,
            )

            raw = self._build_tx(
                self.lighthouse.functions.createLiability(demand, offer),
                eth_nonce + i,
                gas=1_500_000,
            )
            tx_hash = self.w3.eth.send_raw_transaction(raw)
            create_hashes.append(tx_hash)

        # Wait for all createLiability receipts
        click_echo(f"  Waiting for {batch_size} createLiability confirmations...")
        liabilities = []
        create_gas = 0
        for i, tx_hash in enumerate(create_hashes):
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            if receipt["status"] != 1:
                click_echo(f"  createLiability[{i}] REVERTED: {tx_hash.hex()}")
                continue
            create_gas += receipt["gasUsed"]
            logs = self.factory.events.NewLiability().process_receipt(receipt)
            if logs:
                liabilities.append(logs[0]["args"]["liability"])

        click_echo(f"  Created {len(liabilities)}/{batch_size} liabilities, gas={create_gas}")

        if not liabilities:
            return create_gas, 0

        # --- Phase 2: Wait for quota reset ---
        self._wait_for_timeout()

        # --- Phase 3: Build & send all finalizeLiability txs ---
        click_echo(f"  Phase 2: sending {len(liabilities)} finalizeLiability txs...")
        eth_nonce = self.w3.eth.get_transaction_count(self.address)
        finalize_hashes = []
        for i, liability_addr in enumerate(liabilities):
            result_data = os.urandom(34)
            result_sig = signer.build_result(
                liability_addr, result_data, True, self.private_key,
            )
            raw = self._build_tx(
                self.lighthouse.functions.finalizeLiability(
                    liability_addr, result_data, True, result_sig,
                ),
                eth_nonce + i,
                gas=400_000,
            )
            tx_hash = self.w3.eth.send_raw_transaction(raw)
            finalize_hashes.append(tx_hash)

        # Wait for all finalizeLiability receipts, parse XRT minted
        click_echo(f"  Waiting for {len(liabilities)} finalizeLiability confirmations...")
        finalize_gas = 0
        total_xrt = 0
        for i, tx_hash in enumerate(finalize_hashes):
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            if receipt["status"] != 1:
                click_echo(f"  finalizeLiability[{i}] REVERTED: {tx_hash.hex()}")
                continue
            finalize_gas += receipt["gasUsed"]
            for log in receipt["logs"]:
                if (log["address"].lower() == self.xrt.address.lower()
                        and len(log["topics"]) >= 3
                        and log["topics"][0].hex() == TRANSFER_TOPIC):
                    total_xrt += int(log["data"].hex(), 16)

        total_gas = create_gas + finalize_gas
        click_echo(f"  Finalized {len(liabilities)}, gas={finalize_gas}, XRT minted={total_xrt} wn ({total_xrt/1e9:.2f} XRT)")
        return total_gas, total_xrt

    def mine_batch_loop(self, batch_size: int = 20, eth_budget: float = 1.0,
                        sell_every_xrt: float = 1000.0, slippage: float = 0.05):
        """
        Continuous batch mining with auto-sell.
        eth_budget: stop after spending this much ETH on gas.
        sell_every_xrt: swap XRT→ETH after accumulating this many XRT.
        """
        click_echo(f"=== Batch mining: batch={batch_size}, budget={eth_budget} ETH, sell every {sell_every_xrt} XRT ===")

        self._ensure_stake(batch_size)

        eth_start = self.w3.eth.get_balance(self.address)
        total_gas = 0
        total_xrt_minted = 0
        total_eth_from_sells = 0
        batch_num = 0
        xrt_since_last_sell = 0

        try:
            while True:
                eth_now = self.w3.eth.get_balance(self.address)
                eth_spent = (eth_start - eth_now) / 1e18
                if eth_spent >= eth_budget:
                    click_echo(f"\nBudget reached: {eth_spent:.6f} / {eth_budget} ETH")
                    break

                batch_num += 1
                click_echo(f"\n--- Batch {batch_num} (spent {eth_spent:.4f}/{eth_budget} ETH) ---")

                try:
                    gas, xrt = self.mine_batch(batch_size)
                    total_gas += gas
                    total_xrt_minted += xrt
                    xrt_since_last_sell += xrt

                    click_echo(
                        f"  BATCH {batch_num}: gas={gas}, XRT={xrt/1e9:.2f}, "
                        f"total_XRT={total_xrt_minted/1e9:.2f}, ETH_spent={eth_spent:.4f}"
                    )

                    # Auto-sell
                    if xrt_since_last_sell / 1e9 >= sell_every_xrt:
                        xrt_bal = self.xrt.functions.balanceOf(self.address).call()
                        if xrt_bal > 0:
                            click_echo(f"\n  >>> Selling {xrt_bal/1e9:.2f} XRT...")
                            try:
                                eth_received = self.swap_xrt_to_eth(xrt_bal, slippage)
                                total_eth_from_sells += eth_received
                                xrt_since_last_sell = 0
                                click_echo(f"  >>> Received ~{eth_received/1e18:.6f} ETH (total sells: {total_eth_from_sells/1e18:.6f} ETH)")
                            except Exception as e:
                                click_echo(f"  >>> Sell failed: {e}")

                except Exception as e:
                    click_echo(f"  Batch {batch_num} error: {e}")
                    click_echo("  Retrying in 15 seconds...")
                    time.sleep(15)

        except KeyboardInterrupt:
            pass

        eth_end = self.w3.eth.get_balance(self.address)
        xrt_end = self.xrt.functions.balanceOf(self.address).call()
        eth_total_spent = (eth_start - eth_end) / 1e18

        click_echo(f"\n{'='*60}")
        click_echo(f"SUMMARY")
        click_echo(f"  Batches completed:  {batch_num}")
        click_echo(f"  Total XRT minted:   {total_xrt_minted/1e9:.2f} XRT")
        click_echo(f"  XRT on hand:        {xrt_end/1e9:.2f} XRT")
        click_echo(f"  ETH from sells:     {total_eth_from_sells/1e18:.6f} ETH")
        click_echo(f"  ETH spent (net):    {eth_total_spent:.6f} ETH")
        click_echo(f"  Total gas used:     {total_gas}")
        click_echo(f"{'='*60}")

    def _build_create_txs(self, batch_size: int, eth_nonce: int) -> tuple[list, list]:
        """Pre-sign batch_size createLiability txs. Returns (tx_hashes, raw_data_for_later)."""
        token = self.xrt.address
        factory_nonce = self.factory.functions.nonceOf(self.address).call()
        current_block = self.w3.eth.block_number
        deadline = current_block + 300

        hashes = []
        # Store result_data per liability for later finalization
        result_datas = []
        for i in range(batch_size):
            model = os.urandom(34)
            objective = os.urandom(34)

            demand = signer.build_demand(
                model, objective, token, 0,
                self.lighthouse_address, signer.ZERO_ADDRESS, 0,
                deadline, factory_nonce + 2 * i, self.address, self.private_key,
            )
            offer = signer.build_offer(
                model, objective, token, 0,
                signer.ZERO_ADDRESS, self.lighthouse_address, 0,
                deadline, factory_nonce + 2 * i + 1, self.address, self.private_key,
            )

            raw = self._build_tx(
                self.lighthouse.functions.createLiability(demand, offer),
                eth_nonce + i,
                gas=1_500_000,
            )
            tx_hash = self.w3.eth.send_raw_transaction(raw)
            hashes.append(tx_hash)
            result_datas.append(os.urandom(34))

        return hashes, result_datas

    def _build_finalize_txs(self, liabilities: list, result_datas: list,
                            eth_nonce: int) -> list:
        """Pre-sign finalizeLiability txs. Returns tx_hashes."""
        hashes = []
        for i, (liability_addr, result_data) in enumerate(zip(liabilities, result_datas)):
            result_sig = signer.build_result(
                liability_addr, result_data, True, self.private_key,
            )
            raw = self._build_tx(
                self.lighthouse.functions.finalizeLiability(
                    liability_addr, result_data, True, result_sig,
                ),
                eth_nonce + i,
                gas=400_000,
            )
            tx_hash = self.w3.eth.send_raw_transaction(raw)
            hashes.append(tx_hash)
        return hashes

    def _collect_create_receipts(self, hashes: list) -> tuple[list, int]:
        """Wait for createLiability receipts. Returns (liability_addresses, gas_used)."""
        liabilities = []
        gas = 0
        for i, tx_hash in enumerate(hashes):
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            if receipt["status"] != 1:
                click_echo(f"    create[{i}] REVERTED")
                continue
            gas += receipt["gasUsed"]
            logs = self.factory.events.NewLiability().process_receipt(receipt)
            if logs:
                liabilities.append(logs[0]["args"]["liability"])
        return liabilities, gas

    def _collect_finalize_receipts(self, hashes: list) -> tuple[int, int]:
        """Wait for finalizeLiability receipts. Returns (gas_used, xrt_minted)."""
        gas = 0
        xrt = 0
        for i, tx_hash in enumerate(hashes):
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            if receipt["status"] != 1:
                click_echo(f"    finalize[{i}] REVERTED")
                continue
            gas += receipt["gasUsed"]
            for log in receipt["logs"]:
                if (log["address"].lower() == self.xrt.address.lower()
                        and len(log["topics"]) >= 3
                        and log["topics"][0].hex() == TRANSFER_TOPIC):
                    xrt += int(log["data"].hex(), 16)
        return gas, xrt

    def mine_pipeline_loop(self, batch_size: int = 20, eth_budget: float = 1.0,
                           sell_every_xrt: float = 1000.0, slippage: float = 0.05,
                           max_cost_usd: float = 0.0):
        """
        Pipeline mining: overlap finalize(prev) + create(next) in the same block.
        Each round sends batch_size finalize + batch_size create = 2*batch_size txs.
        max_cost_usd: if > 0, dynamically scale batch size based on gas cost per liability.
        """
        cost_info = ""
        if max_cost_usd > 0:
            cost_info = f", max ${max_cost_usd:.2f}/liability"
        click_echo(f"=== Pipeline mining: batch={batch_size}, budget={eth_budget} ETH, sell every {sell_every_xrt} XRT{cost_info} ===")

        # Need 2*batch_size quota (finalize + create in same block)
        self._ensure_stake(batch_size * 2)

        eth_start = self.w3.eth.get_balance(self.address)
        total_xrt_minted = 0
        total_eth_from_sells = 0
        total_gas = 0
        batch_num = 0
        xrt_since_last_sell = 0

        # Bootstrap: first batch is create-only
        prev_liabilities = None
        prev_result_datas = None

        try:
            while True:
                eth_now = self.w3.eth.get_balance(self.address)
                eth_spent = (eth_start - eth_now) / 1e18
                if eth_spent >= eth_budget:
                    click_echo(f"\nBudget reached: {eth_spent:.6f} / {eth_budget} ETH")
                    break

                batch_num += 1

                # Dynamic batch sizing based on gas cost
                current_batch = batch_size
                if max_cost_usd > 0:
                    current_batch = self._effective_batch_size(batch_size, max_cost_usd)
                    if current_batch == 0:
                        gas_price = self.w3.eth.gas_price
                        eth_usd = self.get_eth_usd_price()
                        cost_usd = gas_price * GAS_PER_LIABILITY / 1e18 * eth_usd
                        click_echo(
                            f"\n  Gas too expensive: ${cost_usd:.2f}/liability "
                            f"(limit ${max_cost_usd:.2f}), ETH=${eth_usd:.0f}, "
                            f"gas={gas_price/1e9:.1f} gwei. Waiting 30s..."
                        )
                        batch_num -= 1
                        time.sleep(30)
                        continue
                    if current_batch < batch_size:
                        gas_price = self.w3.eth.gas_price
                        eth_usd = self.get_eth_usd_price()
                        cost_usd = gas_price * GAS_PER_LIABILITY / 1e18 * eth_usd
                        click_echo(
                            f"  Throttle: ${cost_usd:.2f}/liability > ${max_cost_usd:.2f} limit → "
                            f"batch {batch_size}→{current_batch}"
                        )

                eth_nonce = self.w3.eth.get_transaction_count(self.address)

                try:
                    if prev_liabilities is None:
                        # First round: create only
                        click_echo(f"\n--- Round {batch_num}: CREATE {current_batch} (bootstrap) ---")
                        create_hashes, result_datas = self._build_create_txs(current_batch, eth_nonce)
                        click_echo(f"  Sent {current_batch} create txs, waiting...")
                        liabilities, create_gas = self._collect_create_receipts(create_hashes)
                        click_echo(f"  Created {len(liabilities)}/{current_batch}, gas={create_gas}")
                        total_gas += create_gas
                        prev_liabilities = liabilities
                        prev_result_datas = result_datas[:len(liabilities)]
                    else:
                        # Pipeline: finalize(prev) + create(new) simultaneously
                        n_fin = len(prev_liabilities)
                        click_echo(f"\n--- Round {batch_num}: FINALIZE {n_fin} + CREATE {current_batch} (spent {eth_spent:.4f} ETH) ---")

                        # Send finalize txs first (lower nonces)
                        fin_hashes = self._build_finalize_txs(
                            prev_liabilities, prev_result_datas, eth_nonce,
                        )
                        # Then create txs (higher nonces, same block)
                        create_hashes, result_datas = self._build_create_txs(
                            current_batch, eth_nonce + n_fin,
                        )
                        click_echo(f"  Sent {n_fin}+{current_batch} txs, waiting...")

                        # Collect finalize results
                        fin_gas, xrt_minted = self._collect_finalize_receipts(fin_hashes)
                        total_xrt_minted += xrt_minted
                        xrt_since_last_sell += xrt_minted
                        total_gas += fin_gas

                        # Collect create results
                        liabilities, create_gas = self._collect_create_receipts(create_hashes)
                        total_gas += create_gas

                        click_echo(
                            f"  ROUND {batch_num}: fin_gas={fin_gas} create_gas={create_gas} "
                            f"XRT={xrt_minted/1e9:.2f} total={total_xrt_minted/1e9:.2f}"
                        )

                        # Try to top up stake if needed
                        self._ensure_stake(current_batch * 2)

                        prev_liabilities = liabilities
                        prev_result_datas = result_datas[:len(liabilities)]

                        # Auto-sell
                        if xrt_since_last_sell / 1e9 >= sell_every_xrt:
                            xrt_bal = self.xrt.functions.balanceOf(self.address).call()
                            if xrt_bal > 0:
                                click_echo(f"\n  >>> Selling {xrt_bal/1e9:.2f} XRT...")
                                try:
                                    eth_received = self.swap_xrt_to_eth(xrt_bal, slippage)
                                    total_eth_from_sells += eth_received
                                    xrt_since_last_sell = 0
                                    click_echo(f"  >>> Received ~{eth_received/1e18:.6f} ETH (total sells: {total_eth_from_sells/1e18:.6f} ETH)")
                                except Exception as e:
                                    click_echo(f"  >>> Sell failed: {e}")

                except Exception as e:
                    click_echo(f"  Round {batch_num} error: {e}")
                    click_echo("  Retrying in 15s...")
                    prev_liabilities = None
                    prev_result_datas = None
                    time.sleep(15)

        except KeyboardInterrupt:
            pass

        # Finalize any remaining liabilities
        if prev_liabilities:
            click_echo(f"\n--- Finalizing {len(prev_liabilities)} remaining liabilities ---")
            try:
                eth_nonce = self.w3.eth.get_transaction_count(self.address)
                fin_hashes = self._build_finalize_txs(
                    prev_liabilities, prev_result_datas, eth_nonce,
                )
                fin_gas, xrt_minted = self._collect_finalize_receipts(fin_hashes)
                total_xrt_minted += xrt_minted
                total_gas += fin_gas
            except Exception as e:
                click_echo(f"  Final finalize error: {e}")

        # Final sell
        xrt_bal = self.xrt.functions.balanceOf(self.address).call()
        if xrt_bal > 0:
            click_echo(f"\n  >>> Final sell: {xrt_bal/1e9:.2f} XRT...")
            try:
                eth_received = self.swap_xrt_to_eth(xrt_bal, slippage)
                total_eth_from_sells += eth_received
            except Exception as e:
                click_echo(f"  >>> Final sell failed: {e}")

        eth_end = self.w3.eth.get_balance(self.address)
        click_echo(f"\n{'='*60}")
        click_echo(f"PIPELINE SUMMARY")
        click_echo(f"  Rounds:            {batch_num}")
        click_echo(f"  XRT minted:        {total_xrt_minted/1e9:.2f}")
        click_echo(f"  ETH from sells:    {total_eth_from_sells/1e18:.6f}")
        click_echo(f"  ETH profit:        {(eth_end - eth_start)/1e18:.6f}")
        click_echo(f"  Gas used:          {total_gas}")
        click_echo(f"{'='*60}")

    def swap_eth_to_xrt(self, xrt_amount: int, slippage: float = 0.05) -> int:
        """Buy exact xrt_amount (in wn) via Uniswap V2. Returns ETH spent (wei)."""
        path = [
            Web3.to_checksum_address(contract_abi.WETH_ADDRESS),
            self.xrt.address,
        ]
        amounts_in = self.uniswap.functions.getAmountsIn(xrt_amount, path).call()
        eth_needed = int(amounts_in[0] * (1 + slippage))

        click_echo(f"  Buying {xrt_amount/1e9:.2f} XRT for ~{amounts_in[0]/1e18:.6f} ETH (max: {eth_needed/1e18:.6f})")

        deadline = self.w3.eth.get_block("latest")["timestamp"] + 300
        receipt = self._send_tx(
            self.uniswap.functions.swapExactETHForTokens(
                xrt_amount, path, self.address, deadline,
            ),
            gas=200_000,
            value=eth_needed,
        )

        click_echo(f"  Buy done. Gas: {receipt['gasUsed']}")
        return amounts_in[0]

    def swap_xrt_to_eth(self, xrt_amount: int, slippage: float = 0.05) -> int:
        """Swap XRT → ETH via Uniswap V2. Returns ETH received (wei)."""
        path = [
            self.xrt.address,
            Web3.to_checksum_address(contract_abi.WETH_ADDRESS),
        ]
        amounts_out = self.uniswap.functions.getAmountsOut(xrt_amount, path).call()
        min_eth = int(amounts_out[1] * (1 - slippage))

        click_echo(f"  Swapping {xrt_amount/1e9:.2f} XRT → ~{amounts_out[1]/1e18:.6f} ETH (min: {min_eth/1e18:.6f})")

        self._ensure_allowance(contract_abi.UNISWAP_V2_ROUTER, xrt_amount)

        deadline = self.w3.eth.get_block("latest")["timestamp"] + 300
        receipt = self._send_tx(
            self.uniswap.functions.swapExactTokensForETH(
                xrt_amount, min_eth, path, self.address, deadline,
            ),
            gas=200_000,
        )

        click_echo(f"  Swap done. Gas: {receipt['gasUsed']}")
        return amounts_out[1]

    def mine_once(self, model: bytes | None = None, objective: bytes | None = None) -> tuple[str, int]:
        """Single mining cycle. Returns (liability_address, xrt_minted)."""
        if not self.lighthouse:
            raise RuntimeError("No lighthouse set")

        if model is None:
            model = os.urandom(34)
        if objective is None:
            objective = os.urandom(34)

        token = self.xrt.address
        cost = 0
        validator = signer.ZERO_ADDRESS
        validator_fee = 0
        lighthouse_fee = 0
        result_data = os.urandom(34)

        current_block = self.w3.eth.block_number
        deadline = current_block + 100
        nonce = self.factory.functions.nonceOf(self.address).call()

        demand = signer.build_demand(
            model, objective, token, cost,
            self.lighthouse_address, validator, validator_fee,
            deadline, nonce, self.address, self.private_key,
        )
        offer = signer.build_offer(
            model, objective, token, cost,
            validator, self.lighthouse_address, lighthouse_fee,
            deadline, nonce + 1, self.address, self.private_key,
        )

        self._wait_for_timeout()

        receipt = self._send_tx(
            self.lighthouse.functions.createLiability(demand, offer),
            gas=1_500_000,
        )

        logs = self.factory.events.NewLiability().process_receipt(receipt)
        if not logs:
            raise RuntimeError(f"createLiability succeeded but no NewLiability event. Hash: {receipt['transactionHash'].hex()}")

        liability_address = logs[0]["args"]["liability"]

        result_sig = signer.build_result(
            liability_address, result_data, True, self.private_key,
        )

        receipt2 = self._send_tx(
            self.lighthouse.functions.finalizeLiability(
                liability_address, result_data, True, result_sig,
            ),
            gas=400_000,
        )

        xrt_minted = 0
        for log in receipt2["logs"]:
            if (log["address"].lower() == self.xrt.address.lower()
                    and len(log["topics"]) >= 3
                    and log["topics"][0].hex() == TRANSFER_TOPIC):
                xrt_minted = int(log["data"].hex(), 16)
                break

        gas_used = receipt["gasUsed"] + receipt2["gasUsed"]
        click_echo(
            f"Mined {liability_address} | gas={gas_used} | XRT={xrt_minted/1e9:.2f}"
        )
        return liability_address, xrt_minted

    def mine_loop(self, count: int | None = None, model: bytes | None = None,
                  objective: bytes | None = None, min_margin: float = 0.0,
                  force: bool = False):
        """Continuous single mining. count=None → infinite."""
        i = 0
        total_minted = 0
        try:
            while count is None or i < count:
                if not force:
                    prof = self.check_profitability()
                    if not prof["profitable"] or prof["margin"] < min_margin:
                        click_echo(
                            f"Unprofitable: margin={prof['margin']:.1f}%. Waiting 60s..."
                        )
                        time.sleep(60)
                        continue
                try:
                    _, minted = self.mine_once(model, objective)
                    total_minted += minted
                    i += 1
                    click_echo(f"[{i}] total: {total_minted/1e9:.2f} XRT")
                except Exception as e:
                    click_echo(f"Error cycle {i + 1}: {e}")
                    time.sleep(15)
        except KeyboardInterrupt:
            click_echo(f"\nStopped. {i} liabilities, {total_minted/1e9:.2f} XRT")

    def status(self) -> dict:
        """Return status info."""
        info = {
            "address": self.address,
            "xrt_address": self.xrt.address,
            "xrt_balance": self.xrt.functions.balanceOf(self.address).call(),
            "eth_balance": self.w3.eth.get_balance(self.address),
            "factory": self.factory.address,
            "factory_gas_price": self.factory.functions.gasPrice().call(),
            "total_gas_consumed": self.factory.functions.totalGasConsumed().call(),
        }

        info["estimated_xrt_per_cycle"] = self.factory.functions.wnFromGas(ESTIMATED_GAS_PER_CYCLE).call()
        info["profitability"] = self.check_profitability()

        if self.lighthouse:
            info["lighthouse"] = self.lighthouse_address
            info["minimal_stake"] = self.lighthouse.functions.minimalStake().call()
            info["timeout_blocks"] = self.lighthouse.functions.timeoutInBlocks().call()
            info["my_stake"] = self.lighthouse.functions.stakes(self.address).call()
            info["my_index"] = self.lighthouse.functions.indexOf(self.address).call()
            info["marker"] = self.lighthouse.functions.marker().call()
            info["quota"] = self.lighthouse.functions.quota().call()
            info["keep_alive_block"] = self.lighthouse.functions.keepAliveBlock().call()
            info["is_lighthouse"] = self.factory.functions.isLighthouse(self.lighthouse_address).call()

        return info


def click_echo(msg: str):
    import click
    click.echo(msg)
