# ML-DSA Sign Benchmarking Test Sets

Accurately benchmarking ML-DSA signatures is hard, at least if you don't want to run huge numbers of tests.
But it doesn't have to be!
These scripts select specific ML-DSA signing inputs (message, randomness input, and secret key) that will have performance profiles close to average.

## Basic Usage

If you just want to use the test data, the `testsets` folder has a bunch of outputs for different sizes of test sets that you can use to estimate average ML-DSA signing performance.
For example, `testsets/mldsa44_10.json` has a set of 10 inputs for ML-DSA-44 signing that together have a signing time profile close to average.
The more tests you use, the higher the accuracy.

The `.rsp` files there contain exactly the same test inputs as the `.json` ones, but they're designed to match the NIST known-answer test formats.
If your test infrastructure is already built to handle NIST-style `.rsp` files, you might find it easier to use those than the JSON.

## Generating test sets

If you want to generate your own alternative test sets, or re-generate the ones here with different parameters, you'll need to run some local scripts.

First, clone the repo with `--recurse-submodules` (to catch the Dilithium submodule).
If you didn't do this, don't worry, just run `git submodule init` and then `git submodule update` to retrieve it.

Then, from the top directory of this repo, run:
```
./preprocess.sh
```

That will apply a local patch to the `dilithium` submodule and generate some big preprocessed ML-DSA signature datasets.
The local patch ensures that each signature in the output gets annotated with a trace of how many candidate signatures the signing routine had to reject in the process, and why each was rejected.

The data under `testsets` was created with `generate.sh`, which basically just batch-calls `select_tests.py`.
You can look at the usage there for hints, or run `./select_tests.py -h` to see all of the script's options.
