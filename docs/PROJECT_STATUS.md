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
| ComfyUI workflow | Quick-test startup passed | `python ComfyUI/main.py --quick-test-for-ci --disable-auto-launch --dont-print-server` loads `ComfyUI-Hunyuan3DWrapper` without `nodes_math`/`nodes_glsl` import failures | Workflow JSON and live browser execution required |
| Model conversion | Implemented and tested | `scripts/model_converter.py`; GLB Scene info and GLB-to-STL conversion verified | Real meshes still need print-quality review |
| Model collection | Implemented and tested | `scripts/model_collector.py`; isolated add/export test | Real model library curation |
| Bambu printer queue | Implemented queue layer | `bambu_print/print_queue.py`; tests verify default manual start | Real printer validation |
| Bambu MQTT commands | Partially implemented | `bambu_print/printer_client.py` | Protocol validation against a real Bambu printer |
| Hunyuan command bridge | Implemented wrapper | `scripts/hunyuan_quick.py`, `scripts/hunyuan2_image.py`; dry-run verified | Real generation requires weights/hardware |
| Full AI-to-print | Explicit modes | `scripts/ai_to_print.py` uses `--mock` for demo and `--run-generator` for real commands | Real generator and printer validation |
| Continuous generation and print | Explicit modes | `scripts/continuous_print.py` uses `--mock` for demo and `--run-generator` for real commands | Real generator and printer validation |
| Claude crab batch prompts | Command builder verified | `scripts/generate_claude_crabs.py`; `--list` verified | Real Hunyuan3D-1 generation requires weights/hardware |

## Important Boundaries

The root project is an orchestration layer. It does not include model weights and should not commit local virtual environments, printer secrets, generated queues, or large generated models.

Some local directories are useful runtime assets but should stay out of Git:

- `ComfyUI/`
- `Hunyuan3D-1/venv/`
- `outputs/text_*/`, `outputs/img_*/`, `outputs/continuous/`
- `models/converted/`
- `config/printer.json`

## Current Priority

1. Validate real Hunyuan3D generation on a machine with model weights and compatible GPU.
2. Validate MQTT upload/start/pause/resume/stop against a real Bambu printer.
3. Decide whether pre-existing untracked files should be committed, ignored, or left as local-only user assets.

## Hardware and Runtime Probe

Current local probe results:

- GPU: NVIDIA GeForce RTX 5060 Ti, driver 591.86, 16 GB VRAM.
- System Python: PyTorch `2.12.0.dev20260405+cu130`; CUDA is available and sees the RTX 5060 Ti.
- Hunyuan3D-1 venv: dependency smoke test now passes (`pip check`; `main.py --help`). The venv uses PyTorch `2.5.1+cu121`; CUDA sees the GPU but warns that sm_120 is unsupported. `weights/hunyuanDiT` is missing, so text-to-3D generation has not completed.
- Hunyuan3D-1 with system Python: entry import fails because installed `diffusers` expects `Qwen3ForCausalLM`, which the installed `transformers` does not provide.
- Hunyuan3D-2 local weights: safetensors files exist under `Hunyuan3D-2/tencent/Hunyuan3D-2`. After downloading `hunyuan3d-dit-v2-0/config.yaml`, low-step image-to-3D validation completed and wrote `outputs/validation/hunyuan2_image/validation.glb`.
- ComfyUI: after installing `simpleeval`, `blake3`, `PyOpenGL`, and `glfw`, `python ComfyUI/main.py --quick-test-for-ci --disable-auto-launch --dont-print-server` exits 0, detects CUDA, loads `ComfyUI-Hunyuan3DWrapper`, and no longer reports `nodes_math.py` or `nodes_glsl.py` import failures. It may still fall back to local mode if ComfyUI-Manager cannot reach comfyregistry.
- Printer: `config/printer.json` is absent, so Bambu printer validation has not run.

## Local Verification Completed

These checks passed in the current checkout:

```powershell
python -m compileall scripts bambu_print
python -m unittest discover -s tests -v
Hunyuan3D-1\venv\Scripts\python.exe -m pip check
Hunyuan3D-1\venv\Scripts\python.exe Hunyuan3D-1\main.py --help
python scripts/hunyuan_quick.py text "a small robot" --dry-run --lite
python scripts/ai_to_print.py text "a rabbit" --no-print --mock
python scripts/continuous_print.py generate --prompt "a rabbit" --no-print --mock
python scripts/continuous_print.py generate --prompt "a rabbit" --no-print
python scripts/generate_claude_crabs.py --list
python scripts/model_converter.py info outputs/demo/demo.stl
python scripts/model_converter.py info outputs/validation/hunyuan2_image/validation.glb
python scripts/model_converter.py convert outputs/validation/hunyuan2_image/validation.glb stl validation_hunyuan2
python scripts/auto_print.py status
python ComfyUI/main.py --quick-test-for-ci --disable-auto-launch --dont-print-server
```
