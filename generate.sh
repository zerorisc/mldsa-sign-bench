#! /bin/bash

set -e

# Paths to the preprocessed datasets to pick test vectors from.
MLDSA44_DATASET=dilithium/ref/PQCsignKAT_Dilithium2.rsp
MLDSA65_DATASET=dilithium/ref/PQCsignKAT_Dilithium3.rsp
MLDSA87_DATASET=dilithium/ref/PQCsignKAT_Dilithium5.rsp

for n in 1 2 10 100
do
  echo "Generating $n-test sets for mean..."

  for ext in "json" "rsp"
  do
    ./select_tests.py --deterministic --ntests $n --params mldsa44 --rsp $MLDSA44_DATASET --out "testsets/mean/mldsa44_$n.$ext"
    ./select_tests.py --deterministic --ntests $n --params mldsa65 --rsp $MLDSA65_DATASET --out "testsets/mean/mldsa65_$n.$ext"
    ./select_tests.py --deterministic --ntests $n --params mldsa87 --rsp $MLDSA87_DATASET --out "testsets/mean/mldsa87_$n.$ext"
  done

  for pct in 5 50 95
  do
    echo "Generating $n-test sets for ${pct}th percentile..."

    for ext in "json" "rsp"
    do
      ./select_tests.py --deterministic --ntests $n --params mldsa44 --rsp $MLDSA44_DATASET --out "testsets/percentile/$pct/mldsa44_$n.$ext" --percentile $pct
      ./select_tests.py --deterministic --ntests $n --params mldsa65 --rsp $MLDSA65_DATASET --out "testsets/percentile/$pct/mldsa65_$n.$ext" --percentile $pct
      ./select_tests.py --deterministic --ntests $n --params mldsa87 --rsp $MLDSA87_DATASET --out "testsets/percentile/$pct/mldsa87_$n.$ext" --percentile $pct
    done
  done
done
