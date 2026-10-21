#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Compare current/reference endpoint pins at 40 MHz write/16 MHz read SCK."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not args.output.is_absolute() or args.output.exists():
        parser.error('output must be an absolute fresh directory')
    out=args.output.resolve();out.mkdir(parents=True);staged=out/'source';staged.mkdir()
    here=Path(__file__).resolve().parent
    endpoint=here.parents[1]/'gamebub/rtl/esp32_v102_endpoint.sv'
    frozen=here/'reference/esp32_v102_endpoint.sv'
    tb=here/'tb_endpoint_timing.sv'
    shutil.copy2(endpoint,staged/endpoint.name);shutil.copy2(tb,staged/tb.name)
    reference=staged/'esp32_v102_reference.sv'
    original=frozen.read_text()
    assert original.count('module esp32_v102_endpoint (')==1
    reference.write_text(original.replace('module esp32_v102_endpoint (','module esp32_v102_reference ('))
    env=os.environ.copy();env['PATH']='/opt/gamebub-openxc7-20261021/oss-cad-suite/bin:/usr/bin:/bin'
    command=['verilator','--binary','--timing','-Wno-fatal','--top-module','tb_endpoint_timing',
             '--Mdir',str(out/'obj'),*(str(staged/name) for name in (endpoint.name,reference.name,tb.name))]
    evidence={'status':'FAIL','endpoint_sha256':sha(endpoint),'frozen_sha256':sha(frozen),
              'reference_transform':'Only module identifier renamed to esp32_v102_reference',
              'testbench_sha256':sha(tb),'runner_sha256':sha(Path(__file__)),
              'staged_sources':{p.name:sha(p) for p in staged.iterdir()},'steps':[],
              'coverage':{'lane_widths':[1,2,4],'word_bits':[8,16,32],'swap':[False,True],
                          'burst':[False,True],'write_sck_mhz':40,'read_sck_mhz':16,
                          'matrix_cases':36,'read_words':72,'abort_cases':12},
              'unverified':['External pin timing/PVT','Physical FPGA operation','Full production framework ABI']}
    try:
        for name,cmd in [('compile',command),('simulation',[str(out/'obj/Vtb_endpoint_timing')])]:
            with (out/(name+'.log')).open('w') as log:
                result=subprocess.run(cmd,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT)
            evidence['steps'].append({'command':cmd,'returncode':result.returncode})
            if result.returncode:raise RuntimeError(name+' failed; inspect '+str(out))
        text=(out/'simulation.log').read_text()
        if 'MATRIX_PASS cases=36 writeSCK40MHz readSCK16MHz words=72 aborts=12' not in text:
            raise RuntimeError('Missing exact protocol coverage PASS marker')
        evidence['status']='PASS'
    finally:
        evidence['logs']={p.name:sha(p) for p in out.glob('*.log')}
        (out/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('ENDPOINT_TIMING_'+evidence['status']+' '+str(out/'evidence.json'))


if __name__=='__main__':main()
