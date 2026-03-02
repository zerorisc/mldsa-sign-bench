#! /bin/bash

set -e

# Apply local changes to the dilithium submodule.
cd dilithium
git apply ../dilithium.patch

# Generate the large random test datasets with rejection traces.
cd ref
make nistkat
./nistkat/PQCgenKAT_sign2
./nistkat/PQCgenKAT_sign3
./nistkat/PQCgenKAT_sign5
