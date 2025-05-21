# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Obtener la ruta del chromedriver en el entorno
chromedriver_path = None
# Intenta encontrar el chromedriver en el directorio de webdriver_manager
user_path = os.path.expanduser('~')
webdriver_path = os.path.join(user_path, '.wdm', 'drivers', 'chromedriver')
if os.path.exists(webdriver_path):
    for version_dir in os.listdir(webdriver_path):
        driver_dir = os.path.join(webdriver_path, version_dir)
        if os.path.isdir(driver_dir):
            for win_dir in os.listdir(driver_dir):
                if 'win' in win_dir.lower():
                    chrome_dir = os.path.join(driver_dir, win_dir)
                    if os.path.exists(chrome_dir):
                        for file in os.listdir(chrome_dir):
                            if file.endswith('.exe'):
                                chromedriver_path = os.path.join(chrome_dir, file)
                                break

# Datos adicionales a incluir
added_data = []
if chromedriver_path:
    added_data.append((chromedriver_path, '.'))
    print(f"ChromeDriver found and added: {chromedriver_path}")
else:
    print("ChromeDriver not found in webdriver_manager directory.")

# Incluir todo el directorio de webdriver_manager
added_data.extend(collect_data_files('webdriver_manager'))

# Recopilar submódulos
hidden_imports = collect_submodules('webdriver_manager')
hidden_imports.extend(['selenium', 'requests', 'PyQt5'])

a = Analysis(
    ['cremil_downloader.py'],
    pathex=[],
    binaries=[],
    datas=added_data,
    hiddenimports=hidden_imports,
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CREMIL Descarga Comprobantes',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # Cambiar por tu archivo de icono
)