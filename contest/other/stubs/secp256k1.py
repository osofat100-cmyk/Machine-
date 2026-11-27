"""Stub: secp256k1 is only used by bitshares_signing to sign BitShares DEX orders; it will not build here.
A backtest signs nothing, so this stand-in only lets `import qtradex` succeed. Any real use raises."""


class _Any:
    def __getattr__(self, name):
        return 0

    def __call__(self, *a, **k):
        raise RuntimeError("secp256k1 stub: signing is not available in this test")


class PrivateKey:
    def __init__(self, *a, **k):
        raise RuntimeError("secp256k1 stub: signing is not available in this test")


class PublicKey(PrivateKey):
    pass


ffi = _Any()
lib = _Any()
ALL_FLAGS = 0
