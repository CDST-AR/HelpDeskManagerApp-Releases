# -*- mode: python ; coding: utf-8 -*-

import os

block_cipher = None

# Excluir librerías pesadas/no usadas (ajustá si hace falta)
common_excludes = [
    'tensorflow','tensorboard','keras',
    'torch','torchvision','torchaudio',
    'scipy','sympy','sklearn',
    'matplotlib','seaborn',
    'PIL','pillow',
    'notebook','jupyter','IPython',
    'numba','h5py','kiwisolver',
    'grpc','google',
    'boto3','botocore','s3transfer',
    # tests
    'numpy.tests','pandas.tests','matplotlib.tests'
]

# Para asegurar que encuentre tus módulos locales
pathex = [os.path.abspath('.')]

# =========================
# App principal (Main.py)
# =========================
a_app = Analysis(
    ['Main.py'],
    pathex=pathex,
    binaries=[],
    datas=[('ico.ico', '.')],   # agrega otros recursos si usás (templates, etc.)
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=common_excludes,
    noarchive=False,
    optimize=0,  # mantener 0 si usás numpy/pandas
)

pyz_app = PYZ(
    a_app.pure,
    a_app.zipped_data,
    cipher=block_cipher,
)

exe_app = EXE(
    pyz_app,
    a_app.scripts,
    [],
    exclude_binaries=True,
    name='HelpDeskManagerApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                  # ← evita fallos si no tenés UPX
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['ico.ico'],
)

# =========================================
# Runner de actualización (update_runner.py)
# =========================================
a_upd = Analysis(
    ['update_runner.py'],
    pathex=pathex,
    binaries=[],
    datas=[('ico.ico', '.')],   # mismo ícono para la ventana del runner
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=common_excludes,
    noarchive=False,
    optimize=0,
)

pyz_upd = PYZ(
    a_upd.pure,
    a_upd.zipped_data,
    cipher=block_cipher,
)

exe_upd = EXE(
    pyz_upd,
    a_upd.scripts,
    [],
    exclude_binaries=True,
    name='HelpDeskUpdater',     # ← nombre del ejecutable del runner
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                  # ← idem
    console=False,              # ventana Tkinter (sin consola)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['ico.ico'],
)

# =========================
# COLLECT ambos ejecutables
# =========================
coll = COLLECT(
    exe_app,
    exe_upd,                    # incluir runner en la misma salida
    a_app.binaries,
    a_upd.binaries,
    a_app.zipfiles,             # ← importante
    a_upd.zipfiles,             # ← importante
    a_app.datas,
    a_upd.datas,
    strip=False,
    upx=False,                  # por coherencia
    upx_exclude=[],
    name='HelpDeskManagerApp',
)
