# Project Status

## Repository

- GitHub: https://github.com/kevinten-ai/hunyuan3d-comprehensive
- Default branch: `master`
- Local orchestration layer: `scripts/`, `bambu_print/`, `config/`, `docs/`
- Upstream engines included in the checkout: `Hunyuan3D-1/`, `Hunyuan3D-2/`

## Capability Matrix

| Area | Status | Evidence | Remaining gate |
|---|---|---|---|
| Hunyuan3D-1 text-to-3D | Real root workflow passed | CUDA 13 / Torch 2.10, `sm_120`, nvdiffrast, xFormers, isolated 25-step text, 50-step multiview, and 90,000-face OBJ generation passed through `ai_to_print.py` | Texture/baking/render paths and broader visual-quality review remain |
| Hunyuan3D-2 image-to-3D | Low-step local validation passed | `scripts/hunyuan2_image.py` generated `outputs/validation/hunyuan2_image/validation.glb` | Full-quality generation still needs broader validation |
| ComfyUI workflow | Real low-step graph passed | All 13 workflow references are present; `scripts/comfyui_hunyuan_smoke.py --start-server` produced a watertight GLB with 2,356 vertices and 5,000 faces | Full-quality graphs need broader time, memory, and output-quality validation |
| Model conversion | Implemented and tested | `scripts/model_converter.py`, `scripts/glb_to_3mf.py`; GLB Scene info plus GLB-to-STL/3MF conversion and converter CLI failure paths verified | Real meshes still need print-quality review |
| Model collection | Implemented and tested | `scripts/model_collector.py`; isolated add/export test, CLI failure return-code tests, and `MODEL_COLLECTOR_MODELS_DIR` override | Real model library curation |
| Bambu printer queue | Foreground runtime and cross-process control implemented | `auto_print.py start` now remains alive until the queue drains; persisted runtime state lets separate CLI processes pause/resume/stop the owned task, and interrupted monitoring only adopts a matching active filename | Start/stop against the generated model after the occupied build plate is cleared |
| Bambu LAN protocol | Real status, upload, pause, and resume verified | Real MQTT/TLS `pushall` reported active progress, temperatures, errors, and HMS; implicit FTPS uploaded the generated 3MF; a user-started print was paused and restored to `printing` | Generated-model start/stop remains deferred while another print is active and HMS `0300310000010001` is present |
| Hunyuan command bridge | Docker/native backend selection implemented | `auto` prefers the verified 16 GB Docker path; `docker` and `native` remain explicit options, and generated output is mounted back to the root output directory | Optional native runtime remains environment-specific |
| Full AI-to-print | Generation through real printer upload verified | `ai_to_print.py --run-generator --no-print` completed real Hunyuan3D-1 generation and repair; the resulting STL produced a validated P1S project 3MF and that project was uploaded to the printer over FTPS | Physical start/control/completion after the platform and fan condition are cleared |
| Continuous generation and print | Shared real backend and transport wired | `scripts/continuous_print.py` calls the same auto-selected Hunyuan backend, preserves failed prompts for retry, validates printer config, and requires ready-to-print slicer output | Physical unattended-print validation after the current hardware gate |
| Claude crab batch prompts | Command builder verified | `scripts/generate_claude_crabs.py`; `--list` success and missing entrypoint failure return-code paths verified | Batch wrapper still targets the optional native entrypoint |
| Aggregate system preflight | Implemented and tested | `scripts/system_preflight.py` reports Hunyuan weights, ComfyUI assets, slicer settings, and printer config in text or JSON; strict mode returns nonzero for blockers | It may start a disposable CUDA rasterization probe, but does not run model inference, slicing, or printer commands |

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

1. Clear the occupied build plate and resolve HMS `0300310000010001` (part-cooling fan speed/stall) before starting the uploaded validation model.
2. Validate generated-model MQTT start/stop and inspect the physical Hunyuan3D-1 output.
3. Decide whether pre-existing untracked files should be committed, ignored, or left as local-only user assets.

## Hardware and Runtime Probe

Current local probe results:

- GPU: NVIDIA GeForce RTX 5060 Ti, driver 591.86, 16 GB VRAM.
- System Python: PyTorch `2.12.0.dev20260405+cu130`; CUDA is available and sees the RTX 5060 Ti.
- Hunyuan3D-1 venv: `pip check` and `main.py --help` pass. The complete 20-file, 13.5 GiB `weights/hunyuanDiT` snapshot is present in the ignored local weights directory. PyTorch `2.14.0.dev20260808+cu130` detects compute capability 12.0, includes `sm_120`, and passed a real CUDA kernel check.
- Hunyuan3D-1 Docker image uses CUDA 13.0.2 runtime, Torch `2.10.0+cu130`, pinned nvdiffrast 0.4.0, xFormers 0.0.35, libigl 2.5.1, and fast-simplification 0.1.13. A real CUDA rasterization covered 72 pixels on compute capability 12.0. The isolated low-VRAM stages generated `Hunyuan3D-1/outputs/docker-smoke/mesh_vertex_colors.obj`, simplifying 50,934 faces to 1,048 (the requested target was 1,000; disconnected/non-manifold low-step geometry prevented an exact target).
- Local environment overrides are documented in `config/env.example`; root orchestration scripts auto-load repository-root `.env` files without overriding shell variables. `HUNYUAN3D1_BACKEND=auto` prefers Docker, `HUNYUAN3D1_PYTHON` applies to explicit native mode, and `HUNYUAN3D2_MODEL_PATH` controls the default Hunyuan3D-2 model path.
- Hunyuan3D-1 with system Python: entry import fails because installed `diffusers` expects `Qwen3ForCausalLM`, which the installed `transformers` does not provide.
- Hunyuan3D-2 local weights: safetensors files exist under `Hunyuan3D-2/tencent/Hunyuan3D-2`. After downloading `hunyuan3d-dit-v2-0/config.yaml`, low-step image-to-3D validation completed and wrote `outputs/validation/hunyuan2_image/validation.glb`.
- ComfyUI: all 13 unique required and optional/downloadable workflow references are present. `scripts/prepare_comfyui_workflow_assets.py` reuses the official local Hunyuan3D-2 checkpoint, prepares bundled example images, and can cache the fast multiview, upscaler, Paint, and Delight assets. Quick-test loads CUDA and `ComfyUI-Hunyuan3DWrapper`; `scripts/comfyui_hunyuan_smoke.py --start-server` also completed a real 5-step API graph and produced a watertight GLB with 2,356 vertices and 5,000 faces.
- Slicer: `scripts/bambu_slicer_bridge.py` structurally merges a known-good project settings profile into source geometry, auto-scales/orients/arranges it, invokes Bambu Studio CLI, and rejects output without Bambu slice metadata. In addition to the demo slice, the real Hunyuan3D-1 90,000-face output was repaired to STL and sliced into a validated P1S project; the estimate was about 34.3 minutes and 7.95 g filament.
- Printer: an ignored local `config/printer.json` now passes validation with LAN Developer Mode enabled. Authenticated MQTT/TLS used `device/{serial}/report` and `device/{serial}/request`; `pushall` returned a real active-print snapshot, authenticated implicit FTPS uploaded the generated project as `codex_gear_validation.3mf`, and pause/resume returned the user-started job to `printing`. The latest snapshot reports `print_error=0` plus HMS `0300310000010001` (part-cooling-fan speed/stall). HMS `0500050000010007` appeared transiently after a redundant command retry and cleared from a later snapshot. No generated-model start or stop command was sent because another print occupies the plate.
- Slicer output policy: `BAMBU_SLICER_OUTPUT_EXT` must be `.3mf`, `.gcode`, or `.bgcode`; any other output extension is rejected before the slicer runs.
- Aggregate preflight falls back to a disposable Docker CUDA/nvdiffrast/xFormers probe when the native Hunyuan3D-1 venv is incomplete. The current local report is 5/5 ready with no known configuration blockers.

## Local Verification Completed

These checks passed in the current checkout, except where a command is explicitly marked as an expected local gate:

```powershell
python -m compileall scripts bambu_print
python -m unittest discover -s tests -v
python scripts/system_preflight.py --allow-incomplete
Hunyuan3D-1\venv\Scripts\python.exe -m pip check
Hunyuan3D-1\venv\Scripts\python.exe Hunyuan3D-1\main.py --help
python scripts/hunyuan_quick.py text "a small robot" --dry-run --lite
python scripts/ai_to_print.py text "a rabbit" --no-print --mock
python scripts/ai_to_print.py text "a rabbit" --mock
python scripts/continuous_print.py generate --prompt "a rabbit" --no-print --mock
python scripts/continuous_print.py generate --prompt "a rabbit" --mock
python scripts/continuous_print.py generate --prompt "a rabbit" --no-print
python scripts/continuous_print.py prompts --file prompts.txt --delay 0 --mock --no-print
python scripts/continuous_print.py prompts --file missing-prompts.txt --delay 0
python scripts/generate_claude_crabs.py --list
python scripts/model_converter.py info outputs/demo/demo.stl
python scripts/model_converter.py info outputs/validation/hunyuan2_image/validation.glb
python scripts/model_converter.py convert outputs/validation/hunyuan2_image/validation.glb stl validation_hunyuan2
python scripts/model_converter.py convert outputs/validation/hunyuan2_image/validation.glb 3mf validation_hunyuan2
python scripts/glb_to_3mf.py outputs/validation/hunyuan2_image/validation.glb models/converted/validation_hunyuan2.3mf
python scripts/model_converter.py info models/converted/validation_hunyuan2.3mf
python scripts/prepare_comfyui_workflow_assets.py --offline --include-optional
python scripts/check_comfyui_workflow_assets.py
python scripts/comfyui_hunyuan_smoke.py --start-server --timeout 600
python scripts/bambu_slicer_bridge.py outputs/demo/demo.stl outputs/validation/bambu_cli/bridge_demo.gcode.3mf --slicer-exe PATH_TO_BAMBU_STUDIO --template PATH_TO_KNOWN_GOOD_PROJECT
# Requires an ignored local config/printer.json; this machine passes and reads live status:
python scripts/auto_print.py check-config
python scripts/auto_print.py status
# Expected printer discovery gate when no printer is found:
python scripts/ai_to_print.py discover --timeout 0.1
python ComfyUI/main.py --quick-test-for-ci --disable-auto-launch --dont-print-server
```
