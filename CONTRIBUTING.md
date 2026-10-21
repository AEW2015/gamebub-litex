<!-- SPDX-License-Identifier: 0BSD -->

# Contributing

Follow the upstream [LiteX coding style](https://github.com/enjoy-digital/litex/blob/master/doc/coding_style.md).
Match nearby code and distinguish hardware-description modules from ordinary
Python command-line scripts. Do not apply a whole-tree formatter or rename
public registers/signals as incidental cleanup.

Use grouped imports, descriptive section separators and readable aligned tables
where useful. Hardware modules should keep CSRs, CDC, synchronous logic and
specials explicit. Explain timing, ownership and safety constraints in comments.
Retain file-specific licenses; do not label this project as part of upstream
LiteX or change third-party copyright notices.

The maintained example is `examples/tester/`. Put reusable peripherals in
`gamebub/`, verification in `tests/` and host operations in `tools/`.

Before submitting:

```bash
python -m unittest discover -s tests -v
python -m compileall -q gamebub examples tools tests
```

For gateware changes, run the relevant functional simulations and regenerate
the tester. Check its ROM, register map and generated RTL against the prior
version. A comment-only change does not authorize hardware programming or
justify claiming a fresh routed timing result. Use [BUILD.md](docs/BUILD.md)
for the longer tests and implementation flow.
