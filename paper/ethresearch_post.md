# Gas-Proportional Token Emission: A Fourth Paradigm for Web3 Issuance

Token emission mechanisms in blockchain systems follow a surprisingly narrow set of paradigms:

1. **Proof-of-Work** (Bitcoin): emission proportional to *hashrate* — external computational work
2. **Proof-of-Stake** (Ethereum post-Merge): emission proportional to *staked capital*
3. **Proof-of-Resource** (Filecoin, Render): emission proportional to *dedicated resources* (storage, GPU)

We present empirical analysis of a **fourth paradigm** deployed on Ethereum L1 since 2018: **emission proportional to EVM gas consumed by the protocol's own smart contracts**. This mechanism, implemented in the Robonomics Network Factory contract, uses the blockchain's native resource metering — gas — as the direct basis for token minting. To our knowledge, this is the only production system on Ethereum where a token's supply growth is algorithmically tied to the protocol's own gas utilization.

## The Mechanism

The Robonomics Factory (`0x7e384AD1FE06747594a6102EE5b377b273DC1225`) maintains an internal Smoothed Moving Average (SMMA) of observed `tx.gasprice` values, updated with every liability creation and finalization:

$$\text{SMMA}_{n+1} = \frac{\text{SMMA}_n \times 999 + \text{tx.gasprice}}{1000}$$

Token emission (in Wiener units, 1 XRT = $10^9$ Wn) is then:

$$\text{emission} = \text{gasUsed} \times \text{SMMA} \times \frac{10^9}{F_{\text{auction}}}$$

where $F_{\text{auction}}$ is a constant from the initial Dutch auction ($5.66 \times 10^{12}$). The whitepaper's core principle: *"Emission of 1 Wn = 1 gas utilized by Robonomics"* — the cost of computation on the world computer is internalized directly into the token supply.

This creates an **endogenous price oracle** — unlike Chainlink or Uniswap TWAP, the SMMA derives its signal entirely from the behavior of system participants (the actual `tx.gasprice` they pay), not from an external feed. The period-1000 smoothing provides resistance to single-block manipulation: the SMMA can shift at most $(\text{target} - \text{SMMA})/1000$ per call, making flash-loan-style attacks infeasible. This property was built into the design years before the DeFi exploits of 2020-2022 demonstrated why instantaneous price manipulation is dangerous.

## The Experiment

We revisited this mechanism in February 2026, eight years after deployment, under conditions radically different from the design era. Ethereum gas prices have decreased ~100x (from 20-200 gwei in 2018 to ~0.25 gwei in 2026), fundamentally altering the economic equilibrium.

We developed [xrt-classic-miner](https://github.com/ensrationis/xrt-classic-miner), an open-source tool implementing the complete Robonomics liability lifecycle, and conducted a controlled experiment on mainnet:

**Phase 1 — SMMA Pump:** 448 contract calls at 10 gwei priority fee, inflating SMMA from 1.03 to ~4.0 gwei (3.88x amplification). Cost: 2.27 ETH.

**Phase 2 — Mine:** 1,360 liabilities at 1 gwei priority fee, harvesting elevated emission as SMMA decayed. Mined: 24,190 XRT. Revenue from Uniswap V2 sales: 0.841 ETH.

**Net result:** -0.342 ETH (~$665 loss). The experiment was profitable in its mining phase but net-negative due to the pump cost — a research expense to characterize the mechanism's behavior.

### Key Findings

**1. The SMMA behaves as a well-characterized exponential moving average.** Half-life = $\ln(2) \times P / N$ where $P = 1000$ is the smoothing period and $N$ is calls per round. We observed 35-round half-life with 20 calls/round, matching theory exactly.

**2. Post-EIP-1559 semantics preserve mechanism functionality.** The EVM `GASPRICE` opcode returns `baseFee + priorityFee`. With base fees at 0.2 gwei in 2026, the priority fee dominates (83-98% of effective gas price), giving the miner near-complete control over the SMMA signal — a situation impossible in the 2018 design era where competitive gas bidding was necessary for tx inclusion.

**3. Asymmetric convergence creates exploitable transients.** Pumping SMMA from 1 to 10 gwei: each call shifts by ~0.009 gwei. Decay from 2 to 1.2 gwei: each call shifts by ~0.0008 gwei. The 12x speed difference means the SMMA retains "memory" of high-gas periods much longer than those periods lasted. This is inherent to any EMA-based oracle and worth noting for other protocols using similar designs.

**4. Market microstructure limits extraction.** 11 automated sell events on Uniswap V2 (~300K XRT / ~14 ETH liquidity) showed consistent ~1% price degradation per sell, totaling 10.6% cumulative impact. The thin AMM liquidity imposes a natural ceiling on extraction regardless of emission rate.

## The Reflexive Feedback Loop

The most interesting property is the reflexive dynamics:

```
Miner chooses tx.gasprice
    → Updates SMMA
        → Determines emission rate (higher SMMA = more XRT/gas)
            → XRT sold on DEX for ETH
                → Revenue vs. cost determines profitability
                    → Informs next round's gas price choice
```

At equilibrium, miners bid gas prices up only to where marginal emission revenue equals marginal gas cost. Under 2018 conditions (20+ gwei market gas), this equilibrium naturally tracked real network costs — the mechanism was self-regulating. Under 2026 conditions (0.25 gwei), the equilibrium point shifted dramatically, but the feedback mechanism still operates correctly.

The breakeven condition at steady state:

$$\frac{P_{\text{XRT}} \times g_{\text{eff}}}{F_{\text{auction}}} = 2 \times g_{\text{eff}} \times 10^{-9}$$

simplifies to $P_{\text{XRT}} = 2 \times F_{\text{auction}} \times 10^{-9}$, which is independent of gas price — at steady state, profitability depends only on XRT market price relative to the auction constant.

## Why This Matters for Mechanism Design

The Robonomics emission mechanism is, as far as we know, the only production deployment of **gas-as-unit-of-account** for token issuance. While Bitcoin's PoW links emission to external computation and Ethereum's PoS links it to capital lockup, the Robonomics approach links emission to the blockchain's own internal measure of computational cost. Gas is the EVM's native accounting unit — using it as the emission basis creates a direct, on-chain feedback loop between protocol utilization and token supply that requires no external oracle.

The design dates to 2018, predating:
- EIP-1559 (fee market reform)
- EIP-2612 (permit/meta-transactions — Robonomics used deferred signatures years earlier)
- EIP-1167 (minimal proxy — Robonomics used `DELEGATECALL` factory pattern independently)
- The DeFi oracle exploitation era (Robonomics SMMA was manipulation-resistant by design)

The contracts remain live and functional on Ethereum mainnet. Studying them offers lessons for anyone designing long-lived on-chain economic mechanisms:

1. **Environmental assumptions are the most fragile invariant.** The mechanism correctly tracks gas costs — what changed was the 100x drop in gas prices, not any internal property.
2. **Endogenous oracles have bounded domains.** The SMMA works when `tx.gasprice` reflects genuine market conditions. Post-EIP-1559, with base fees near zero, the sender controls the signal.
3. **The smoothing period encodes a temporal security assumption.** Period-1000 assumes legitimate traffic dominates on the timescale of ~1000 observations. Under low-frequency conditions, this assumption may not hold.
4. **Immutable contracts are time capsules.** The Robonomics v5 contracts faithfully execute 2018 economic logic in 2026. That the equilibrium shifted is not a bug — it's the fundamental challenge of encoding economic policy in immutable code.

## Links

- **Paper:** [Empirical Study of Gas-Proportional Token Emission](https://github.com/ensrationis/xrt-classic-miner/blob/master/paper/xrt_emission_experiment.pdf) (Lonshakov, Krupenkin, 2026)
- **Code:** [xrt-classic-miner](https://github.com/ensrationis/xrt-classic-miner) (open source, Python)
- **Factory contract:** [0x7e384AD1...1225](https://etherscan.io/address/0x7e384AD1FE06747594a6102EE5b377b273DC1225)
- **Robonomics whitepaper:** [Lonshakov et al., 2018](https://static.robonomics.network/docs/whitepaper/Robonomics-whitepaper-en.pdf)

We'd be interested in hearing from anyone who knows of other gas-proportional emission mechanisms, or who has thoughts on the design space between PoW/PoS/PoResource issuance models.
