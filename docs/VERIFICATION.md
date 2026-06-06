# Verification

## Local Checks

Run these from the repository root:

```powershell
python -m compileall scripts bambu_print
python -m unittest discover -s tests -v
Hunyuan3D-1\venv\Scripts\python.exe -m pip check
Hunyuan3D-1\venv\Scripts\python.exe Hunyuan3D-1\main.py --help
python -c "from scripts import hunyuan2_image; import os; os.environ['HUNYUAN3D2_MODEL_PATH']='custom/model/path'; print(hunyuan2_image.default_model_path())"
python scripts/hunyuan_quick.py text "a small robot" --dry-run
python scripts/hunyuan_quick.py image Hunyuan3D-2/assets/demo.png --dry-run --quality lite
python scripts/ai_to_print.py text "a rabbit" --no-print --mock
python scripts/continuous_print.py generate --prompt "a rabbit" --no-print --mock
python scripts/continuous_print.py generate --prompt "a rabbit" --no-print
python scripts/generate_claude_crabs.py --list
python scripts/model_converter.py info outputs/demo/demo.stl
python scripts/model_converter.py info outputs/validation/hunyuan2_image/validation.glb
python scripts/model_converter.py convert outputs/validation/hunyuan2_image/validation.glb stl validation_hunyuan2
python scripts/model_converter.py convert outputs/validation/hunyuan2_image/validation.glb 3mf validation_hunyuan2
python scripts/glb_to_3mf.py outputs/validation/hunyuan2_image/validation.glb models/converted/validation_hunyuan2.3mf
python scripts/model_converter.py info models/converted/validation_hunyuan2.3mf
# Printer config gate; expected nonzero until config/printer.json exists:
python scripts/auto_print.py check-config
python scripts/auto_print.py status
python scripts/check_comfyui_workflow_assets.py --allow-missing
python ComfyUI/main.py --quick-test-for-ci --disable-auto-launch --dont-print-server
python ComfyUI/main.py --listen 127.0.0.1 --port 8190 --disable-auto-launch
```

The `auto_print.py check-config` command validates the local JSON fields without connecting to the printer. Without `config/printer.json`, the expected result is a clear message asking the user to configure the printer. The `status`, `start`, and `watch` commands also require a valid local config before they create a queue client.

## External Checks

These checks require hardware, model weights, or local services that cannot be proven by static tests alone:

- Hunyuan3D-1 real text-to-3D generation requires model weights and a compatible Python/CUDA environment.
- Hunyuan3D-2 real image-to-3D generation requires model weights and a compatible Python/CUDA environment.
- ComfyUI Hunyuan3D workflow validation still requires aligning the example workflow asset paths, then loading and executing a workflow graph.
- Bambu Lab validation requires printer IP, access code, serial number, and local network control enabled.

## Current External Gate Findings

- RTX 5060 Ti is present and system Python has CUDA-enabled PyTorch nightly.
- Hunyuan3D-1 dependency/CLI smoke validation now passes in `Hunyuan3D-1/venv`:
  - `Hunyuan3D-1\venv\Scripts\python.exe -m pip check`
  - `Hunyuan3D-1\venv\Scripts\python.exe Hunyuan3D-1\main.py --help`
  - root text wrappers now prefer `HUNYUAN3D1_PYTHON`, then `Hunyuan3D-1/venv/Scripts/python.exe`, then the current interpreter.
- Optional local environment variables are documented in `config/env.example`; `.env` and `.env.*` are ignored.
- Hunyuan3D-2 image wrapper defaults to `HUNYUAN3D2_MODEL_PATH` when `--model-path` is not supplied.
- Hunyuan3D-1 real text-to-3D generation is still gated:
  - `Hunyuan3D-1/weights/hunyuanDiT` is missing locally;
  - the venv Torch build is `2.5.1+cu121` and warns that RTX 5060 Ti sm_120 is unsupported;
  - baking/render extras still need real PyTorch3D/DUSt3R/libigl support if `--do_bake` or `--do_render` is required.
- Hunyuan3D-2 low-step local validation passed after adding `hunyuan3d-dit-v2-0/config.yaml` to the ignored local model folder. Command used:

```powershell
python scripts/hunyuan2_image.py --image Hunyuan3D-2/assets/demo.png --output outputs/validation/hunyuan2_image --output-name validation.glb --model-path Hunyuan3D-2/tencent/Hunyuan3D-2 --low-vram --steps 5 --octree-resolution 128 --num-chunks 4000
```

To restore the required config file in a fresh checkout with the safetensors already present:

```powershell
python -c "from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='tencent/Hunyuan3D-2', filename='hunyuan3d-dit-v2-0/config.yaml', local_dir='Hunyuan3D-2/tencent/Hunyuan3D-2')"
```
- GLB-to-STL and GLB-to-3MF conversion are verified against `outputs/validation/hunyuan2_image/validation.glb` using both `scripts/model_converter.py` and the dedicated `scripts/glb_to_3mf.py` wrapper. The generated `models/converted/validation_hunyuan2.3mf` is readable by `model_converter.py info` and reports watertight output in this local run.
- ComfyUI quick test exits successfully, detects CUDA, and loads `ComfyUI-Hunyuan3DWrapper`. After installing `simpleeval`, `blake3`, `PyOpenGL`, and `glfw`, `nodes_glsl.py` and `nodes_math.py` no longer fail to import. A temporary browser validation at `http://127.0.0.1:8190` rendered the ComfyUI UI (`Unsaved Workflow`, `Manager`, queue status, zoom controls). `python scripts/check_comfyui_workflow_assets.py --allow-missing` verifies the example workflow gates: 13 asset references checked, 7 unique required assets missing, and 2 unique optional/downloadable assets missing in the current local checkout.
- Printer validation is pending because `config/printer.json` is not present. `python scripts/auto_print.py check-config` is the local preflight gate before network/printer validation.

## Release Gate

Before publishing or opening a PR, verify:

```powershell
git status --short
python -m compileall scripts bambu_print
python -m unittest discover -s tests -v
```

Do not stage `.env`, `config/printer.json`, virtual environments, model weights, generated queues, or large generated output files.
