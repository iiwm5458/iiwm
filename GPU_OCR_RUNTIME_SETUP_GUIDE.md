# NIKKE C ARENA Tool GPU OCR 环境配置教程

本教程用于给工具启用 GPU 图像识别。配置完成后，重新打开 GUI，即可在“截图与数据识别参数设置”中选择 GPU 模式。

## 一、开始前确认

- Windows 64 位。
- NVIDIA 显卡及其驱动已经正常安装。
- 在命令提示符中运行 nvidia-smi 能显示显卡信息。
- 请先关闭 NIKKE C ARENA Tool。

完整安装包已经自带专用 Python 3.10 运行时：

~~~
runtime_python310_base\
~~~

不需要安装系统 Python，不需要配置 PATH，也不需要 py -3.10。该运行时仅供本工具创建 GPU 环境使用，不会影响电脑中已有的 Python、Anaconda 或开发环境。

## 二、固定依赖版本

GPU OCR 将在工具目录中创建独立环境：

~~~
runtime_gpu\
~~~

当前锁定组合：

~~~
Python 3.10.8
paddlepaddle-gpu==2.6.2
paddleocr==2.7.3
numpy==1.26.4
opencv-python-headless==4.9.0.80
rapidfuzz==3.14.5
lxml==6.1.1
openpyxl==3.1.5
Pillow==12.3.0
nvidia-cuda-runtime-cu11==11.8.89
nvidia-cuda-nvrtc-cu11==11.8.89
nvidia-cublas-cu11==11.11.3.6
nvidia-cudnn-cu11==8.9.5.29
~~~

版本清单位于：

~~~
dataanalysis\arena_ocr_tool\requirements-ocr-gpu.txt
~~~

## 三、一键配置

普通网络环境双击：

~~~
setup_gpu_runtime.bat
~~~

该版本从官方 PyPI 下载依赖：

~~~
https://pypi.org/simple
~~~

中国大陆网络环境可双击：

~~~
setup_gpu_runtime_cn.bat
~~~

该版本默认使用清华 PyPI 镜像：

~~~
https://pypi.tuna.tsinghua.edu.cn/simple
~~~

如清华镜像下载报错，可双击：

~~~
setup_gpu_runtime_aliyun.bat
~~~

该版本使用阿里云 PyPI 镜像：

~~~
https://mirrors.aliyun.com/pypi/simple/
~~~

三个脚本安装完全相同的锁定版本。运行前会提示将下载第三方组件和相关许可信息；确认后按任意键继续。若两个国内镜像都失败，再使用官方 PyPI 脚本。

脚本会自动：

1. 检查 NVIDIA 驱动和 nvidia-smi。
2. 使用工具自带的私有 Python 3.10 创建 runtime_gpu。
3. 安装 GPU 版 PaddleOCR、CUDA/cuDNN pip 运行库及其它锁定依赖。
4. 使用工具内置的离线 PaddleOCR 默认模型，不会在首次识图时下载模型。
5. 写入 DLL 搜索路径辅助文件。
6. 验证 Paddle 已启用 CUDA 且检测到 NVIDIA GPU。

完成后显示 GPU runtime setup succeeded 即表示配置成功。关闭并重新打开 GUI 后，GPU 模式会变为可用。

## 四、第三方下载与许可说明

正式安装包不内置 runtime_gpu 或 wheelhouse_gpu，也不直接再分发 NVIDIA CUDA/cuDNN 运行库。

用户运行一键配置脚本后，脚本会从所选 PyPI 源下载 PaddlePaddle GPU 与 NVIDIA CUDA/cuDNN pip 运行库等第三方组件。继续执行代表用户自行确认并接受相应第三方组件的许可条款。

脚本不会安装或修改 NVIDIA 驱动，不写系统目录，不修改系统 PATH，也不注册 Python Launcher。

## 五、手动配置命令

如需手动创建 GPU 环境，在工具安装目录中运行：

~~~powershell
.\runtime_python310_base\python.exe -m venv runtime_gpu
.\runtime_gpu\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\runtime_gpu\Scripts\python.exe -m pip install -r .\dataanalysis\arena_ocr_tool\requirements-ocr-gpu.txt
~~~

随后可运行下列命令验证：

~~~powershell
.\runtime_gpu\Scripts\python.exe -c "from PIL import Image; import cv2, numpy, openpyxl, paddleocr, paddle; print('paddle', paddle.__version__); print('compiled_with_cuda', paddle.device.is_compiled_with_cuda()); print('cuda_device_count', paddle.device.cuda.device_count())"
~~~

正常结果应包含：

~~~
paddle 2.6.2
compiled_with_cuda True
cuda_device_count 1
~~~

## 六、常见问题

### 找不到 nvidia-smi

NVIDIA 驱动不可用或未正确安装。请先安装或修复驱动。

### 提示私有 Python 基础运行时缺失

安装包可能不完整。请重新安装完整版本的 NIKKE C ARENA Tool，并确认安装目录含有：

~~~
runtime_python310_base\python.exe
~~~

### GPU 按钮仍是灰色

确认：

- runtime_gpu\Scripts\python.exe 存在。
- 验证命令显示 compiled_with_cuda True。
- 验证命令显示 cuda_device_count 大于 0。
- 已关闭并重新打开 GUI。

### 配置中断或旧环境异常

重新运行同一个一键配置脚本即可。若发现旧 runtime_gpu 由早期系统 Python 创建，脚本会将它替换为由工具私有运行时创建的新环境，然后重新安装依赖。

### 国内镜像下载失败

先尝试另一个国内镜像脚本：清华镜像失败时使用 setup_gpu_runtime_aliyun.bat；阿里云镜像失败时使用 setup_gpu_runtime_cn.bat。两个国内镜像都失败后，再改用 setup_gpu_runtime.bat 的官方 PyPI 源，并检查网络、代理或安全软件设置。

## 七、封装说明

完整正式包包含：

~~~
runtime_core\
runtime_cpu\
runtime_python310_base\
setup_gpu_runtime.bat
setup_gpu_runtime_cn.bat
setup_gpu_runtime_aliyun.bat
setup_gpu_runtime.ps1
dataanalysis\arena_ocr_tool\requirements-ocr-gpu.txt
GPU_OCR_RUNTIME_SETUP_GUIDE.md
GPU_OCR_RUNTIME_SETUP_GUIDE.pdf
~~~

GPU 环境 runtime_gpu 仍由用户在需要时通过一键配置创建。这样既避免随包再分发 NVIDIA 运行库，也不会让不使用 GPU OCR 的用户承担额外下载与磁盘占用。
