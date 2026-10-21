# Repository guidance

- Read `CONTRIBUTING.md` and the linked upstream LiteX coding style before edits.
- Maintain one main example: `examples/tester/`; do not reintroduce phase folders.
- Keep reusable gateware in `gamebub/`, tests in `tests/`, and host tools in `tools/`.
- Preserve upstream reference bytes, licenses, register ABI and signal names unless
  the task explicitly calls for a functional change and the change is verified.
- Do not run formatters blindly over Migen control expressions or imported RTL.
- Run syntax/unit checks and the smallest relevant simulation; report omissions.
- Hardware programming is opt-in; do not change ESP32 firmware or persistent flash.
- Open-source DEFAULT-model timing is not external-I/O/CDC/-1/PVT signoff.
