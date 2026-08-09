# Project Status

## Repository

- GitHub: https://github.com/kevinten-ai/hunyuan3d-comprehensive
- Default branch: `master`
- Local orchestration layer: `scripts/`, `bambu_print/`, `config/`, `docs/`
- Upstream engines included in the checkout: `Hunyuan3D-1/`, `Hunyuan3D-2/`

## Capability Matrix

| Area | Status | Evidence | Remaining gate |
|---|---|---|---|
| Hunyuan3D-1 text-to-3D | Weights and CUDA runtime verified | The local 13.5 GiB `weights/hunyuanDiT` snapshot is complete; Torch `2.14.0.dev20260808+cu130` executed a CUDA kernel with `sm_120` support | Install CUDA Toolkit and MSVC, compile `nvdiffrast`, then rerun real low-step generation |
| Hunyuan3D-2 image-to-3D | Low-step local validation passed | `scripts/hunyuan2_image.py` generated `outputs/validation/hunyuan2_image/validation.glb` | Full-quality generation still needs broader validation |
| ComfyUI workflow | Real low-step graph passed | All 13 workflow references are present; `scripts/comfyui_hunyuan_smoke.py --start-server` produced a watertight GLB with 2,356 vertices and 5,000 faces | Full-quality graphs need broader time, memory, and output-quality validation |
| Model conversion | Implemented and tested | `scripts/model_converter.py`, `scripts/glb_to_3mf.py`; GLB Scene info plus GLB-to-STL/3MF conversion and converter CLI failure paths verified | Real meshes still need print-quality review |
| Model collection | Implemented and tested | `scripts/model_collector.py`; isolated add/export test, CLI failure return-code tests, and `MODEL_COLLECTOR_MODELS_DIR` override | Real model library curation |
| Bambu printer queue | Implemented queue layer | `bambu_print/print_queue.py`; tests verify default manual start, status serialization, ready-to-print file enforcement including generic 3MF rejection, upload-failure and start-command-failure job handling, current-job cancel/pause/resume/stop failure handling, clear-on-stop-failure handling, and CLI failure return codes; `scripts/auto_print.py config/check-config` validates local config fields and rejects tracked template placeholders without connecting | Real printer validation |
| Bambu LAN protocol | Implemented, locally tested | `bambu_print/printer_client.py`; tests verify implicit FTPS command construction without exposing credentials in process arguments, `device/{serial}` MQTT topics, P1 status fields, `pushall`, `project_file`/`gcode_file` payloads, matched device acknowledgements, rejections, and control-command envelopes | FTPS upload and MQTT start/pause/resume/stop validation against a real Bambu printer |
| Hunyuan command bridge | Implemented wrapper | `scripts/hunyuan_quick.py`, `scripts/hunyuan2_image.py`; dry-run and local failure return-code paths verified | Real Hunyuan3D-1 generation requires the remaining native runtime dependency |
| Full AI-to-print | Explicit modes | `scripts/ai_to_print.py` uses `--mock` for demo and `--run-generator` for real commands; local success and failure paths are covered; source models require validated slicer output before queueing; the Bambu Studio CLI bridge has separately completed a real P1S slice | Real Hunyuan3D-1 generation and real-printer transport/control validation |
| Continuous generation and print | Explicit modes | `scripts/continuous_print.py` uses explicit mock/real modes, preserves failed prompts for retry, validates printer config, and requires ready-to-print slicer output; the Bambu Studio CLI bridge has separately completed a real P1S slice | Real generator and real-printer transport/control validation |
| Claude crab batch prompts | Command builder verified | `scripts/generate_claude_crabs.py`; `--list` success and missing Hunyuan3D-1 entrypoint failure return-code paths verified | Real Hunyuan3D-1 generation requires the remaining native runtime dependency |
| Aggregate system preflight | Implemented and tested | `scripts/system_preflight.py` reports Hunyuan weights, ComfyUI assets, slicer settings, and printer config in text or JSON; strict mode returns nonzero for blockers | It is a read-only prerequisite audit, not real inference/slicing/printing |

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

1. Install the Hunyuan3D-1 native build toolchain, compile `nvdiffrast`, and complete a real low-step text-to-3D run.
2. Enable LAN Only or Developer Mode and validate FTPS upload plus MQTT start/pause/resume/stop against a real Bambu printer.
3. Decide whether pre-existing untracked files should be committed, ignored, or left as local-only user assets.

## Hardware and Runtime Probe

Current local probe results:

- GPU: NVIDIA GeForce RTX 5060 Ti, driver 591.86, 16 GB VRAM.
- System Python: PyTorch `2.12.0.dev20260405+cu130`; CUDA is available and sees the RTX 5060 Ti.
- Hunyuan3D-1 venv: `pip check` and `main.py --help` pass. The complete 20-file, 13.5 GiB `weights/hunyuanDiT` snapshot is present in the ignored local weights directory. PyTorch `2.14.0.dev20260808+cu130` detects compute capability 12.0, includes `sm_120`, and passed a real CUDA kernel check.
- Hunyuan3D-1 low-step generation reached SVRM initialization, then stopped at `ModuleNotFoundError: nvdiffrast`. This core mesh reconstruction dependency must be compiled from source on Windows after installing CUDA Toolkit and MSVC; no generation output was produced.
- Local environment overrides are documented in `config/env.example`; root orchestration scripts auto-load repository-root `.env` files without overriding shell variables. `HUNYUAN3D1_PYTHON` controls the Hunyuan3D-1 Python executable and `HUNYUAN3D2_MODEL_PATH` controls the default Hunyuan3D-2 model path.
- Hunyuan3D-1 with system Python: entry import fails because installed `diffusers` expects `Qwen3ForCausalLM`, which the installed `transformers` does not provide.
- Hunyuan3D-2 local weights: safetensors files exist under `Hunyuan3D-2/tencent/Hunyuan3D-2`. After downloading `hunyuan3d-dit-v2-0/config.yaml`, low-step image-to-3D validation completed and wrote `outputs/validation/hunyuan2_image/validation.glb`.
- ComfyUI: all 13 unique required and optional/downloadable workflow references are present. `scripts/prepare_comfyui_workflow_assets.py` reuses the official local Hunyuan3D-2 checkpoint, prepares bundled example images, and can cache the fast multiview, upscaler, Paint, and Delight assets. Quick-test loads CUDA and `ComfyUI-Hunyuan3DWrapper`; `scripts/comfyui_hunyuan_smoke.py --start-server` also completed a real 5-step API graph and produced a watertight GLB with 2,356 vertices and 5,000 faces.
- Slicer: `scripts/bambu_slicer_bridge.py` structurally merges a known-good project settings profile into source geometry, auto-scales/orients/arranges it, invokes Bambu Studio CLI, and rejects output without Bambu slice metadata. A real local run converted `outputs/demo/demo.stl` into a validated P1S project containing `Metadata/plate_1.gcode`; the reported estimate was about 38.9 minutes and 5.11 g filament.
- Printer: local screenshots confirm Bambu Studio is connected to a real P1S with AMS and show a completed print; a read-only probe also found Bambu Studio using MQTT/TLS on port 8883. The repository client now follows the LAN protocol boundary: implicit FTPS on port 990, MQTT/TLS on port 8883, `device/{serial}/report` and `device/{serial}/request`, P1 status fields, and printer-reported command results. This is locally unit-tested but not a real-device claim. `scripts/auto_print.py discover --timeout 3` found no printer and `config/printer.json` is absent, so transport/control validation remains pending. Configuration supports Developer Mode confirmation, AMS mapping, timelapse, and timeout options without tracking printer secrets.
- Slicer output policy: `BAMBU_SLICER_OUTPUT_EXT` must be `.3mf`, `.gcode`, or `.bgcode`; any other output extension is rejected before the slicer runs.
- Aggregate preflight: `python scripts/system_preflight.py --allow-incomplete` currently reports 3 ready areas and 2 blocked areas. Hunyuan3D-2, ComfyUI, and the Bambu slicer bridge are ready; the blockers are Hunyuan3D-1 `nvdiffrast` and missing `config/printer.json`. Strict mode exits 1.

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
# Expected printer config gate until config/printer.json exists:
python scripts/auto_print.py check-config
python scripts/auto_print.py status
# Expected printer discovery gate when no printer is found:
python scripts/ai_to_print.py discover --timeout 0.1
python ComfyUI/main.py --quick-test-for-ci --disable-auto-launch --dont-print-server
```
