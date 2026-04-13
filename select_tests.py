#! /usr/bin/env python3

import argparse
import json
import math
import random
from enum import Enum, auto

# ML-DSA parameter options.
class Params(Enum):
  MLDSA44 = auto()
  MLDSA65 = auto()
  MLDSA87 = auto()

# Termination conditions for sign loop iterations. Note: Checks must appear in
# the order they are checked in the algorithm!
class Iteration(Enum):
  Z = 0
  R0 = 1
  CT0 = 2
  H = 3
  PASS = 4

# ML-DSA constants
N = 256
Q = (1 << 23) - (1 << 13) + 1

def z_pass_chance(l, beta, gamma1):
  return (1 - (beta / (gamma1 - 0.5)))**(l*N)

def r0_pass_chance(k, beta, gamma2):
  return ((2*(gamma2 - beta) - 1) / (2*gamma2))**(k*N)

def pass_chance(params, check):
  if params == Params.MLDSA44:
    k = 4
    l = 4
    tau = 39 
    eta = 2
    gamma1 = 1 << 17
    gamma2 = (Q - 1) // 88
  elif params == Params.MLDSA65:
    k = 6
    l = 5
    tau = 49 
    eta = 4
    gamma1 = 1 << 19
    gamma2 = (Q - 1) // 32
  elif params == Params.MLDSA87:
    k = 8
    l = 7
    tau = 60 
    eta = 2
    gamma1 = 1 << 19
    gamma2 = (Q - 1) // 32
  else:
    raise ValueError(f'Unrecognized parameters: {params}')
  beta = tau * eta
  if check == Iteration.Z:
    return z_pass_chance(l=l, beta=beta, gamma1=gamma1)
  elif check == Iteration.R0:
    return r0_pass_chance(k=k, beta=beta, gamma2=gamma2)
  elif check == Iteration.CT0 or check == Iteration.H:
    # These checks have a high probability of passing and don't need to be too
    # exact. The Dilithium paper states that the chance they both pass is
    # 98-99%, so this number is sqrt(0.985). 
    return 0.9925
  elif check == Iteration.PASS:
    return 1
  else:
    raise ValueError(f'Unrecognized check: {check}')

def parse_rsp(rsp):
  '''Parse test vector from a .rsp file.'''
  # fields and whether they are encoded in hex or not
  fields = {
    'count': False,
    'seed': True,
    'mlen': False,
    'msg': True,
    'rnd': True,
    'pk': True,
    'sk': True,
    'smlen': False,
    'sm': True,
    'iterlen': False,
    'iter': True,
  }
  out = []
  testvec = {}
  for line in rsp:
    if '=' not in line:
      if testvec:
        raise ValueError(f'Found a blank line before the test vector was complete: {testvec}')
      continue
    name, value = line.split('=')
    name = name.strip()
    value = value.strip()
    if name not in fields:
      raise ValueError(f'Unrecognized field: "{name}"')
    if name in testvec:
      raise ValueError(f'Duplicated field {name} in test vector: {testvec}')
    is_hex = fields[name]
    if is_hex:
      value = bytes.fromhex(value)
    else:
      value = int(value)
    testvec[name] = value
    if all([name in testvec for name in fields]):
      count = testvec['count']
      if len(testvec['msg']) != testvec['mlen']:
        raise ValueError(f'mlen does not match in test vector with count={count}')
      if len(testvec['sm']) != testvec['smlen']:
        raise ValueError(f'smlen does not match in test vector with count={count}')
      if len(testvec['iter']) != testvec['iterlen']:
        raise ValueError(f'iterlen does not match in test vector with count={count}')
      out.append(testvec)
      testvec = {}
  assert not testvec
  return out

def write_sample_json(params, sample, dst):
  '''Write sample test vectors to a file in JSON form.'''
  data = []
  for i in range(len(sample)):
    t = sample[i]
    tdata = {'test_id': i}
    for field in ['mlen', 'msg', 'rnd', 'sk']:
      value = t[field]
      if isinstance(value, bytes):
        value = value.hex()
      tdata[field] = value
    # special treatment for 'sm': remove the message from the end.
    mlen = t['mlen']
    assert t['sm'][-mlen:] == t['msg']
    tdata['siglen'] = t['smlen'] - mlen
    tdata['sig'] = t['sm'][:-mlen].hex()
    data.append(tdata)
  json.dump(data, dst)

def write_sample_rsp(params, sample, dst):
  '''Write sample test vectors to a file in NIST .rsp form.'''
  for i in range(len(sample)):
    t = sample[i]
    for field in ['mlen', 'msg', 'rnd', 'sk', 'smlen', 'sm']:
      value = t[field]
      if isinstance(value, bytes):
        value = value.hex()
      dst.write(f'{field} = {value}\n')

def incorporate_testvec(passes, fails, testvec):
  '''Helper for distance_from_ideal.'''
  failed_check_lookup = {
    0: Iteration.Z,
    1: Iteration.R0,
    2: Iteration.CT0,
    3: Iteration.H,
  }
  for failed_check_code in testvec['iter']:
    if failed_check_code not in failed_check_lookup:
      raise ValueError(f'Unrecognized iteration code: {failed_check_code}')
    failed_check = failed_check_lookup[failed_check_code]
    for check in Iteration:
      if check == failed_check:
        fails[check.name] += 1
        break
      passes[check.name] += 1
  # final successful iteration
  for check in Iteration:
      passes[check.name] += 1

def distance(ideal, sample, verbose=False):
  '''Serves as the objective function to minimize in a sample.'''
  passes = {check.name:0 for check in Iteration}
  fails = {check.name:0 for check in Iteration}
  for testvec in sample:
    incorporate_testvec(passes, fails, testvec)
  actual = {c.name: passes[c.name] / (passes[c.name] + fails[c.name]) for c in Iteration}
  if verbose:
      print('actual:', actual)
  return sum([abs(ideal[c.name] - actual[c.name]) for c in Iteration])

def get_sample(params, n, testvecs, ideal):
  '''Greedy algorithm that clusters the data and picks the datapoint in each
     cluster that brings it closest to the goal at the moment.'''
  sample = []
  cluster_size = len(testvecs) // n
  if cluster_size <= 2:
    raise ValueError(f'Not enough data to sample from (minimum 2x target size, recommended 10x)')
  for i in range(n):
    best_dist = None
    best_testvec = None
    for t in testvecs[i*cluster_size:(i+1)*cluster_size]:
      witht_dist = distance(ideal, sample + [t])
      if best_dist is None or witht_dist < best_dist:
        best_dist = witht_dist
        best_testvec = t
    sample.append(best_testvec)
  return sample

def check_params(params, testvecs):
  '''Check that the secret key lengths in the tests match the parameters.'''
  if params == Params.MLDSA44:
    sklen = 2560
  elif params == Params.MLDSA65:
    sklen = 4032
  elif params == Params.MLDSA87:
    sklen = 4896
  for t in testvecs:
    if len(t['sk']) != sklen:
      raise ValueError(f'Key length {len(t["sk"])} in testvec does not match parameters!')


def get_percentile_ideal(params, percentile):
  '''Get a performance profile that corresponds to a specific percentile.

  Can be used to get test sets that estimate the median (50%) or specific
  points like 95th percentile latency for better estimates of cases that need
  strong eventual guarantees.


  Relies on some assumptions about the performance of checks relative to one
  another; may not translate well across different implementations.
  '''
  assert 0 <= percentile < 100

  pass_rates = {check: pass_chance(params, check) for check in Iteration}

  # keep simulating traces, shortest first, until the target percentile is reached.
  proportion_done = 0.0
  queue = [(Iteration.Z, [], [], 1.0)]
  while len(queue) > 0:
    next_check, trace, rejections, prob = queue.pop(0)
    if next_check == Iteration.PASS:
      proportion_done += prob
      if proportion_done * 100 >= percentile:
        ideal = {}
        for check in Iteration:
          if check == Iteration.PASS:
            ideal[check.name] = 1.0
          else:
            ideal[check.name] = 1.0 - (rejections.count(check) / trace.count(check))
        return ideal
      continue
    # enqueue the passed case
    passed_next_check = Iteration((next_check.value + 1) % len(Iteration))
    passed_prob = pass_rates[next_check]
    queue.append((passed_next_check, trace + [next_check], rejections, prob * passed_prob))
    # enqueue the failed case
    failed_prob =  1.0 - passed_prob
    queue.append((Iteration.Z, trace + [next_check], rejections + [next_check], prob * failed_prob))

    # timing assumption: Z >> R0 >> CT0 >> H (same as check order!)
    # Z >> R is reliably true for memory-optimized implementations since it
    # includes A expansion; CT0 and H matter less because they fail so rarely
    queue.sort(key=lambda x: (x[0].value, -x[1].count(Iteration.Z)), reverse=True)

  raise RuntimeError('Should not get here!')

if __name__ == '__main__':
  param_lookup = {x.name.lower(): x for x in Params}
  parser = argparse.ArgumentParser(description='Sample synthetic test data for ML-DSA.')
  parser.add_argument('--ntests', type=int, default=100,
                      help='Number of test vectors to select.')
  parser.add_argument('--rsp', type=argparse.FileType('r'),
                      help='Augmented .rsp file with source data (use - for stdin).')
  parser.add_argument('--out', type=argparse.FileType('w'),
                      help='Destination file for sampled test vectors (use - for stdout). '
                      'If the filename has a .rsp extension, uses NIST .rsp format instead '
                      'of JSON.')
  parser.add_argument('--params', type=str,
                      help=f'ML-DSA parameters (options: {list(param_lookup.keys())}).')
  parser.add_argument('--percentile', required=False, type=int,
                      help=f'Percentile to target (1-99).')
  parser.add_argument('--deterministic', required=False, action='store_true',
                      help=f'Sample deterministically instead of pseudo-randomly.')
  parser.add_argument('--verbose', required=False, action='store_true')
  args = parser.parse_args()

  if args.params not in param_lookup:
    raise ValueError(f'Unrecognized parameters: {args.params}')
  params = param_lookup[args.params]

  testvecs = parse_rsp(args.rsp)
  check_params(params, testvecs)
  if args.verbose:
    print(f'Sampling {args.ntests} tests from a set of {len(testvecs)}...')

  # Shuffle the test vectors so that every sampling gets a slightly different
  # selection of tests.
  if not args.deterministic:
    random.shuffle(testvecs)

  if args.percentile is not None:
    if not 0 < args.percentile < 100:
        raise ValueError(f"invalid percentile {args.percentile}: (must be in range 1-99)")
    ideal = get_percentile_ideal(params, args.percentile)
  else:
    # aim for mean
    ideal = {check.name: pass_chance(params, check) for check in Iteration}

  sample = get_sample(params, args.ntests, testvecs, ideal)
  if args.verbose:
    print('selected tests:', sorted([t['count'] for t in sample]))
    print('ideal:', ideal)
    print('distance from ideal:', distance(ideal, sample, verbose=True))

  if args.out.name.endswith('.rsp'):
    write_sample_rsp(params, sample, args.out)
  else:
    write_sample_json(params, sample, args.out)
