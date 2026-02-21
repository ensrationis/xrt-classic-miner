"""Demand/offer/result message encoding & signing for Robonomics v1.0 (v5)."""

from eth_abi import encode
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def _addr_bytes(addr: str) -> bytes:
    return bytes.fromhex(addr[2:].lower().zfill(40))


def _encode_packed_demand(
    model: bytes,
    objective: bytes,
    token: str,
    cost: int,
    lighthouse: str,
    validator: str,
    validator_fee: int,
    deadline: int,
    nonce: int,
    sender: str,
) -> bytes:
    """encodePacked for demand hash (v1.0 format with nonce and sender)."""
    return (
        model
        + objective
        + _addr_bytes(token)
        + cost.to_bytes(32, "big")
        + _addr_bytes(lighthouse)
        + _addr_bytes(validator)
        + validator_fee.to_bytes(32, "big")
        + deadline.to_bytes(32, "big")
        + nonce.to_bytes(32, "big")
        + _addr_bytes(sender)
    )


def _encode_packed_offer(
    model: bytes,
    objective: bytes,
    token: str,
    cost: int,
    validator: str,
    lighthouse: str,
    lighthouse_fee: int,
    deadline: int,
    nonce: int,
    sender: str,
) -> bytes:
    """encodePacked for offer hash (validator before lighthouse). v1.0 format."""
    return (
        model
        + objective
        + _addr_bytes(token)
        + cost.to_bytes(32, "big")
        + _addr_bytes(validator)
        + _addr_bytes(lighthouse)
        + lighthouse_fee.to_bytes(32, "big")
        + deadline.to_bytes(32, "big")
        + nonce.to_bytes(32, "big")
        + _addr_bytes(sender)
    )


def _encode_packed_result(
    liability: str,
    result: bytes,
    success: bool,
) -> bytes:
    """encodePacked for result hash."""
    return (
        _addr_bytes(liability)
        + result
        + (b"\x01" if success else b"\x00")
    )


def _sign_hash(msg_bytes: bytes, private_key: str) -> bytes:
    """keccak256 + EIP-191 sign."""
    msg_hash = Web3.keccak(msg_bytes)
    signable = encode_defunct(primitive=msg_hash)
    signed = Account.sign_message(signable, private_key=private_key)
    return signed.signature


def build_demand(
    model: bytes,
    objective: bytes,
    token: str,
    cost: int,
    lighthouse: str,
    validator: str,
    validator_fee: int,
    deadline: int,
    nonce: int,
    sender: str,
    private_key: str,
) -> bytes:
    """Build signed demand bytes for lighthouse.createLiability().

    v1.0 format: 10 ABI params, nonce is uint256 from factory.nonceOf(),
    sender is address (verified via ecrecover).
    """
    signature = _sign_hash(
        _encode_packed_demand(
            model, objective, token, cost, lighthouse,
            validator, validator_fee, deadline, nonce, sender,
        ),
        private_key,
    )
    return encode(
        [
            "bytes", "bytes", "address", "uint256",
            "address", "address", "uint256", "uint256",
            "address", "bytes",
        ],
        [
            model, objective, Web3.to_checksum_address(token), cost,
            Web3.to_checksum_address(lighthouse),
            Web3.to_checksum_address(validator),
            validator_fee, deadline,
            Web3.to_checksum_address(sender), signature,
        ],
    )


def build_offer(
    model: bytes,
    objective: bytes,
    token: str,
    cost: int,
    validator: str,
    lighthouse: str,
    lighthouse_fee: int,
    deadline: int,
    nonce: int,
    sender: str,
    private_key: str,
) -> bytes:
    """Build signed offer bytes for lighthouse.createLiability().

    v1.0 format: 10 ABI params, nonce is uint256 from factory.nonceOf(),
    sender is address (verified via ecrecover).
    """
    signature = _sign_hash(
        _encode_packed_offer(
            model, objective, token, cost, validator,
            lighthouse, lighthouse_fee, deadline, nonce, sender,
        ),
        private_key,
    )
    return encode(
        [
            "bytes", "bytes", "address", "uint256",
            "address", "address", "uint256", "uint256",
            "address", "bytes",
        ],
        [
            model, objective, Web3.to_checksum_address(token), cost,
            Web3.to_checksum_address(validator),
            Web3.to_checksum_address(lighthouse),
            lighthouse_fee, deadline,
            Web3.to_checksum_address(sender), signature,
        ],
    )


def build_result(
    liability: str,
    result: bytes,
    success: bool,
    private_key: str,
) -> bytes:
    """Build result signature for lighthouse.finalizeLiability()."""
    return _sign_hash(
        _encode_packed_result(liability, result, success),
        private_key,
    )
