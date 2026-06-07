# Hunyuan3D Print Orchestration Handoff

This handoff summarizes the current delivery state for the local Hunyuan3D + ComfyUI + Bambu Lab orchestration project. It is intentionally explicit about what is proven locally and what still requires model weights, GPU runtime validation, or a real printer.

## Current Capability

- The root repository contains orchestration scripts for Hunyuan3D-1 text-to-3D, Hunyuan3D-2 image-to-3D, model conversion, model collection, ComfyUI workflow checks, and Bambu Lab queue management.
- Root generation scripts avoid false success: dry runs only print commands, mock mode creates tiny local STL files for demos, and real generation requires explicit `--run-generator`.
- Local CLI failure paths return nonzero for Hunyuan quick generation, AI-to-print no-model flows, continuous print no-model flows, model conversion input errors, model collection input errors, Claude crab generation gates, and Bambu queue failures.
- Printer configuration has a local preflight gate. Template values in `config/printer.json.example` are rejected before queue creation or network attempts.
- Current release evidence is maintained in `docs/VERIFICATION.md` and `docs/RELEASE_READINESS.md`.

## Install And Run

From the repository root:

```powershell
python -m pip install -r requirements-print.txt
copy config\env.example .env
copy config\printer.json.example config\printer.json
```

`requirements-print.txt` covers the root printer, queue, conversion, and repair helpers (`paho-mqtt`, `requests`, `numpy`, `trimesh`, and `numpy-stl`). Hunyuan3D-1 and Hunyuan3D-2 keep their upstream dependency instructions in their own folders.

Edit `.env` only for local overrides such as `HUNYUAN3D1_PYTHON`, `HUNYUAN3D2_MODEL_PATH`, and `MODEL_COLLECTOR_MODELS_DIR`. The tracked template is `config/env.example`. Do not commit `.env`.

`BAMBU_SLICER_COMMAND` is optional and should stay unset until a local slicer command has been verified. It supports `{input}`, `{output}`, and `{output_dir}` placeholders. `BAMBU_SLICER_OUTPUT_EXT` must be a ready-to-print output extension; unsafe values are rejected before slicer execution. AI-to-print and continuous-print only continue queueing if that command produces a validated Bambu/OrcaSlicer project `.3mf`, `.gcode`, or `.bgcode`.

Edit `config/printer.json` with real Bambu Lab values before printer validation. Replace `YOUR_PRINTER_IP`, `YOUR_ACCESS_CODE`, and `YOUR_PRINTER_SERIAL` before running queue commands. Do not commit `config/printer.json`; keep `config/printer.json.example` as the tracked template.

## Generate Models

Command construction can be checked without loading models:

```powershell
python scripts/hunyuan_quick.py text "a small robot" --dry-run --lite
python scripts/hunyuan_quick.py image Hunyuan3D-2/assets/demo.png --dry-run --quality lite
```

Demo workflows use mock mode:

```powershell
python scripts/ai_to_print.py text "a rabbit" --no-print --mock
python scripts/continuous_print.py generate --prompt "a rabbit" --no-print --mock
```

Real generation uses explicit backend execution:

```powershell
python scripts/hunyuan_quick.py text "a small robot" --lite
python scripts/hunyuan_quick.py image Hunyuan3D-2/assets/demo.png --quality lite
python scripts/ai_to_print.py text "a rabbit" --run-generator --no-print
```

## Print Workflow

Configure and validate the local printer config first:

```powershell
python scripts/auto_print.py config --host YOUR_PRINTER_IP --access-code YOUR_ACCESS_CODE --serial YOUR_PRINTER_SERIAL
python scripts/auto_print.py check-config
```

Queueing a model does not automatically start printing:

```powershell
python scripts/auto_print.py add path\to\plate.gcode --name "test print"
python scripts/auto_print.py start
python scripts/auto_print.py status
python scripts/auto_print.py watch
```

The raw queue accepts only ready-to-print files such as `.gcode`, `.bgcode`, or Bambu/OrcaSlicer project `.3mf` files with slice metadata. Source geometry such as STL/OBJ/GLB and generic geometry 3MF files must be converted for a slicer and then sliced/exported before queueing; the AI-to-print and continuous-print entry points reject source geometry before direct queueing.

For automated source-model-to-print handoff, configure `BAMBU_SLICER_COMMAND` after validating the slicer command outside this repo. Keep `BAMBU_SLICER_OUTPUT_EXT` on a validated output extension such as `.3mf`, `.gcode`, or `.bgcode`. Leave it unset for manual Bambu Studio / OrcaSlicer export.

AI-to-print and continuous-print entry points reuse the same printer preflight before automatic queue creation.

## Verification

Use the release gate before publishing or changing PR state:

```powershell
git status --short
python -m compileall scripts bambu_print
python -m unittest discover -s tests -v
```

See `docs/VERIFICATION.md` for the detailed command list and expected nonzero local gates. See `docs/RELEASE_READINESS.md` for the current capability and external gate summary.

## Remaining Risks

- Hunyuan3D-1 real text-to-3D is not complete locally because `weights/hunyuanDiT` is missing and the Torch stack still needs RTX 50-series sm_120 validation.
- Hunyuan3D-2 has passed a low-step local validation, but full-quality settings still need broader runtime and output-quality validation.
- ComfyUI quick test and browser launch have passed, but example workflow execution still needs model/input asset alignment.
- Bambu Lab MQTT connection confirmation failure/timeout paths are covered locally, but upload/start/pause/resume/stop still require a real printer, valid `config/printer.json`, local network access, and protocol validation.
- Generated outputs, queue state, model weights, virtual environments, `.env`, and `config/printer.json` should remain untracked.
- Repository hygiene tests verify that common large model artifacts such as `.safetensors`, `.ckpt`, `.bin`, `.onnx`, generated GLB/3MF outputs, local ComfyUI assets, printer config, and `.env` remain ignored while tracked templates stay visible.
