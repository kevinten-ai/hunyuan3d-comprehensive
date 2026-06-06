# Project Status

## Repository

- GitHub: https://github.com/kevinten-ai/hunyuan3d-comprehensive
- Default branch: `master`
- Local orchestration layer: `scripts/`, `bambu_print/`, `config/`, `docs/`
- Upstream engines included in the checkout: `Hunyuan3D-1/`, `Hunyuan3D-2/`

## Capability Matrix

| Area | Status | Evidence | Remaining gate |
|---|---|---|---|
| Hunyuan3D-1 text-to-3D | External engine present | `Hunyuan3D-1/main.py` | CUDA/model weights required for real generation |
| Hunyuan3D-2 image-to-3D | External engine present | `Hunyuan3D-2/minimal_demo.py`, `Hunyuan3D-2/examples/` | CUDA/model weights required for real generation |
| ComfyUI workflow | Local checkout present, not tracked | `ComfyUI/` exists locally; `ComfyUI-Win-Blackwell` is a submodule pointer | Workflow JSON and live launch required |
| Model conversion | Implemented utility | `scripts/model_converter.py` | Real meshes still need print-quality review |
| Model collection | Implemented utility | `scripts/model_collector.py` | Sample add/export verification |
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
- Hunyuan3D-1 venv: PyTorch `2.5.1+cu121`; CUDA sees the GPU but warns that sm_120 is unsupported. The venv also lacks `einops`.
- Hunyuan3D-1 with system Python: entry import fails because installed `diffusers` expects `Qwen3ForCausalLM`, which the installed `transformers` does not provide.
- Hunyuan3D-2 local weights: safetensors files exist under `Hunyuan3D-2/tencent/Hunyuan3D-2`, but the local folder lacks `config.yaml`, so the pipeline cannot load from that directory yet.
- ComfyUI: `python ComfyUI/main.py --quick-test-for-ci --disable-auto-launch --dont-print-server` exits 0, detects CUDA and loads `ComfyUI-Hunyuan3DWrapper`, but reports missing `simpleeval` and OpenGL dependencies for some `comfy_extras` nodes.
- Printer: `config/printer.json` is absent, so Bambu printer validation has not run.

## Local Verification Completed

These checks passed in the current checkout:

```powershell
python -m compileall scripts bambu_print
python -m unittest discover -s tests -v
python scripts/hunyuan_quick.py text "a small robot" --dry-run --lite
python scripts/ai_to_print.py text "a rabbit" --no-print --mock
python scripts/continuous_print.py generate --prompt "a rabbit" --no-print --mock
python scripts/continuous_print.py generate --prompt "a rabbit" --no-print
python scripts/generate_claude_crabs.py --list
python scripts/model_converter.py info outputs/demo/demo.stl
python scripts/auto_print.py status
python ComfyUI/main.py --quick-test-for-ci --disable-auto-launch --dont-print-server
```
