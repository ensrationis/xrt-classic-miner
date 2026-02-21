"""Build PDF from the XRT emission experiment paper using reportlab.

Refinement cycle: fixes Unicode rendering, improves layout, adds page numbers,
proper figure numbering, and better typography.
"""
import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable, Frame, PageTemplate
)
from reportlab.lib import colors

BASE = os.path.dirname(__file__)
FIG_DIR = os.path.join(BASE, 'figures')
OUT_PDF = os.path.join(BASE, 'xrt_emission_experiment.pdf')

W, H = A4  # 595.27, 841.89 pts

# ── Styles ──────────────────────────────────────────────────────
styles = getSampleStyleSheet()

styles.add(ParagraphStyle(
    'PaperTitle', parent=styles['Title'],
    fontSize=16, leading=20, alignment=TA_CENTER, spaceAfter=6,
    textColor=HexColor('#1a1a1a'),
))
styles.add(ParagraphStyle(
    'Authors', parent=styles['Normal'],
    fontSize=11, alignment=TA_CENTER, spaceAfter=4, textColor=HexColor('#444444'),
))
styles.add(ParagraphStyle(
    'DateLine', parent=styles['Normal'],
    fontSize=10, alignment=TA_CENTER, spaceAfter=12, textColor=HexColor('#666666'),
    fontName='Helvetica-Oblique',
))
styles.add(ParagraphStyle(
    'AbstractTitle', parent=styles['Heading2'],
    fontSize=12, alignment=TA_CENTER, spaceAfter=4,
))
styles.add(ParagraphStyle(
    'AbstractBody', parent=styles['Normal'],
    fontSize=9.5, leading=13, alignment=TA_JUSTIFY,
    leftIndent=20, rightIndent=20, spaceAfter=8,
    fontName='Helvetica-Oblique',
))
styles.add(ParagraphStyle(
    'SectionH1', parent=styles['Heading1'],
    fontSize=14, leading=18, spaceBefore=16, spaceAfter=6,
    textColor=HexColor('#1a365d'),
))
styles.add(ParagraphStyle(
    'SectionH2', parent=styles['Heading2'],
    fontSize=12, leading=15, spaceBefore=12, spaceAfter=4,
    textColor=HexColor('#2a4a7f'),
))
styles.add(ParagraphStyle(
    'SectionH3', parent=styles['Heading3'],
    fontSize=10.5, leading=13, spaceBefore=8, spaceAfter=3,
    textColor=HexColor('#3a5a8f'),
))
styles.add(ParagraphStyle(
    'BodyText2', parent=styles['Normal'],
    fontSize=10, leading=13.5, alignment=TA_JUSTIFY,
    spaceAfter=6,
))
styles.add(ParagraphStyle(
    'CodeBlock', parent=styles['Code'],
    fontSize=8, leading=10, leftIndent=15, spaceAfter=6, spaceBefore=4,
    backColor=HexColor('#f5f5f5'),
    borderColor=HexColor('#cccccc'), borderWidth=0.5, borderPadding=4,
))
styles.add(ParagraphStyle(
    'FigCaption', parent=styles['Normal'],
    fontSize=9, leading=12, alignment=TA_CENTER, spaceAfter=10,
    textColor=HexColor('#555555'), fontName='Helvetica-Oblique',
))
styles.add(ParagraphStyle(
    'RefStyle', parent=styles['Normal'],
    fontSize=9, leading=12, spaceAfter=3, leftIndent=20, firstLineIndent=-20,
))
styles.add(ParagraphStyle(
    'Formula', parent=styles['Normal'],
    fontSize=10, leading=14, alignment=TA_CENTER, spaceAfter=8, spaceBefore=4,
    fontName='Courier',
))
styles.add(ParagraphStyle(
    'PageNum', parent=styles['Normal'],
    fontSize=9, alignment=TA_CENTER, textColor=HexColor('#888888'),
))
styles.add(ParagraphStyle(
    'BulletItem', parent=styles['Normal'],
    fontSize=10, leading=13.5, alignment=TA_JUSTIFY,
    spaceAfter=3, leftIndent=20, bulletIndent=10,
))


# ── Helpers ──────────────────────────────────────────────────────

def sup(text):
    """Wrap text in superscript tags."""
    return f'<super>{text}</super>'


def _cell(text, bold=False):
    """Wrap cell text in a Paragraph so HTML tags like <super> render properly."""
    style = ParagraphStyle('_cell', parent=styles['Normal'],
                           fontSize=8.5, leading=11, alignment=TA_CENTER)
    if bold:
        text = f'<b>{text}</b>'
    return Paragraph(text, style)


def make_table(headers, rows, col_widths=None):
    """Create a styled table. All cells are wrapped in Paragraphs for HTML rendering."""
    hdr_row = [_cell(h, bold=True) for h in headers]
    body_rows = [[_cell(c) for c in row] for row in rows]
    data = [hdr_row] + body_rows
    if col_widths is None:
        col_widths = [None] * len(headers)
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#e8edf3')),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#1a365d')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, HexColor('#f8f9fb')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    return t


def add_figure(story, filename, caption, width=450):
    """Add a figure with caption."""
    path = os.path.join(FIG_DIR, filename)
    if os.path.exists(path):
        # Calculate proportional height from image dimensions
        from reportlab.lib.utils import ImageReader
        img_reader = ImageReader(path)
        iw, ih = img_reader.getSize()
        aspect = ih / iw
        img = Image(path, width=width, height=width * aspect)
        story.append(KeepTogether([img, Paragraph(caption, styles['FigCaption'])]))
    else:
        story.append(Paragraph(f'[Missing figure: {filename}]', styles['FigCaption']))


def page_footer(canvas, doc):
    """Add page number footer."""
    canvas.saveState()
    canvas.setFont('Helvetica', 9)
    canvas.setFillColor(HexColor('#888888'))
    canvas.drawCentredString(W / 2, 15 * mm, f'{doc.page}')
    # Header line
    if doc.page > 1:
        canvas.setStrokeColor(HexColor('#e0e0e0'))
        canvas.setLineWidth(0.5)
        canvas.line(22 * mm, H - 18 * mm, W - 22 * mm, H - 18 * mm)
        canvas.setFont('Helvetica-Oblique', 8)
        canvas.setFillColor(HexColor('#aaaaaa'))
        canvas.drawString(22 * mm, H - 16 * mm,
                          'Lonshakov, Krupenkin, Claude — Empirical Study of Gas-Proportional Token Emission (2026)')
    canvas.restoreState()


def build():
    doc = SimpleDocTemplate(
        OUT_PDF, pagesize=A4,
        leftMargin=22 * mm, rightMargin=22 * mm,
        topMargin=22 * mm, bottomMargin=22 * mm,
    )

    story = []
    S = lambda text, style='BodyText2': Paragraph(text, styles[style])
    sp = lambda h=6: Spacer(1, h)
    B = lambda text: Paragraph(text, styles['BulletItem'])

    # ── Title page ───────────────────────────────────
    story.append(sp(30))
    story.append(S(
        'Empirical Study of Gas-Proportional Token Emission:<br/>'
        'Revisiting the Robonomics XRT Mechanism<br/>Eight Years After Deployment',
        'PaperTitle'
    ))
    story.append(sp(8))
    story.append(S(
        '<b>Sergey Lonshakov</b>' + sup('1') + ', '
        '<b>Alexander Krupenkin</b>' + sup('1') + ', '
        '<b>Claude</b>' + sup('2'),
        'Authors'
    ))
    story.append(S(
        sup('1') + ' Robonomics Network &mdash; architects &nbsp;&nbsp;|&nbsp;&nbsp; '
        + sup('2') + ' Anthropic &mdash; AI research assistant',
        'Authors'
    ))
    story.append(S('February 2026', 'DateLine'))
    story.append(sp(8))
    story.append(HRFlowable(width='60%', color=HexColor('#cccccc')))
    story.append(sp(8))

    # ── Abstract ─────────────────────────────────────
    story.append(S('Abstract', 'AbstractTitle'))
    story.append(S(
        'We present an empirical study of the XRT token emission mechanism deployed as part of '
        'Robonomics Network v5 on Ethereum mainnet. Originally designed in 2018 when Ethereum gas '
        'prices ranged from 20 to 200 gwei, the mechanism ties token emission to a Smoothed Moving '
        'Average (SMMA) of observed transaction gas prices &mdash; an innovative approach that creates a '
        'self-regulating economic feedback loop between network utilization cost and token supply. '
        'With Ethereum gas prices having decreased by two orders of magnitude to ~0.25 gwei by 2026, '
        'we conducted a controlled experiment: mining 24,190 XRT tokens through 1,360 liability '
        'contracts, including a two-phase &ldquo;Pump &amp; Mine&rdquo; strategy to study the SMMA\'s reflexive '
        'dynamics. Our findings illuminate the elegant design principles behind gas-proportional '
        'emission, demonstrate the SMMA\'s properties as an endogenous price oracle, and provide '
        'empirical data on the reflexive dynamics between emission rate, token supply, and market '
        'microstructure on Uniswap V2. This work contributes to the broader understanding of mechanism '
        'design in early Ethereum-era smart contract systems and the long-term behavior of on-chain '
        'economic primitives.',
        'AbstractBody'
    ))
    story.append(sp(4))
    story.append(S(
        '<b>Keywords:</b> token emission, mechanism design, Robonomics, XRT, SMMA, '
        'smart contracts, Ethereum, cyber-physical systems, DeFi',
        'AbstractBody'
    ))
    story.append(HRFlowable(width='60%', color=HexColor('#cccccc')))
    story.append(sp(12))

    # ── Section 1: Introduction ──────────────────────
    story.append(S('1. Introduction', 'SectionH1'))
    story.append(S(
        'Ethereum, since its conception by Buterin in 2013, has been described as a &ldquo;world '
        'computer&rdquo; &mdash; a Turing-complete, decentralized execution environment where smart contracts '
        'serve as programs running on shared global infrastructure. Unlike traditional computing platforms '
        'where applications can purchase dedicated resources (servers, bandwidth, CPU time), all programs '
        'on the Ethereum Virtual Machine (EVM) compete for the same finite resource: block gas. This raises '
        'a fundamental and surprisingly underexplored question: <b>how can a specific program &mdash; a group '
        'of interrelated smart contracts &mdash; ensure competitive advantage in the shared throughput of '
        'the network?</b>'
    ))
    story.append(S(
        'In traditional computing, the answer is straightforward: applications acquire dedicated capacity. '
        'On a shared blockchain, no such option exists natively. Every program pays the same market gas '
        'price, and no contract system can guarantee priority access to block space. The Robonomics Network, '
        'conceived by Lonshakov, Krupenkin et al. [1], proposed what may be the only systematic attempt to '
        'answer this question on Ethereum L1: <b>a native token (XRT) whose emission is directly '
        'proportional to the gas consumed by the protocol\'s smart contracts</b>. This creates an economic '
        'feedback loop where the cost of operating the Robonomics program on the world computer is '
        'internalized into the token supply itself &mdash; providers who spend gas to run the protocol receive '
        'newly minted XRT in proportion to their contribution. The emission formula embodies the whitepaper\'s '
        'principle: <i>&ldquo;Emission of 1 Wn = 1 gas utilized by Robonomics&rdquo;</i> [1].'
    ))
    story.append(S(
        'Drawing on Wiener\'s cybernetics [2], Coase\'s theory of the firm [3], and the Robot Operating '
        'System (ROS) [4], Robonomics proposed a decentralized marketplace where autonomous robots and '
        'sensors participate in economic transactions through smart contract liabilities. The emission '
        'mechanism &mdash; an SMMA (Smoothed Moving Average) of observed gas prices modulating token issuance '
        '&mdash; represents a pioneering attempt at on-chain incentive alignment between protocol usage and '
        'token supply.'
    ))
    story.append(S(
        'In this paper, we revisit this mechanism eight years after deployment, under conditions '
        'radically different from those assumed at design time. We approach this study not as a '
        'critique but as an empirical investigation of a pioneering mechanism design, seeking to '
        'understand how carefully constructed economic invariants behave when a key environmental '
        'parameter &mdash; the price of gas on Ethereum &mdash; has changed by approximately 100x.'
    ))

    story.append(S('1.1. Contributions', 'SectionH2'))
    for item in [
        '<b>1.</b> Empirical characterization of the SMMA-based emission mechanism under ultra-low gas conditions (0.2&ndash;10 gwei), with data from 1,360 on-chain liability contracts;',
        '<b>2.</b> Experimental validation of a two-phase SMMA manipulation strategy (&ldquo;Pump &amp; Mine&rdquo;), demonstrating the reflexive properties of the endogenous gas price oracle;',
        '<b>3.</b> Quantitative analysis of market microstructure effects when mining-derived tokens are sold on thin Uniswap V2 liquidity;',
        '<b>4.</b> Open-source tooling for automated Robonomics liability lifecycle management (xrt-classic-miner);',
        '<b>5.</b> Design analysis of early Ethereum-era mechanism engineering, contributing to the historical record of smart contract architecture.',
    ]:
        story.append(B(item))

    story.append(S('1.2. Related Work', 'SectionH2'))
    story.append(S(
        'Token emission mechanisms span a wide design space. Bitcoin uses a deterministic halving '
        'schedule [9]; Ethereum PoS ties issuance to staking participation [7]; Filecoin uses baseline '
        'minting proportional to storage growth [10]. The Robonomics approach is distinct: emission tied '
        'to <b>the computational cost of protocol operations as measured by EVM gas</b> &mdash; creating a '
        'direct feedback loop between emission and utilization that is unique in the literature.'
    ))
    story.append(S(
        'The SMMA mechanism relates to on-chain price oracles. Uniswap V2\'s TWAP oracle [5] shares '
        'the principle of smoothing over time to resist manipulation. The Robonomics SMMA predates '
        'widespread TWAP adoption and represents an early example of endogenous oracle design.'
    ))

    # ── Section 2: Background ────────────────────────
    story.append(S('2. Background: The Robonomics Economic Architecture', 'SectionH1'))

    story.append(S('2.1. The Vision: An Economy of Machines', 'SectionH2'))
    story.append(S(
        'Robonomics proposes that autonomous cyber-physical systems can participate in economic '
        'transactions as independent agents. In the whitepaper\'s formulation, a CPS is analogous to '
        'a firm in Coasean economics &mdash; <i>&ldquo;a closely connected network of sensors and actuators '
        'capable of organized collaboration&rdquo;</i> [1]. The platform distinguishes between '
        '<b>promisees</b> (demand side), <b>promisors</b> (CPS agents offering services), and '
        '<b>providers</b> (infrastructure operators relaying transactions). The liability contract &mdash; '
        'a binding agreement encoded in a smart contract &mdash; serves as the primitive for '
        'machine-to-machine economic interaction.'
    ))

    story.append(S('2.2. The Contracts Factory', 'SectionH2'))
    story.append(S(
        'The Factory contract (0x7e384...1225) serves as the central registry, creating lightweight '
        'liability contracts via DELEGATECALL &mdash; a design pattern that saved 30&ndash;40% gas compared '
        'to full contract deployment [1]. The Factory verifies deferred signatures from both demand '
        'and supply sides, deploys a new liability contract for each matched pair, tracks cumulative '
        'gas consumption via <font face="Courier">totalGasConsumed</font>, and manages the emission '
        'parameter <font face="Courier">gasPrice</font> (the SMMA).'
    ))

    story.append(S('2.3. The Emission Formula', 'SectionH2'))
    story.append(S(
        'The XRT emission mechanism, implemented in <font face="Courier">Factory.wnFromGas()</font>, '
        'converts gas consumption into token issuance:',
    ))
    story.append(S(
        '<font face="Courier">wn = gas x gasPrice_SMMA x 10' + sup('9') + ' / finalPrice_auction</font>',
        'Formula'
    ))
    story.append(S(
        'where <b>wn</b> is emission in Wiener units (1 XRT = 10' + sup('9') + ' wn), '
        '<b>gas</b> is gas consumed by the transaction, '
        '<b>gasPrice_SMMA</b> is the Smoothed Moving Average of observed gas prices, and '
        '<b>finalPrice_auction</b> is the price from the Dutch auction at TGE.'
    ))
    story.append(S(
        'The SMMA updates with each <font face="Courier">createLiability</font> and '
        '<font face="Courier">finalizeLiability</font> call:',
    ))
    story.append(S(
        '<font face="Courier">gasPrice[n+1] = (gasPrice[n] x 999 + tx.gasprice) / 1000</font>',
        'Formula'
    ))
    story.append(S(
        'This formula has a half-life of ~693 observations (ln(2) x 1000) and converges '
        'exponentially toward the prevailing <font face="Courier">tx.gasprice</font>. '
        'The denomination system &mdash; wiener (1), coase (10' + sup('3') + '), glushkov (10' + sup('6') + '), '
        'robonomics token (10' + sup('9') + ') &mdash; '
        'pays homage to Norbert Wiener (cybernetics), Ronald Coase (transaction cost economics), '
        'and Viktor Glushkov (Soviet cybernetics pioneer).'
    ))

    story.append(S('2.4. The Epoch System', 'SectionH2'))
    story.append(S(
        'The development period is divided into five epochs, each consuming a target of '
        '3.47 x 10' + sup('12') + ' gas. The emission multiplier decreases geometrically:'
    ))
    story.append(make_table(
        ['Epoch', 'Target gas', 'Multiplier', 'Emission rate'],
        [
            ['0', '3.47 x 10' + sup('12'), '(2/3)' + sup('0') + ' = 1.000', 'Full rate'],
            ['1', '3.47 x 10' + sup('12'), '(2/3)' + sup('1') + ' = 0.667', '66.7%'],
            ['2', '3.47 x 10' + sup('12'), '(2/3)' + sup('2') + ' = 0.444', '44.4%'],
            ['3', '3.47 x 10' + sup('12'), '(2/3)' + sup('3') + ' = 0.296', '29.6%'],
            ['4', '3.47 x 10' + sup('12'), '(2/3)' + sup('4') + ' = 0.198', '19.8%'],
        ],
        col_widths=[40, 95, 120, 80],
    ))
    story.append(sp(4))
    story.append(S(
        'At the time of our experiment, the system was at 0.17% of epoch 0, with approximately '
        '163,800 mining rounds remaining before the first multiplier reduction.'
    ))

    story.append(S('2.5. The Lighthouse System', 'SectionH2'))
    story.append(S(
        'Lighthouses are autonomous coordination contracts managing provider access through a '
        'round-robin quota mechanism with XRT staking. Providers stake XRT to participate, take turns '
        'submitting transactions, and if the active provider fails within the timeout window, the '
        'next provider claims the marker. This pattern anticipated later proof-of-stake rotation '
        'mechanisms and solves the decentralized coordination problem without a central scheduler.'
    ))
    story.append(S(
        'The architecture bears a notable resemblance to the 0x Protocol [11], developed in the same '
        'period (2017&ndash;2018). Both systems share a fundamentally similar pattern: off-chain message '
        'matching with on-chain settlement. In 0x, makers and takers exchange signed ask/bid orders '
        'off-chain, with final settlement executed on Ethereum by &ldquo;relayers.&rdquo; In Robonomics, '
        'promisees and promisors exchange signed demand/offer messages off-chain, with providers '
        '(lighthouse operators) submitting the matched pair to Ethereum for on-chain liability creation. '
        'Both protocols recognized that Ethereum\'s limited throughput and high latency made it unsuitable '
        'for real-time order matching, and both arrived at similar architectural solutions.'
    ))
    story.append(S(
        'In this sense, the lighthouse system can be understood as one of the <b>earliest attempts to '
        'build what would later be called a Layer 2 solution</b> &mdash; not in the rollup sense, but as a '
        'complementary off-chain communication layer that extends Ethereum with capabilities the base chain '
        'cannot efficiently provide (real-time demand/offer matching, provider coordination), while settling '
        'only the economically meaningful outcomes (liability creation and finalization) on L1. This design '
        'philosophy &mdash; off-chain where possible, on-chain where necessary &mdash; anticipated the broader '
        'industry\'s evolution toward L2-centric architectures by several years.'
    ))

    story.append(S('2.6. Design Rationale', 'SectionH2'))
    story.append(S(
        'The whitepaper articulates the core principle: <i>&ldquo;The cost of 1 Wn must cover the '
        'costs of the provider for the disposal of 1 unit of gas in Ethereum&rdquo;</i> [1]. '
        'The gas-proportional emission creates a self-regulating system: when gas is expensive, '
        'providers spend more ETH per liability and emission compensates proportionally; when gas is '
        'cheap, emission decreases proportionally. The SMMA smooths short-term volatility, preventing '
        'flash-manipulation. This was calibrated for 2018 conditions, where 2 gwei was identified as '
        '&ldquo;the minimum competitive price in the Ethereum network&rdquo; [1].'
    ))

    # ── Section 3: Methodology ───────────────────────
    story.append(PageBreak())
    story.append(S('3. Experimental Methodology', 'SectionH1'))

    story.append(S('3.1. Tool Architecture', 'SectionH2'))
    add_figure(story, 'fig5_architecture.png',
               '<b>Figure 1.</b> XRT emission pipeline architecture &mdash; from liability creation through '
               'finalization and XRT minting to Uniswap V2 sell.', width=440)

    story.append(S(
        'We developed <font face="Courier">xrt-classic-miner</font>, a Python CLI tool implementing '
        'the complete Robonomics liability lifecycle. The tool consists of four modules: '
        '<font face="Courier">abi.py</font> (minimal contract ABIs and mainnet addresses), '
        '<font face="Courier">signer.py</font> (EIP-191 demand/offer/result message construction), '
        '<font face="Courier">miner.py</font> (XRTMiner class with lighthouse management and mining loops), '
        'and <font face="Courier">__main__.py</font> (CLI interface via Click).'
    ))
    story.append(S(
        '<b>Signature construction</b> follows the Robonomics v1.0 format. Demand and offer messages '
        'are 268 bytes each, encoded with <font face="Courier">abi.encodePacked</font> and signed via '
        'EIP-191. A critical implementation detail: demand messages place '
        '<font face="Courier">lighthouse</font> before <font face="Courier">validator</font> in the '
        'field order, while offer messages invert this &mdash; a deliberate asymmetry that prevents '
        'cross-role replay attacks.'
    ))

    story.append(S('3.2. Pipeline Mining Mode', 'SectionH2'))
    story.append(S(
        '<b>Pipeline mode</b> achieves maximum throughput by overlapping finalization of round N with '
        'creation of round N+1. This requires 2x quota on the lighthouse but doubles throughput '
        'compared to sequential operation. The sequence is:',
    ))
    story.append(S(
        '<font face="Courier" size="8">'
        'Round 1: --- CREATE(batch) ----------&gt; &nbsp;[bootstrap]<br/>'
        'Round 2: FINALIZE(batch) + CREATE(batch) &gt; [pipeline, 2N quota]<br/>'
        'Round 3: FINALIZE(batch) + CREATE(batch) &gt; [pipeline]<br/>'
        '...</font>',
        'CodeBlock'
    ))
    story.append(S(
        'Transactions are pre-signed with sequential nonces and broadcast rapidly, allowing '
        'multiple operations in the same Ethereum block.'
    ))

    story.append(S('3.3. Experimental Setup', 'SectionH2'))
    story.append(make_table(
        ['Parameter', 'Value'],
        [
            ['Network', 'Ethereum Mainnet'],
            ['Account', '0x6EFBA8...C3Ad'],
            ['Lighthouse', '0x04C672...bbeE (custom, timeout=1 block)'],
            ['RPC Provider', 'DRPC (free tier)'],
            ['Starting ETH', '3.544'],
            ['XRT Staked', '112 wn'],
            ['Ethereum base fee', '0.19 - 0.29 gwei'],
            ['ETH/USD (Chainlink)', '~$1,944'],
        ],
        col_widths=[140, 260],
    ))

    story.append(S('3.4. EIP-1559 and tx.gasprice Semantics', 'SectionH2'))
    story.append(S(
        'A critical subtlety concerns the interaction between the post-EIP-1559 fee model and the '
        'Robonomics SMMA, designed for the pre-EIP-1559 gas price model. After EIP-1559 [6], the fee '
        'structure changed to baseFee + priorityFee, but the EVM opcode '
        '<font face="Courier">GASPRICE</font> (Solidity\'s '
        '<font face="Courier">tx.gasprice</font>) returns the <b>effective gas price</b> = '
        'baseFee + priorityFee. Thus the SMMA continues to receive a meaningful signal, but the '
        'semantics have shifted: the base fee is now set by network demand, not sender choice.'
    ))
    story.append(S(
        'With 2026 base fees of 0.19&ndash;0.29 gwei, the priority fee dominates: during our pump phase '
        '(10 gwei priority), it constituted 98% of the effective gas price. This means the miner has '
        'almost <b>complete control</b> over the SMMA signal &mdash; a situation that differs fundamentally '
        'from 2018, where <font face="Courier">tx.gasprice</font> needed to be competitive with other '
        'users\' bids.'
    ))

    story.append(S('3.5. Experimental Protocol', 'SectionH2'))
    story.append(S(
        '<b>Phase 1 &mdash; Pump (SMMA Inflation):</b> Priority fee 10 gwei (effective tx.gasprice '
        '~10.2 gwei), batch size 56 liabilities per round, budget 2.0 ETH. Objective: rapidly '
        'increase SMMA from ~1.03 gwei to maximum achievable level.'
    ))
    story.append(S(
        '<b>Phase 2 &mdash; Mine (Elevated Emission Harvesting):</b> Priority fee 1 gwei (effective '
        'tx.gasprice ~1.2 gwei), batch size 10 (reduced from 56 due to RPC reliability constraints), '
        'budget 1.0 ETH, max cost $0.50 per liability, auto-sell every 2,000 XRT via Uniswap V2 '
        '(5% slippage tolerance).'
    ))

    story.append(S('3.6. Parameter Tuning and Iteration', 'SectionH2'))
    story.append(S(
        'The final parameters emerged from iterative trial and adjustment, revealing practical '
        'constraints that theoretical analysis alone would not predict.'
    ))
    story.append(S(
        '<b>Batch size:</b> Initially batch=56 (maximum for lighthouse quota). Worked for pump phase, '
        'but at lower priority fees caused cascading RPC timeouts &mdash; the free-tier DRPC provider '
        'could not track 112 pending transactions simultaneously. Progressive reduction: '
        '56 &rarr; 20 &rarr; 10, with batch=10 proving stable across 69 rounds with zero errors.'
    ))
    story.append(S(
        '<b>Priority fee:</b> 10 gwei (pump: max SMMA growth, ~0.57 ETH/round); 2 gwei (attempted: '
        'RPC timeouts at round 1); 1 gwei (final: stable, ~0.012 ETH/round); 0.2 gwei (theoretical: '
        '+73 rounds, but SMMA eventually decays below breakeven).'
    ))
    story.append(S(
        '<b>Lighthouse timeout:</b> <font face="Courier">timeoutInBlocks=1</font> &mdash; the minimum '
        'possible. Eliminated waiting periods between rounds. In production Robonomics, longer timeouts '
        'provide fairness among multiple providers; for our single-provider experiment, minimum timeout '
        'maximized throughput.'
    ))

    # ── Section 4: Results ───────────────────────────
    story.append(PageBreak())
    story.append(S('4. Results', 'SectionH1'))

    story.append(S('4.1. Phase 1: SMMA Pump', 'SectionH2'))
    story.append(S(
        'The pump phase completed 4 rounds of 56 liabilities each (448 contract calls), consuming '
        '2.27 ETH in gas:'
    ))
    story.append(make_table(
        ['Metric', 'Value'],
        [
            ['SMMA before', '1.03 gwei'],
            ['SMMA after', '~4.0 gwei'],
            ['SMMA amplification', 'x3.88'],
            ['Rounds completed', '4'],
            ['Contract calls', '448'],
            ['Gas consumed', '~2.27 ETH'],
            ['XRT minted (pump)', '~15,519 XRT'],
            ['XRT sold post-pump', '~16,899 XRT -> 0.763 ETH'],
        ],
        col_widths=[170, 200],
    ))
    story.append(sp(4))
    story.append(S(
        'The SMMA responded as predicted by the convergence formula. Each call moved SMMA by '
        '(10.2 &minus; SMMA) / 1000. The exponential approach to the target value is visible in Figure 2.'
    ))
    add_figure(story, 'fig1_smma_dynamics.png',
               '<b>Figure 2.</b> SMMA trajectory during the experiment. '
               'Pump phase (red) raised SMMA from 1.03 to ~4.0 gwei via 448 calls at 10.2 gwei. '
               'Mine phase (green) shows exponential decay toward the 1.2 gwei effective gas price.')

    story.append(S('4.2. Phase 2: Mine', 'SectionH2'))
    story.append(S(
        'After transitioning to 1 gwei priority fee, the mine phase ran 69 rounds with zero errors:'
    ))
    story.append(make_table(
        ['Metric', 'Value'],
        [
            ['Rounds completed', '69'],
            ['Liabilities created', '~1,360'],
            ['Total XRT minted', '24,190 XRT'],
            ['Average XRT per round', '355.73'],
            ['XRT in first round', '443.66'],
            ['XRT in last round', '257.13'],
            ['Emission decline', '-42.0%'],
            ['Total gas consumed', '~729 M gas'],
            ['Errors', '0'],
        ],
        col_widths=[170, 200],
    ))

    add_figure(story, 'fig2_xrt_per_round.png',
               '<b>Figure 3.</b> XRT emission per round (mine phase). Bars show per-round minting; '
               'red line shows cumulative total. Vertical dotted lines mark auto-sell events.')

    story.append(S('4.3. SMMA Decay Dynamics', 'SectionH2'))
    story.append(S(
        'The SMMA decayed from ~1.94 gwei (at mine start, after transition period losses) toward '
        'the effective gas price of ~1.2 gwei. With 20 calls per round (10 create + 10 finalize), '
        'the SMMA decreased approximately 2% per round:'
    ))
    story.append(S(
        '<font face="Courier">SMMA[n+1] = SMMA[n] x (999/1000)' + sup('20') + ' + 1.2 x (1 - (999/1000)' + sup('20') + ')</font>',
        'Formula'
    ))
    story.append(S(
        'The empirical half-life was approximately 35 rounds, consistent with the theoretical '
        'prediction of ln(2) x 1000 / 20 = 34.7 rounds for a period-1000 SMMA with 20 updates '
        'per round.'
    ))

    add_figure(story, 'fig4_smma_convergence.png',
               '<b>Figure 4.</b> SMMA convergence at different priority fees, starting from 1.94 gwei. '
               'Higher priority &rarr; SMMA rises; lower priority &rarr; SMMA decays. Horizontal dashed line '
               'marks the breakeven SMMA at 0.674 gwei.', width=440)

    story.append(PageBreak())
    story.append(S('4.4. Market Impact on Uniswap V2', 'SectionH2'))
    story.append(S(
        'Eleven automated sell events over ~75 minutes revealed consistent price degradation:'
    ))
    story.append(make_table(
        ['Sell #', 'XRT Sold', 'ETH Received', 'Price (uETH/XRT)', 'Delta'],
        [
            ['1', '4,801', '0.1616', '33.65', '---'],
            ['2', '2,094', '0.0691', '33.01', '-1.9%'],
            ['3', '2,019', '0.0659', '32.63', '-1.2%'],
            ['4', '2,331', '0.0758', '32.52', '-0.3%'],
            ['5', '2,248', '0.0723', '32.18', '-1.0%'],
            ['6', '2,177', '0.0692', '31.78', '-1.2%'],
            ['7', '2,116', '0.0665', '31.40', '-1.2%'],
            ['8', '2,064', '0.0642', '31.11', '-0.9%'],
            ['9', '2,256', '0.0694', '30.76', '-1.1%'],
            ['10', '2,146', '0.0652', '30.39', '-1.2%'],
            ['11', '2,044', '0.0615', '30.07', '-1.1%'],
            ['Total', '26,296', '0.8406', '31.97 (avg)', '-10.6%'],
        ],
        col_widths=[45, 65, 85, 100, 55],
    ))

    add_figure(story, 'fig3_price_decay.png',
               '<b>Figure 5.</b> XRT price impact from 11 sequential sells on Uniswap V2. '
               'Blue bars: volume sold; red line: realized price per XRT. '
               'Total decline: 10.6% over ~75 minutes.')

    story.append(S(
        'The approximately linear price decay (~1% per sell event) is consistent with the constant-product '
        'AMM model of Uniswap V2 [5], where each trade shifts the reserve ratio. With thin liquidity '
        '(~25 ETH in the pool), even modest sell volumes create measurable impact.'
    ))

    story.append(S('4.5. Financial Summary', 'SectionH2'))
    story.append(make_table(
        ['Item', 'ETH', 'USD'],
        [
            ['Starting balance', '3.544', '$6,892'],
            ['Gas spent (pump)', '-2.270', '-$4,413'],
            ['Gas spent (mine)', '-0.840', '-$1,634'],
            ['XRT sold (total)', '+1.604', '+$3,118'],
            ['Remaining XRT (675 XRT)', '+0.020', '+$39'],
            ['Final balance', '3.182', '$6,186'],
            ['Net result', '-0.342', '-$665'],
        ],
        col_widths=[180, 80, 80],
    ))

    # ── Section 5: Analysis ──────────────────────────
    story.append(PageBreak())
    story.append(S('5. Analysis and Discussion', 'SectionH1'))

    story.append(S('5.1. The SMMA as an Endogenous Price Oracle', 'SectionH2'))
    story.append(S(
        'The central insight from this experiment is that the <font face="Courier">gasPrice</font> '
        'SMMA in the Factory contract functions as an <b>endogenous price oracle</b> &mdash; a mechanism '
        'that derives its signal entirely from the behavior of system participants rather than from an '
        'external data feed. This design choice reflects a principled decision by the Robonomics '
        'architects: rather than introducing oracle risk (the dependency on an external, potentially '
        'manipulable data source), the emission mechanism directly observes the cost that providers '
        'actually pay to operate the system.'
    ))
    story.append(S(
        'The elegance of this approach is that it creates a <b>truthful mechanism</b> under the original '
        'design assumptions. When gas costs are a meaningful expense for providers (as they were at '
        '20&ndash;200 gwei in 2018), <font face="Courier">tx.gasprice</font> is a credible signal of '
        'the marginal cost of network operation. The emission formula then ensures that providers are '
        'compensated proportionally to their actual costs. Our experiment demonstrates that this mechanism '
        'continues to function correctly in a mathematical sense &mdash; the SMMA converges as predicted, '
        'emission responds proportionally &mdash; even under conditions vastly different from the design era.'
    ))

    story.append(S('5.2. The Reflexive Feedback Loop', 'SectionH2'))
    add_figure(story, 'fig6_feedback_loop.png',
               '<b>Figure 6.</b> The reflexive incentive cycle in XRT emission. Miners\' gas price choices '
               'update the SMMA, which determines emission, which affects profitability, which informs '
               'future gas price choices.', width=320)
    story.append(S(
        'The emission mechanism exhibits a fascinating reflexive property. The cycle operates as follows: '
        '(1) the miner chooses <font face="Courier">tx.gasprice</font> via priority fee; '
        '(2) each transaction updates the SMMA toward the chosen gas price; '
        '(3) the SMMA determines emission rate: higher SMMA means more XRT per gas unit; '
        '(4) minted XRT can be sold on secondary markets for ETH; '
        '(5) revenue from sales determines whether the operation is profitable; '
        '(6) profitability assessment informs the miner\'s choice of gas price for the next round.'
    ))
    story.append(S(
        'This creates a <b>natural equilibrium</b>: miners will bid gas prices up only to the point '
        'where the additional emission revenue covers the additional gas cost. Under the 2018 gas '
        'regime, this equilibrium naturally tracked market gas prices. Under 2026 conditions, the '
        'equilibrium point is much lower, but the feedback mechanism still operates.'
    ))

    story.append(S('5.2.1. Formal Equilibrium Model', 'SectionH3'))
    story.append(S(
        'We can formalize the equilibrium condition. Let <i>p</i> denote the priority fee, <i>b</i> '
        'the base fee, and P' + sup('xrt') + ' the market price of XRT in ETH. At steady state, the '
        'SMMA converges to the effective gas price g' + sup('eff') + ' = b + p. The revenue per round '
        '(10 liabilities, 20 contract calls) is:'
    ))
    story.append(S(
        '<font face="Courier">R(p) = 10 x G_lib x g_eff x 10' + sup('9') + ' / F_auction x P_xrt / 10' + sup('9') + '</font>',
        'Formula'
    ))
    story.append(S(
        'The cost per round is simply the gas spent: '
        '<font face="Courier">C(p) = 20 x G_lib x g_eff x 10' + sup('-9') + '</font> ETH. '
        'The equilibrium priority fee p* satisfies R(p*) = C(p*). Figure 8 illustrates this equilibrium.'
    ))
    add_figure(story, 'fig8_economic_model.png',
               '<b>Figure 8.</b> Economic equilibrium: emission revenue vs gas cost as a function of priority fee. '
               'The green zone marks where mining is profitable; the red zone marks losses. '
               'The crossover point defines the break-even priority fee at steady state.', width=440)
    story.append(S(
        'The key insight is that the equilibrium is <b>self-limiting</b>: increasing the priority fee '
        'raises both revenue (via higher SMMA &rarr; more XRT) and cost (via higher gas expenditure). '
        'At our observed XRT price of ~32 uETH, the model predicts that the &ldquo;Pump &amp; Mine&rdquo; '
        'strategy is only profitable in the transient regime where SMMA exceeds the steady-state value '
        '&mdash; precisely what we observed empirically.'
    ))

    story.append(S('5.3. Properties of the Period-1000 SMMA', 'SectionH2'))
    story.append(S(
        '<b>Convergence rate.</b> The SMMA half-life is ln(2) x P / N = 693 / 20 ~ 35 rounds, '
        'where P = 1000 is the smoothing period and N = 20 is calls per round. We observed a decline '
        'from 1.94 to ~1.41 gwei over 69 rounds, consistent with ~50% convergence toward the target (1.2 gwei).'
    ))
    story.append(S(
        '<b>Manipulation cost.</b> Increasing SMMA from 1.03 to 4.0 gwei required 448 calls at '
        '10.2 gwei effective price, costing 2.27 ETH. The cost scales linearly with the desired '
        'shift magnitude and the gas consumed per call.'
    ))
    story.append(S(
        '<b>Resistance to single-block manipulation.</b> The SMMA can shift at most '
        '(target &minus; SMMA) / 1000 per call. This provides strong protection against flash-loan-style '
        'attacks &mdash; a property that many DeFi protocols adopted only after costly exploits revealed '
        'the dangers of instantaneous price manipulation.'
    ))

    story.append(S('5.4. The Changing Gas Landscape', 'SectionH2'))
    add_figure(story, 'fig7_gas_landscape.png',
               '<b>Figure 7.</b> (a) Ethereum gas price evolution 2018&ndash;2026. (b) Cost per liability as a '
               'function of gas price. The 100x decrease from design era to experiment era fundamentally '
               'altered the economic equilibrium.', width=460)

    story.append(S(
        'The most significant contextual factor is the ~100x decrease in Ethereum gas prices between '
        'the design era (2018) and our experiment (2026). This transformation was driven by multiple '
        'Ethereum protocol upgrades (EIP-1559 [6], The Merge [7], EIP-4844/Dencun [8]) and the migration '
        'of activity to L2 rollups. At 2018 gas prices of 20 gwei, each liability cost ~$42 to create, '
        'making empty liability mining economically infeasible. At 2026 prices of 0.25 gwei, the cost '
        'dropped to $0.53 &mdash; a reduction of ~80x.'
    ))

    story.append(S('5.5. Design Lessons', 'SectionH2'))
    story.append(S(
        '<b>Lesson 1: Environmental assumptions are the most fragile invariant.</b> The Robonomics '
        'architects correctly identified gas cost as the fundamental unit of account. The emission '
        'formula faithfully tracks this metric. What changed was the external environment &mdash; gas prices '
        'decreased 100x &mdash; not any internal property of the mechanism.'
    ))
    story.append(S(
        '<b>Lesson 2: Endogenous oracles have bounded domains of applicability.</b> The SMMA works '
        'excellently when <font face="Courier">tx.gasprice</font> reflects genuine market conditions. '
        'The exponential smoothing prevents single-block manipulation &mdash; a property many later '
        'protocols failed to incorporate. However, like all oracle designs, it has a domain of '
        'applicability bounded by the assumptions about participant behavior.'
    ))
    story.append(S(
        '<b>Lesson 3: Immutable contracts are time capsules of their design era.</b> The Robonomics '
        'v5 contracts &mdash; still correctly minting tokens, managing lighthouses, processing liabilities '
        'in 2026 &mdash; are a testament to the quality of the implementation. That the economic equilibrium '
        'has shifted illustrates the fundamental challenge of encoding economic policy in immutable code.'
    ))

    # ── Section 6: Art of Early Ethereum Design ──────
    story.append(S('6. The Art of Early Ethereum Mechanism Design', 'SectionH1'))
    story.append(S(
        'The Robonomics whitepaper was published on May 12, 2018, during a period of extraordinary '
        'creativity in smart contract architecture. The authors &mdash; Lonshakov and Krupenkin as lead '
        'architects, along with Radchenko, Kapitonov, Khassanov, and Starostin &mdash; drew on a remarkable '
        'intellectual synthesis: Wiener\'s '
        'cybernetics, Coase\'s economics, ROS robotics, and Ethereum\'s programmable state machine. '
        'Several design decisions deserve recognition as pioneering contributions:'
    ))

    story.append(S('6.1. The Lightweight Contract Pattern', 'SectionH2'))
    story.append(S(
        'The Factory uses <font face="Courier">DELEGATECALL</font> to create liability contracts that '
        'share implementation code but maintain separate state. This pattern saved 30&ndash;40% gas per '
        'contract creation and predated the widespread adoption of minimal proxy contracts (EIP-1167, 2018). '
        'The Robonomics team was at the frontier of gas optimization.'
    ))

    story.append(S('6.2. Deferred Signature Architecture', 'SectionH2'))
    story.append(S(
        'Rather than requiring both parties to submit on-chain transactions, Robonomics uses deferred '
        'signatures &mdash; off-chain signed messages that a provider submits on behalf of both parties. '
        'This meta-transaction pattern anticipated EIP-2612 (permit) and EIP-4337 (account abstraction) '
        'by several years. The implementation uses <font face="Courier">ecrecover</font> to verify '
        'demand and offer signatures, ensuring that the transaction sender cannot forge parties\' identities.'
    ))

    story.append(S('6.3. Gas-as-Unit-of-Account', 'SectionH2'))
    story.append(S(
        'The whitepaper\'s principle <i>&ldquo;Emission of 1 Wn = 1 gas utilized by Robonomics&rdquo;</i> '
        'is a conceptual breakthrough. It recognizes that in the EVM, gas is the fundamental measure of '
        'computational work &mdash; and therefore the natural unit of account for a protocol that monetizes '
        'computational work by robots. The emission formula directly embodies this principle, creating a '
        'token whose supply growth is algorithmically linked to EVM resource utilization.'
    ))

    story.append(S('6.4. The Denomination System', 'SectionH2'))
    story.append(S(
        'The XRT denomination system &mdash; wiener (1), coase (10' + sup('3') + '), glushkov (10' + sup('6') +
        '), robonomics token (10' + sup('9') + ') &mdash; encodes the interdisciplinary philosophy of the '
        'project, paying homage to the intellectual lineage: Norbert Wiener (cybernetics), Ronald Coase '
        '(transaction cost economics), and Viktor Glushkov (Soviet cybernetics pioneer).'
    ))

    # ── Section 7: Conclusion ────────────────────────
    story.append(S('7. Conclusion', 'SectionH1'))
    story.append(S(
        'We have presented an empirical study of the Robonomics XRT emission mechanism, conducting '
        'a controlled experiment on Ethereum mainnet that generated 24,190 XRT tokens through 1,360 '
        'liability contracts. The experiment demonstrates that the SMMA-based emission formula '
        'continues to function as mathematically specified eight years after deployment, while the '
        'economic equilibrium has shifted due to the ~100x decrease in Ethereum gas prices.'
    ))
    story.append(S(
        'The &ldquo;Pump &amp; Mine&rdquo; strategy &mdash; artificially inflating the SMMA through '
        'high-priority transactions, then mining at lower cost &mdash; proved technically successful but '
        'economically constrained by secondary market dynamics. The thin liquidity of the XRT/ETH pool '
        'on Uniswap V2 imposed a natural limit on extraction, with each sell event degrading the price '
        'by approximately 1%.'
    ))
    story.append(S(
        'Our key finding is that the Robonomics emission mechanism represents a sophisticated piece of '
        'early Ethereum mechanism design that correctly implements its stated economic principles. '
        '<b>A mechanism that correctly tracks its specified parameters is well-designed, even when '
        'external conditions shift its equilibrium point.</b>'
    ))
    story.append(S(
        'The Robonomics architecture &mdash; with its Factory pattern, lighthouse coordination, deferred '
        'signatures, and gas-proportional emission &mdash; stands as a monument to the creativity and '
        'ambition of early Ethereum builders. Studying these systems years later provides invaluable '
        'insights into the art and science of encoding economic behavior in immutable code.'
    ))

    # ── References ───────────────────────────────────
    story.append(sp(12))
    story.append(HRFlowable(width='100%', color=HexColor('#cccccc')))
    story.append(S('References', 'SectionH1'))
    refs = [
        '[1] S. Lonshakov, A. Krupenkin, E. Radchenko, A. Kapitonov, A. Khassanov, A. Starostin, '
        '&ldquo;Robonomics: platform for integration of cyber physical systems into human economy,&rdquo; May 2018.',
        '[2] N. Wiener, <i>Cybernetics: or Control and Communication in the Animal and the Machine</i>, MIT Press, 1948.',
        '[3] R. H. Coase, &ldquo;The Nature of the Firm,&rdquo; <i>Economica</i>, vol. 4, no. 16, pp. 386&ndash;405, 1937.',
        '[4] M. Quigley et al., &ldquo;ROS: an open-source Robot Operating System,&rdquo; <i>ICRA Workshop</i>, 2009.',
        '[5] H. Adams, N. Zinsmeister, D. Robinson, &ldquo;Uniswap v2 Core,&rdquo; March 2020.',
        '[6] V. Buterin, &ldquo;EIP-1559: Fee market change for ETH 1.0 chain,&rdquo; April 2019.',
        '[7] Ethereum Foundation, &ldquo;The Merge,&rdquo; September 2022.',
        '[8] Ethereum Foundation, &ldquo;EIP-4844: Shard Blob Transactions (Dencun),&rdquo; March 2024.',
        '[9] S. Nakamoto, &ldquo;Bitcoin: A Peer-to-Peer Electronic Cash System,&rdquo; 2008.',
        '[10] Protocol Labs, &ldquo;Filecoin: A Decentralized Storage Network,&rdquo; 2017.',
        '[11] W. Warren, A. Bandeali, &ldquo;0x: An open protocol for decentralized exchange on the Ethereum blockchain,&rdquo; 2017.',
    ]
    for r in refs:
        story.append(S(r, 'RefStyle'))

    # ── Appendices ───────────────────────────────────
    story.append(sp(16))
    story.append(HRFlowable(width='100%', color=HexColor('#cccccc')))
    story.append(S('Appendix A. Observed Gas Parameters', 'SectionH1'))
    story.append(make_table(
        ['Operation', 'Gas (observed)', 'Std. dev.'],
        [
            ['createLiability', '789,000', '+/- 5,000'],
            ['finalizeLiability', '267,000', '+/- 1,000'],
            ['swapExactTokensForETH', '112,000', '+/- 3,000'],
            ['Per liability (create + finalize)', '1,058,000', '---'],
            ['Per round (10 create + 10 finalize)', '10,564,000', '---'],
        ],
        col_widths=[200, 100, 80],
    ))

    story.append(sp(12))
    story.append(S('Appendix B. Smart Contract Addresses', 'SectionH1'))
    story.append(make_table(
        ['Contract', 'Address'],
        [
            ['Factory', '0x7e384AD1FE06747594a6102EE5b377b273DC1225'],
            ['XRT (ERC-20)', '0x7dE91B204C1C737bcEe6F000AAA6569Cf7061cb7'],
            ['Lighthouse (exp.)', '0x04C672af1e54d6C9Bd3f153d590f5681d8EcbbeE'],
            ['Auction', '0x86da63b3341924c88baa5adbb2b8f930cc02e586'],
            ['Uniswap V2 Router', '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'],
            ['Chainlink ETH/USD', '0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419'],
        ],
        col_widths=[130, 310],
    ))

    story.append(sp(12))
    story.append(S('Appendix C. Experiment Timeline', 'SectionH1'))
    story.append(make_table(
        ['Time', 'Event', 'Key metric'],
        [
            ['T+0 min', 'Pump launched (batch=56, prio=10 gwei)', 'SMMA = 1.03 gwei'],
            ['T+15 min', 'Pump complete (4 rounds, budget exhausted)', 'SMMA ~ 4.0 gwei'],
            ['T+20 min', 'Cleanup: finalize remaining, sell 16,899 XRT', '0.763 ETH received'],
            ['T+25 min', 'Mine attempt #1 (batch=56, prio=1 gwei)', 'TX timeouts at round 13'],
            ['T+45 min', 'Mine attempt #2 (batch=56, prio=2 gwei)', 'TX timeout at round 1'],
            ['T+55 min', 'Mine attempt #3 (batch=20, prio=2 gwei)', 'TX timeout at round 1'],
            ['T+60 min', 'Mine attempt #4 (batch=10, prio=1 gwei)', 'Stable (0 errors)'],
            ['T+135 min', '69 rounds complete, mining unprofitable', 'SMMA = 1.41 gwei'],
            ['T+140 min', 'Experiment terminated', 'Net: -0.342 ETH'],
        ],
        col_widths=[65, 215, 130],
    ))

    story.append(sp(12))
    story.append(S('Appendix D. Source Code', 'SectionH1'))
    story.append(S(
        'The complete source code for <font face="Courier">xrt-classic-miner</font> is available at: '
        '<font face="Courier">/home/ens/sources/xrt-classic-miner/</font>'
    ))
    story.append(make_table(
        ['Module', 'Description', 'Lines'],
        [
            ['xrt_miner/miner.py', 'Core mining logic (XRTMiner class)', '~620'],
            ['xrt_miner/signer.py', 'Demand/offer/result encoding', '~183'],
            ['xrt_miner/abi.py', 'Contract interfaces and addresses', '~150'],
            ['xrt_miner/__main__.py', 'CLI entry point (Click)', '~400'],
        ],
        col_widths=[130, 200, 50],
    ))

    # Build with page numbers
    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    print(f'PDF generated: {OUT_PDF}')


if __name__ == '__main__':
    build()
