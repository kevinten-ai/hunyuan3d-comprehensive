# Release Readiness

## Current Capability

- The repository now has a documented orchestration layer for Hunyuan3D-1, Hunyuan3D-2, ComfyUI, model conversion, model collection, and Bambu Lab queue management.
- Root generation entry points are truthful:
  - `--dry-run` prints commands without loading models.
  - `--mock` creates a tiny local STL for workflow tests and demos.
  - `--run-generator` is required before scripts call real Hunyuan3D generation.
- Bambu queue `add` persists jobs without auto-connecting or starting the printer.
- Local tests cover root command construction, mock generation, continuous generation safety, model converter output, Bambu exports, and queue persistence.

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
python scripts/auto_print.py status
python scripts/generate_claude_crabs.py --list
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
  - full-quality generation settings still need broader runtime and output-quality validation.
- ComfyUI:
  - quick test exits 0, detects CUDA, and loads `ComfyUI-Hunyuan3DWrapper`;
  - `nodes_math.py` and `nodes_glsl.py` import after installing `simpleeval`, `blake3`, `PyOpenGL`, and `glfw`;
  - browser launch at `http://127.0.0.1:8190` rendered the ComfyUI UI;
  - Hunyuan3D workflow graph execution is still pending.
- Bambu Lab printer:
  - `config/printer.json` is absent;
  - MQTT upload/start/pause/resume/stop have not been validated against a real printer.

## Suggested Next Steps

1. Add `Hunyuan3D-1/weights/hunyuanDiT`, then install/update the Hunyuan3D-1 Torch stack for RTX 50-series support and run a real low-step text-to-3D validation.
2. Keep a complete Hunyuan3D-2 local model snapshot, including `config.yaml`, then validate full-quality generation settings.
3. Load a Hunyuan3D workflow graph in ComfyUI and run it end to end.
4. Create local `config/printer.json` from `config/printer.json.example`, then validate Bambu queue commands on the real printer.
