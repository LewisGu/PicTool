#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAW File Copy by JPG - Optimized Version
根据JPG文件名自动匹配并复制对应RAW格式文件
"""

import os
import shutil
import sys
import time
import logging
import configparser
from pathlib import Path
from typing import List, Tuple, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QMainWindow, QWidget, QPushButton,
    QLabel, QPlainTextEdit, QMessageBox, QDialog, QDialogButtonBox,
    QVBoxLayout, QFileDialog
)
from PySide6.QtGui import QIcon


# ==================== 常量配置 ====================

# 使用用户目录，避免硬编码D盘
APP_DIR = Path.home() / "CopyRAWFileByJpg"
APP_DIR.mkdir(parents=True, exist_ok=True)

INI_FILE = APP_DIR / "config.ini"
LOG_FILE = APP_DIR / f"{time.strftime('%Y-%m-%d-%H_%M_%S')}.log"

# RAW格式映射表
RAW_FORMAT_MAP: Dict[str, str] = {
    'Canon': '.CR2',
    'Fuji': '.RAF',
    'Nikon': '.NEF',
    'Ricoh': '.DNG',
    'Sony': '.ARW',
    'Pentax': '.PEF',
    'Olympus': '.ORF',
    'Panasonic': '.RW2'
}

DEFAULT_BRAND = 'Nikon'
DEFAULT_FORMAT = '.NEF'


# ==================== 日志配置 ====================

def setup_logging(log_path: Path) -> None:
    """配置日志记录"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_path, mode='w', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )


# ==================== 工具函数 ====================

def log_print(msg: str) -> None:
    """记录日志"""
    logging.info(msg)


def ensure_dir(path: Path) -> None:
    """确保目录存在"""
    path.mkdir(parents=True, exist_ok=True)
    log_print(f'Created directory: {path}')


def get_file_stem(filename: str) -> str:
    """获取文件名（不含扩展名），支持多后缀如 .tar.gz"""
    return Path(filename).stem


def get_file_suffix(filename: str) -> str:
    """获取文件扩展名（包含点，如 .jpg）"""
    return Path(filename).suffix


def list_files(directory: Path) -> Tuple[List[str], bool]:
    """
    获取目录下所有文件的完整文件名列表
    返回: (文件列表, 是否为空)
    """
    if not directory.exists():
        return [], True
    
    files = [f.name for f in directory.iterdir() if f.is_file()]
    return files, len(files) == 0


def has_jpg_files(file_list: List[str]) -> bool:
    """检查文件列表中是否包含JPG文件"""
    return any(get_file_suffix(f).lower() == '.jpg' for f in file_list)


def find_matching_raw_files(jpg_files: List[str], raw_files: List[str], raw_ext: str) -> bool:
    """
    检查是否存在文件名匹配的 JPG-RAW 对
    """
    jpg_stems = {get_file_stem(f) for f in jpg_files if get_file_suffix(f).lower() == '.jpg'}
    raw_stems = {get_file_stem(f) for f in raw_files if get_file_suffix(f).lower() == raw_ext.lower()}
    return not jpg_stems.isdisjoint(raw_stems)


def analyze_raw_formats(file_list: List[str]) -> Tuple[str, str]:
    """
    分析RAW文件格式，返回建议品牌和提示消息
    """
    # 统计非JPG扩展名
    suffix_counts: Dict[str, int] = {}
    for f in file_list:
        ext = get_file_suffix(f)
        if ext and ext.lower() != '.jpg':
            suffix_counts[ext] = suffix_counts.get(ext, 0) + 1
    
    if not suffix_counts:
        return "", "未找到任何RAW格式文件"
    
    # 找出数量最多的格式
    max_ext = max(suffix_counts, key=suffix_counts.get)
    total_types = len(suffix_counts)
    
    # 构造消息
    msg_lines = [f"RAW文件共 {total_types} 类格式："]
    for ext, count in sorted(suffix_counts.items(), key=lambda x: -x[1]):
        msg_lines.append(f"  {ext} 文件 {count} 个")
    
    # 查找对应品牌
    brand = None
    for b, e in RAW_FORMAT_MAP.items():
        if e.lower() == max_ext.lower():
            brand = b
            break
    
    if brand:
        msg_lines.append(f"\n建议匹配品牌：{brand}")
    else:
        brand = "Unknown"
        msg_lines.append(f"\n未识别品牌，使用格式：{max_ext}")
    
    return brand, "\n".join(msg_lines)


# ==================== 文件复制类 ====================

class RawFileCopier:
    """RAW文件复制处理器"""
    
    def __init__(self, jpg_files: List[str], jpg_dir: Path, raw_dir: Path, raw_ext: str):
        self.jpg_files = jpg_files
        self.jpg_dir = jpg_dir
        self.raw_dir = raw_dir
        self.raw_ext = raw_ext
        self.success_count = 0
        self.fail_count = 0
        self.failed_files: List[str] = []
    
    def process_all(self) -> Tuple[int, int, List[str]]:
        """执行所有复制操作"""
        total = len(self.jpg_files)
        
        for i, jpg_name in enumerate(self.jpg_files, 1):
            result = self._copy_single(jpg_name)
            if result:
                self.success_count += 1
            else:
                self.fail_count += 1
            
            # 每10个文件或最后一个打印进度
            if i % 10 == 0 or i == total:
                log_print(f"Progress: {i}/{total} ({self.success_count} success, {self.fail_count} failed)")
        
        return self.success_count, self.fail_count, self.failed_files
    
    def _copy_single(self, jpg_name: str) -> bool:
        """复制单个文件对应的RAW"""
        stem = get_file_stem(jpg_name)
        raw_name = stem + self.raw_ext
        
        src = self.raw_dir / raw_name
        dst = self.jpg_dir / raw_name
        
        if not src.exists():
            log_print(f"Source not found: {src}")
            self.failed_files.append(raw_name)
            return False
        
        try:
            shutil.copy2(src, dst)  # copy2保留元数据
            log_print(f"Copied: {raw_name}")
            return True
        except PermissionError:
            log_print(f"Permission denied: {raw_name}")
            self.failed_files.append(raw_name)
            return False
        except shutil.SameFileError:
            log_print(f"Source and destination are the same: {raw_name}")
            self.failed_files.append(raw_name)
            return False
        except Exception as e:
            log_print(f"Copy failed {raw_name}: {e}")
            self.failed_files.append(raw_name)
            return False


# ==================== 对话框 ====================

class BrandSuggestDialog(QDialog):
    """品牌建议对话框"""
    
    def __init__(self, message: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("品牌自动分析")
        self.setMinimumWidth(300)
        self.accepted_flag = False
        
        layout = QVBoxLayout(self)
        
        self.label = QLabel(message)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        
        button_box = QDialogButtonBox()
        accept_btn = button_box.addButton("接受建议", QDialogButtonBox.AcceptRole)
        reject_btn = button_box.addButton("放弃", QDialogButtonBox.RejectRole)
        
        accept_btn.clicked.connect(self._on_accept)
        reject_btn.clicked.connect(self.reject)
        layout.addWidget(button_box)
    
    def _on_accept(self):
        self.accepted_flag = True
        self.accept()
    
    @staticmethod
    def ask(message: str, parent=None) -> bool:
        """静态方法，显示对话框并返回用户是否接受"""
        dialog = BrandSuggestDialog(message, parent)
        dialog.exec()
        return dialog.accepted_flag


# ==================== 主窗口 ====================

class PicApp(QMainWindow):
    """主应用程序窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RAW文件懒人复制 v3.0")
        self.setFixedSize(320, 420)
        
        # 初始化状态
        self.current_brand = DEFAULT_BRAND
        self.current_format = DEFAULT_FORMAT
        self.config = configparser.ConfigParser()
        
        self._load_config()
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置UI界面"""
        central = QWidget()
        self.setCentralWidget(central)
        
        # JPG路径
        self.jpg_label = QLabel("JPG文件路径", central)
        self.jpg_label.setAlignment(Qt.AlignCenter)
        self.jpg_label.setGeometry(10, 10, 300, 20)
        
        self.jpg_input = QPlainTextEdit(central)
        self.jpg_input.setPlaceholderText("请输入JPG文件源路径（或点击右侧浏览）")
        self.jpg_input.setGeometry(10, 35, 250, 50)
        
        self.jpg_browse = QPushButton("浏览...", central)
        self.jpg_browse.setGeometry(270, 35, 40, 50)
        self.jpg_browse.clicked.connect(self._browse_jpg)
        
        # RAW路径
        self.raw_label = QLabel("RAW文件路径", central)
        self.raw_label.setAlignment(Qt.AlignCenter)
        self.raw_label.setGeometry(10, 95, 300, 20)
        
        self.raw_input = QPlainTextEdit(central)
        self.raw_input.setPlaceholderText("请输入待匹配的RAW文件源路径")
        self.raw_input.setGeometry(10, 120, 250, 50)
        
        self.raw_browse = QPushButton("浏览...", central)
        self.raw_browse.setGeometry(270, 120, 40, 50)
        self.raw_browse.clicked.connect(self._browse_raw)
        
        # 品牌选择
        self.brand_label = QLabel("当前适用品牌", central)
        self.brand_label.setAlignment(Qt.AlignCenter)
        self.brand_label.setGeometry(10, 185, 300, 20)
        
        self.brand_combo = QComboBox(central)
        self._refresh_brand_list(self.current_brand)
        self.brand_combo.setGeometry(110, 210, 100, 25)
        self.brand_combo.currentTextChanged.connect(self._on_brand_changed)
        
        # 操作按钮
        self.analyze_btn = QPushButton("品牌自动分析", central)
        self.analyze_btn.setGeometry(110, 250, 100, 30)
        
        self.copy_btn = QPushButton("一键复制", central)
        self.copy_btn.setGeometry(110, 290, 100, 40)
        self.copy_btn.setStyleSheet("QPushButton { font-weight: bold; }")
        
        self.log_btn = QPushButton("查看日志", central)
        self.log_btn.setGeometry(110, 345, 100, 30)
        
        # 版权信息
        self.copyright = QLabel("RAW文件懒人复制 v3.0 | Optimized", central)
        self.copyright.setAlignment(Qt.AlignCenter)
        self.copyright.setGeometry(10, 390, 300, 20)
    
    def _connect_signals(self):
        """连接信号与槽"""
        self.copy_btn.clicked.connect(self._on_copy)
        self.analyze_btn.clicked.connect(self._on_analyze)
        self.log_btn.clicked.connect(self._on_view_log)
    
    def _browse_jpg(self):
        """浏览选择JPG目录"""
        path = QFileDialog.getExistingDirectory(self, "选择JPG文件目录")
        if path:
            self.jpg_input.setPlainText(path)
    
    def _browse_raw(self):
        """浏览选择RAW目录"""
        path = QFileDialog.getExistingDirectory(self, "选择RAW文件目录")
        if path:
            self.raw_input.setPlainText(path)
    
    def _load_config(self):
        """加载配置文件"""
        if not INI_FILE.exists():
            self._save_config()
            return
        
        try:
            self.config.read(INI_FILE, encoding='utf-8')
            self.current_brand = self.config.get('baseconf', 'brand', fallback=DEFAULT_BRAND)
            self.current_format = self.config.get('baseconf', 'formatname', fallback=DEFAULT_FORMAT)
            log_print(f"Config loaded: brand={self.current_brand}")
        except Exception as e:
            log_print(f"Config load failed: {e}")
            self.current_brand = DEFAULT_BRAND
            self.current_format = DEFAULT_FORMAT
    
    def _save_config(self):
        """保存配置文件"""
        try:
            if 'baseconf' not in self.config.sections():
                self.config.add_section('baseconf')
            self.config.set('baseconf', 'brand', self.current_brand)
            self.config.set('baseconf', 'formatname', self.current_format)
            with open(INI_FILE, 'w', encoding='utf-8') as f:
                self.config.write(f)
        except Exception as e:
            log_print(f"Config save failed: {e}")
    
    def _refresh_brand_list(self, priority_brand: str):
        """刷新品牌列表，指定品牌置顶"""
        self.brand_combo.clear()
        brands = [priority_brand] + [b for b in RAW_FORMAT_MAP.keys() if b != priority_brand]
        self.brand_combo.addItems(brands)
    
    def _on_brand_changed(self, brand: str):
        """品牌切换"""
        if brand in RAW_FORMAT_MAP:
            self.current_brand = brand
            self.current_format = RAW_FORMAT_MAP[brand]
            log_print(f"Brand switched to {brand}")
    
    def _get_paths(self) -> Tuple[Optional[Path], Optional[Path]]:
        """获取并验证输入路径"""
        jpg_text = self.jpg_input.toPlainText().strip()
        raw_text = self.raw_input.toPlainText().strip()
        
        if not jpg_text or not raw_text:
            QMessageBox.warning(self, "错误", "请输入JPG和RAW文件路径")
            return None, None
        
        jpg_path = Path(jpg_text)
        raw_path = Path(raw_text)
        
        if not jpg_path.exists():
            QMessageBox.warning(self, "错误", f"JPG路径不存在：\n{jpg_path}")
            return None, None
        if not raw_path.exists():
            QMessageBox.warning(self, "错误", f"RAW路径不存在：\n{raw_path}")
            return None, None
        
        return jpg_path, raw_path
    
    def _validate_copy(self, jpg_path: Path, raw_path: Path) -> bool:
        """验证是否可以执行复制"""
        if jpg_path.resolve() == raw_path.resolve():
            QMessageBox.warning(self, "错误", "输入的路径相同，请检查")
            return False
        
        jpg_files, _ = list_files(jpg_path)
        if not has_jpg_files(jpg_files):
            QMessageBox.warning(self, "错误", "JPG路径下没有找到JPG文件")
            return False
        
        raw_files, _ = list_files(raw_path)
        if not find_matching_raw_files(jpg_files, raw_files, self.current_format):
            QMessageBox.warning(self, "错误", 
                f"两路径下没有名称一致的 {self.current_format} 文件")
            return False
        
        return True
    
    def _on_copy(self):
        """一键复制"""
        jpg_path, raw_path = self._get_paths()
        if not jpg_path or not raw_path:
            return
        
        if not self._validate_copy(jpg_path, raw_path):
            return
        
        # 获取JPG文件列表
        jpg_files = [f for f in os.listdir(jpg_path) 
                     if f.lower().endswith('.jpg')]
        
        # 执行复制
        copier = RawFileCopier(jpg_files, jpg_path, raw_path, self.current_format)
        success, failed, failed_list = copier.process_all()
        
        # 显示结果
        msg = f"复制完成！\n成功：{success} 个\n失败：{failed} 个"
        if failed > 0:
            msg += f"\n\n失败文件：{', '.join(failed_list[:5])}"
            if len(failed_list) > 5:
                msg += f" 等共 {len(failed_list)} 个"
            QMessageBox.warning(self, "完成（有失败）", msg)
        else:
            QMessageBox.information(self, "完成", msg)
    
    def _on_analyze(self):
        """品牌自动分析"""
        jpg_path, raw_path = self._get_paths()
        if not jpg_path or not raw_path:
            return
        
        raw_files, is_empty = list_files(raw_path)
        if is_empty:
            QMessageBox.warning(self, "错误", "RAW路径下不含任何文件")
            return
        
        suggest_brand, message = analyze_raw_formats(raw_files)
        if not suggest_brand:
            QMessageBox.information(self, "分析结果", message)
            return
        
        if BrandSuggestDialog.ask(message, self):
            self._refresh_brand_list(suggest_brand)
            self.brand_combo.setCurrentText(suggest_brand)
    
    def _on_view_log(self):
        """查看日志文件"""
        try:
            if sys.platform == 'win32':
                os.startfile(LOG_FILE)
            else:
                import subprocess
                subprocess.run(['xdg-open', str(LOG_FILE)])
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开日志文件：{e}")
    
    def closeEvent(self, event):
        """关闭时保存配置"""
        self._save_config()
        log_print(f"Application closing, brand={self.current_brand}")
        event.accept()


# ==================== 入口 ====================

if __name__ == '__main__':
    setup_logging(LOG_FILE)
    log_print("=" * 50)
    log_print("Application started")
    
    app = QApplication(sys.argv)
    
    # 设置应用图标（支持相对路径或打包后的路径）
    icon_path = Path(__file__).parent / "app.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
        log_print(f"Icon loaded: {icon_path}")
    
    window = PicApp()
    window.show()
    sys.exit(app.exec())