#!/usr/bin/env python3
"""Generate actual memory controllers and run independent SV pin models/BFMs."""
import argparse,hashlib,json,os,pathlib,subprocess,sys,time
from migen import *
from migen.fhdl import verilog
from litex.soc.interconnect import wishbone
from controllers import GameBubSRAM,GameBubSDRAM,sram_pads,sdram_pads

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
 if a.output.exists():p.error('output must be fresh')
 a.output.mkdir(parents=True);out=a.output.resolve();here=pathlib.Path(__file__).resolve().parent
 fixture=here/'reference/sram_test_pkg.sv'
 if not fixture.is_file():raise FileNotFoundError('Known-good v1.6 fixture required: '+str(fixture))
 top=Module();s=sram_pads();d=sdram_pads()
 top.submodules.sram=sr=GameBubSRAM(s);top.submodules.sdram=dr=GameBubSDRAM(d)
 wb=wishbone.Interface(data_width=32,address_width=32,addressing='word')
 for field,*_ in wb.layout:getattr(wb,field).name_override='wb_'+field
 top.comb += [wb.connect(sr.bus),wb.connect(dr.bus),sr.bus.cyc.eq(wb.cyc & ~wb.adr[28]),
              sr.bus.stb.eq(wb.stb & ~wb.adr[28]),dr.bus.cyc.eq(wb.cyc & wb.adr[28]),
              dr.bus.stb.eq(wb.stb & wb.adr[28]),
              wb.ack.eq(Mux(wb.adr[28],dr.bus.ack,sr.bus.ack)),
              wb.dat_r.eq(Mux(wb.adr[28],dr.bus.dat_r,sr.bus.dat_r)),wb.err.eq(0)]
 # Independent known-good LiteX SRAM models retain the entire apertures and
 # compare their byte-enable semantics against the two external pin memories.
 top.submodules.sram_reference=rs=wishbone.SRAM(512*1024)
 top.submodules.sdram_reference=rd=wishbone.SRAM(32*1024*1024)
 reference_data=Signal(32,name='reference_data')
 top.comb += [wb.connect(rs.bus),wb.connect(rd.bus),
              rs.bus.cyc.eq(wb.cyc & ~wb.adr[28]),rs.bus.stb.eq(wb.stb & ~wb.adr[28]),
              rd.bus.cyc.eq(wb.cyc & wb.adr[28]),rd.bus.stb.eq(wb.stb & wb.adr[28]),
              reference_data.eq(Mux(wb.adr[28],rd.bus.dat_r,rs.bus.dat_r)),
              wb.ack.eq(Mux(wb.adr[28],dr.bus.ack,sr.bus.ack)),
              wb.dat_r.eq(Mux(wb.adr[28],dr.bus.dat_r,sr.bus.dat_r)),wb.err.eq(0)]
 dr.initialized.name_override='memory_ready'
 ios=set(s.flatten()+d.flatten()+wb.flatten()+[dr.initialized,reference_data])
 rtl=verilog.convert(top,ios=ios,name='memory_test_top')
 (out/'memory_test_top.v').write_text(str(rtl))
 env=os.environ.copy();env['PATH']='/opt/gamebub-openxc7-20261021/oss-cad-suite/bin:/usr/bin:/bin'
 cmds=[['verilator','--binary','--timing','-Wno-fatal','--top-module','tb_memory','--Mdir',str(out/'obj'),
        str(out/'memory_test_top.v'),str(fixture),str(here/'pin_models.sv'),str(here/'tb_memory.sv')],
       [str(out/'obj/Vtb_memory')],
       [str(out/'obj/Vtb_memory'),'+corrupt_sram'],
       [str(out/'obj/Vtb_memory'),'+corrupt_sdram']]
 result={'schema':1,'status':'FAIL','claims':'Exact generated LiteX/LiteDRAM RTL to independent SRAM/SDRAM pin models; no hardware', 'steps':[]}
 try:
  for i,cmd in enumerate(cmds):
   with (out/f'{i}.log').open('w') as log:
    r=subprocess.run(cmd,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT)
   expected_failure = i >= 2
   logtext=(out/f'{i}.log').read_text()
   expected_message='Read mismatch addr'+('00000000' if i==2 else '40000000')
   passed=(r.returncode!=0 and expected_message in logtext) if expected_failure else r.returncode==0
   result['steps'].append({'command':cmd,'returncode':r.returncode,'expected_pin_fault':expected_failure,'status':'PASS' if passed else 'FAIL'})
   if not passed:raise RuntimeError(f'command failed: see{out}/{i}.log')
  result['status']='PASS'
 finally:
  result['sources']={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [here/'controllers.py',here/'pin_models.sv',here/'tb_memory.sv',fixture,out/'memory_test_top.v']}
  (out/'evidence.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result))
if __name__=='__main__':main()
