#!/bin/bash
name=$1; tf=$2; dir=$(venv/bin/python -c "
import re,glob,os
for f in glob.glob('downloads/fts/user_data/strategies/**/*.py', recursive=True):
    if re.search(r'^class\s+$name\s*\(', open(f).read(), re.M): print(os.path.dirname(f)); break")
extra=""; [ -n "$tf" ] && extra="--timeframe $tf"
venv/bin/freqtrade lookahead-analysis -c config.json --strategy $name --strategy-path $dir $extra \
  --timerange 20261001-20261121 --fee 0.007 --minimum-trade-amount 1 --targeted-trade-amount 20 \
  --lookahead-analysis-exportfilename lookahead/$name.csv > lookahead/$name.log 2>&1
echo "$name done: $(grep -E "│ *$name" lookahead/$name.log | tail -1 | tr -s ' ')"
