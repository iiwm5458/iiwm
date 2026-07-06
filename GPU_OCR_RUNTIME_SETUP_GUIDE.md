# NIKKE OCR GPU 环境傻瓜式配置文档

本文用于帮助用户给本工具配置 GPU 版 PaddleOCR。配置成功后，重新打开 GUI，在“截图与数据识别参数设置”里即可选择 GPU 模式。

## 一、适用条件

请先确认电脑满足：

- Windows 64-bit。
- 有 NVIDIA 显卡。
- 已安装 NVIDIA 显卡驱动。
- 能正常运行 `nvidia-smi`。/*NVIDIA System Management Interface）是 NVIDIA 官方提供的命令行工具，用于监控、管理和配置 NVIDIA GPU 显卡。它基于 NVML（NVIDIA 管理库）开发，随 NVIDIA 显卡驱动一同安装。*/
- 已安装 Python 3.10 64-bit，并且 `py -3.10` 可用。

本脚本不会安装或修改显卡驱动，不会写系统目录，不会修改系统 PATH。它只会在工具目录下创建或修复：

```text
runtime_gpu/
```

## 二、当前固定依赖组合

本项目当前验证通过的 GPU OCR 组合为：

```text
Python 3.10 64-bit
paddlepaddle-gpu==2.6.2
paddleocr==2.7.3
numpy==1.26.4
opencv-python-headless==4.9.0.80
rapidfuzz
lxml
openpyxl
Pillow
nvidia-cuda-runtime-cu11==11.8.89
nvidia-cuda-nvrtc-cu11==11.8.89
nvidia-cublas-cu11==11.11.3.6
nvidia-cudnn-cu11==8.9.5.29
```

这些依赖已经写在：

```text
dataanalysis/arena_ocr_tool/requirements-ocr-gpu.txt
```

## 三、一键配置方法

普通用户优先双击：

```text
setup_gpu_runtime.bat
```

该版本使用官方 PyPI：

```text
https://pypi.org/simple
```

中国大陆用户如果遇到下载慢、连接失败、超时，可以改用：

```text
setup_gpu_runtime_cn.bat
```

该版本默认使用清华 PyPI 镜像：

```text
https://pypi.tuna.tsinghua.edu.cn/simple
```

两个版本安装的依赖版本完全相同，都读取同一份：

```text
dataanalysis/arena_ocr_tool/requirements-ocr-gpu.txt
```

脚本会自动执行：

1. 检查 `nvidia-smi`。
2. 创建 `runtime_gpu`，如果已经存在则复用并修复依赖。
3. 安装 GPU 版 PaddleOCR 与 CUDA/cuDNN pip 运行库。
4. 写入 `runtime_gpu\Lib\site-packages\sitecustomize.py`，让 Windows 能找到虚拟环境里的 NVIDIA DLL。
5. 验证 GUI 检测所需条件：

```python
import paddleocr
import paddle
paddle.device.is_compiled_with_cuda()
paddle.device.cuda.device_count()
```

如果最后提示配置成功，请关闭并重新打开 GUI。GPU 模式应变为可选。

## 四、下载来源与许可提示

普通发布包不内置 `wheelhouse_gpu`，也不直接分发 NVIDIA CUDA/cuDNN 运行库。

用户运行：

```text
setup_gpu_runtime.bat
```

后，脚本会在开始安装前提示用户：即将下载 PaddlePaddle GPU 与 NVIDIA CUDA/cuDNN runtime 等第三方组件，用户继续运行即表示自行确认并接受对应第三方组件的许可条款。

官方版在线安装时，脚本会显式使用：

```text
https://pypi.org/simple
```

中国大陆镜像版会显式使用：

```text
https://pypi.tuna.tsinghua.edu.cn/simple
```

如果镜像源暂时没有同步某个大体积 NVIDIA 包，可以换回官方版 `setup_gpu_runtime.bat`，或者编辑 `setup_gpu_runtime_cn.bat` 里的：

```text
CN_PIP_INDEX
```

改为其它可用 PyPI 镜像。

## 五、离线安装包

如果工具目录下存在：

```text
wheelhouse_gpu/
```

一键配置脚本会优先使用离线安装。

但为了避免直接再分发 NVIDIA 运行库带来的许可问题，普通正式包不建议包含 `wheelhouse_gpu`。该目录仅建议保留在开发包或个人自用环境中。

```powershell
pip install --no-index --find-links wheelhouse_gpu -r dataanalysis/arena_ocr_tool/requirements-ocr-gpu.txt
```

如果没有 `wheelhouse_gpu`，脚本会从网络下载依赖。

## 六、手动配置命令

如果不想使用一键脚本，可以在工具目录中手动执行：

```powershell
py -3.10 -m venv runtime_gpu
.\runtime_gpu\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\runtime_gpu\Scripts\python.exe -m pip install -r .\dataanalysis\arena_ocr_tool\requirements-ocr-gpu.txt
```

然后写入 DLL 搜索路径：

```powershell
$site = & .\runtime_gpu\Scripts\python.exe -c "import site; print(site.getsitepackages()[0])"
@'
"""Register bundled NVIDIA runtime DLL directories for Paddle GPU on Windows."""

from __future__ import annotations

import os
from pathlib import Path


if os.name == "nt" and hasattr(os, "add_dll_directory"):
    site_packages = Path(__file__).resolve().parent
    for relative in (
        "nvidia/cuda_runtime/bin",
        "nvidia/cublas/bin",
        "nvidia/cuda_nvrtc/bin",
        "nvidia/cudnn/bin",
    ):
        dll_dir = site_packages / relative
        if dll_dir.exists():
            try:
                os.add_dll_directory(str(dll_dir))
            except OSError:
                pass
'@ | Set-Content -LiteralPath (Join-Path $site "sitecustomize.py") -Encoding UTF8
```

## 七、验证命令

在工具目录中执行：

```powershell
.\runtime_gpu\Scripts\python.exe -c "from PIL import Image; import cv2, numpy, openpyxl, paddleocr, paddle; print('paddle', paddle.__version__); print('compiled_with_cuda', paddle.device.is_compiled_with_cuda()); print('cuda_device_count', paddle.device.cuda.device_count())"
```

正常结果应类似：

```text
paddle 2.6.2
compiled_with_cuda True
cuda_device_count 1
```

只要这里显示 `True` 且显卡数量大于 `0`，重新打开 GUI 后，GPU 模式就应该可以选择。

## 八、常见问题

### 1. 找不到 `nvidia-smi`

说明 NVIDIA 驱动不可用，或驱动没有正确安装。请先安装或修复显卡驱动。

### 2. 找不到 `py -3.10`

请安装 Python 3.10 64-bit。建议使用 python.org 的安装包，不建议使用 Microsoft Store 版 Python。

### 3. `compiled_with_cuda False`

说明当前 `runtime_gpu` 中安装的不是 GPU 版 Paddle，或安装被 CPU 版 Paddle 覆盖。可以重新运行：

```text
setup_gpu_runtime.bat
```

### 4. `cuda_device_count 0`

说明 Paddle GPU 版已经装上，但无法看到 NVIDIA 显卡。优先检查驱动和 `nvidia-smi`。

### 5. GUI 里 GPU 模式仍然是灰色

请确认：

- `runtime_gpu\Scripts\python.exe` 存在。
- 上方验证命令输出 `compiled_with_cuda True`。
- 上方验证命令输出 `cuda_device_count` 大于 `0`。
- 已经关闭并重新打开 GUI。

如果 `runtime_gpu` 放在其它目录，需要设置：

```powershell
setx NIKKE_OCR_GPU_PYTHON "D:\你的路径\runtime_gpu\Scripts\python.exe"
```

然后重新打开 GUI。

## 九、封装说明

普通用户正式包建议默认带 `runtime_cpu`，GPU 环境作为可选增强。

普通正式包建议附带：

```text
setup_gpu_runtime.bat
setup_gpu_runtime_cn.bat
setup_gpu_runtime.ps1
dataanalysis/arena_ocr_tool/requirements-ocr-gpu.txt
GPU_OCR_RUNTIME_SETUP_GUIDE.md
```

不建议在普通正式包中附带：

```text
runtime_gpu/
wheelhouse_gpu/
```

这样可以让用户自行通过 pip 下载第三方 GPU runtime，降低我们直接再分发 NVIDIA 运行库的许可风险。脚本仍然不负责安装 NVIDIA 显卡驱动。
