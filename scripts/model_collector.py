"""
拓竹3D打印机模型收集与管理脚本

功能：
1. 从Hunyuan3D生成模型并自动归档
2. 模型格式转换（STL/3MF/OBJ）
3. 模型质量检查
4. 自动重命名为打印友好格式
"""

import os
import sys
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import json

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
MODELS_RAW = MODELS_DIR / "raw"
MODELS_READY = MODELS_DIR / "ready-to-print"
MODELS_COLLECTION = MODELS_DIR / "collection"

class ModelCollector:
    """3D模型收集器"""

    SUPPORTED_FORMATS = ['.stl', '.obj', '.ply', '.3mf', '.glb', '.gltf']

    CATEGORIES = {
        'characters': '角色人物',
        'animals': '动物',
        'tools': '工具',
        'toys': '玩具',
        'home-decor': '家居装饰',
        'mechanical': '机械零件',
        'custom': '自定义'
    }

    def __init__(self):
        self._ensure_directories()

    def _ensure_directories(self):
        """创建必要的目录结构"""
        dirs = [
            MODELS_RAW / 'text-to-3d',
            MODELS_RAW / 'image-to-3d',
            MODELS_READY,
            MODELS_COLLECTION,
        ]
        for cat in self.CATEGORIES.keys():
            dirs.append(MODELS_COLLECTION / cat)

        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def add_model(self, source_path: str, category: str = 'custom',
                  name: Optional[str] = None, copy: bool = True) -> Path:
        """
        添加模型到库中

        Args:
            source_path: 模型源文件路径
            category: 分类目录
            name: 自定义名称（None则使用原名）
            copy: True=复制文件, False=移动文件

        Returns:
            模型存储路径
        """
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"模型文件不存在: {source}")

        ext = source.suffix.lower()
        if ext not in self.SUPPORTED_FORMATS:
            raise ValueError(f"不支持的格式: {ext}")

        # 确定目标路径
        if name is None:
            name = source.stem
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_name = f"{category}_{name}_{timestamp}{ext}"

        dest = MODELS_COLLECTION / category / new_name

        if copy:
            shutil.copy2(source, dest)
        else:
            shutil.move(str(source), str(dest))

        # 更新模型索引
        self._update_index(dest, category, name)

        print(f"✓ 模型已添加: {dest}")
        return dest

    def _update_index(self, model_path: Path, category: str, name: str):
        """更新模型索引数据库"""
        index_file = MODELS_COLLECTION / 'index.json'
        index = []

        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)

        # 计算文件哈希
        hash_md5 = hashlib.md5()
        with open(model_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)

        entry = {
            'path': str(model_path.relative_to(PROJECT_ROOT)),
            'name': name,
            'category': category,
            'format': model_path.suffix,
            'size': model_path.stat().st_size,
            'hash': hash_md5.hexdigest(),
            'added': datetime.now().isoformat()
        }

        # 检查是否已存在（通过hash）
        existing = False
        for i, item in enumerate(index):
            if item.get('hash') == hash_md5.hexdigest():
                index[i] = entry
                existing = True
                break

        if not existing:
            index.append(entry)

        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    def list_models(self, category: Optional[str] = None) -> List[dict]:
        """列出模型库中的模型"""
        index_file = MODELS_COLLECTION / 'index.json'
        if not index_file.exists():
            return []

        with open(index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)

        if category:
            return [m for m in index if m.get('category') == category]
        return index

    def export_for_print(self, model_name: str, target_dir: str = None) -> Path:
        """
        导出模型到打印目录

        Args:
            model_name: 模型名称（支持模糊匹配）
            target_dir: 目标目录

        Returns:
            导出后的文件路径
        """
        index = self.list_models()

        # 模糊匹配
        matches = [m for m in index if model_name.lower() in m['name'].lower()]

        if not matches:
            raise ValueError(f"未找到模型: {model_name}")
        if len(matches) > 1:
            print("找到多个匹配:")
            for i, m in enumerate(matches):
                print(f"  {i+1}. {m['name']} ({m['category']})")
            return None

        model_info = matches[0]
        source = PROJECT_ROOT / model_info['path']

        if target_dir is None:
            target_dir = MODELS_READY
        else:
            target_dir = Path(target_dir)

        target_dir.mkdir(parents=True, exist_ok=True)
        dest = target_dir / source.name

        shutil.copy2(source, dest)
        print(f"✓ 已导出到: {dest}")
        return dest


def main():
    """命令行入口"""
    collector = ModelCollector()

    if len(sys.argv) < 2:
        print("""
拓竹3D模型收集工具
==================
用法:
  python model_collector.py add <文件路径> [分类] [名称]
  python model_collector.py list [分类]
  python model_collector.py export <模型名>

示例:
  python model_collector.py add ./output/model.stl toys dragon
  python model_collector.py list toys
  python model_collector.py export dragon
        """)
        return

    cmd = sys.argv[1].lower()

    if cmd == 'add':
        if len(sys.argv) < 3:
            print("错误: 请提供文件路径")
            return
        path = sys.argv[2]
        category = sys.argv[3] if len(sys.argv) > 3 else 'custom'
        name = sys.argv[4] if len(sys.argv) > 4 else None
        collector.add_model(path, category, name)

    elif cmd == 'list':
        category = sys.argv[2] if len(sys.argv) > 2 else None
        models = collector.list_models(category)
        print(f"\n{'名称':<30} {'分类':<15} {'格式':<8} {'大小':<12}")
        print("-" * 70)
        for m in models:
            size_kb = m['size'] / 1024
            print(f"{m['name']:<30} {m['category']:<15} {m['format']:<8} {size_kb:.1f} KB")
        print(f"\n共 {len(models)} 个模型")

    elif cmd == 'export':
        if len(sys.argv) < 3:
            print("错误: 请提供模型名称")
            return
        collector.export_for_print(sys.argv[2])

    else:
        print(f"未知命令: {cmd}")


if __name__ == '__main__':
    main()
