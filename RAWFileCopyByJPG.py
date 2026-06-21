from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QComboBox, QMainWindow, QWidget, QPushButton, QLabel,
    QLineEdit, QMessageBox, QDialog, QVBoxLayout,
    QHBoxLayout, QProgressBar, QFrame, QSizePolicy
)
from PySide6.QtGui import QGuiApplication, QFont, QIcon
import os
import shutil
from pathlib import Path
from collections import Counter
import logging
from logging.handlers import RotatingFileHandler
import time
import sys
import configparser
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Qt6 默认启用高 DPI 缩放，无需手动设置 AA_EnableHighDpiScaling（已废弃）

# ===== 基准分辨率：3180 x 2160 =====
BASE_W = 3180
BASE_H = 2160

# —— 基准尺寸（像素，在 3180×2160 下测得舒适）——
BASE_WIN_W        = 720      # 窗口初始宽（收窄）
BASE_WIN_H        = 820      # 窗口初始高（大字需要更高）
BASE_WIN_MIN_W    = 520      # 窗口最小宽（收窄）
BASE_WIN_MIN_H    = 680      # 窗口最小高

FONT_TITLE_PX     = 34       # 标题：RAW 文件懒人复制（放大）
FONT_BODY_PX      = 20       # 正文：卡片标题、按钮、输入框（放大）
FONT_SMALL_PX     = 15       # 状态行、版权（放大）
FONT_PROGRESS_PX  = 14       # 进度条文字（放大）

HEIGHT_INPUT      = 56       # QLineEdit / QComboBox
HEIGHT_BTN        = 60       # 普通按钮
HEIGHT_BTN_MAIN   = 72       # 绿色一键复制
HEIGHT_PROGRESS   = 36       # 进度条
HEIGHT_LABEL      = 28       # 卡片内标题

WIDTH_INPUT       = 380      # QLineEdit 最小宽度
WIDTH_COMBO       = 220      # QComboBox 最小宽度
WIDTH_BTN         = 200      # 普通按钮最小宽度
WIDTH_BTN_MAIN    = 240      # 一键复制按钮最小宽度
WIDTH_PROGRESS    = 380      # 进度条最小宽度

MAIN_MARGIN_L     = 22
MAIN_MARGIN_T     = 16
MAIN_MARGIN_R     = 22
MAIN_MARGIN_B     = 16
MAIN_SPACING       = 14

CARD_MARGIN_L    = 18
CARD_MARGIN_T    = 14
CARD_MARGIN_R    = 18
CARD_MARGIN_B    = 14
CARD_SPACING       = 8

# 日志配置
DEFAULT_INI_DIR = Path(os.path.expanduser("~")) / "CopyRAWFileByJpg"
DEFAULT_INI_FILE = DEFAULT_INI_DIR / "config.ini"
DEFAULT_LOG_DIR = DEFAULT_INI_DIR / "logs"
DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
NOW = time.strftime("%Y-%m-%d-%H_%M_%S", time.localtime())
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / f"{NOW}.log"

DEFAULT_RAW_FORMAT = {
    "Canon": ".CR2", "Fuji": ".RAF", "Nikon": ".NEF", "Ricoh": ".DNG",
    "Sony": ".ARW", "Pentax": ".PEF", "Olympus": ".ORF", "Panasonic": ".RW2"
}

# —— 配置/常量集中（避免硬编码字符串散落在多处） ——
DEFAULT_BRAND = "Nikon"
DEFAULT_FORMAT_EXT = ".NEF"
INI_SECTION = "baseconf"
INI_KEY_BRAND = "brand"
INI_KEY_FORMAT = "formatname"

# 图标路径配置（支持 PyInstaller 打包）
def get_app_icon_path():
    """获取应用图标路径，兼容开发环境和 PyInstaller 打包"""
    icon_name = "app.ico"
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的临时目录
        return Path(sys._MEIPASS) / "resources" / icon_name
    else:
        # 开发环境
        return Path(__file__).parent / "resources" / icon_name

APP_ICON_PATH = get_app_icon_path()

# EXE 文件自身图标由 PyInstaller --icon=resources/app.ico 在打包时嵌入，
# 此处仅用于 QMainWindow 的 setWindowIcon（标题栏/任务栏图标）

# 日志配置：带轮转的日志文件，避免无限增长
def setup_logging():
    """配置带轮转的日志系统"""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # 清除已有 handler（防止重复输出）
    for h in list(logger.handlers):
        logger.removeHandler(h)

    # 日志格式：时间-级别-模块-消息
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(module)s:%(lineno)-4d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 文件 handler：轮转，最大 5MB，保留 3 个备份
    try:
        DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            str(DEFAULT_LOG_FILE),
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    except (OSError, PermissionError) as e:
        # 日志目录不可写时降级到 console
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        logger.addHandler(console)

    return logger

_logger = setup_logging()


def log_print(msg):
    """记录 INFO 级别的日志"""
    _logger.info(msg)


def log_screen_print(msg):
    """同时输出到控制台和日志文件"""
    print(msg)
    _logger.info(msg)


def check_dir(path):
    """检查路径是否为有效目录，处理空字符串和权限问题"""
    if not path or not str(path).strip():
        return False
    try:
        p = Path(str(path).strip().strip('"'))
        return p.is_dir() and os.access(str(p), os.R_OK)
    except (OSError, ValueError):
        return False


def mkdir(path):
    """安全创建目录，处理权限和已存在情况"""
    if not path or not str(path).strip():
        return False
    try:
        p = Path(str(path).strip().strip('"'))
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            log_print(f"the folder {path} has created")
        return True
    except (PermissionError, OSError) as e:
        log_print(f"mkdir failed for {path}: {e}")
        return False


def get_files_in_dir(file_path):
    """使用 os.scandir() 替代 Path.iterdir()，DirEntry 已缓存文件类型，无须额外 stat 调用"""
    try:
        p = str(file_path).strip().strip('"')
        if not os.path.isdir(p):
            return [], True
        files = []
        with os.scandir(p) as it:
            for entry in it:
                if entry.is_file():
                    files.append(Path(entry.path))
        return files, len(files) == 0
    except (OSError, PermissionError) as e:
        log_print(f"get_files_in_dir failed for {file_path}: {e}")
        return [], True


def scan_jpg_and_raw_dirs(jpg_dir, raw_dir, raw_format):
    """
    一次性扫描 JPG 和 RAW 目录，使用 os.scandir() 提升性能。
    返回：
    - jpg_files: JPG 文件名列表
    - raw_stems: RAW 文件名 stem 集合（用于快速匹配）
    - has_match: 是否存在 JPG-RAW 匹配
    - jpg_exists: JPG 目录是否有 JPG 文件
    - error: 错误信息（如有）
    """
    jpg_files = []
    jpg_stems = set()
    raw_stems = set()
    jpg_exists = False
    error_msg = None

    # 扫描 JPG 目录（使用 os.scandir，比 Path.iterdir 更快）
    try:
        with os.scandir(str(jpg_dir).strip().strip('"')) as it:
            for entry in it:
                if entry.is_file():
                    name = entry.name
                    if name.lower().endswith('.jpg'):
                        jpg_files.append(name)
                        jpg_stems.add(name[:-4])  # stem = name without .jpg
                        jpg_exists = True
    except PermissionError:
        error_msg = f"无法访问 JPG 目录（权限不足）：{jpg_dir}"
        log_print(f"PermissionError on jpg_dir: {jpg_dir}")
    except OSError as e:
        error_msg = f"JPG 目录访问失败：{e}"
        log_print(f"OSError on jpg_dir {jpg_dir}: {e}")

    # 扫描 RAW 目录
    raw_ext = raw_format.lower()
    ext_len = len(raw_format)
    try:
        with os.scandir(str(raw_dir).strip().strip('"')) as it:
            for entry in it:
                if entry.is_file():
                    name = entry.name
                    if name.lower().endswith(raw_ext):
                        raw_stems.add(name[:-ext_len])
    except PermissionError:
        if not error_msg:
            error_msg = f"无法访问 RAW 目录（权限不足）：{raw_dir}"
        log_print(f"PermissionError on raw_dir: {raw_dir}")
    except OSError as e:
        if not error_msg:
            error_msg = f"RAW 目录访问失败：{e}"
        log_print(f"OSError on raw_dir {raw_dir}: {e}")

    # 检查是否有匹配
    has_match = bool(jpg_stems & raw_stems)

    return jpg_files, raw_stems, has_match, jpg_exists, error_msg


def get_all_file_suffix_info(file_list, exclude_jpg=False):
    """统计文件扩展名信息，优化字符串操作"""
    suffix_dict = Counter()
    for f in file_list:
        # 直接从文件名获取扩展名，避免多次字符串操作
        name = f.name if hasattr(f, 'name') else str(f)
        # 从右找最后一个点
        dot_pos = name.rfind('.')
        if dot_pos > 0:
            suffix = name[dot_pos + 1:].lower()
            if exclude_jpg and suffix == 'jpg':
                continue
            suffix_dict[suffix] += 1
    suffix_list = list(suffix_dict.keys())
    return suffix_list, suffix_dict


def construct_auto_analyze_msg(suffix_list, suffix_dict):
    msg = f"RAW 文件共 {len(suffix_list)} 类格式，分别为\n"
    for item in suffix_list:
        msg += f"  {item} 文件 {suffix_dict[item]} 个\n"
    if suffix_list:
        max_key = max(suffix_list, key=lambda k: suffix_dict[k])
        max_key = f".{max_key.upper()}"  # 转大写以匹配 DEFAULT_RAW_FORMAT
        brand_map = {v: k for k, v in DEFAULT_RAW_FORMAT.items()}
        brand = brand_map.get(max_key, "Unknown")
        msg += f"\n建议匹配：{brand}"
        return msg, brand
    return "未检测到 RAW 文件", "Unknown"


class CopyWorker(QThread):
    progress = Signal(int)
    finished_copy = Signal(int, int, str)
    log_msg = Signal(str)

    def __init__(self, jpg_files, jpg_dir, raw_dir, raw_format, parent=None):
        super().__init__(parent)
        self.jpg_files = jpg_files
        self.jpg_dir = str(jpg_dir)
        self.raw_dir = str(raw_dir)
        self.raw_format = raw_format
        self._is_running = True
        self._lock = threading.Lock()
        self._success = 0
        self._failed = 0

    def _copy_single_file(self, jpg_file):
        """复制单个文件的辅助函数，供线程池调用"""
        if not self._is_running:
            return None, None, None

        # 直接字符串操作获取 stem
        name = jpg_file
        if name.lower().endswith('.jpg'):
            stem = name[:-4]
        else:
            stem = Path(name).stem

        raw_name = stem + self.raw_format
        src_path = os.path.join(self.raw_dir, raw_name)
        dst_path = os.path.join(self.jpg_dir, raw_name)

        if os.path.exists(src_path):
            try:
                # 使用 1MB 缓冲替代 shutil.copy2 默认的 64KB，减少大文件复制的系统调用次数
                with open(src_path, 'rb') as src_fh, open(dst_path, 'wb') as dst_fh:
                    shutil.copyfileobj(src_fh, dst_fh, length=1024 * 1024)
                shutil.copystat(src_path, dst_path)
                return raw_name, True, None  # 成功时不记录日志，减少 I/O
            except Exception as e:
                return raw_name, False, f"copy failed {raw_name}: {e}"
        else:
            return raw_name, False, f"{src_path} not exist"

    def run(self):
        total = len(self.jpg_files)
        self._success = 0
        self._failed = 0
        last_percent = 0
        completed = 0

        try:
            # 使用线程池并发复制，max_workers=4 适合 I/O 密集型
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(self._copy_single_file, f): f for f in self.jpg_files}

                for future in as_completed(futures):
                    if not self._is_running:
                        # 取消未完成的任务
                        for f in futures:
                            if not f.done():
                                f.cancel()
                        break

                    try:
                        raw_name, success, log_msg = future.result()
                    except Exception as e:
                        # 子线程内未捕获的异常（如 OOM、句柄耗尽）
                        log_print(f"复制任务异常: {e}")
                        with self._lock:
                            self._failed += 1
                        continue

                    if raw_name is None:
                        continue

                    with self._lock:
                        if success:
                            self._success += 1
                        else:
                            self._failed += 1
                            if log_msg:
                                log_print(log_msg)
                        completed += 1

                    # 更新进度（每 1% emit 一次）
                    percent = int(completed / total * 100)
                    if percent != last_percent or completed == total:
                        self.progress.emit(percent)
                        last_percent = percent
        except Exception as e:
            # 线程池自身异常（OOM、线程创建失败）
            log_print(f"CopyWorker fatal error: {e}")
            with self._lock:
                self._failed += (total - completed)
            self.finished_copy.emit(self._success, self._failed, f"复制任务异常终止: {e}")
            return

        # 最后写一条汇总日志
        log_print(f"复制完成: 成功 {self._success}, 失败 {self._failed}")
        msg = f"成功复制 {self._success} 个文件，失败 {self._failed} 个"
        if self._failed > 0:
            msg += "，请检查日志！"
        self.finished_copy.emit(self._success, self._failed, msg)

    def stop(self):
        self._is_running = False
        self.wait(1000)


class BrandDialog(QDialog):
    def __init__(self, msg, scale, parent=None):
        super().__init__(parent)
        self.setWindowTitle("品牌分析建议")
        s = scale

        self.setMinimumWidth(int(360 * s))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(int(22*s), int(18*s), int(22*s), int(16*s))
        layout.setSpacing(int(12*s))

        font_body = QFont()
        font_body.setPixelSize(int(FONT_BODY_PX * s))
        font_small = QFont()
        font_small.setPixelSize(int(FONT_SMALL_PX * s))

        lbl = QLabel(msg)
        lbl.setFont(font_body)
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        lbl.setMinimumHeight(int(90 * s))
        lbl.setStyleSheet("color:#333;")
        layout.addWidget(lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        ok_btn = QPushButton("接受")
        ok_btn.setFont(font_body)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setMinimumHeight(int(HEIGHT_BTN * s))
        ok_btn.setStyleSheet(
            "QPushButton{background:#2196F3;color:white;border:none;border-radius:6px;padding:4px 18px;}"
            "QPushButton:hover{background:#1976D2;}"
            "QPushButton:pressed{background:#0D47A1;}"
        )
        cancel_btn = QPushButton("放弃")
        cancel_btn.setFont(font_body)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setMinimumHeight(int(HEIGHT_BTN * s))
        cancel_btn.setStyleSheet(
            "QPushButton{background:#9E9E9E;color:white;border:none;border-radius:6px;padding:4px 18px;}"
            "QPushButton:hover{background:#757575;}"
        )
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)


class PicApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # —— 1. 从屏幕信息计算 scale ——
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableVirtualGeometry()
            sw, sh = avail.width(), avail.height()
        else:
            sw, sh = BASE_W, BASE_H

        # 相对基准 3180×2160 的比例，取较小者；限制在 [0.6, 1.5]
        scale = min(sw / BASE_W, sh / BASE_H)
        if scale < 0.6: scale = 0.6
        if scale > 1.5: scale = 1.5
        # 如果当前屏就是或接近基准，scale 给 1.0
        if abs(sw - BASE_W) < 80 and abs(sh - BASE_H) < 80:
            scale = 1.0
        self.scale = scale
        s = scale

        # —— 2. 字体（全部像素字号）——
        font_title = QFont()
        font_title.setPixelSize(int(FONT_TITLE_PX * s))
        font_title.setBold(True)
        self.font_title = font_title

        font_body = QFont()
        font_body.setPixelSize(int(FONT_BODY_PX * s))
        self.font_body = font_body

        font_small = QFont()
        font_small.setPixelSize(int(FONT_SMALL_PX * s))
        self.font_small = font_small

        font_progress = QFont()
        font_progress.setPixelSize(int(FONT_PROGRESS_PX * s))
        self.font_progress = font_progress

        # —— 3. 窗口尺寸 ——
        self.setWindowTitle("RAW 文件懒人复制 v3.0")
        self.resize(int(BASE_WIN_W * s), int(BASE_WIN_H * s))
        self.setMinimumSize(int(BASE_WIN_MIN_W * s), int(BASE_WIN_MIN_H * s))
        self.setFont(font_body)

        # —— 4. 窗口图标 —
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        else:
            log_print("图标文件未找到: " + str(APP_ICON_PATH))

        self.init_data()
        self.setup_ui()
        self.set_connect()

    # 便捷：按 scale 缩放整数
    def v(self, base):
        return int(base * self.scale)

    def setup_ui(self):
        s = self.scale
        central = QWidget()
        central.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        central.setFont(self.font_body)
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(self.v(MAIN_MARGIN_L), self.v(MAIN_MARGIN_T),
                                        self.v(MAIN_MARGIN_R), self.v(MAIN_MARGIN_B))
        main_layout.setSpacing(self.v(MAIN_SPACING))

        # === 标题 ===
        title_label = QLabel("RAW 文件懒人复制")
        title_label.setFont(self.font_title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color:#1976D2;")
        title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        title_label.setMinimumHeight(self.v(HEIGHT_LABEL + 18))
        main_layout.addWidget(title_label)

        # —— 卡片工厂 ——
        def make_card():
            card = QFrame()
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            card.setStyleSheet(
                "QFrame{background:#ffffff;border:1px solid #e0e0e0;border-radius:6px;}"
            )
            return card

        card_ml = self.v(CARD_MARGIN_L)
        card_mt = self.v(CARD_MARGIN_T)
        card_mr = self.v(CARD_MARGIN_R)
        card_mb = self.v(CARD_MARGIN_B)
        card_sp = self.v(CARD_SPACING)

        h_label = self.v(HEIGHT_LABEL)
        h_input = self.v(HEIGHT_INPUT)
        h_btn   = self.v(HEIGHT_BTN)
        h_btn_main = self.v(HEIGHT_BTN_MAIN)
        h_prog  = self.v(HEIGHT_PROGRESS)

        w_input = self.v(WIDTH_INPUT)
        w_combo = self.v(WIDTH_COMBO)
        w_btn   = self.v(WIDTH_BTN)
        w_btn_main = self.v(WIDTH_BTN_MAIN)
        w_prog  = self.v(WIDTH_PROGRESS)

        pad_px = self.v(10)
        ddw_px = self.v(26)
        ar1_px = self.v(5)
        ar2_px = self.v(6)
        input_style = (
            "QLineEdit{background:#ffffff;border:1px solid #cccccc;border-radius:6px;"
            "padding:0 " + str(pad_px) + "px;color:#222;selection-background-color:#BBDEFB;}"
            "QLineEdit:focus{border:1px solid #2196F3;}"
        )
        combo_style = (
            "QComboBox{background:#ffffff;border:1px solid #cccccc;border-radius:6px;"
            "padding:0 " + str(pad_px) + "px;color:#222;}"
            "QComboBox:focus{border:1px solid #2196F3;}"
            "QComboBox::drop-down{subcontrol-origin:padding;subcontrol-position:top right;"
            "width:" + str(ddw_px) + "px;border-left:1px solid #e0e0e0;border-top-right-radius:6px;"
            "border-bottom-right-radius:6px;}"
            "QComboBox::down-arrow{image:none;"
            "border-left:" + str(ar1_px) + "px solid transparent;"
            "border-right:" + str(ar1_px) + "px solid transparent;"
            "border-top:" + str(ar2_px) + "px solid #666666;}}"
        )

        # === 路径卡片（JPG + RAW 合并）===
        path_card = make_card()
        path_layout = QVBoxLayout(path_card)
        path_layout.setContentsMargins(card_ml, card_mt, card_mr, card_mb)
        path_layout.setSpacing(card_sp)

        def add_label_row(text, parent_layout):
            lab = QLabel(text)
            lab.setFont(self.font_body)
            lab.setStyleSheet("font-weight:bold;color:#555;")
            lab.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            lab.setMinimumHeight(h_label)
            parent_layout.addWidget(lab)

        def add_input_row(placeholder, parent_layout):
            le = QLineEdit()
            le.setFont(self.font_body)
            le.setPlaceholderText(placeholder)
            le.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            le.setMinimumSize(w_input, h_input)
            le.setStyleSheet(input_style)
            parent_layout.addWidget(le)
            return le

        add_label_row("JPG 文件路径", path_layout)
        self.jpgdir_le = add_input_row(
            "请输入 JPG 文件源路径（例如：D:\\Photos\\JPG）", path_layout
        )
        path_layout.addSpacing(self.v(4))
        add_label_row("RAW 文件路径", path_layout)
        self.rawdir_le = add_input_row(
            "请输入待匹配的 RAW 文件源路径（例如：D:\\Photos\\RAW）", path_layout
        )

        main_layout.addWidget(path_card)

        # === 品牌与格式卡片 ===
        brand_card = make_card()
        brand_layout = QVBoxLayout(brand_card)
        brand_layout.setContentsMargins(card_ml, card_mt, card_mr, card_mb)
        brand_layout.setSpacing(card_sp)

        add_label_row("品牌与格式", brand_layout)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(self.v(10))
        brand_lab = QLabel("当前适用品牌:")
        brand_lab.setFont(self.font_body)
        brand_lab.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        brand_lab.setMinimumHeight(h_label)
        brand_row.addWidget(brand_lab)

        self.brand_cbb = QComboBox()
        self.brand_cbb.setFont(self.font_body)
        self.brand_cbb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.brand_cbb.setMinimumSize(w_combo, h_input)
        self.brand_cbb.setStyleSheet(combo_style)
        brand_row.addWidget(self.brand_cbb, 1)
        brand_layout.addLayout(brand_row)

        self.auto_analyze_btn = QPushButton("品牌自动分析")
        self.auto_analyze_btn.setFont(self.font_body)
        self.auto_analyze_btn.setCursor(Qt.PointingHandCursor)
        self.auto_analyze_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.auto_analyze_btn.setMinimumSize(w_btn, h_btn)
        self.auto_analyze_btn.setStyleSheet(
            "QPushButton{background:#FF9800;color:white;border:none;border-radius:6px;"
            "padding:4px 16px;font-weight:bold;}"
            "QPushButton:hover{background:#F57C00;}"
            "QPushButton:pressed{background:#E65100;}"
            "QPushButton:disabled{background:#E0C79A;}"
        )
        brand_layout.addWidget(self.auto_analyze_btn)

        main_layout.addWidget(brand_card)

        # === 操作卡片 ===
        action_card = make_card()
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(card_ml, card_mt, card_mr, card_mb)
        action_layout.setSpacing(card_sp)

        add_label_row("操作", action_layout)

        self.onekey_copy_btn = QPushButton("一键复制")
        self.onekey_copy_btn.setFont(self.font_body)
        self.onekey_copy_btn.setCursor(Qt.PointingHandCursor)
        self.onekey_copy_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.onekey_copy_btn.setMinimumSize(w_btn_main, h_btn_main)
        self.onekey_copy_btn.setStyleSheet(
            "QPushButton{background:#4CAF50;color:white;border:none;border-radius:6px;"
            "padding:4px 16px;font-weight:bold;}"
            "QPushButton:hover{background:#43A047;}"
            "QPushButton:pressed{background:#2E7D32;}"
            "QPushButton:disabled{background:#A5D6A7;}"
        )
        action_layout.addWidget(self.onekey_copy_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setFont(self.font_progress)
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.progress_bar.setMinimumSize(w_prog, h_prog)
        self.progress_bar.setStyleSheet(
            "QProgressBar{background:#eeeeee;border:1px solid #cccccc;border-radius:4px;"
            "text-align:center;color:#333;padding:0px;}"
            "QProgressBar::chunk{background:#4CAF50;border-radius:3px;}"
        )
        action_layout.addWidget(self.progress_bar)

        self.check_log_btn = QPushButton("查看日志")
        self.check_log_btn.setFont(self.font_body)
        self.check_log_btn.setCursor(Qt.PointingHandCursor)
        self.check_log_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.check_log_btn.setMinimumSize(w_btn, h_btn)
        self.check_log_btn.setStyleSheet(
            "QPushButton{background:#607D8B;color:white;border:none;border-radius:6px;"
            "padding:4px 16px;font-weight:bold;}"
            "QPushButton:hover{background:#546E7A;}"
            "QPushButton:pressed{background:#37474F;}"
            "QPushButton:disabled{background:#B0BEC5;}"
        )
        action_layout.addWidget(self.check_log_btn)

        main_layout.addWidget(action_card)

        # stretch 把卡片和底部状态行分开
        main_layout.addStretch(1)

        # === 状态行 ===
        self.status_label = QLabel("就绪")
        self.status_label.setFont(self.font_small)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color:#555;")
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.status_label.setMinimumHeight(self.v(HEIGHT_LABEL))
        main_layout.addWidget(self.status_label)

        # === 版权信息 ===
        copyright_label = QLabel("RAW 文件懒人复制 v3.0 \u00b7 Copyright By Lewisgu")
        copyright_label.setFont(self.font_small)
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet("color:#9E9E9E;")
        copyright_label.setWordWrap(True)
        copyright_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        copyright_label.setMinimumHeight(self.v(HEIGHT_LABEL))
        main_layout.addWidget(copyright_label)

        # —— 最后填充下拉，避免信号回调依赖未初始化对象 ——
        self.brand_list_gen(self.oribrand)

    def init_data(self):
        self.filecopy_valid = False
        self.cur_logfile = str(DEFAULT_LOG_FILE)
        self.input_rawdir = ""
        self.input_jpgdir = ""
        self.copy_worker = None
        self.check_ini_file()

    def set_connect(self):
        self.onekey_copy_btn.clicked.connect(self.one_key_copy_slot)
        self.auto_analyze_btn.clicked.connect(self.auto_analyze_slot)
        self.brand_cbb.currentTextChanged.connect(self.change_brand)  # Qt6: 用 currentTextChanged 替代 currentIndexChanged[str]
        self.check_log_btn.clicked.connect(self.check_log_slot)

    def warning_window(self, msg):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("错误")
        box.setText(msg)
        box.setStandardButtons(QMessageBox.Ok)
        box.exec_()

    def info_window(self, msg):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Information)
        box.setWindowTitle("提示")
        box.setText(msg)
        box.setStandardButtons(QMessageBox.Ok)
        box.exec_()

    def create_ini_file(self):
        self.config.read(str(DEFAULT_INI_FILE))
        if not self.config.has_section(INI_SECTION):
            self.config.add_section(INI_SECTION)
        self.write_ini_file()

    def write_ini_file(self):
        try:
            self.config.set(INI_SECTION, INI_KEY_BRAND, self.oribrand)
            self.config.set(INI_SECTION, INI_KEY_FORMAT, self.rawformat)
            with open(DEFAULT_INI_FILE, "w", encoding="utf-8") as f:
                self.config.write(f)
        except Exception as e:
            log_print(f"config write error: {e}")

    def check_ini_file(self):
        if DEFAULT_INI_FILE.exists():
            self.config = configparser.ConfigParser()
            self.config.read(str(DEFAULT_INI_FILE), encoding="utf-8")
            try:
                self.oribrand = self.config.get(INI_SECTION, INI_KEY_BRAND)
                self.rawformat = self.config.get(INI_SECTION, INI_KEY_FORMAT)
            except (configparser.NoSectionError, configparser.NoOptionError):
                self.oribrand = DEFAULT_BRAND
                self.rawformat = DEFAULT_FORMAT_EXT
                self.create_ini_file()
            log_print("brand info loaded")
        else:
            mkdir(DEFAULT_INI_DIR)
            self.config = configparser.ConfigParser()
            self.oribrand = DEFAULT_BRAND
            self.rawformat = DEFAULT_FORMAT_EXT
            self.create_ini_file()

    def change_brand(self, brand):
        self.oribrand = brand
        self.rawformat = DEFAULT_RAW_FORMAT.get(self.oribrand, DEFAULT_FORMAT_EXT)
        log_print(f"brand manual switch to {self.oribrand}")
        self.status_label.setText(f"当前品牌: {self.oribrand} | 格式: {self.rawformat}")

    def check_log_slot(self):
        """打开日志文件，处理文件不存在的情况"""
        try:
            log_path = str(DEFAULT_LOG_FILE)
            if not os.path.exists(log_path):
                self.warning_window(f"日志文件不存在：{log_path}")
                return

            if sys.platform == "win32":
                os.startfile(log_path)
            elif sys.platform == "darwin":
                os.system(f'open "{log_path}"')
            else:
                os.system(f'xdg-open "{log_path}"')
        except Exception as e:
            log_print(f"open log file failed: {e}")
            self.warning_window(f"无法打开日志文件：{e}")

    def check_jpg_raw_dir(self):
        """检查路径并一次性扫描两个目录"""
        # 处理空路径
        raw_path = str(self.input_rawdir).strip().strip('"')
        jpg_path = str(self.input_jpgdir).strip().strip('"')

        if not raw_path or not jpg_path:
            self.warning_window("请输入有效的 JPG 和 RAW 目录路径")
            return

        if not check_dir(jpg_path):
            self.warning_window(f"JPG 目录无效或无法访问：{jpg_path}")
            return

        if not check_dir(raw_path):
            self.warning_window(f"RAW 目录无效或无法访问：{raw_path}")
            return

        try:
            raw_resolved = Path(raw_path).resolve()
            jpg_resolved = Path(jpg_path).resolve()
            if raw_resolved == jpg_resolved:
                self.warning_window("JPG 和 RAW 目录不能是同一个路径")
                return
        except OSError as e:
            self.warning_window(f"路径解析失败：{e}")
            return

        # 一次性扫描 JPG 和 RAW 目录
        jpg_files, raw_stems, has_match, jpg_exists, error_msg = scan_jpg_and_raw_dirs(
            jpg_path, raw_path, self.rawformat
        )

        if error_msg:
            self.warning_window(error_msg)
            return

        # 缓存扫描结果供后续使用
        self._jpg_files = jpg_files
        self._raw_stems = raw_stems

        if not jpg_exists:
            self.warning_window("JPG 目录下没有找到 .jpg 文件")
            return

        if not has_match:
            self.warning_window(
                f"未找到名称匹配的 {self.rawformat} 文件\n"
                f"JPG 文件数：{len(jpg_files)}，匹配 RAW 数：0"
            )
            return

        self.filecopy_valid = True
        self.status_label.setText(
            f"扫描完成：{len(jpg_files)} 个 JPG，可复制 {len(set(jpg_files).intersection(set(name + self.rawformat for name in jpg_files)))} 个 RAW"
        )

    def one_key_copy_slot(self):
        self.input_jpgdir = self.jpgdir_le.text().strip()
        self.input_rawdir = self.rawdir_le.text().strip()
        self.filecopy_valid = False

        # 检查是否已有任务在执行
        if self.copy_worker and self.copy_worker.isRunning():
            self.warning_window("当前已有复制任务在执行，请等待完成")
            return

        self.check_jpg_raw_dir()
        if self.filecopy_valid:
            # 使用已缓存的扫描结果，无需再次扫描
            jpg_files = getattr(self, '_jpg_files', [])
            if not jpg_files:
                self.warning_window("JPG 路径下没有找到 JPG 文件")
                return

            try:
                log_print(f"start copy file photo by {self.oribrand} device, total: {len(jpg_files)}")
                self.progress_bar.setValue(0)
                self.onekey_copy_btn.setEnabled(False)
                self.auto_analyze_btn.setEnabled(False)
                self.status_label.setText(f"正在复制 {len(jpg_files)} 个文件...")

                self.copy_worker = CopyWorker(
                    jpg_files, self.input_jpgdir, self.input_rawdir, self.rawformat
                )
                self.copy_worker.progress.connect(self.progress_bar.setValue)
                self.copy_worker.finished_copy.connect(self.on_copy_finished)
                self.copy_worker.start()
            except Exception as e:
                log_print(f"copy task start failed: {e}")
                self.warning_window(f"启动复制任务失败：{e}")
                self.onekey_copy_btn.setEnabled(True)
                self.auto_analyze_btn.setEnabled(True)

    def on_copy_finished(self, success, failed, msg):
        self.onekey_copy_btn.setEnabled(True)
        self.auto_analyze_btn.setEnabled(True)
        self.status_label.setText(msg)
        log_screen_print(msg)
        if failed > 0:
            self.warning_window(msg)
        else:
            self.info_window(msg)

    def brand_list_gen(self, brand):
        brand_list = [brand] + [k for k in DEFAULT_RAW_FORMAT.keys() if k != brand]
        self.brand_cbb.blockSignals(True)
        self.brand_cbb.clear()
        self.brand_cbb.addItems(brand_list)
        self.brand_cbb.blockSignals(False)
        self.oribrand = brand
        self.rawformat = DEFAULT_RAW_FORMAT.get(brand, DEFAULT_FORMAT_EXT)
        self.status_label.setText(f"当前品牌: {self.oribrand} | 格式: {self.rawformat}")

    def brand_advice(self, local_file_list):
        _, suffix_dict = get_all_file_suffix_info(local_file_list, exclude_jpg=True)
        suffix_list = list(suffix_dict.keys())
        msg, suggest_brand = construct_auto_analyze_msg(suffix_list, suffix_dict)
        dialog = BrandDialog(msg, self.scale, self)
        if dialog.exec_() == QDialog.Accepted:
            self.brand_list_gen(suggest_brand)

    def auto_analyze_slot(self):
        """自动分析 RAW 目录中的文件格式"""
        raw_path = self.rawdir_le.text().strip().strip('"')
        jpg_path = self.jpgdir_le.text().strip().strip('"')

        if not raw_path or not jpg_path:
            self.warning_window("请输入有效的目录路径")
            return

        if not check_dir(raw_path):
            self.warning_window(f"RAW 目录无效：{raw_path}")
            return
        if not check_dir(jpg_path):
            self.warning_window(f"JPG 目录无效：{jpg_path}")
            return

        try:
            local_files, empty_flag = get_files_in_dir(raw_path)
            if empty_flag:
                self.warning_window("RAW 目录下没有文件")
                return
            self.brand_advice(local_files)
        except Exception as e:
            log_print(f"auto analyze failed: {e}")
            self.warning_window(f"自动分析失败：{e}")

    def closeEvent(self, event):
        """安全关闭：停止复制任务并保存配置"""
        try:
            if self.copy_worker and self.copy_worker.isRunning():
                self.copy_worker.stop()
                self.copy_worker.wait(2000)
            self.write_ini_file()
            log_print(f"application closed, brand: {self.oribrand}")
        except Exception as e:
            log_print(f"close event error: {e}")
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pic_app = PicApp()
    pic_app.show()
    sys.exit(app.exec_())
