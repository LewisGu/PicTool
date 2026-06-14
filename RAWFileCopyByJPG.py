from PySide2.QtCore import Qt, QThread, Signal
from PySide2.QtWidgets import (
    QApplication, QComboBox, QMainWindow, QWidget, QPushButton, QLabel,
    QLineEdit, QMessageBox, QDialog, QVBoxLayout,
    QHBoxLayout, QProgressBar, QFrame, QSizePolicy
)
from PySide2.QtGui import QGuiApplication, QFont, QIcon
import os
import shutil
from pathlib import Path
from collections import Counter
import logging
import time
import sys
import configparser

# 高 DPI 适配（交由我们自己按分辨率 scale，不依赖 Qt 的 AA_EnableHighDpiScaling）
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

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

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %a %H:%M:%S",
    filename=str(DEFAULT_LOG_FILE),
    filemode="w"
)


def log_print(msg):
    logging.info(msg)


def log_screen_print(msg):
    print(msg)
    logging.info(msg)


def check_dir(path):
    return Path(path).is_dir()


def exist_jpg_file(file_list):
    for f in file_list:
        if f.suffix.lower() == ".jpg":
            return True
    return False


def jpg_raw_file_precise_match(jpg_files, raw_files, raw_format):
    jpg_prefixes = {f.stem for f in jpg_files}
    raw_prefixes = {f.stem for f in raw_files if f.suffix.lower() == raw_format.lower()}
    return bool(jpg_prefixes & raw_prefixes)


def mkdir(path):
    p = Path(path)
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)
        log_print(f"the folder {path} has created")


def get_files_in_dir(file_path):
    p = Path(file_path)
    if not p.is_dir():
        return [], True
    files = [f for f in p.iterdir() if f.is_file()]
    return files, len(files) == 0


def get_all_file_suffix_info(file_list, exclude_jpg=False):
    suffix_list = []
    suffix_dict = Counter()
    for f in file_list:
        suffix = f.suffix.lstrip(".").lower()
        if not suffix:
            continue
        if exclude_jpg and suffix == "jpg":
            continue
        if suffix not in suffix_list:
            suffix_list.append(suffix)
        suffix_dict[suffix] += 1
    return suffix_list, suffix_dict


def construct_auto_analyze_msg(suffix_list, suffix_dict):
    msg = f"RAW 文件共 {len(suffix_list)} 类格式，分别为\n"
    for item in suffix_list:
        msg += f"  {item} 文件 {suffix_dict[item]} 个\n"
    if suffix_list:
        max_key = max(suffix_list, key=lambda k: suffix_dict[k])
        max_key = f".{max_key}"
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
        self.jpg_dir = Path(jpg_dir)
        self.raw_dir = Path(raw_dir)
        self.raw_format = raw_format
        self._is_running = True

    def run(self):
        success = 0
        failed = 0
        total = len(self.jpg_files)
        for i, jpg_file in enumerate(self.jpg_files, 1):
            if not self._is_running:
                break
            name = Path(jpg_file).stem
            raw_name = name + self.raw_format
            src = self.raw_dir / raw_name
            dst = self.jpg_dir / raw_name
            if src.exists():
                try:
                    shutil.copy2(str(src), str(dst))
                    log_print(f"copy file {raw_name}")
                    success += 1
                except Exception as e:
                    log_print(f"copy failed {raw_name}: {e}")
                    failed += 1
            else:
                log_print(f"{src} not exist in the folder")
                failed += 1
            self.progress.emit(int(i / total * 100))
        msg = f"成功复制 {success} 个文件，失败 {failed} 个"
        if failed > 0:
            msg += "，请检查日志！"
        self.finished_copy.emit(success, failed, msg)

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
        self.brand_cbb.currentIndexChanged[str].connect(self.change_brand)
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
        if not self.config.has_section("baseconf"):
            self.config.add_section("baseconf")
        self.write_ini_file()

    def write_ini_file(self):
        try:
            self.config.set("baseconf", "brand", self.oribrand)
            self.config.set("baseconf", "formatname", self.rawformat)
            with open(DEFAULT_INI_FILE, "w", encoding="utf-8") as f:
                self.config.write(f)
        except Exception as e:
            log_print(f"config write error: {e}")

    def check_ini_file(self):
        if DEFAULT_INI_FILE.exists():
            self.config = configparser.ConfigParser()
            self.config.read(str(DEFAULT_INI_FILE), encoding="utf-8")
            try:
                self.oribrand = self.config.get("baseconf", "brand")
                self.rawformat = self.config.get("baseconf", "formatname")
            except (configparser.NoSectionError, configparser.NoOptionError):
                self.oribrand = "Nikon"
                self.rawformat = ".NEF"
                self.create_ini_file()
            log_print("brand info loaded")
        else:
            mkdir(DEFAULT_INI_DIR)
            self.config = configparser.ConfigParser()
            self.oribrand = "Nikon"
            self.rawformat = ".NEF"
            self.create_ini_file()

    def change_brand(self, brand):
        self.oribrand = brand
        self.rawformat = DEFAULT_RAW_FORMAT.get(self.oribrand, ".NEF")
        log_print(f"brand manual switch to {self.oribrand}")
        self.status_label.setText(f"当前品牌: {self.oribrand} | 格式: {self.rawformat}")

    def check_log_slot(self):
        log_path = str(DEFAULT_LOG_FILE)
        if sys.platform == "win32":
            os.startfile(log_path)
        elif sys.platform == "darwin":
            os.system(f'open "{log_path}"')
        else:
            os.system(f'xdg-open "{log_path}"')

    def check_jpg_raw_dir(self):
        if check_dir(self.input_rawdir) and check_dir(self.input_jpgdir):
            if Path(self.input_rawdir).resolve() == Path(self.input_jpgdir).resolve():
                self.warning_window("输入的路径相同，请检查")
            else:
                if self.jpg_raw_file_match():
                    self.filecopy_valid = True
                else:
                    self.warning_window("两路径下没有名称一致的文件，或 JPG 路径下没有 JPG 文件")
        else:
            self.warning_window("JPG 或 RAW 路径非法，请检查")

    def jpg_raw_file_match(self):
        jpg_files, _ = get_files_in_dir(self.input_jpgdir)
        if exist_jpg_file(jpg_files):
            raw_files, _ = get_files_in_dir(self.input_rawdir)
            return jpg_raw_file_precise_match(jpg_files, raw_files, self.rawformat)
        return False

    def get_jpgfiles_list(self):
        p = Path(self.input_jpgdir)
        self.jpgfileslist = [f.name for f in p.iterdir() if f.is_file() and f.suffix.lower() == ".jpg"]

    def one_key_copy_slot(self):
        self.input_jpgdir = self.jpgdir_le.text().strip()
        self.input_rawdir = self.rawdir_le.text().strip()
        self.filecopy_valid = False
        self.check_jpg_raw_dir()
        if self.filecopy_valid:
            self.get_jpgfiles_list()
            if not self.jpgfileslist:
                self.warning_window("JPG 路径下没有找到 JPG 文件")
                return
            log_print(f"start copy file photo by {self.oribrand} device")
            self.progress_bar.setValue(0)
            self.onekey_copy_btn.setEnabled(False)
            self.status_label.setText("正在复制...")
            self.copy_worker = CopyWorker(
                self.jpgfileslist, self.input_jpgdir, self.input_rawdir, self.rawformat
            )
            self.copy_worker.progress.connect(self.progress_bar.setValue)
            self.copy_worker.finished_copy.connect(self.on_copy_finished)
            self.copy_worker.start()

    def on_copy_finished(self, success, failed, msg):
        self.onekey_copy_btn.setEnabled(True)
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
        self.rawformat = DEFAULT_RAW_FORMAT.get(brand, ".NEF")
        self.status_label.setText(f"当前品牌: {self.oribrand} | 格式: {self.rawformat}")

    def brand_advice(self, local_file_list):
        _, suffix_dict = get_all_file_suffix_info(local_file_list, exclude_jpg=True)
        suffix_list = list(suffix_dict.keys())
        msg, suggest_brand = construct_auto_analyze_msg(suffix_list, suffix_dict)
        dialog = BrandDialog(msg, self.scale, self)
        if dialog.exec_() == QDialog.Accepted:
            self.brand_list_gen(suggest_brand)

    def auto_analyze_slot(self):
        self.input_jpgdir = self.jpgdir_le.text().strip()
        self.input_rawdir = self.rawdir_le.text().strip()
        if check_dir(self.input_rawdir) and check_dir(self.input_jpgdir):
            local_files, empty_flag = get_files_in_dir(self.input_rawdir)
            if empty_flag:
                self.warning_window("本路径下不含任何文件，请检查路径")
            else:
                self.brand_advice(local_files)
        else:
            self.warning_window("路径非法，请检查")

    def closeEvent(self, event):
        if self.copy_worker and self.copy_worker.isRunning():
            self.copy_worker.stop()
        self.write_ini_file()
        log_print(f"brand change to {self.oribrand}")
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pic_app = PicApp()
    pic_app.show()
    sys.exit(app.exec_())
