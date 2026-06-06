"""
生成 Claude 主题小螃蟹 3D 模型集合。

使用 Hunyuan3D-1 text-to-3D 命令。真实生成需要 Hunyuan3D-1 依赖、
模型权重和可用硬件环境。
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'Hunyuan3D-1'))
sys.path.insert(0, str(PROJECT_ROOT))

# Claude 小螃蟹创意提示词集合
CLAUDE_CRAB_PROMPTS = [
    {
        "name": "claude_crab_classic",
        "prompt": "A cute cartoon crab with Claude AI mascot colors, orange body with warm coral color, large friendly eyes, wearing a small graduation cap, 3D figurine style, chibi style, smooth surface suitable for 3D printing",
        "desc": "经典版 - Claude配色小螃蟹戴学士帽"
    },
    {
        "name": "claude_crab_astronaut",
        "prompt": "A cute astronaut crab wearing a space helmet, Claude orange and cream color scheme, crab claws holding a small star, space theme, cute chibi style, smooth 3D model suitable for printing",
        "desc": "宇航员版 - 穿太空服的Claude螃蟹"
    },
    {
        "name": "claude_crab_wizard",
        "prompt": "A magical wizard crab with Claude colors, orange and warm white, wearing a pointed wizard hat with star patterns, holding a magic wand, cute fantasy style, smooth 3D printable model",
        "desc": "巫师版 - 戴魔法帽的Claude螃蟹"
    },
    {
        "name": "claude_crab_superhero",
        "prompt": "A superhero crab mascot, Claude orange color with cream cape, heroic pose, strong stance, comic book style, cute but powerful, smooth surface for 3D printing, chibi superhero",
        "desc": "超级英雄版 - 披斗篷的Claude螃蟹"
    },
    {
        "name": "claude_crab_sleepy",
        "prompt": "A sleepy cute crab character, Claude warm orange color, wearing pajamas and a nightcap, holding a small pillow, eyes half closed, very cute and cozy, chibi style, smooth 3D model",
        "desc": "睡衣版 - 穿睡衣的困困螃蟹"
    },
    {
        "name": "claude_crab_coffee",
        "prompt": "A cute crab barista, Claude orange colors, wearing an apron, holding a coffee cup with latte art, cheerful expression, cafe theme, adorable chibi style, smooth 3D printable model",
        "desc": "咖啡师版 - 围裙螃蟹端咖啡"
    },
    {
        "name": "claude_crab_gamer",
        "prompt": "A gamer crab character, Claude orange color, wearing headphones, holding a game controller, focused gaming expression, cute geeky style, modern chibi design, smooth 3D model for printing",
        "desc": "游戏玩家版 - 戴耳机的玩家螃蟹"
    },
    {
        "name": "claude_crab_spring",
        "prompt": "A spring festival crab, Claude warm colors, wearing traditional Chinese tang suit with floral patterns, holding a red envelope or lantern, celebratory pose, cute festive chibi style, smooth 3D printable model",
        "desc": "春节版 - 穿唐装的喜庆螃蟹"
    }
]


def build_crab_command(prompt: str, output_dir: str, lite: bool = True, save_memory: bool = True) -> list[str]:
    """Build the Hunyuan3D-1 command for one crab prompt."""
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / 'Hunyuan3D-1' / 'main.py'),
        '--text_prompt', prompt,
        '--save_folder', output_dir,
    ]
    if lite:
        cmd.append('--use_lite')
    if save_memory:
        cmd.append('--save_memory')
    return cmd


def generate_claude_crabs(output_base: str = None, start_index: int = 0, count: int = None):
    """
    批量生成 Claude 小螃蟹 3D 模型
    """
    main_file = PROJECT_ROOT / 'Hunyuan3D-1' / 'main.py'
    if not main_file.exists():
        print("错误: 找不到 Hunyuan3D-1/main.py")
        return

    # 设置输出目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = output_base or f"./outputs/claude_crabs_{timestamp}"
    
    # 确定要生成的模型数量
    prompts_to_generate = CLAUDE_CRAB_PROMPTS[start_index:]
    if count:
        prompts_to_generate = prompts_to_generate[:count]
    
    total = len(prompts_to_generate)
    print(f"\n{'='*60}")
    print(f"[START] 开始生成 {total} 个 Claude 小螃蟹 3D 模型")
    print(f"{'='*60}\n")
    
    successful = []
    failed = []
    
    for i, crab_config in enumerate(prompts_to_generate, 1):
        name = crab_config["name"]
        prompt = crab_config["prompt"]
        desc = crab_config["desc"]
        
        output_dir = f"{output_base}/{name}"
        
        print(f"\n[{i}/{total}] 生成: {desc}")
        print(f"   提示词: {prompt[:80]}...")
        print(f"   输出: {output_dir}")
        
        try:
            # 调用 Hunyuan3D-1 生成模型
            # 使用 --text_prompt 和 --use_lite 参数快速生成
            import subprocess
            
            cmd = build_crab_command(prompt, output_dir)
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT / 'Hunyuan3D-1'))
            
            if result.returncode == 0:
                print(f"   [OK] 成功 -> {output_dir}")
                successful.append({
                    "name": name,
                    "desc": desc,
                    "path": output_dir
                })
            else:
                print(f"   [FAIL] 失败: {result.stderr[:200] if result.stderr else '未知错误'}")
                failed.append({
                    "name": name,
                    "desc": desc,
                    "error": result.stderr[:200] if result.stderr else "未知错误"
                })
                
        except Exception as e:
            print(f"   [FAIL] 异常: {str(e)}")
            failed.append({
                "name": name,
                "desc": desc,
                "error": str(e)
            })
    
    # 输出总结
    print(f"\n{'='*60}")
    print("生成完成总结:")
    print(f"{'='*60}")
    print(f"[OK] 成功: {len(successful)}/{total}")
    print(f"[FAIL] 失败: {len(failed)}/{total}")
    
    if successful:
        print("\n成功的模型:")
        for s in successful:
            print(f"   {s['desc']}: {s['path']}")
    
    if failed:
        print("\n失败的模型:")
        for f in failed:
            print(f"   {f['desc']}: {f.get('error', '未知')}")
    
    print(f"\n所有输出保存在: {output_base}")
    print("\n提示: 用 3D Viewer 或 Blender 查看 .glb 文件")
    print(f"   在线查看: https://3dviewer.net/")
    
    return successful, failed


def generate_single_crab(prompt_index: int = 0):
    """生成单个指定的小螃蟹"""
    if prompt_index >= len(CLAUDE_CRAB_PROMPTS):
        print(f"错误: 索引超出范围 (0-{len(CLAUDE_CRAB_PROMPTS)-1})")
        return
    
    crab = CLAUDE_CRAB_PROMPTS[prompt_index]
    print(f"生成单个模型: {crab['desc']}")
    
    output_base = f"./outputs/claude_crab_single_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    return generate_claude_crabs(
        output_base=output_base,
        start_index=prompt_index,
        count=1
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='生成 Claude 小螃蟹 3D 模型')
    parser.add_argument('--all', action='store_true', help='生成全部8个模型')
    parser.add_argument('--index', type=int, default=0, help='生成指定索引的模型 (0-7)')
    parser.add_argument('--count', type=int, default=None, help='生成前N个模型')
    parser.add_argument('--output', '-o', help='输出目录')
    parser.add_argument('--list', action='store_true', help='列出所有可用的螃蟹设计')
    
    args = parser.parse_args()
    
    if args.list:
        print("\n[Claude Crab Designs] 可用的 Claude 小螃蟹设计:\n")
        for i, crab in enumerate(CLAUDE_CRAB_PROMPTS):
            print(f"{i}. {crab['desc']}")
            print(f"   Prompt: {crab['prompt'][:60]}...")
            print()
    elif args.all:
        generate_claude_crabs(output_base=args.output)
    else:
        generate_claude_crabs(
            output_base=args.output,
            start_index=args.index,
            count=args.count or 2  # 默认生成2个
        )
