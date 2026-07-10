"""Build the end-user PDF guide for the optional GPU OCR runtime."""

from __future__ import annotations

from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "GPU_OCR_RUNTIME_SETUP_GUIDE.pdf"
FONT_PATH = Path(r"C:\Windows\Fonts\simhei.ttf")


def make_paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text.replace("\n", "<br/>"), style)


def make_code(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def build_styles() -> dict[str, ParagraphStyle]:
    if not FONT_PATH.exists():
        raise RuntimeError(f"Required Chinese font was not found: {FONT_PATH}")

    pdfmetrics.registerFont(TTFont("NikkeGuide", str(FONT_PATH)))
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="NikkeGuide",
            fontSize=22,
            leading=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0B4E78"),
            spaceAfter=10,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["BodyText"],
            fontName="NikkeGuide",
            fontSize=10,
            leading=16,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#48657A"),
            spaceAfter=16,
        ),
        "heading": ParagraphStyle(
            "Heading",
            parent=base["Heading2"],
            fontName="NikkeGuide",
            fontSize=15,
            leading=22,
            textColor=colors.HexColor("#0A6B9E"),
            spaceBefore=12,
            spaceAfter=7,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="NikkeGuide",
            fontSize=10.4,
            leading=17,
            textColor=colors.HexColor("#1B2D3A"),
            spaceAfter=6,
        ),
        "note": ParagraphStyle(
            "Note",
            parent=base["BodyText"],
            fontName="NikkeGuide",
            fontSize=10,
            leading=16,
            textColor=colors.HexColor("#743400"),
            leftIndent=8,
            rightIndent=8,
            spaceAfter=2,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=base["Code"],
            fontName="Courier",
            fontSize=8.2,
            leading=12,
            textColor=colors.HexColor("#17364A"),
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName="NikkeGuide",
            fontSize=9.1,
            leading=14,
            textColor=colors.HexColor("#415968"),
            spaceAfter=4,
        ),
    }


def panel(content, width=17.7 * cm, background="#F1FAFF", border="#8ED7F8"):
    table = Table([[content]], colWidths=[width])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(background)),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor(border)),
                ("LEFTPADDING", (0, 0), (-1, -1), 11),
                ("RIGHTPADDING", (0, 0), (-1, -1), 11),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#B8D9E8"))
    canvas.line(1.65 * cm, 1.35 * cm, A4[0] - 1.65 * cm, 1.35 * cm)
    canvas.setFont("NikkeGuide", 8)
    canvas.setFillColor(colors.HexColor("#587282"))
    canvas.drawString(1.65 * cm, 0.88 * cm, "NIKKE C ARENA Tool - GPU OCR 环境配置教程")
    canvas.drawRightString(A4[0] - 1.65 * cm, 0.88 * cm, f"第 {document.page} 页")
    canvas.restoreState()


def build_pdf() -> None:
    styles = build_styles()
    document = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,
        leftMargin=1.65 * cm,
        rightMargin=1.65 * cm,
        topMargin=1.45 * cm,
        bottomMargin=1.8 * cm,
        title="NIKKE C ARENA Tool GPU OCR 环境配置教程",
        author="NIKKE C ARENA Tool",
    )

    story = [
        make_paragraph("NIKKE C ARENA Tool", styles["title"]),
        make_paragraph("GPU OCR 环境一键配置教程", styles["title"]),
        make_paragraph(
            "适用于 NVIDIA 显卡用户。完整安装包已经内置专用 Python 3.10；用户无需安装或配置系统 Python。",
            styles["subtitle"],
        ),
        make_paragraph("开始前确认", styles["heading"]),
        panel(
            [
                make_paragraph("<b>1.</b> Windows 64 位，已安装并正常使用 NVIDIA 显卡驱动。", styles["body"]),
                make_paragraph("<b>2.</b> 在命令提示符中运行 nvidia-smi 后能看到显卡信息。", styles["body"]),
                make_paragraph("<b>3.</b> 先关闭本工具；完成配置后需要重新打开 GUI。", styles["body"]),
                make_paragraph(
                    "<b>4.</b> 无需安装 Python 3.10，无需设置 PATH，也不需要 py -3.10。",
                    styles["body"],
                ),
            ]
        ),
        Spacer(1, 10),
        make_paragraph("工具私有 Python 运行时", styles["heading"]),
        make_paragraph(
            "完整安装包包含 runtime_python310_base。它只在工具目录内使用，用于创建 runtime_gpu，"
            "不会写注册表、不注册 Python Launcher、不修改系统 PATH，也不会影响已有 Python、Anaconda 或开发环境。",
            styles["body"],
        ),
        panel(
            [make_code("runtime_python310_base\\\nruntime_gpu\\", styles["code"])],
            background="#F7FBFE",
            border="#A7D7EB",
        ),
        Spacer(1, 10),
        make_paragraph("一键配置", styles["heading"]),
        make_paragraph("在工具安装目录中，按网络环境双击下列其中一个文件：", styles["body"]),
    ]

    rows = [
        [make_paragraph("文件", styles["body"]), make_paragraph("下载来源与适用情况", styles["body"])],
        [
            make_paragraph("setup_gpu_runtime.bat", styles["body"]),
            make_paragraph("官方 PyPI。适合可正常访问官方源的网络环境。", styles["body"]),
        ],
        [
            make_paragraph("setup_gpu_runtime_cn.bat", styles["body"]),
            make_paragraph("清华 PyPI 镜像。适合中国大陆网络环境。", styles["body"]),
        ],
    ]
    table = Table(rows, colWidths=[6.0 * cm, 11.7 * cm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "NikkeGuide"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.6),
                ("LEADING", (0, 0), (-1, -1), 15),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#147DAE")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F6FCFF")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#A7D7EB")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend(
        [
            table,
            Spacer(1, 8),
            make_paragraph(
                "运行前会显示第三方下载和许可提示。确认后脚本会检查驱动、创建独立 GPU 环境、"
                "安装锁定版本依赖并验证 CUDA。出现 GPU runtime setup succeeded 即表示完成。",
                styles["body"],
            ),
            panel(
                [
                    make_paragraph(
                        "<b>重要：</b>脚本会从所选 PyPI 源下载 PaddlePaddle GPU、NVIDIA CUDA/cuDNN pip "
                        "运行库和其它第三方组件。继续运行代表用户自行确认并接受相应许可条款。",
                        styles["note"],
                    )
                ],
                background="#FFF7EC",
                border="#E9BE77",
            ),
            PageBreak(),
            make_paragraph("固定版本与离线模型", styles["heading"]),
            panel(
                [
                    make_paragraph("为避免安装到不兼容的新版本，脚本锁定以下核心组合：", styles["body"]),
                    make_paragraph(
                        "Python 3.10.8；paddlepaddle-gpu 2.6.2；paddleocr 2.7.3；"
                        "CUDA runtime 11.8.89；CUDA NVRTC 11.8.89；"
                        "cuBLAS 11.11.3.6；cuDNN 8.9.5.29。",
                        styles["small"],
                    ),
                    make_paragraph(
                        "工具内置 PaddleOCR 默认模型，首次识图不会下载模型。完整 CUDA Toolkit 通常不是必需项；"
                        "但 NVIDIA 驱动必须由用户自行安装并保持可用。",
                        styles["small"],
                    ),
                ]
            ),
            make_paragraph("配置完成后开启 GPU 模式", styles["heading"]),
            make_paragraph("<b>1.</b> 关闭并重新启动 NIKKE C ARENA Tool。", styles["body"]),
            make_paragraph("<b>2.</b> 打开“截图与数据识别参数设置”。", styles["body"]),
            make_paragraph("<b>3.</b> 在“OCR 运行模式”中选择 GPU。", styles["body"]),
            make_paragraph(
                "当 GPU 选项可点击，并且环境验证通过后，后续手工战斗图像识别将使用 GPU 环境。",
                styles["body"],
            ),
            make_paragraph("手动配置命令", styles["heading"]),
            panel(
                [
                    make_code(
                        ".\\runtime_python310_base\\python.exe -m venv runtime_gpu\n"
                        ".\\runtime_gpu\\Scripts\\python.exe -m pip install --upgrade pip setuptools wheel\n"
                        ".\\runtime_gpu\\Scripts\\python.exe -m pip install -r .\\dataanalysis\\arena_ocr_tool\\requirements-ocr-gpu.txt",
                        styles["code"],
                    )
                ],
                background="#F7FBFE",
                border="#A7D7EB",
            ),
            Spacer(1, 9),
            make_paragraph("常见问题", styles["heading"]),
            make_paragraph(
                "<b>找不到 nvidia-smi：</b>请安装或修复 NVIDIA 显卡驱动。",
                styles["body"],
            ),
            make_paragraph(
                "<b>提示私有 Python 基础运行时缺失：</b>重新安装完整版本，并确认安装目录存在 runtime_python310_base\\python.exe。",
                styles["body"],
            ),
            make_paragraph(
                "<b>GPU 按钮仍是灰色：</b>确认 runtime_gpu\\Scripts\\python.exe 存在，验证结果显示 compiled_with_cuda True "
                "且 cuda_device_count 大于 0，然后重新打开 GUI。",
                styles["body"],
            ),
            make_paragraph(
                "<b>配置中断或旧环境异常：</b>重新运行同一个脚本即可。发现旧 runtime_gpu 由早期系统 Python 创建时，"
                "脚本会替换为工具私有运行时创建的新环境。",
                styles["body"],
            ),
            make_paragraph(
                "<b>国内镜像下载失败：</b>改用 setup_gpu_runtime.bat 的官方 PyPI 源，并检查网络、代理或安全软件设置。",
                styles["body"],
            ),
        ]
    )

    document.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    build_pdf()
