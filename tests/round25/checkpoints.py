# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
"""Compare bounded externally captured checkpoints, not restore machine state.

No KVM checkpoint producer is claimed in this increment. Both capture manifests
must identify the same kernel/root/source/input/environment and checkpoint scope.
"""
import re
HASH=re.compile(r'[0-9a-f]{64}\Z')
IDENTITY=('source_sha256','kernel_sha256','root_sha256','input_sha256','environment_sha256','scope')
STATE=('registers_sha256','ram_sha256','devices_sha256','input_offset')
def validate(run):
    if set(run)!={'schema','identity','checkpoints','complete'} or run['schema']!='linux001.checkpoints.v1':raise ValueError('checkpoint schema')
    if run['complete'] is not True:raise ValueError('incomplete capture')
    identity=run['identity']
    if set(identity)!=set(IDENTITY) or identity['scope']!='same-host-selected-state-v1':raise ValueError('identity fields/scope')
    if any(not isinstance(identity[k],str) or not HASH.fullmatch(identity[k]) for k in IDENTITY[:-1]):raise ValueError('identity hash')
    points=run['checkpoints']
    if not isinstance(points,list) or not 1<=len(points)<=4096:raise ValueError('checkpoint bounds')
    previous=0
    for i,p in enumerate(points):
        if set(p)!=set(STATE)|{'ordinal'} or type(p['ordinal']) is not int or p['ordinal']!=i:raise ValueError('checkpoint order')
        for k in STATE[:-1]:
            if not isinstance(p[k],str) or not HASH.fullmatch(p[k]):raise ValueError('state hash')
        if type(p['input_offset']) is not int or not previous<=p['input_offset']<=1048576:raise ValueError('input offset')
        previous=p['input_offset']
    return run

def compare(left,right):
    validate(left);validate(right)
    if left['identity']!=right['identity']:raise ValueError('incompatible run identities')
    for i,(a,b) in enumerate(zip(left['checkpoints'],right['checkpoints'])):
        for field in STATE:
            if a[field]!=b[field]:return {'status':'FAIL','ordinal':i,'field':field}
    if len(left['checkpoints'])!=len(right['checkpoints']):return {'status':'FAIL','ordinal':min(len(left['checkpoints']),len(right['checkpoints'])),'field':'missing_checkpoint'}
    return {'status':'PASS','checkpoints':len(left['checkpoints']),'scope':'selected-state equality only; no restore/replay claim'}
