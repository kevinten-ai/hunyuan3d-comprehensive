# Hunyuan3D System Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current Hunyuan3D + ComfyUI + Bambu Lab integration from a mixed prototype into a documented, testable, and releasable local system.

**Architecture:** Keep Tencent Hunyuan3D-1, Tencent Hunyuan3D-2, and ComfyUI as upstream engines. Harden the root project as the orchestration layer: command wrappers, model conversion, model library management, printer queue management, configuration, tests, and documentation.

**Tech Stack:** Python 3, argparse, subprocess, pathlib, unittest/pytest-compatible tests, trimesh for model conversion, paho-mqtt plus system curl/FTPS for Bambu printer integration, GitHub master branch as release source.

---

## Current State Audit

- GitHub repository: `kevinten-ai/hunyuan3d-comprehensive`, public, default branch `master`.
- Local branch for this work: `codex/hunyuan3d-system-hardening`.
- Root project purpose: local AI 3D model generation for Bambu Lab printing.
- Tracked upstream engine folders: `Hunyuan3D-1/`, `Hunyuan3D-2/`.
- Local-only large/runtime folders currently present: `ComfyUI/`, `Hunyuan3D-1/venv/`, generated assets in `outputs/`, and local script additions.
- Implemented root utilities: model conversion, model collection, printer queue scaffolding, printer CLI.
- Prototype or misleading areas: `scripts/hunyuan_quick.py`, `scripts/ai_to_print.py`, and parts of `scripts/continuous_print.py` print or create simulated outputs instead of calling real generation workflows.
- External validation requirements: real CUDA GPU, model weights, ComfyUI workflows, and a reachable Bambu printer are required to prove full end-to-end printing.

## File Structure

- Modify `.gitignore`: protect local ComfyUI checkouts, virtual environments, logs, printer secrets, generated queues, and model outputs.
- Modify `config/printer.json.example`: document safe placeholder fields without secrets.
- Create `docs/PROJECT_STATUS.md`: current capability matrix, real vs prototype status, and verification evidence.
- Create `docs/VERIFICATION.md`: commands that can be run locally plus external validation gates for GPU/model/printer.
- Create `tests/`: lightweight tests for command construction, config handling, queue persistence, and status serialization.
- Modify `scripts/hunyuan_quick.py`: convert from print-only placeholder to real subprocess command bridge with explicit `--dry-run`.
- Modify `scripts/ai_to_print.py`: stop silent simulation by default; require explicit mock mode or a real generated model path.
- Modify `scripts/continuous_print.py`: mark simulation as mock mode and prevent fake files from being treated as production output.
- Modify `README.md` and `PRINT_WORKFLOW.md`: align docs with current implemented behavior and external prerequisites.

## Task 1: Baseline Documentation

**Files:**
- Create: `docs/PROJECT_STATUS.md`
- Create: `docs/VERIFICATION.md`
- Modify: `.gitignore`

- [ ] **Step 1: Record the current capability matrix**

Create `docs/PROJECT_STATUS.md` with these sections:

```markdown
# Project Status

## Repository

- GitHub: https://github.com/kevinten-ai/hunyuan3d-comprehensive
- Default branch: master
- Local orchestration layer: scripts/, bambu_print/, config/, docs/

## Capability Matrix

| Area | Status | Evidence | Remaining gate |
|---|---|---|---|
| Hunyuan3D-1 text-to-3D | External engine present | Hunyuan3D-1/main.py | CUDA/model weights required |
| Hunyuan3D-2 image-to-3D | External engine present | Hunyuan3D-2/minimal_demo.py and examples/ | CUDA/model weights required |
| ComfyUI workflow | Local checkout present, not tracked | ComfyUI/ exists locally | workflow JSON and live launch required |
| Model conversion | Implemented utility | scripts/model_converter.py | trimesh installed and sample conversion |
| Model collection | Implemented utility | scripts/model_collector.py | sample add/export test |
| Bambu printer queue | Implemented queue layer | bambu_print/print_queue.py | real printer validation |
| Bambu MQTT commands | Partially implemented | bambu_print/printer_client.py | protocol validation against real printer |
| Full AI-to-print | Prototype | scripts/ai_to_print.py contains simulated generation | replace or isolate mock behavior |
```

- [ ] **Step 2: Record verification commands**

Create `docs/VERIFICATION.md` with commands:

```markdown
# Verification

## Local Checks

```powershell
python -m compileall scripts bambu_print
python -m unittest discover -s tests -v
python scripts/hunyuan_quick.py text "a small robot" --dry-run
python scripts/model_converter.py info outputs/demo/demo.stl
python scripts/auto_print.py status
```

## External Checks

- Hunyuan3D-1 real generation requires model weights and CUDA.
- Hunyuan3D-2 real generation requires model weights and CUDA.
- ComfyUI validation requires launching the local ComfyUI checkout and loading a Hunyuan3D workflow.
- Bambu Lab validation requires printer IP, access code, serial number, and local network control enabled.
```

- [ ] **Step 3: Harden ignore rules**

Add ignore entries for local-only assets:

```gitignore
ComfyUI/
Hunyuan3D-1/venv/
venv/
.venv/
*.log
config/printer.json
.3d_print_queue/
models/converted/
outputs/text_*/
outputs/img_*/
outputs/continuous/
```

## Task 2: Hunyuan Command Bridge

**Files:**
- Test: `tests/test_hunyuan_quick.py`
- Modify: `scripts/hunyuan_quick.py`

- [ ] **Step 1: Write failing command-builder tests**

Create `tests/test_hunyuan_quick.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import hunyuan_quick


def test_build_text_command_targets_hunyuan1_main():
    command = hunyuan_quick.build_text_command("a small robot", "out/text", lite=True)

    assert command[0] == sys.executable
    assert str(Path("Hunyuan3D-1") / "main.py") in command[1]
    assert "--text_prompt" in command
    assert "a small robot" in command
    assert "--save_folder" in command
    assert "out/text" in command
    assert "--use_lite" in command


def test_build_image_command_targets_hunyuan2_shape_example():
    command = hunyuan_quick.build_image_command("input.png", "out/image", quality="standard")

    assert command[0] == sys.executable
    assert str(Path("Hunyuan3D-2") / "examples" / "shape_gen.py") in command[1]
    assert "--image-path" in command
    assert "input.png" in command
    assert "--output-dir" in command
    assert "out/image" in command


def test_dry_run_returns_command_without_running_process(tmp_path):
    result = hunyuan_quick.text_to_3d("a cup", output_dir=str(tmp_path), lite=True, dry_run=True)

    assert result["mode"] == "text"
    assert result["dry_run"] is True
    assert result["returncode"] is None
    assert "--text_prompt" in result["command"]
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
python -m unittest tests.test_hunyuan_quick -v
```

Expected: FAIL because `build_text_command`, `build_image_command`, and `dry_run` support do not exist yet.

- [ ] **Step 3: Implement command bridge**

Add functions to `scripts/hunyuan_quick.py`:

```python
def build_text_command(prompt: str, output_dir: str, lite: bool = False) -> list[str]:
    command = [
        sys.executable,
        str(PROJECT_ROOT / "Hunyuan3D-1" / "main.py"),
        "--text_prompt",
        prompt,
        "--save_folder",
        output_dir,
    ]
    if lite:
        command.append("--use_lite")
    return command


def build_image_command(image_path: str, output_dir: str, quality: str = "standard") -> list[str]:
    command = [
        sys.executable,
        str(PROJECT_ROOT / "Hunyuan3D-2" / "examples" / "shape_gen.py"),
        "--image-path",
        image_path,
        "--output-dir",
        output_dir,
    ]
    if quality == "lite":
        command.append("--low-vram-mode")
    return command
```

Update CLI commands to support `--dry-run`, run the subprocess only when not in dry run, and return a structured result.

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```powershell
python -m unittest tests.test_hunyuan_quick -v
```

Expected: PASS.

## Task 3: Printer Queue Safety Tests

**Files:**
- Test: `tests/test_print_queue.py`
- Modify: `bambu_print/print_queue.py` if tests reveal behavior gaps

- [ ] **Step 1: Write tests for supported extension validation and priority order**

Create `tests/test_print_queue.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from bambu_print import PrintQueue


def make_queue(tmp_path):
    return PrintQueue(
        printer_host="192.0.2.10",
        access_code="dummy",
        serial="SN000",
        queue_dir=str(tmp_path),
    )


def test_add_rejects_unsupported_file_extension(tmp_path):
    source = tmp_path / "bad.txt"
    source.write_text("not a model", encoding="utf-8")
    queue = make_queue(tmp_path / "queue")

    with pytest.raises(ValueError):
        queue.add(str(source))


def test_add_persists_supported_model_job(tmp_path):
    source = tmp_path / "model.stl"
    source.write_text("solid test\nendsolid test\n", encoding="utf-8")
    queue_dir = tmp_path / "queue"
    queue = make_queue(queue_dir)

    job_id = queue.add(str(source), name="test model", priority=5)
    reloaded = make_queue(queue_dir)

    assert job_id
    assert len(reloaded.list_queue()) == 1
    assert reloaded.list_queue()[0]["name"] == "test model"
```

- [ ] **Step 2: Run tests to verify current behavior**

Run:

```powershell
python -m unittest tests.test_print_queue -v
```

Expected: PASS if current implementation is already safe; otherwise fail with a concrete queue persistence or validation issue.

## Task 4: Truthful AI-to-Print Behavior

**Files:**
- Test: `tests/test_ai_to_print.py`
- Modify: `scripts/ai_to_print.py`
- Modify: `scripts/continuous_print.py`

- [ ] **Step 1: Write tests that default generation does not silently fake success**

Create `tests/test_ai_to_print.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import ai_to_print


def test_text_generation_requires_mock_mode_for_placeholder(tmp_path):
    result = ai_to_print.generate_text_to_3d("a rabbit", output_dir=str(tmp_path), mock=False)

    assert result is None


def test_text_generation_mock_mode_returns_expected_path(tmp_path):
    result = ai_to_print.generate_text_to_3d("a rabbit", output_dir=str(tmp_path), mock=True)

    assert result.endswith("model.stl")
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
python -m unittest tests.test_ai_to_print -v
```

Expected: FAIL because `mock` is not currently accepted.

- [ ] **Step 3: Implement explicit mock mode**

Update generation functions so the default behavior reports missing real backend and returns `None`; add `mock=True` and CLI `--mock` for demo workflows.

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```powershell
python -m unittest tests.test_ai_to_print -v
```

Expected: PASS.

## Task 5: Release-Ready Documentation

**Files:**
- Modify: `README.md`
- Modify: `PRINT_WORKFLOW.md`
- Modify: `bambu_print/README.md`

- [ ] **Step 1: Update README**

State these facts plainly:

```markdown
This repository is the orchestration layer around Hunyuan3D-1, Hunyuan3D-2, ComfyUI, and Bambu Lab printing. The root scripts do not include model weights. Full generation requires installing dependencies and downloading upstream model weights.
```

- [ ] **Step 2: Update workflow docs**

Add a "Verified locally" section with commands that pass in this checkout and an "External validation required" section for GPU and printer workflows.

- [ ] **Step 3: Run documentation smoke checks**

Run:

```powershell
python -m compileall scripts bambu_print
python -m unittest discover -s tests -v
git status --short
```

Expected: Python compiles, tests pass, and `git status` shows only intentional edits.

## Completion Audit

- [ ] GitHub repository identified and default branch confirmed.
- [ ] Local and remote baseline documented.
- [ ] Prototype code no longer silently claims real generation.
- [ ] Root orchestration utilities have automated tests.
- [ ] Config templates are safe to commit.
- [ ] README and workflow docs match current behavior.
- [ ] External validation gates are documented with runnable commands.
- [ ] No virtual environment, large model, printer secret, or generated print queue is staged.
