# Release Readiness

## Current Capability

- The repository now has a documented orchestration layer for Hunyuan3D-1, Hunyuan3D-2, ComfyUI, model conversion, model collection, and Bambu Lab queue management.
- Root generation entry points are truthful:
  - `--dry-run` prints commands without loading models.
  - `--mock` creates a tiny local STL for workflow tests and demos.
  - `--run-generator` is required before scripts call real Hunyuan3D generation.
  - root Hunyuan command failures return nonzero with ordinary error output.
- Bambu queue `add` persists jobs without auto-connecting or starting the printer; upload failures mark jobs failed without sending a print-start command; current-job cancel/pause/resume state changes only proceed after the matching printer command succeeds.
- Bambu client tests cover default status fields, MQTT report parsing, queue status serialization, HTTP upload success/failure return values, and local `project_file` command payload construction.
- `model_converter.py` returns nonzero for local CLI input failures and reports missing files without tracebacks.
- `auto_print.py` returns nonzero for local add/remove/cancel failure paths instead of reporting a false-success CLI exit.
- `ai_to_print.py` returns nonzero when generation does not produce a model, while `--mock --no-print` remains a local success path.
- `continuous_print.py generate` returns nonzero for missing inputs or no-model generation and returns success for the local `--mock --no-print` path.
- `generate_claude_crabs.py` returns success for `--list` and nonzero for missing Hunyuan3D-1 entrypoint or failed batch generation.
- `auto_print.py config` rejects host/access-code/serial template printer values before writing local config.
- AI-to-print and continuous-print entry points reuse the printer config preflight, so template `printer.json` values do not trigger queue creation.
- `model_collector.py` supports isolated model-library roots through `MODEL_COLLECTOR_MODELS_DIR` and returns nonzero for local CLI input failures.
- `config/env.example` documents optional local environment overrides, and `.env` files are ignored.
- Repository hygiene tests cover local-only runtime/model artifacts, tracked templates, and a 100 MB tracked-file threshold.
- Requirements tests cover the root print/conversion dependency list.
- Local tests cover root command construction, mock generation, continuous generation safety, model converter output, model collection CLI gates, Bambu exports, and queue persistence.

## Verified Locally

```powershell
python -m compileall scripts bambu_print
python -m unittest discover -s tests -v
Hunyuan3D-1\venv\Scripts\python.exe -m pip check
Hunyuan3D-1\venv\Scripts\python.exe Hunyuan3D-1\main.py --help
python scripts/hunyuan_quick.py text "a small robot" --dry-run --lite
python scripts/hunyuan_quick.py image Hunyuan3D-2/assets/demo.png --dry-run --quality lite
python scripts/ai_to_print.py text "a rabbit" --no-print --mock
python scripts/continuous_print.py generate --prompt "a rabbit" --no-print --mock
python scripts/model_converter.py info outputs/demo/demo.stl
python scripts/model_converter.py info outputs/validation/hunyuan2_image/validation.glb
python scripts/model_converter.py convert outputs/validation/hunyuan2_image/validation.glb stl validation_hunyuan2
python scripts/model_converter.py convert outputs/validation/hunyuan2_image/validation.glb 3mf validation_hunyuan2
python scripts/glb_to_3mf.py outputs/validation/hunyuan2_image/validation.glb models/converted/validation_hunyuan2.3mf
python scripts/model_converter.py info models/converted/validation_hunyuan2.3mf
# Expected printer config gate until config/printer.json exists:
python scripts/auto_print.py check-config
python scripts/auto_print.py status
python scripts/generate_claude_crabs.py --list
python scripts/check_comfyui_workflow_assets.py --allow-missing
python ComfyUI/main.py --quick-test-for-ci --disable-auto-launch --dont-print-server
```

## Not Yet Release-Complete

These items still require environment or hardware changes before the full end-to-end system can be called complete:

- Hunyuan3D-1 environment:
  - `Hunyuan3D-1/venv` now passes `pip check` and `main.py --help`;
  - root Hunyuan3D-1 wrappers prefer the project venv or `HUNYUAN3D1_PYTHON`;
  - `weights/hunyuanDiT` is missing locally, so text-to-3D generation has not completed;
  - `Hunyuan3D-1/venv` Torch still needs RTX 5060 Ti sm_120-compatible validation;
  - optional baking/render paths still require real PyTorch3D/DUSt3R/libigl support.
- Hunyuan3D-2 direct pipeline:
  - low-step local validation passed after downloading `hunyuan3d-dit-v2-0/config.yaml`;
  - `HUNYUAN3D2_MODEL_PATH` can override the default model path for the root wrapper;
  - full-quality generation settings still need broader runtime and output-quality validation.
- ComfyUI:
  - quick test exits 0, detects CUDA, and loads `ComfyUI-Hunyuan3DWrapper`;
  - `nodes_math.py` and `nodes_glsl.py` import after installing `simpleeval`, `blake3`, `PyOpenGL`, and `glfw`;
  - browser launch at `http://127.0.0.1:8190` rendered the ComfyUI UI;
  - `scripts/check_comfyui_workflow_assets.py` reports 7 unique required missing assets and 2 unique optional/downloadable missing assets for the local example workflows.
- Bambu Lab printer:
  - `config/printer.json` is absent;
  - local config preflight is available through `python scripts/auto_print.py config/check-config`;
  - `scripts/ai_to_print.py` and `scripts/continuous_print.py` reuse the local preflight before queue creation;
  - local protocol tests cover status parsing and `project_file` payload construction;
  - MQTT upload/start/pause/resume/stop have not been validated against a real printer.

## Suggested Next Steps

1. Add `Hunyuan3D-1/weights/hunyuanDiT`, then install/update the Hunyuan3D-1 Torch stack for RTX 50-series support and run a real low-step text-to-3D validation.
2. Keep a complete Hunyuan3D-2 local model snapshot, including `config.yaml`, then validate full-quality generation settings.
3. Align ComfyUI example workflow assets and model paths, then run a Hunyuan3D workflow graph end to end.
4. Create local `config/printer.json` from `config/printer.json.example`, then validate Bambu queue commands on the real printer.
