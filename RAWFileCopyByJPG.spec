# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec: RAWFileCopyByJPG
关键：icon='resources/app.ico' 将 app.ico 嵌入 EXE，
在 Windows 资源管理器中浏览 exe 时即显示该图标（而不是 Python 默认图标）。
同时 window titlebar/taskbar 图标由 Python 代码中的 setWindowIcon 从
sys._MEIPASS/resources/app.ico 读取。
"""

block_cipher = None

# 只收集实际使用的 PySide6 模块，避免打包整个 Qt（Charts/WebEngine/3D 等）
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
]

a = Analysis(
    ['RAWFileCopyByJPG.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources/app.ico', 'resources'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RAWFileCopyByJPG',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/app.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RAWFileCopyByJPG',
)
