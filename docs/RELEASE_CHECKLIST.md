<!-- SPDX-License-Identifier: 0BSD -->

# First tagged release checklist

The source repository is already public. This checklist is for the first
**tagged experimental release**, not a claim that release artifacts are ready.
Do not label the demo production-ready or fully timing-qualified.

## Source package

- [x] One main tester example, build instructions and control descriptions.
- [x] Mixed-license boundaries, imported references and notices preserved.
- [x] Full Rev4 pinout, CSV and checks for documentation drift.
- [x] Document active, inactive and unmapped interfaces without claiming all are implemented.
- [x] Record hardware observations separately from simulation and timing limits.
- [ ] Confirm CI is green for the exact release-candidate commit.
- [ ] Reproduce bootstrap, generation, simulations and implementation in a fresh
  Ubuntu 22.04/WSL environment; the recorded environment is not a clean-machine test.

## Binary release package

- [ ] Select the release-candidate commit and build its bitstream/ELF pair.
- [ ] Include a manifest of commit, tool versions, source bindings, firmware,
  constraints, reports and SHA-256 hashes. Do not relabel an older tested image
  as a build of the new commit just because its firmware payload matches.
- [ ] Preserve all notices required by included LiteX/Migen/LiteDRAM/VexRiscv
  and GameBub-derived generated material; the source license summary alone is
  not a blanket binary redistribution license.
- [ ] Keep actual build, simulation and available internal timing evidence with
  the package. Record external I/O setup/hold, CDC and -1/PVT as not signed off.
- [ ] Provide exact volatile-programming and recovery steps; never select a JTAG
  adapter by list position or silently update persistent storage/ESP32 firmware.

## Physical acceptance of that image

- [ ] Verify the exact packaged bitstream hash, target device, DONE and CRC.
- [ ] Confirm clean bars, tester UI, both shoulders, A-start and B-stop.
- [ ] Run both reserved 4 KiB memory tests; do not claim full-capacity qualification.
- [ ] Confirm physical sound and motor movement, including timeout/stop behavior.
  Digital simulations passed, but these observations are still outstanding.
- [ ] Retest the installed ESP32 volume overlay on the release image and record
  observed menu behavior. Do not launch a game while expecting the volatile image
  to remain loaded; ESP32 can replace it.

The existing [status report](STATUS.md) is the baseline, not a substitute for
these release-candidate-specific checks. No tag, GitHub Release or hardware
deployment is created automatically by this checklist.
