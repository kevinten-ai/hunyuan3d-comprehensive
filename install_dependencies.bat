@echo off
echo ========================================
echo   拓竹AI打印系统 - 依赖安装
echo ========================================
echo.

echo [1/4] 安装 PyTorch (CUDA 13.0)...
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu130

echo.
echo [2/4] 安装基础依赖...
pip install trimesh numpy pillow requests

echo.
echo [3/4] 安装 MQTT 支持 (打印)...
pip install paho-mqtt

echo.
echo [4/4] 安装 ComfyUI 核心依赖...
cd ComfyUI
pip install -r requirements.txt
cd ..

echo.
echo ========================================
echo   安装完成！
echo ========================================
echo.
echo 下一步:
echo   1. 配置打印机: python scripts/auto_print.py config --host 192.168.1.100 --access-code 你的码 --serial 序列号
echo   2. 启动 ComfyUI: cd ComfyUI ^&^& run_blackwell.bat
echo   3. 开始生成: python scripts/ai_to_print.py text "一只可爱的兔子"
echo.
pause
