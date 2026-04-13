#! /bin/bash

set -e

# Paths to the preprocessed datasets to pick test vectors from.
MLDSA44_DATASET=dilithium/ref/PQCsignKAT_Dilithium2.rsp
MLDSA65_DATASET=dilithium/ref/PQCsignKAT_Dilithium3.rsp
MLDSA87_DATASET=dilithium/ref/PQCsignKAT_Dilithium5.rsp

for n in 1 2 10 100
do
  # Generate JSON formats
  ./select_tests.py --deterministic --ntests $n --params mldsa44 --rsp $MLDSA44_DATASET --out "testsets/mldsa44_$n.json"
  ./select_tests.py --deterministic --ntests $n --params mldsa65 --rsp $MLDSA65_DATASET --out "testsets/mldsa65_$n.json"
  ./select_tests.py --deterministic --ntests $n --params mldsa87 --rsp $MLDSA87_DATASET --out "testsets/mldsa87_$n.json"

  # Generate RSP formats
  ./select_tests.py --deterministic --ntests $n --params mldsa44 --rsp $MLDSA44_DATASET --out "testsets/mldsa44_$n.rsp"
  ./select_tests.py --deterministic --ntests $n --params mldsa65 --rsp $MLDSA65_DATASET --out "testsets/mldsa65_$n.rsp"
  ./select_tests.py --deterministic --ntests $n --params mldsa87 --rsp $MLDSA87_DATASET --out "testsets/mldsa87_$n.rsp"

  # Generate median testvecs
  ./select_tests.py --deterministic --ntests $n --params mldsa44 --rsp $MLDSA44_DATASET --out "testsets/mldsa44_median_$n.json" --percentile 50
  ./select_tests.py --deterministic --ntests $n --params mldsa65 --rsp $MLDSA65_DATASET --out "testsets/mldsa65_median_$n.json" --percentile 50
  ./select_tests.py --deterministic --ntests $n --params mldsa87 --rsp $MLDSA87_DATASET --out "testsets/mldsa87_median_$n.json" --percentile 50
done
