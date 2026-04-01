import os
from huggingface_hub import snapshot_download

def download_hunyuan_weights():
    target_dir = r"D:\projects\3d\Hunyuan3D-1\weights"
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    print(f"正在开始下载 Tencent/Hunyuan3D-1 权重到: {target_dir}")
    print("这可能需要较长时间，请保持网络连接...")
    
    try:
        snapshot_download(
            repo_id="Tencent/Hunyuan3D-1",
            local_dir=target_dir,
            local_dir_use_symlinks=False,
            resume_download=True,
            # 排除掉一些非必要的超大文件（如果有的话），优先下载核心权重
            ignore_patterns=["*.msgpack", "*.h5", "*.tflite"] 
        )
        print("\n[成功] 权重下载完成！")
    except Exception as e:
        print(f"\n[错误] 下载过程中出现问题: {e}")
        print("请检查网络连接或代理设置。您可以尝试手动运行: ")
        print(f"huggingface-cli download Tencent/Hunyuan3D-1 --local-dir {target_dir}")

if __name__ == "__main__":
    download_hunyuan_weights()
