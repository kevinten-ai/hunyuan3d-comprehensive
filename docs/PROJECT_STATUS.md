# Project Status

## Repository

- GitHub: https://github.com/kevinten-ai/hunyuan3d-comprehensive
- Default branch: `master`
- Local orchestration layer: `scripts/`, `bambu_print/`, `config/`, `docs/`
- Upstream engines included in the checkout: `Hunyuan3D-1/`, `Hunyuan3D-2/`

## Capability Matrix

| Area | Status | Evidence | Remaining gate |
|---|---|---|---|
| Hunyuan3D-1 text-to-3D | CLI/dependency smoke test passed | `Hunyuan3D-1/venv/Scripts/python.exe Hunyuan3D-1/main.py --help`; wrappers prefer the Hunyuan3D-1 venv | Missing `weights/hunyuanDiT`; real generation still needs compatible Torch/RTX 50 validation |
| Hunyuan3D-2 image-to-3D | Low-step local validation passed | `scripts/hunyuan2_image.py` generated `outputs/validation/hunyuan2_image/validation.glb` | Full-quality generation still needs broader validation |
| ComfyUI workflow | Quick-test and browser launch passed | Quick test loads `ComfyUI-Hunyuan3DWrapper`; browser at `http://127.0.0.1:8190` rendered the ComfyUI UI; asset checker reports missing workflow assets | Example workflows exist, but referenced model/input assets are missing or path-mismatched |
| Model conversion | Implemented and tested | `scripts/model_converter.py`, `scripts/glb_to_3mf.py`; GLB Scene info plus GLB-to-STL/3MF conversion and converter CLI failure paths verified | Real meshes still need print-quality review |
| Model collection | Implemented and tested | `scripts/model_collector.py`; isolated add/export test, CLI failure return-code tests, and `MODEL_COLLECTOR_MODELS_DIR` override | Real model library curation |
| Bambu printer queue | Implemented queue layer | `bambu_print/print_queue.py`; tests verify default manual start, status serialization, ready-to-print file enforcement including generic 3MF rejection, upload-failure and start-command-failure job handling, current-job cancel/pause/resume/stop failure handling, clear-on-stop-failure handling, and CLI failure return codes; `scripts/auto_print.py config/check-config` validates local config fields and rejects tracked template placeholders without connecting | Real printer validation |
| Bambu MQTT commands | Partially implemented | `bambu_print/printer_client.py`; local tests verify MQTT connection callback success/failure/timeout handling, status parsing, HTTP upload success/failure return values, empty-file start rejection, and `project_file` command payload construction | Protocol validation against a real Bambu printer |
| Hunyuan command bridge | Implemented wrapper | `scripts/hunyuan_quick.py`, `scripts/hunyuan2_image.py`; dry-run and local failure return-code paths verified | Real generation requires weights/hardware |
| Full AI-to-print | Explicit modes | `scripts/ai_to_print.py` uses `--mock` for demo and `--run-generator` for real commands; local success, no-model failure, print-request-without-printer-config failure, and no-printer discovery return-code paths verified; printer config preflight rejects template config; source models are rejected before direct queueing unless a verified external `BAMBU_SLICER_COMMAND` produces validated ready output; invalid `BAMBU_SLICER_OUTPUT_EXT` output extension values are rejected before slicer execution | Real generator, slicer output, and printer validation |
| Continuous generation and print | Explicit modes | `scripts/continuous_print.py` uses `--mock` for demo and `--run-generator` for real commands; local generate success, no-model failure, print-request-without-printer-config failure, and prompts-mode file/generation/queue failure return-code paths verified; failed prompt-list items are not marked processed; printer config preflight rejects template config; source models are rejected before direct queueing unless a verified external `BAMBU_SLICER_COMMAND` produces validated ready output; invalid `BAMBU_SLICER_OUTPUT_EXT` output extension values are rejected before slicer execution | Real generator, slicer output, and printer validation |
| Claude crab batch prompts | Command builder verified | `scripts/generate_claude_crabs.py`; `--list` success and missing Hunyuan3D-1 entrypoint failure return-code paths verified | Real Hunyuan3D-1 generation requires weights/hardware |

## Important Boundaries

The root project is an orchestration layer. It does not include model weights and should not commit local virtual environments, printer secrets, generated queues, or large generated models.

Some local directories are useful runtime assets but should stay out of Git:

- `ComfyUI/`
- `Hunyuan3D-1/venv/`
- `outputs/text_*/`, `outputs/img_*/`, `outputs/continuous/`
- `models/raw/`
- `models/collection/`
- `models/converted/`
- `.continuous_*.json`
- `.env`
- `config/printer.json`

Repository hygiene tests verify these local-only paths plus common large model formats (`*.safetensors`, `*.ckpt`, `*.bin`, `*.onnx`, `*.engine`) stay ignored while tracked templates remain visible.

## Current Priority

1. Validate real Hunyuan3D generation on a machine with model weights and compatible GPU.
2. Validate MQTT upload/start/pause/resume/stop against a real Bambu printer.
3. Decide whether pre-existing untracked files should be committed, ignored, or left as local-only user assets.

## Hardware and Runtime Probe

Current local probe results:

- GPU: NVIDIA GeForce RTX 5060 Ti, driver 591.86, 16 GB VRAM.
- System Python: PyTorch `2.12.0.dev20260405+cu130`; CUDA is available and sees the RTX 5060 Ti.
- Hunyuan3D-1 venv: dependency smoke test now passes (`pip check`; `main.py --help`). The venv uses PyTorch `2.5.1+cu121`; CUDA sees the GPU but warns that sm_120 is unsupported. `weights/hunyuanDiT` is missing, so text-to-3D generation has not completed.
- Local environment overrides are documented in `config/env.example`; root orchestration scripts auto-load repository-root `.env` files without overriding shell variables. `HUNYUAN3D1_PYTHON` controls the Hunyuan3D-1 Python executable and `HUNYUAN3D2_MODEL_PATH` controls the default Hunyuan3D-2 model path.
- Hunyuan3D-1 with system Python: entry import fails because installed `diffusers` expects `Qwen3ForCausalLM`, which the installed `transformers` does not provide.
- Hunyuan3D-2 local weights: safetensors files exist under `Hunyuan3D-2/tencent/Hunyuan3D-2`. After downloading `hunyuan3d-dit-v2-0/config.yaml`, low-step image-to-3D validation completed and wrote `outputs/validation/hunyuan2_image/validation.glb`.
- ComfyUI: after installing `simpleeval`, `blake3`, `PyOpenGL`, and `glfw`, `python ComfyUI/main.py --quick-test-for-ci --disable-auto-launch --dont-print-server` exits 0, detects CUDA, loads `ComfyUI-Hunyuan3DWrapper`, and no longer reports `nodes_math.py` or `nodes_glsl.py` import failures. A temporary server on `http://127.0.0.1:8190` rendered the ComfyUI browser UI with `Unsaved Workflow`, `Manager`, queue status, and zoom controls visible. Example workflows exist under `ComfyUI/custom_nodes/ComfyUI-Hunyuan3DWrapper/example_workflows/`; `scripts/check_comfyui_workflow_assets.py --allow-missing` currently reports 7 unique required missing assets and 2 unique optional/downloadable missing assets. It may still fall back to local mode if ComfyUI-Manager cannot reach comfyregistry.
- Printer: `config/printer.json` is absent, so Bambu printer validation has not run. The local preflight catches missing config, host/access-code/serial template placeholders, and unsupported queue connection methods before config writes, queue creation, or any network attempt. `scripts/auto_print.py` only accepts ready-to-print queue files (`.gcode`, `.bgcode`, or Bambu/OrcaSlicer project `.3mf` with slice metadata); `scripts/ai_to_print.py` and `scripts/continuous_print.py` reject generated source geometry before automatic queueing unless optional `BAMBU_SLICER_COMMAND` creates a validated ready file. Local unit tests cover default printer status, MQTT connection confirmation failure/timeout handling, MQTT status report parsing, queue status serialization, generic 3MF rejection, external slicer-command success/failure handling, `BAMBU_SLICER_OUTPUT_EXT` output extension rejection before slicer execution, upload-failure job handling without starting print, start-command-failure job handling without monitoring, current-job cancel/pause/resume/stop failure handling, clear-on-stop-failure handling, empty-file start rejection, HTTP upload success/failure return values, Bambu `project_file` command payload construction, AI-to-print no-printer discovery failures, and `auto_print.py` CLI failure return codes.

## Local Verification Completed

These checks passed in the current checkout, except where a command is explicitly marked as an expected local gate:

```powershell
python -m compileall scripts bambu_print
python -m unittest discover -s tests -v
Hunyuan3D-1\venv\Scripts\python.exe -m pip check
Hunyuan3D-1\venv\Scripts\python.exe Hunyuan3D-1\main.py --help
python scripts/hunyuan_quick.py text "a small robot" --dry-run --lite
python scripts/ai_to_print.py text "a rabbit" --no-print --mock
python scripts/ai_to_print.py text "a rabbit" --mock
python scripts/continuous_print.py generate --prompt "a rabbit" --no-print --mock
python scripts/continuous_print.py generate --prompt "a rabbit" --mock
python scripts/continuous_print.py generate --prompt "a rabbit" --no-print
python scripts/continuous_print.py prompts --file missing-prompts.txt --delay 0
python scripts/generate_claude_crabs.py --list
python scripts/model_converter.py info outputs/demo/demo.stl
python scripts/model_converter.py info outputs/validation/hunyuan2_image/validation.glb
python scripts/model_converter.py convert outputs/validation/hunyuan2_image/validation.glb stl validation_hunyuan2
python scripts/model_converter.py convert outputs/validation/hunyuan2_image/validation.glb 3mf validation_hunyuan2
python scripts/glb_to_3mf.py outputs/validation/hunyuan2_image/validation.glb models/converted/validation_hunyuan2.3mf
python scripts/model_converter.py info models/converted/validation_hunyuan2.3mf
python scripts/check_comfyui_workflow_assets.py --allow-missing
# Expected printer config gate until config/printer.json exists:
python scripts/auto_print.py check-config
python scripts/auto_print.py status
# Expected printer discovery gate when no printer is found:
python scripts/ai_to_print.py discover --timeout 0.1
python ComfyUI/main.py --quick-test-for-ci --disable-auto-launch --dont-print-server
```
