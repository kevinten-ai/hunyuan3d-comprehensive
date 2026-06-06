# Verification

## Local Checks

Run these from the repository root:

```powershell
python -m compileall scripts bambu_print
python -m unittest discover -s tests -v
python scripts/hunyuan_quick.py text "a small robot" --dry-run
python scripts/hunyuan_quick.py image Hunyuan3D-2/assets/demo.png --dry-run --quality lite
python scripts/ai_to_print.py text "a rabbit" --no-print --mock
python scripts/continuous_print.py generate --prompt "a rabbit" --no-print --mock
python scripts/continuous_print.py generate --prompt "a rabbit" --no-print
python scripts/generate_claude_crabs.py --list
python scripts/model_converter.py info outputs/demo/demo.stl
python scripts/auto_print.py status
python ComfyUI/main.py --quick-test-for-ci --disable-auto-launch --dont-print-server
```

The `auto_print.py status` command requires `config/printer.json`. Without that local secret file, the expected result is a clear message asking the user to configure the printer.

## External Checks

These checks require hardware, model weights, or local services that cannot be proven by static tests alone:

- Hunyuan3D-1 real text-to-3D generation requires model weights and a compatible Python/CUDA environment.
- Hunyuan3D-2 real image-to-3D generation requires model weights and a compatible Python/CUDA environment.
- ComfyUI validation requires launching the local ComfyUI checkout and loading a Hunyuan3D workflow.
- Bambu Lab validation requires printer IP, access code, serial number, and local network control enabled.

## Current External Gate Findings

- RTX 5060 Ti is present and system Python has CUDA-enabled PyTorch nightly.
- Hunyuan3D-1 is not yet runnable in the checked environments:
  - system Python fails on a `diffusers`/`transformers` import mismatch;
  - `Hunyuan3D-1/venv` lacks `einops` and uses a Torch build that warns sm_120 is unsupported.
- Hunyuan3D-2 local safetensors are present, but the local model directory is missing `config.yaml`.
- ComfyUI quick test exits successfully and detects CUDA, but reports missing optional dependencies for `nodes_glsl.py` and `nodes_math.py`.
- Printer validation is pending because `config/printer.json` is not present.

## Release Gate

Before publishing or opening a PR, verify:

```powershell
git status --short
python -m compileall scripts bambu_print
python -m unittest discover -s tests -v
```

Do not stage `config/printer.json`, virtual environments, model weights, generated queues, or large generated output files.
