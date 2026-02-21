"""Minimal contract ABIs and mainnet addresses for Robonomics v5."""

# Ethereum Mainnet addresses
FACTORY_ADDRESS = "0x7e384AD1FE06747594a6102EE5b377b273DC1225"
XRT_ADDRESS = "0x7de91b204c1c737bcee6f000aaa6569cf7061cb7"
WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
UNISWAP_V2_ROUTER = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
CHAINLINK_ETH_USD = "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419"
AUCTION_ADDRESS = "0x86da63b3341924c88baa5adbb2b8f930cc02e586"

FACTORY_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_gas", "type": "uint256"}],
        "name": "wnFromGas",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "_account", "type": "address"}],
        "name": "nonceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "totalGasConsumed",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "gasPrice",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "gasEpoch",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "_lighthouse", "type": "address"}],
        "name": "isLighthouse",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_minimalStake", "type": "uint256"},
            {"name": "_timeoutInBlocks", "type": "uint256"},
            {"name": "_name", "type": "string"},
        ],
        "name": "createLighthouse",
        "outputs": [{"name": "", "type": "address"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "xrt",
        "outputs": [{"name": "", "type": "address"}],
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "lighthouse", "type": "address"},
            {"indexed": False, "name": "name", "type": "string"},
        ],
        "name": "NewLighthouse",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "liability", "type": "address"},
        ],
        "name": "NewLiability",
        "type": "event",
    },
]

LIGHTHOUSE_ABI = [
    {
        "constant": False,
        "inputs": [{"name": "_value", "type": "uint256"}],
        "name": "refill",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [{"name": "_value", "type": "uint256"}],
        "name": "withdraw",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_demand", "type": "bytes"},
            {"name": "_offer", "type": "bytes"},
        ],
        "name": "createLiability",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_liability", "type": "address"},
            {"name": "_result", "type": "bytes"},
            {"name": "_success", "type": "bool"},
            {"name": "_signature", "type": "bytes"},
        ],
        "name": "finalizeLiability",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "minimalStake",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "_index", "type": "uint256"}],
        "name": "providers",
        "outputs": [{"name": "", "type": "address"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "_provider", "type": "address"}],
        "name": "stakes",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "_provider", "type": "address"}],
        "name": "indexOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "marker",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "quota",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "keepAliveBlock",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "timeoutInBlocks",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
]

XRT_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
]

UNISWAP_V2_ROUTER_ABI = [
    {
        "constant": True,
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "path", "type": "address[]"},
        ],
        "name": "getAmountsOut",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"},
        ],
        "name": "swapExactTokensForETH",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"},
        ],
        "name": "swapExactETHForTokens",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "type": "function",
        "payable": True,
        "stateMutability": "payable",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "amountOut", "type": "uint256"},
            {"name": "path", "type": "address[]"},
        ],
        "name": "getAmountsIn",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "type": "function",
    },
]

AUCTION_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "finalPrice",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
]

CHAINLINK_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "latestAnswer",
        "outputs": [{"name": "", "type": "int256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
]

LIABILITY_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "promisee",
        "outputs": [{"name": "", "type": "address"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "promisor",
        "outputs": [{"name": "", "type": "address"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "isFinalized",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
]
