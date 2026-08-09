# Hunyuan3D Print Orchestration Handoff

This handoff summarizes the current delivery state for the local Hunyuan3D + ComfyUI + Bambu Lab orchestration project. It is intentionally explicit about what is proven locally and what still requires model weights, GPU runtime validation, or a real printer.

## Current Capability

- The root repository contains orchestration scripts for Hunyuan3D-1 text-to-3D, Hunyuan3D-2 image-to-3D, model conversion, model collection, ComfyUI workflow checks, and Bambu Lab queue management.
- Root generation scripts avoid false success: dry runs only print commands, mock mode creates tiny local STL files for demos, and real generation requires explicit `--run-generator`.
- Local CLI failure paths return nonzero for Hunyuan quick generation, AI-to-print no-model flows, continuous print no-model flows, model conversion input errors, model collection input errors, Claude crab generation gates, and Bambu queue failures.
- Printer configuration has a local preflight gate. Template values in `config/printer.json.example` are rejected before queue creation or network attempts.
- `scripts/system_preflight.py` provides a read-only aggregate gate for Hunyuan weights, ComfyUI workflow assets, slicer configuration, and printer configuration. Real Hunyuan3D-2, ComfyUI, and Bambu CLI smoke runs are recorded separately below.
- Current release evidence is maintained in `docs/VERIFICATION.md` and `docs/RELEASE_READINESS.md`.

## Install And Run

From the repository root:

```powershell
python -m pip install -r requirements-print.txt
copy config\env.example .env
copy config\printer.json.example config\printer.json
python scripts/system_preflight.py --allow-incomplete
```

Use `python scripts/system_preflight.py` without `--allow-incomplete` as a strict local release gate, or add `--json --allow-incomplete` for machine-readable status reporting.

`requirements-print.txt` covers the root printer, queue, conversion, and repair helpers (`paho-mqtt`, `numpy`, `trimesh`, and `numpy-stl`). FTPS upload uses the system `curl` executable so the access code can be supplied through standard input instead of process arguments. Hunyuan3D-1 and Hunyuan3D-2 keep their upstream dependency instructions in their own folders.

Edit `.env` only for local overrides such as `HUNYUAN3D1_PYTHON`, `HUNYUAN3D2_MODEL_PATH`, `MODEL_COLLECTOR_MODELS_DIR`, and `BAMBU_PRINTER_CA_CERT`. Root orchestration scripts auto-load `.env` from the repository root without overriding variables already set in the shell. When the CA path is omitted, the printer client also checks `resources/cert/printer.cer` next to `BAMBU_SLICER_EXE`. The tracked template is `config/env.example`. Do not commit `.env`.

Set `BAMBU_SLICER_EXE` and `BAMBU_SLICER_TEMPLATE` to Bambu Studio and a known-good project profile, then use `python scripts/bambu_slicer_bridge.py "{input}" "{output}"` as `BAMBU_SLICER_COMMAND`. The bridge auto-scales, orients, arranges, slices, and validates its project `.3mf`. AI-to-print and continuous-print only continue queueing after that ready-file validation passes.

`BAMBU_SLICER_OUTPUT_EXT` controls the expected output extension and must remain `.3mf`, `.gcode`, or `.bgcode`; unsupported values are rejected before slicer execution.

Edit `config/printer.json` with real Bambu Lab values before printer validation. Replace `YOUR_PRINTER_IP`, `YOUR_ACCESS_CODE`, and `YOUR_PRINTER_SERIAL`, then set `lan_developer_mode` only after enabling LAN Only or Developer Mode on the printer. Optional `use_ams`, `ams_mapping`, and `timelapse` fields control the print command. Do not commit `config/printer.json`; keep `config/printer.json.example` as the tracked template.

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
python scripts/auto_print.py config --host YOUR_PRINTER_IP --serial YOUR_PRINTER_SERIAL --developer-mode
python scripts/auto_print.py check-config
```

The config command prompts for the Access Code without echoing it, keeping the secret out of shell history and process arguments. The LAN client uploads over implicit FTPS on TCP 990, then uses MQTT/TLS on TCP 8883 with `device/{serial}/report` and `device/{serial}/request` for status, commands, and matched device acknowledgements. Bambu Lab documents Developer Mode MQTT/FTP as unsupported interfaces, so firmware updates require renewed real-device validation. Add `--use-ams --ams-slot 0` when a specific AMS slot is required.

Queueing a model does not automatically start printing:

```powershell
python scripts/auto_print.py add path\to\plate.gcode --name "test print"
python scripts/auto_print.py start
python scripts/auto_print.py status
python scripts/auto_print.py watch
```

The raw queue accepts only ready-to-print files such as `.gcode`, `.bgcode`, or Bambu/OrcaSlicer project `.3mf` files with slice metadata. Source geometry such as STL/OBJ/GLB and generic geometry 3MF files must be converted for a slicer and then sliced/exported before queueing; the AI-to-print and continuous-print entry points reject source geometry before direct queueing.

For automated source-model-to-print handoff, configure the bundled bridge from `config/env.example`. Its template provides printer/process/filament settings while the input provides the model geometry. A real local smoke run created a validated P1S project with embedded plate G-code.

AI-to-print and continuous-print entry points reuse the same printer preflight before automatic queue creation.

## Verification

Use the release gate before publishing or changing PR state:

```powershell
git status --short
python -m compileall scripts bambu_print
python -m unittest discover -s tests -v
python scripts/system_preflight.py --allow-incomplete
```

See `docs/VERIFICATION.md` for the detailed command list and expected nonzero local gates. See `docs/RELEASE_READINESS.md` for the current capability and external gate summary.

## Remaining Risks

- Hunyuan3D-1 weights are complete and the Torch CUDA `sm_120` path is verified, but real text-to-3D still stops at the missing native `nvdiffrast` dependency. Windows needs CUDA Toolkit and MSVC before compiling it from source.
- Hunyuan3D-2 has passed a low-step local validation, but full-quality settings still need broader runtime and output-quality validation.
- ComfyUI quick test, all 13 workflow asset references, and a real low-step API graph have passed; full-quality graphs remain a performance and visual-quality follow-up.
- Bambu Studio is visibly connected to a real P1S with AMS, but the repository discovery command found no printer. The repository's FTPS/MQTT protocol construction and failure paths are unit-tested, while direct upload/start/pause/resume/stop still require a valid local `config/printer.json`, enabled LAN Only or Developer Mode, local network access, and real-device validation.
- Generated outputs, local model workspace files, continuous-print state files, queue state, model weights, virtual environments, `.env`, and `config/printer.json` should remain untracked.
- Repository hygiene tests verify that common large model artifacts such as `.safetensors`, `.ckpt`, `.bin`, `.onnx`, generated GLB/3MF outputs, local ComfyUI assets, printer config, and `.env` remain ignored while tracked templates stay visible.
