# Verification

## Local Checks

Run these from the repository root:

```powershell
python -m compileall scripts bambu_print
python -m unittest discover -s tests -v
python -m unittest tests.test_ai_to_print -v
python -m unittest tests.test_continuous_print -v
python -m unittest tests.test_generate_claude_crabs -v
python -m unittest tests.test_hunyuan_quick -v
python -m unittest tests.test_repository_hygiene -v
python -m unittest tests.test_requirements -v
python -m unittest tests.test_model_converter_cli -v
python -m unittest tests.test_model_collector_cli tests.test_model_collector -v
python scripts/system_preflight.py --allow-incomplete
python scripts/system_preflight.py --json --allow-incomplete
Hunyuan3D-1\venv\Scripts\python.exe -m pip check
Hunyuan3D-1\venv\Scripts\python.exe Hunyuan3D-1\main.py --help
python -c "from scripts import hunyuan2_image; import os; os.environ['HUNYUAN3D2_MODEL_PATH']='custom/model/path'; print(hunyuan2_image.default_model_path())"
python scripts/hunyuan_quick.py text "a small robot" --dry-run
python scripts/hunyuan_quick.py image Hunyuan3D-2/assets/demo.png --dry-run --quality lite
python scripts/ai_to_print.py text "a rabbit" --no-print --mock
python scripts/continuous_print.py generate --prompt "a rabbit" --no-print --mock
# Prompt-list local demo after creating a small prompts file:
python scripts/continuous_print.py prompts --file prompts.txt --delay 0 --mock --no-print
# Expected printer-config gate when print is requested without config:
python scripts/ai_to_print.py text "a rabbit" --mock
python scripts/continuous_print.py generate --prompt "a rabbit" --mock
# Expected no-model gate unless --mock or --run-generator is supplied:
python scripts/continuous_print.py generate --prompt "a rabbit" --no-print
# Expected prompt-file gate when the file is missing:
python scripts/continuous_print.py prompts --file missing-prompts.txt --delay 0
python scripts/generate_claude_crabs.py --list
python scripts/model_converter.py info outputs/demo/demo.stl
python scripts/model_converter.py info outputs/validation/hunyuan2_image/validation.glb
python scripts/model_converter.py convert outputs/validation/hunyuan2_image/validation.glb stl validation_hunyuan2
python scripts/model_converter.py convert outputs/validation/hunyuan2_image/validation.glb 3mf validation_hunyuan2
python scripts/glb_to_3mf.py outputs/validation/hunyuan2_image/validation.glb models/converted/validation_hunyuan2.3mf
python scripts/model_converter.py info models/converted/validation_hunyuan2.3mf
# Requires an ignored local config/printer.json; this machine passes and reads live status:
python scripts/auto_print.py check-config
python scripts/auto_print.py status
# Printer discovery gate; expected nonzero when no printer is found locally:
python scripts/ai_to_print.py discover --timeout 0.1
python scripts/prepare_comfyui_workflow_assets.py --offline --include-optional
python scripts/check_comfyui_workflow_assets.py
python scripts/comfyui_hunyuan_smoke.py --start-server --timeout 600
python scripts/bambu_slicer_bridge.py outputs/demo/demo.stl outputs/validation/bambu_cli/bridge_demo.gcode.3mf --slicer-exe PATH_TO_BAMBU_STUDIO --template PATH_TO_KNOWN_GOOD_PROJECT
python ComfyUI/main.py --quick-test-for-ci --disable-auto-launch --dont-print-server
python ComfyUI/main.py --listen 127.0.0.1 --port 8190 --disable-auto-launch
```

The `auto_print.py config` and `auto_print.py check-config` commands validate the local JSON fields without connecting to the printer. Without `config/printer.json`, the expected result is a clear message asking the user to configure the printer. With valid local config, `status` connects over MQTT, waits for a full snapshot, and reports live error/HMS fields. `start` and `watch` also require valid config before creating a queue client. `add`, `remove`, `cancel`, `stop`, and `clear` return nonzero on local failure paths. `scripts/ai_to_print.py` and `scripts/continuous_print.py` reuse the same validation before automatic printing.

`scripts/model_collector.py` supports `MODEL_COLLECTOR_MODELS_DIR` for isolated local model-library roots. The CLI returns nonzero for unknown commands, missing required arguments, and missing export targets.

`scripts/model_converter.py` returns nonzero for unknown commands, missing required arguments, and missing input files, and reports those user errors without a Python traceback.

`scripts/hunyuan_quick.py` returns nonzero for real backend command failures and invalid batch folders while keeping dry-run command construction testable without model weights.

`scripts/ai_to_print.py` returns nonzero when generation does not produce a model, when print is requested without valid printer config, and when its printer discovery command finds no printer locally. `--mock --no-print` remains the local success demo path. Before automatic queueing, it rejects source model files and generic geometry 3MF with instructions to convert plus slice first.

`scripts/continuous_print.py generate` returns nonzero when required inputs are missing, generation does not produce a model, or print is requested without valid printer config; `--mock --no-print` remains the local single-generation success demo path. `continuous_print.py prompts` returns nonzero when the prompt file is missing or empty, when a prompt does not generate a model, or when a generated model cannot be queued; failed prompts are not marked as processed, UTF-8 BOMs are stripped from prompt files, and `--mock --no-print` is the local prompt-list demo path. Before automatic queueing, it rejects source model files and generic geometry 3MF with instructions to convert plus slice first.

`BAMBU_SLICER_COMMAND` and `BAMBU_SLICER_OUTPUT_EXT` are local hooks for the bundled Bambu Studio CLI bridge. Tests cover command success/failure, reject an unsafe output extension before invoking the slicer, and validate generated output before queueing. A real local run produced a P1S project with embedded plate G-code; broader model/process profiles and print quality remain external checks.

`scripts/generate_claude_crabs.py --list` returns success without loading models. Generation commands return nonzero when the Hunyuan3D-1 entrypoint is missing or the batch does not complete successfully.

`scripts/system_preflight.py` is non-destructive. Strict mode returns nonzero while any known local prerequisite is blocked; `--allow-incomplete` keeps report generation successful, and `--json` emits the same findings for automation. The Hunyuan3D-1 fallback may start a disposable Docker container for a small CUDA/nvdiffrast rasterization probe. It does not execute model inference, a slicer, a ComfyUI graph, or a printer connection.

## External Checks

These checks require hardware, model weights, or local services that cannot be proven by static tests alone:

- Hunyuan3D-1 native mode still requires a locally compatible `nvdiffrast`, but the default Docker backend has passed real generation.
- Hunyuan3D-2 has passed a low-step run; full-quality generation requires broader runtime and output-quality validation.
- ComfyUI has passed a low-step Hunyuan3D API graph; full-quality workflows require broader runtime and output-quality validation.
- Bambu Lab status and FTPS upload are verified with ignored local credentials; physical start/control validation still requires a clear build plate and a printer without blocking hardware warnings.

## Current External Gate Findings

- RTX 5060 Ti is present and system Python has CUDA-enabled PyTorch nightly.
- Hunyuan3D-1 dependency/CLI smoke validation now passes in `Hunyuan3D-1/venv`:
  - `Hunyuan3D-1\venv\Scripts\python.exe -m pip check`
  - `Hunyuan3D-1\venv\Scripts\python.exe Hunyuan3D-1\main.py --help`
  - root text wrappers use `HUNYUAN3D1_BACKEND=auto` to prefer Docker; explicit `native` mode uses `HUNYUAN3D1_PYTHON`, then the project venv, then the current interpreter.
- Optional local environment variables are documented in `config/env.example`; root orchestration scripts auto-load repository-root `.env` files without overriding shell variables, and `.env` / `.env.*` remain ignored.
- Hunyuan3D-2 image wrapper defaults to `HUNYUAN3D2_MODEL_PATH` when `--model-path` is not supplied.
- Hunyuan3D-1 real low-step text-to-3D passed through the CUDA 13 Docker path:
  - the complete 20-file, 13.5 GiB `Hunyuan3D-1/weights/hunyuanDiT` snapshot is present locally and remains ignored by Git;
  - the runtime reports Torch `2.10.0+cu130`, compute capability 12.0, and a real nvdiffrast triangle with 72 covered pixels;
  - the 16 GB low-VRAM flow ran text-to-image, background removal, one-step lite multiview generation, and xFormers-backed SVRM in isolated processes;
  - SVRM generated `Hunyuan3D-1/outputs/docker-smoke/mesh_vertex_colors.obj` and reduced 50,934 faces to 1,048 for a 1,000-face target; the low-step mesh is not watertight and needs repair before printing;
  - baking/GIF extras still require optional PyTorch3D/DUSt3R support and were intentionally excluded from the core image.
- The root orchestration path also passed a higher-step local integration run: `ai_to_print.py --run-generator --no-print` auto-selected Docker, completed 25-step text-to-image and 50-step multiview generation, produced an exact 90,000-face OBJ, and exported a repaired STL. Visual inspection found a clear, nonblank blue gear-shaped organizer with consistent silhouettes across the six views; the mesh remains non-watertight.
- Hunyuan3D-2 low-step local validation passed after adding `hunyuan3d-dit-v2-0/config.yaml` to the ignored local model folder. Command used:

```powershell
python scripts/hunyuan2_image.py --image Hunyuan3D-2/assets/demo.png --output outputs/validation/hunyuan2_image --output-name validation.glb --model-path Hunyuan3D-2/tencent/Hunyuan3D-2 --low-vram --steps 5 --octree-resolution 128 --num-chunks 4000
```

To restore the required config file in a fresh checkout with the safetensors already present:

```powershell
python -c "from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='tencent/Hunyuan3D-2', filename='hunyuan3d-dit-v2-0/config.yaml', local_dir='Hunyuan3D-2/tencent/Hunyuan3D-2')"
```
- GLB-to-STL and GLB-to-3MF conversion are verified against `outputs/validation/hunyuan2_image/validation.glb` using both `scripts/model_converter.py` and the dedicated `scripts/glb_to_3mf.py` wrapper. The generated `models/converted/validation_hunyuan2.3mf` is readable by `model_converter.py info` and reports watertight output in this local run.
- ComfyUI quick test exits successfully, detects CUDA, and loads `ComfyUI-Hunyuan3DWrapper`. All 13 unique workflow references are present. `python scripts/comfyui_hunyuan_smoke.py --start-server --timeout 600` completed a real 5-step API graph and produced a watertight GLB with 2,356 vertices and 5,000 faces.
- `scripts/bambu_slicer_bridge.py` completed real Bambu Studio CLI slices from both the demo STL and the generated Hunyuan3D-1 STL. The generated-model project passed `is_bambu_project_3mf`, with an estimate of about 34.3 minutes and 7.95 g filament.
- `python scripts/system_preflight.py --json` now reports 5/5 ready with no known local configuration blocker.
- With LAN Developer Mode enabled, authenticated MQTT/TLS `pushall` on `device/{serial}/report` and `device/{serial}/request` returned a real active-print snapshot from the P1S, and `auto_print.py status` reproduced that state after the full-snapshot fix. Authenticated implicit FTPS uploaded the generated sliced project as `codex_gear_validation.3mf`. The current machine reports `print_error=0` and HMS `0300310000010001`, which the installed P1S HMS resource identifies as a part-cooling-fan speed/stall warning. A user-started print also occupies the plate, so no repository start command was sent; start/pause/resume/stop remain the physical gate. Bambu Lab describes Developer Mode MQTT/FTP as unsupported interfaces, so firmware changes are a compatibility risk.

## Release Gate

Before publishing or opening a PR, verify:

```powershell
git status --short
python -m compileall scripts bambu_print
python -m unittest discover -s tests -v
python scripts/system_preflight.py
```

Do not stage `.env`, `config/printer.json`, virtual environments, model weights, generated queues, or large generated output files.
