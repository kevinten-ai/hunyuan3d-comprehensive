# Release Readiness

## Current Capability

- The repository now has a documented orchestration layer for Hunyuan3D-1, Hunyuan3D-2, ComfyUI, model conversion, model collection, and Bambu Lab queue management.
- Root generation entry points are truthful:
  - `--dry-run` prints commands without loading models.
  - `--mock` creates a tiny local STL for workflow tests and demos.
  - `--run-generator` is required before scripts call real Hunyuan3D generation.
  - root Hunyuan command failures return nonzero with ordinary error output.
- Bambu queue `add` persists jobs without auto-connecting or starting the printer; upload failures mark jobs failed without sending a print-start command; start-command failures mark jobs failed without entering monitor mode; current-job cancel/pause/resume/stop state changes only proceed after the matching printer command succeeds; `clear` does not discard queued work when stopping the active print fails.
- The Bambu queue only accepts ready-to-print files (`.gcode`, `.bgcode`, or Bambu/OrcaSlicer project `.3mf` with slice metadata); AI-to-print and continuous-print reject generated source geometry before queueing and instruct the user to convert plus slice first.
- AI-to-print and continuous-print can use the bundled Bambu Studio bridge through `BAMBU_SLICER_COMMAND`; the bridge requires an existing executable and known-good project template, then auto-scales/orients/arranges/slices and validates the generated project before queueing.
- `BAMBU_SLICER_OUTPUT_EXT` restricts the expected output extension to `.3mf`, `.gcode`, or `.bgcode`; unsupported values are rejected before slicer execution.
- Bambu client tests cover default and P1 status fields, MQTT connection callback success/failure/timeout handling, `device/{serial}` topics, full-status requests, queue status serialization, FTPS command construction without credentials in process arguments, empty-file start rejection, `project_file`/`gcode_file` payloads, matched device acknowledgements, command rejection, and pause/resume/stop envelopes.
- `model_converter.py` returns nonzero for local CLI input failures and reports missing files without tracebacks.
- `auto_print.py` returns nonzero for local add/remove/cancel/stop/clear failure paths instead of reporting a false-success CLI exit.
- `ai_to_print.py` returns nonzero when generation does not produce a model, when print is requested without valid printer config, and when `ai_to_print.py discover` finds no printer locally; `--mock --no-print` remains a local success path.
- `continuous_print.py generate` returns nonzero for missing inputs, no-model generation, or print requested without valid printer config; `continuous_print.py prompts` returns nonzero when the prompt file is missing or empty, when generation fails, or when a generated model cannot be queued, strips UTF-8 BOMs from prompt files, and the local `--mock --no-print` path remains successful.
- `generate_claude_crabs.py` returns success for `--list` and nonzero for missing Hunyuan3D-1 entrypoint or failed batch generation.
- `auto_print.py config` rejects host/access-code/serial template printer values before writing local config.
- AI-to-print and continuous-print entry points reuse the printer config preflight, so template `printer.json` values do not trigger queue creation.
- AI-to-print and continuous-print entry points do not treat generated STL/OBJ/GLB or generic geometry 3MF as printer-ready files.
- `model_collector.py` supports isolated model-library roots through `MODEL_COLLECTOR_MODELS_DIR` and returns nonzero for local CLI input failures.
- `config/env.example` documents optional local environment overrides; root orchestration scripts auto-load repository-root `.env` files without overriding shell variables, and `.env` files are ignored.
- Repository hygiene tests cover local-only runtime/model artifacts, tracked templates, and a 100 MB tracked-file threshold.
- Requirements tests cover the root print/conversion dependency list.
- Local tests cover root command construction, mock generation, continuous generation safety, model converter output, model collection CLI gates, Bambu exports, and queue persistence.
- `scripts/system_preflight.py` provides a read-only text/JSON aggregate gate and returns nonzero in strict mode while Hunyuan, ComfyUI, slicer, or printer prerequisites are blocked.

## Verified Locally

```powershell
python -m compileall scripts bambu_print
python -m unittest discover -s tests -v
python scripts/system_preflight.py --allow-incomplete
Hunyuan3D-1\venv\Scripts\python.exe -m pip check
Hunyuan3D-1\venv\Scripts\python.exe Hunyuan3D-1\main.py --help
python scripts/hunyuan_quick.py text "a small robot" --dry-run --lite
python scripts/hunyuan_quick.py image Hunyuan3D-2/assets/demo.png --dry-run --quality lite
python scripts/ai_to_print.py text "a rabbit" --no-print --mock
python scripts/ai_to_print.py text "a rabbit" --mock
python scripts/continuous_print.py generate --prompt "a rabbit" --no-print --mock
python scripts/continuous_print.py generate --prompt "a rabbit" --mock
python scripts/continuous_print.py prompts --file prompts.txt --delay 0 --mock --no-print
python scripts/continuous_print.py prompts --file missing-prompts.txt --delay 0
python scripts/model_converter.py info outputs/demo/demo.stl
python scripts/model_converter.py info outputs/validation/hunyuan2_image/validation.glb
python scripts/model_converter.py convert outputs/validation/hunyuan2_image/validation.glb stl validation_hunyuan2
python scripts/model_converter.py convert outputs/validation/hunyuan2_image/validation.glb 3mf validation_hunyuan2
python scripts/glb_to_3mf.py outputs/validation/hunyuan2_image/validation.glb models/converted/validation_hunyuan2.3mf
python scripts/model_converter.py info models/converted/validation_hunyuan2.3mf
# Expected printer config gate until config/printer.json exists:
python scripts/auto_print.py check-config
python scripts/auto_print.py status
# Expected printer discovery gate when no printer is found:
python scripts/ai_to_print.py discover --timeout 0.1
python scripts/generate_claude_crabs.py --list
python scripts/check_comfyui_workflow_assets.py
python ComfyUI/main.py --quick-test-for-ci --disable-auto-launch --dont-print-server
python scripts/comfyui_hunyuan_smoke.py --start-server --timeout 600
python scripts/bambu_slicer_bridge.py outputs/demo/demo.stl outputs/validation/bambu_cli/bridge_demo.gcode.3mf --slicer-exe PATH_TO_BAMBU_STUDIO --template PATH_TO_KNOWN_GOOD_PROJECT
```

## Not Yet Release-Complete

These items still require environment or hardware changes before the full end-to-end system can be called complete:

- Aggregate preflight currently reports 3 ready areas and 2 blocked areas. Hunyuan3D-2, ComfyUI, and the Bambu slicer bridge are ready; Hunyuan3D-1 `nvdiffrast` and local printer configuration remain blocked. Run without `--allow-incomplete` for the strict nonzero release gate.

- Hunyuan3D-1 environment:
  - `Hunyuan3D-1/venv` now passes `pip check` and `main.py --help`;
  - root Hunyuan3D-1 wrappers prefer the project venv or `HUNYUAN3D1_PYTHON`;
  - the ignored local `weights/hunyuanDiT` snapshot is complete at 20 files and 13.5 GiB;
  - the venv uses PyTorch `2.14.0.dev20260808+cu130`; a real CUDA kernel passed on compute capability 12.0 and the build includes `sm_120`;
  - a low-step generation attempt reached SVRM initialization but failed because the core `nvdiffrast` dependency is missing; Windows requires CUDA Toolkit and MSVC to compile it from source;
  - optional baking/render paths still require real PyTorch3D/DUSt3R/libigl support.
- Hunyuan3D-2 direct pipeline:
  - low-step local validation passed after downloading `hunyuan3d-dit-v2-0/config.yaml`;
  - `HUNYUAN3D2_MODEL_PATH` can override the default model path for the root wrapper;
  - full-quality generation settings still need broader runtime and output-quality validation.
- ComfyUI:
  - quick test exits 0, detects CUDA, and loads `ComfyUI-Hunyuan3DWrapper`;
  - `nodes_math.py` and `nodes_glsl.py` import after installing `simpleeval`, `blake3`, `PyOpenGL`, and `glfw`;
  - browser launch at `http://127.0.0.1:8190` rendered the ComfyUI UI;
  - all 13 unique workflow asset references are present;
  - a real 5-step API graph produced a watertight GLB with 2,356 vertices and 5,000 faces.
- Bambu Studio slicer:
  - the bundled bridge produced a validated P1S project `.3mf` from the demo STL;
  - the archive contains plate G-code and slice metadata, with a reported estimate of about 38.9 minutes and 5.11 g filament;
  - a known-good local project template remains required for printer, process, and filament settings.
- Bambu Lab printer:
  - local screenshots confirm Bambu Studio is connected to a real P1S with AMS and show a completed print, but this is not repository protocol validation;
  - `scripts/auto_print.py discover --timeout 3` found no printer even though the Studio process had an established port 8883 session;
  - `config/printer.json` is absent;
  - local config preflight is available through `python scripts/auto_print.py config/check-config` and validates Developer Mode confirmation, AMS mapping, timelapse, and timeout values;
  - `scripts/ai_to_print.py` and `scripts/continuous_print.py` reuse the local preflight before queue creation;
  - the repository client uses implicit FTPS on TCP 990 for upload and MQTT/TLS on TCP 8883 with `device/{serial}/report` and `device/{serial}/request` for status, commands, and acknowledgements;
  - Bambu Lab describes Developer Mode MQTT/FTP as unsupported interfaces, so compatibility can change with firmware;
  - FTPS upload and MQTT start/pause/resume/stop have not been validated against a real printer.

## Suggested Next Steps

1. Install CUDA Toolkit and Visual Studio Build Tools, compile `nvdiffrast` in the Hunyuan3D-1 venv, then rerun the real low-step text-to-3D validation.
2. Validate full-quality Hunyuan3D-2 and ComfyUI generation settings and visual quality.
3. Enable LAN Only or Developer Mode, create local `config/printer.json` from `config/printer.json.example`, then validate Bambu FTPS upload and MQTT control commands on the real printer.
