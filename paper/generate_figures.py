"""Generate all figures for the XRT emission experiment paper.

Refinement cycles 2-5: improved quality, higher DPI, better typography,
better color schemes, proper aspect ratios, added economic model figure.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, ArrowStyle
import numpy as np
import os

OUT = os.path.join(os.path.dirname(__file__), 'figures')
os.makedirs(OUT, exist_ok=True)

# Global style — publication quality
plt.rcParams.update({
    'font.size': 11,
    'font.family': 'sans-serif',
    'axes.titlesize': 13,
    'axes.labelsize': 12,
    'axes.linewidth': 0.8,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'figure.dpi': 200,
    'savefig.dpi': 200,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.15,
    'figure.facecolor': 'white',
    'axes.facecolor': '#fafbfc',
    'axes.grid': True,
    'grid.alpha': 0.25,
    'grid.linewidth': 0.5,
    'legend.framealpha': 0.9,
    'legend.edgecolor': '#cccccc',
})

# Color palette
C_BLUE = '#2563eb'
C_RED = '#dc2626'
C_GREEN = '#16a34a'
C_AMBER = '#d97706'
C_PURPLE = '#7c3aed'
C_GRAY = '#6b7280'
C_LIGHT_BLUE = '#93c5fd'
C_LIGHT_RED = '#fca5a5'
C_LIGHT_GREEN = '#86efac'


# ═══════════════════════════════════════════════════════════════════
# Figure 1: SMMA dynamics — pump phase + mine phase
# ═══════════════════════════════════════════════════════════════════
def fig1_smma_dynamics():
    fig, ax = plt.subplots(figsize=(10, 4.5))

    # Simulate SMMA trajectory
    smma = 1.03  # starting SMMA (gwei)
    PERIOD = 1000
    trajectory = []

    # Phase 1: PUMP — 4 rounds, batch=56, eff_gp=10.2 gwei
    for r in range(4):
        for call in range(112):  # 56 create + 56 finalize
            trajectory.append(smma)
            smma += (10.2 - smma) / PERIOD

    pump_end = len(trajectory)

    # Transition gap (finalization, selling, reconfiguration) — ~200 calls
    for call in range(200):
        trajectory.append(smma)
        smma += (1.2 - smma) / PERIOD

    mine_start = len(trajectory)

    # Phase 2: MINE — 69 rounds, batch=10, eff_gp=1.2 gwei
    for r in range(69):
        for call in range(20):  # 10 create + 10 finalize
            trajectory.append(smma)
            smma += (1.2 - smma) / PERIOD

    x = np.arange(len(trajectory))
    ax.plot(x, trajectory, color=C_BLUE, linewidth=1.8, alpha=0.95, zorder=3)

    # Shade phases
    ax.axvspan(0, pump_end, alpha=0.10, color=C_RED, label='Phase 1: Pump (10 gwei priority)')
    ax.axvspan(pump_end, mine_start, alpha=0.06, color=C_AMBER, label='Transition (reconfiguration)')
    ax.axvspan(mine_start, len(trajectory), alpha=0.07, color=C_GREEN, label='Phase 2: Mine (1 gwei priority)')

    # Breakeven line
    ax.axhline(y=0.674, color=C_RED, linestyle='--', alpha=0.5, linewidth=1)
    ax.text(len(trajectory) * 0.78, 0.80, 'Breakeven SMMA\n(at 0.45 gwei eff.)',
            fontsize=9, color=C_RED, ha='center', style='italic')

    # Target lines
    ax.axhline(y=10.2, color=C_RED, linestyle=':', alpha=0.3, linewidth=0.8)
    ax.text(pump_end * 0.5, 10.5, 'pump target: 10.2 gwei', fontsize=8, color=C_RED, ha='center', alpha=0.6)
    ax.axhline(y=1.2, color=C_GREEN, linestyle=':', alpha=0.3, linewidth=0.8)
    ax.text(len(trajectory) * 0.9, 1.35, 'mine target: 1.2 gwei', fontsize=8, color=C_GREEN, ha='center', alpha=0.6)

    # Phase annotations
    ax.annotate('SMMA peak\n~4.0 gwei', xy=(pump_end, 4.0), xytext=(pump_end + 100, 4.3),
                fontsize=9, ha='left', arrowprops=dict(arrowstyle='->', color=C_GRAY, lw=1),
                color=C_GRAY)

    ax.set_xlabel('Contract calls (cumulative)')
    ax.set_ylabel('SMMA gasPrice (gwei)')
    ax.set_title('SMMA Trajectory During Pump & Mine Experiment', fontweight='bold')
    ax.legend(loc='upper right', fontsize=9)
    ax.set_ylim(0, 11)

    fig.savefig(os.path.join(OUT, 'fig1_smma_dynamics.png'))
    plt.close()
    print('fig1 done')


# ═══════════════════════════════════════════════════════════════════
# Figure 2: XRT emission per round (mine phase)
# ═══════════════════════════════════════════════════════════════════
def fig2_xrt_per_round():
    rounds = list(range(2, 70))
    xrt = [
        443.66, 439.50, 435.82, 432.18, 428.68, 425.57, 421.88, 418.79,
        415.50, 412.51, 409.85, 406.36, 403.53, 400.63, 398.59, 395.26,
        392.55, 389.80, 386.95, 384.58, 382.28, 380.58, 377.66, 375.58,
        373.36, 371.23, 369.23, 367.86, 365.40, 363.60, 361.72, 359.92,
        358.26, 357.06, 354.84, 353.34, 351.70, 350.25, 348.71, 347.75,
        345.78, 344.57, 343.33, 342.06, 340.81, 340.38, 304.66, 337.54,
        303.51, 335.49, 301.01, 333.61, 299.69, 298.62, 297.92, 297.16,
        329.48, 328.15, 294.54, 326.78, 293.04, 324.84, 324.08, 258.86,
        258.35, 258.18, 257.88, 257.13,
    ]

    fig, ax1 = plt.subplots(figsize=(10, 4.5))

    bars = ax1.bar(rounds, xrt, color=C_LIGHT_BLUE, edgecolor=C_BLUE, alpha=0.7,
                   width=0.8, linewidth=0.3, label='XRT minted per round')

    # Cumulative
    ax2 = ax1.twinx()
    cumulative = np.cumsum(xrt)
    ax2.plot(rounds, cumulative, color=C_RED, linewidth=2.2, label='Cumulative XRT', zorder=5)
    ax2.set_ylabel('Cumulative XRT', color=C_RED)
    ax2.tick_params(axis='y', labelcolor=C_RED)

    ax1.set_xlabel('Round number')
    ax1.set_ylabel('XRT per round')
    ax1.set_title('XRT Emission per Round (Mine Phase, batch=10, prio=1 gwei)', fontweight='bold')

    # Mark sell events with subtle vertical lines
    sell_rounds = [6, 11, 16, 22, 28, 34, 40, 46, 53, 58, 64]
    for i, sr in enumerate(sell_rounds):
        if sr - 2 < len(xrt):
            ax1.axvline(x=sr, color=C_AMBER, linestyle=':', alpha=0.4, linewidth=1)
    ax1.text(8, 460, 'auto-sell events', fontsize=8, color=C_AMBER, style='italic')

    # Trend line
    z = np.polyfit(rounds, xrt, 1)
    p = np.poly1d(z)
    ax1.plot(rounds, p(rounds), '--', color=C_PURPLE, alpha=0.5, linewidth=1.2, label='Trend')

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='center right', fontsize=9)

    fig.savefig(os.path.join(OUT, 'fig2_xrt_per_round.png'))
    plt.close()
    print('fig2 done')


# ═══════════════════════════════════════════════════════════════════
# Figure 3: XRT sell price decay on Uniswap V2
# ═══════════════════════════════════════════════════════════════════
def fig3_price_decay():
    sells = [
        (1, 4801.06, 0.161558), (2, 2094.24, 0.069128), (3, 2018.96, 0.065870),
        (4, 2331.42, 0.075817), (5, 2247.64, 0.072325), (6, 2176.76, 0.069183),
        (7, 2115.91, 0.066450), (8, 2064.30, 0.064211), (9, 2256.19, 0.069402),
        (10, 2145.56, 0.065208), (11, 2044.14, 0.061474),
    ]
    nums = [s[0] for s in sells]
    prices = [s[2] / s[1] * 1e6 for s in sells]  # micro-ETH per XRT
    volumes = [s[1] for s in sells]

    fig, ax1 = plt.subplots(figsize=(9, 4.5))

    ax1.bar(nums, volumes, color=C_LIGHT_BLUE, edgecolor=C_BLUE, alpha=0.6,
            width=0.6, linewidth=0.5, label='XRT sold per swap')
    ax1.set_ylabel('XRT sold per swap', color=C_BLUE)
    ax1.set_xlabel('Sell event #')
    ax1.tick_params(axis='y', labelcolor=C_BLUE)

    ax2 = ax1.twinx()
    ax2.plot(nums, prices, 'o-', color=C_RED, linewidth=2.2, markersize=7,
             markeredgecolor='white', markeredgewidth=1.5, label='Price (uETH/XRT)', zorder=5)
    ax2.set_ylabel('Price (uETH per XRT)', color=C_RED)
    ax2.tick_params(axis='y', labelcolor=C_RED)

    # Fill area under price line
    ax2.fill_between(nums, prices, alpha=0.08, color=C_RED)

    # Annotate total decline
    ax2.annotate(f'{prices[0]:.1f}', xy=(1, prices[0]), xytext=(1.5, prices[0] + 0.8),
                fontsize=9, color=C_RED, fontweight='bold')
    ax2.annotate(f'{prices[-1]:.1f}', xy=(11, prices[-1]), xytext=(10.5, prices[-1] - 1.0),
                fontsize=9, color=C_RED, fontweight='bold')
    ax2.annotate('', xy=(11.3, prices[-1]), xytext=(11.3, prices[0]),
                arrowprops=dict(arrowstyle='<->', color=C_GRAY, lw=1.5))
    ax2.text(11.6, (prices[0] + prices[-1]) / 2, '-10.6%', fontsize=10, color=C_RED,
             fontweight='bold', va='center')

    ax1.set_title('XRT Price Impact from Sequential Sells on Uniswap V2', fontweight='bold')

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=9)

    fig.savefig(os.path.join(OUT, 'fig3_price_decay.png'))
    plt.close()
    print('fig3 done')


# ═══════════════════════════════════════════════════════════════════
# Figure 4: SMMA convergence simulation at different priority fees
# ═══════════════════════════════════════════════════════════════════
def fig4_smma_convergence():
    fig, ax = plt.subplots(figsize=(10, 4.5))
    SMMA_START = 1.94
    PERIOD = 1000
    CALLS_PER_ROUND = 20

    scenarios = [
        (10.0, C_RED, '10.0 gwei (aggressive pump)', '--'),
        (2.0, C_AMBER, '2.0 gwei (moderate)', '-'),
        (1.0, C_BLUE, '1.0 gwei (our experiment)', '-'),
        (0.2, C_GREEN, '0.2 gwei (hypothetical cheap)', '-'),
        (0.0, C_PURPLE, '0.0 gwei (theoretical min)', ':'),
    ]

    for prio, color, label, ls in scenarios:
        base = 0.25
        eff = base + prio
        smma = SMMA_START
        values = [smma]
        for r in range(100):
            for _ in range(CALLS_PER_ROUND):
                smma += (eff - smma) / PERIOD
            values.append(smma)
        ax.plot(range(101), values, color=color, linewidth=2, label=f'prio={label}', linestyle=ls)

    ax.axhline(y=0.674, color=C_GRAY, linestyle='--', alpha=0.5, linewidth=1.2)
    ax.text(87, 0.85, 'Breakeven\n(0.674 gwei)', fontsize=9, color=C_GRAY, ha='center',
            style='italic',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=C_GRAY, alpha=0.8))

    # Mark half-life
    ax.axvline(x=35, color=C_BLUE, linestyle=':', alpha=0.3, linewidth=1)
    ax.text(36, 0.3, 't_1/2 ~ 35\nrounds', fontsize=8, color=C_BLUE, alpha=0.7)

    ax.set_xlabel('Rounds (20 contract calls each)')
    ax.set_ylabel('SMMA gasPrice (gwei)')
    ax.set_title('SMMA Convergence at Different Priority Fees (starting from 1.94 gwei)', fontweight='bold')
    ax.legend(fontsize=8.5, loc='right')
    ax.set_ylim(0, 12)

    fig.savefig(os.path.join(OUT, 'fig4_smma_convergence.png'))
    plt.close()
    print('fig4 done')


# ═══════════════════════════════════════════════════════════════════
# Figure 5: Architecture diagram (Robonomics emission flow)
# ═══════════════════════════════════════════════════════════════════
def fig5_architecture():
    fig, ax = plt.subplots(figsize=(12, 6.5))
    ax.set_xlim(-0.5, 12)
    ax.set_ylim(-0.5, 7)
    ax.axis('off')

    def box(ax, x, y, w, h, text, fc, ec, fontsize=11, bold=False):
        rect = FancyBboxPatch((x - w/2, y - h/2), w, h,
                              boxstyle="round,pad=0.15", facecolor=fc, edgecolor=ec, linewidth=1.8)
        ax.add_patch(rect)
        weight = 'bold' if bold else 'normal'
        ax.text(x, y, text, fontsize=fontsize, ha='center', va='center', fontweight=weight, zorder=10)

    def arrow(ax, x1, y1, x2, y2, color='#374151', style='->', lw=1.5, ls='-'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle=style, color=color, lw=lw, linestyle=ls))

    def label(ax, x, y, text, **kw):
        defaults = dict(fontsize=8.5, ha='center', va='center', color='#374151')
        defaults.update(kw)
        ax.text(x, y, text, **defaults)

    # Boxes
    box(ax, 1.5, 5.5, 2.4, 0.9, 'Miner\n(tx.origin)', '#dbeafe', '#2563eb', bold=True)
    box(ax, 5.5, 5.5, 2.4, 0.9, 'Lighthouse\n(provider queue)', '#fef3c7', '#d97706')
    box(ax, 5.5, 3.2, 2.4, 0.9, 'Factory\n(DELEGATECALL)', '#fef3c7', '#d97706')
    box(ax, 9.5, 5.5, 2.4, 0.9, 'Liability\n(new contract)', '#f3f4f6', '#6b7280')
    box(ax, 5.5, 1.0, 2.4, 0.9, 'XRT Token\n(mint to tx.origin)', '#dcfce7', '#16a34a', bold=True)
    box(ax, 1.5, 1.0, 2.4, 0.9, 'SMMA\ngasPrice oracle', '#fce7f3', '#db2777')
    box(ax, 9.5, 1.0, 2.4, 0.9, 'Uniswap V2\n(XRT -> ETH)', '#dcfce7', '#16a34a')
    box(ax, 9.5, 3.2, 2.4, 0.9, 'Liability\n(finalize + result)', '#f3f4f6', '#6b7280')

    # Step 1: Miner -> Lighthouse
    arrow(ax, 2.7, 5.5, 4.3, 5.5, C_BLUE)
    label(ax, 3.5, 5.9, '1. createLiability\n(demand + offer sigs)', color=C_BLUE, fontsize=8)

    # Step 2: Lighthouse -> Factory
    arrow(ax, 5.5, 5.05, 5.5, 3.65, C_AMBER)
    label(ax, 4.3, 4.35, '2. deploy\nliability', color=C_AMBER, fontsize=8)

    # Step 3: Factory -> Liability
    arrow(ax, 6.7, 3.2, 8.3, 3.2, C_GRAY)

    # Step 3b: Miner -> Lighthouse (finalize)
    arrow(ax, 2.7, 5.1, 4.3, 5.1, C_BLUE, ls='dashed')
    label(ax, 3.5, 4.7, '3. finalizeLiability\n(result sig)', color=C_BLUE, fontsize=8)

    # Step 4: Factory -> XRT (mint)
    arrow(ax, 5.5, 2.75, 5.5, 1.45, C_GREEN, lw=2.5)
    label(ax, 7.0, 2.1, '4. mint XRT\nwn = gas x SMMA\nx 10^9 / finalPrice', color=C_GREEN, fontsize=8.5, fontweight='bold')

    # SMMA update
    arrow(ax, 4.3, 1.0, 2.7, 1.0, '#db2777', style='<->')
    label(ax, 3.5, 0.5, 'tx.gasprice\nupdates SMMA', color='#db2777', fontsize=8)

    # Step 5: XRT -> Uniswap
    arrow(ax, 6.7, 1.0, 8.3, 1.0, C_GREEN)
    label(ax, 7.5, 0.5, '5. sell XRT', color=C_GREEN, fontsize=8)

    # Step 6: ETH returns to miner
    arrow(ax, 9.5, 1.45, 1.5, 5.05, C_GREEN, ls='dotted', lw=1.2)
    label(ax, 10.8, 3.5, '6. ETH\nreturns', color=C_GREEN, fontsize=8)

    ax.set_title('XRT Emission Pipeline Architecture', fontsize=14, fontweight='bold', pad=15)

    fig.savefig(os.path.join(OUT, 'fig5_architecture.png'))
    plt.close()
    print('fig5 done')


# ═══════════════════════════════════════════════════════════════════
# Figure 6: Emission formula feedback loop
# ═══════════════════════════════════════════════════════════════════
def fig6_feedback_loop():
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_xlim(-3.2, 3.2)
    ax.set_ylim(-3.2, 3.2)
    ax.axis('off')
    ax.set_aspect('equal')

    # Draw circular nodes
    angles = [90, 18, -54, -126, -198]
    labels = [
        'tx.gasprice\n(miner sets\npriority fee)',
        'SMMA\nupdates\n(period=1000)',
        'XRT\nemission\n(wn = gas x SMMA)',
        'XRT -> ETH\n(Uniswap V2\nsell)',
        'Profitability\nassessment\n(ROI check)',
    ]
    node_colors = ['#dbeafe', '#fef3c7', '#dcfce7', '#fce7f3', '#f3f4f6']
    edge_colors = [C_BLUE, C_AMBER, C_GREEN, '#db2777', C_GRAY]

    r = 2.1
    positions = []
    for i, (ang, label, fc, ec) in enumerate(zip(angles, labels, node_colors, edge_colors)):
        rad = np.radians(ang)
        x, y = r * np.cos(rad), r * np.sin(rad)
        positions.append((x, y))
        bbox = dict(boxstyle='round,pad=0.5', facecolor=fc, edgecolor=ec, linewidth=2.2)
        ax.text(x, y, label, fontsize=9.5, ha='center', va='center', bbox=bbox, zorder=5)

    # Draw arrows between consecutive nodes
    for i in range(5):
        x1, y1 = positions[i]
        x2, y2 = positions[(i + 1) % 5]
        dx = x2 - x1
        dy = y2 - y1
        length = np.sqrt(dx**2 + dy**2)
        shrink = 0.62 / length
        ax.annotate('', xy=(x2 - dx * shrink, y2 - dy * shrink),
                    xytext=(x1 + dx * shrink, y1 + dy * shrink),
                    arrowprops=dict(arrowstyle='->', color='#374151', lw=2.2,
                                    connectionstyle='arc3,rad=0.08'))

    # Center label
    ax.text(0, 0, 'Robonomics\nEmission\nFeedback Loop', fontsize=13, ha='center', va='center',
            style='italic', color='#374151', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.6', facecolor='white', edgecolor='#d1d5db',
                      linewidth=1.5, alpha=0.95))

    # Equilibrium note
    ax.text(0, -3.0, 'Natural equilibrium: miners bid gas up only until\nemission revenue = gas cost',
            fontsize=9, ha='center', va='center', color=C_GRAY, style='italic')

    ax.set_title('Reflexive Incentive Cycle in XRT Emission', fontsize=14, fontweight='bold', pad=15)

    fig.savefig(os.path.join(OUT, 'fig6_feedback_loop.png'))
    plt.close()
    print('fig6 done')


# ═══════════════════════════════════════════════════════════════════
# Figure 7: Gas cost landscape — 2018 vs 2026
# ═══════════════════════════════════════════════════════════════════
def fig7_gas_landscape():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Left: Gas price evolution
    periods = ['2018\n(design)', '2020\n(DeFi)', '2022\n(Merge)', '2024\n(Dencun)', '2026\n(exper.)']
    gas_typical = [20, 80, 30, 15, 0.25]
    gas_peak = [200, 600, 300, 100, 5]
    x = np.arange(len(periods))

    bars1 = ax1.bar(x - 0.17, gas_typical, 0.32, color=C_LIGHT_BLUE, edgecolor=C_BLUE,
                    linewidth=0.8, label='Typical gas (gwei)')
    bars2 = ax1.bar(x + 0.17, gas_peak, 0.32, color=C_LIGHT_RED, edgecolor=C_RED,
                    linewidth=0.8, alpha=0.7, label='Peak gas (gwei)')

    # Value labels on bars
    for bar, val in zip(bars1, gas_typical):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.2,
                f'{val}', ha='center', va='bottom', fontsize=8, color=C_BLUE)

    ax1.set_xticks(x)
    ax1.set_xticklabels(periods, fontsize=9)
    ax1.set_ylabel('Gas price (gwei)')
    ax1.set_yscale('log')
    ax1.legend(fontsize=8.5, loc='upper right')
    ax1.set_title('(a) Ethereum Gas Price Evolution', fontsize=11, fontweight='bold')

    # Highlight the drop
    ax1.annotate('', xy=(4, 0.25), xytext=(0, 20),
                arrowprops=dict(arrowstyle='->', color=C_RED, lw=1.5, ls='dashed',
                                connectionstyle='arc3,rad=0.3'))
    ax1.text(2, 3, '~100x\ndrop', fontsize=10, color=C_RED, ha='center', fontweight='bold')

    # Right: Cost per liability
    gas_prices = np.logspace(-0.7, 2.5, 200)  # 0.2 to 300 gwei
    cost_usd_at_2000 = gas_prices * 1.058e6 / 1e9 * 2000

    ax2.plot(gas_prices, cost_usd_at_2000, color=C_BLUE, linewidth=2.5)
    ax2.fill_between(gas_prices, cost_usd_at_2000, alpha=0.05, color=C_BLUE)

    # Era markers
    markers = [
        (0.25, C_GREEN, '2026\n$0.53', 'left'),
        (20, C_AMBER, '2018\n$42', 'left'),
        (80, C_RED, '2020\n$169', 'left'),
    ]
    for gp, color, txt, ha in markers:
        cost = gp * 1.058e6 / 1e9 * 2000
        ax2.axvline(x=gp, color=color, linestyle='--', alpha=0.6, linewidth=1.5)
        ax2.plot(gp, cost, 'o', color=color, markersize=8, zorder=5)
        ax2.annotate(txt, xy=(gp, cost), xytext=(gp * 1.5, cost * 1.5),
                    fontsize=8.5, color=color, fontweight='bold',
                    arrowprops=dict(arrowstyle='->', color=color, lw=1))

    ax2.set_xlabel('Gas price (gwei)')
    ax2.set_ylabel('Cost per liability (USD, at ETH=$2000)')
    ax2.set_xscale('log')
    ax2.set_yscale('log')
    ax2.set_title('(b) Liability Creation Cost vs Gas Price', fontsize=11, fontweight='bold')

    fig.suptitle('Ethereum Gas Price Landscape: Design Era vs Experiment Era',
                 fontsize=13, fontweight='bold', y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig7_gas_landscape.png'))
    plt.close()
    print('fig7 done')


# ═══════════════════════════════════════════════════════════════════
# Figure 8: Economic equilibrium model (NEW)
# ═══════════════════════════════════════════════════════════════════
def fig8_economic_model():
    """Show the economic equilibrium: emission revenue vs gas cost as a function of priority fee."""
    fig, ax = plt.subplots(figsize=(10, 5))

    GAS_PER_LIABILITY = 1_058_000
    FINAL_PRICE = 5_662_799_692_218  # from contract
    BASE_FEE = 0.25  # gwei
    SMMA_START = 1.94  # gwei
    XRT_PRICE_ETH = 32e-6  # ~32 uETH per XRT (from sells data)
    PERIOD = 1000

    # Range of priority fees to analyze
    prios = np.linspace(0, 15, 300)

    # For each priority fee, simulate 50 rounds then compute steady state
    revenues = []
    costs = []
    profits = []

    for prio in prios:
        eff_gp = BASE_FEE + prio  # gwei

        # Cost per liability in ETH
        cost_eth = eff_gp * 1e-9 * GAS_PER_LIABILITY
        cost_per_round = cost_eth * 20  # 10 create + 10 finalize ~ 20 txs

        # Steady-state SMMA converges to eff_gp
        # But in practice, SMMA lags. Use SMMA after 30 rounds from start.
        smma = SMMA_START * 1e9  # in wei
        for _ in range(30 * 20):  # 30 rounds * 20 calls
            smma += (eff_gp * 1e9 - smma) / PERIOD

        # XRT minted per round (gas per round * smma / finalPrice)
        gas_per_round = GAS_PER_LIABILITY * 10  # 10 liabilities
        # Actually: wn per liability = gas * smma * 1e9 / finalPrice
        # But smma is already in wei (gwei * 1e9)
        # wnFromGas: gas * gasPrice * 1e9 / finalPrice
        # where gasPrice is in wei
        wn_per_round = gas_per_round * smma * 1e9 / FINAL_PRICE
        xrt_per_round = wn_per_round / 1e9

        # Revenue in ETH
        revenue = xrt_per_round * XRT_PRICE_ETH

        revenues.append(revenue)
        costs.append(cost_per_round)
        profits.append(revenue - cost_per_round)

    revenues = np.array(revenues)
    costs = np.array(costs)
    profits = np.array(profits)

    ax.plot(prios, revenues * 1000, color=C_GREEN, linewidth=2.5, label='XRT revenue (mETH/round)')
    ax.plot(prios, costs * 1000, color=C_RED, linewidth=2.5, label='Gas cost (mETH/round)')
    ax.fill_between(prios, revenues * 1000, costs * 1000,
                    where=revenues > costs, alpha=0.12, color=C_GREEN, label='Profit zone')
    ax.fill_between(prios, revenues * 1000, costs * 1000,
                    where=revenues < costs, alpha=0.08, color=C_RED, label='Loss zone')

    # Find crossover
    crossover_idx = np.where(np.diff(np.sign(profits)))[0]
    if len(crossover_idx) > 0:
        cross_prio = prios[crossover_idx[0]]
        ax.axvline(x=cross_prio, color=C_GRAY, linestyle=':', alpha=0.7)
        ax.text(cross_prio + 0.3, ax.get_ylim()[1] * 0.85,
                f'Break-even\nprio ~ {cross_prio:.1f} gwei',
                fontsize=10, color=C_GRAY, fontweight='bold')

    # Mark our experiment
    ax.axvline(x=1.0, color=C_BLUE, linestyle='--', alpha=0.6, linewidth=1.5)
    ax.text(1.3, ax.get_ylim()[1] * 0.5, 'Our experiment\n(1 gwei prio)',
            fontsize=9, color=C_BLUE, fontweight='bold')

    ax.set_xlabel('Priority fee (gwei)')
    ax.set_ylabel('mETH per round')
    ax.set_title('Economic Equilibrium: Emission Revenue vs Gas Cost\n(after 30 rounds of SMMA convergence)',
                 fontweight='bold')
    ax.legend(fontsize=9, loc='upper left')
    ax.set_xlim(0, 15)

    fig.savefig(os.path.join(OUT, 'fig8_economic_model.png'))
    plt.close()
    print('fig8 done')


if __name__ == '__main__':
    fig1_smma_dynamics()
    fig2_xrt_per_round()
    fig3_price_decay()
    fig4_smma_convergence()
    fig5_architecture()
    fig6_feedback_loop()
    fig7_gas_landscape()
    fig8_economic_model()
    print('\nAll figures generated in', OUT)
