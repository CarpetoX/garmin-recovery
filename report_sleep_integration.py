#!/usr/bin/env python3
"""V2.4.6 additive integration; retains original certificate logic and immutable ledger."""
import hashlib
import json
from pathlib import Path
import report_delivery_gate as gate

TARGETS={'0830':'09:05','1645':'17:10','2245':'23:10'}
_original_build=gate.build_certificate
_original_snapshot=gate.compact_cycle_snapshot

def sleep_state():
    obj=gate._read_json('morning_sleep_status.json',{})
    return obj if isinstance(obj,dict) else {}

def build(chain, file_times, now):
    cert=_original_build(chain,file_times,now)
    cert['gate_version']='2.4.6'
    cert['target_report_at']=TARGETS.get(chain['slot']['slot'],cert['target_report_at'])
    state=sleep_state()
    # Never equate a successful workflow with confirmed sleep.
    cert['morning_sleep']={
        'state':state.get('state','unavailable'),
        'is_definitive':bool(state.get('is_definitive')),
        'generated_at':state.get('generated_at'),
        'date':state.get('date'),
        'earliest_definitive_at':state.get('earliest_definitive_at'),
    }
    cert['physiological_report_status']=('definitive' if state.get('is_definitive') and state.get('date')==now.date().isoformat() else 'provisional') if chain['slot']['slot']=='0830' else 'not_evaluated_for_this_slot'
    cert['limitations'].append('Data-ready certificate does not certify completed sleep; consult morning_sleep_status.json.')
    return cert

def snapshot(cert):
    data,_=_original_snapshot(cert)
    data['morning_sleep']=cert.get('morning_sleep',{})
    data['physiological_report_status']=cert.get('physiological_report_status','unknown')
    raw=json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    return data,hashlib.sha256(raw).hexdigest()

gate.build_certificate=build
gate.compact_cycle_snapshot=snapshot
# Gate's SLOTS is used to identify runs and build target; only change targets.
gate.SLOTS=tuple((h,m,code,TARGETS.get(code,target)) for h,m,code,target in gate.SLOTS)

if __name__=='__main__':
    raise SystemExit(gate.main())
