"""Write rozier/config.mjs: 0xRozier's config.js with only TOKENS, TARGET_RATIOS, COINGECKO_IDS for PEARL+USDC and
ENABLE_YIELD_FARMING false (no Aave in the test). PEARL band 0.195-0.205 = same +-2.5% of target as its USDC band."""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "..", "downloads", "0xRozier_rebalancing-bot", "config.js")).read()
start, end = src.index("export const TOKENS"), src.index("// Seuils de rebalancing")
tokens = '''export const TOKENS = {
    PEARL: { symbol: "PEARL", address: "stand-in-pearl", decimals: 8 },
    USDC: { symbol: "USDC", address: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", decimals: 6 },
};

export const TARGET_RATIOS = {
    PEARL: { target: 0.20, min: 0.195, max: 0.205, description: "PEARL" },
    USDC: { target: 0.80, min: 0.78, max: 0.82, description: "Stablecoin" },
};

'''
src = src[:start] + tokens + src[end:]
src = re.sub(r"export const COINGECKO_IDS = \{.*?\};", 'export const COINGECKO_IDS = {\n    PEARL: "pearl",\n    USDC: "usd-coin",\n};',
             src, flags=re.S)
assert "ENABLE_YIELD_FARMING: true" in src
src = src.replace("ENABLE_YIELD_FARMING: true", "ENABLE_YIELD_FARMING: false")
with open(os.path.join(HERE, "config.mjs"), "w") as f:
    f.write("// user config for the test, made by make_config.py from config.js\n" + src)
print("wrote config.mjs")
