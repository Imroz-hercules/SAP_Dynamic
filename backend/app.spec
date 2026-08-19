# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('public', 'public')]
binaries = []
hiddenimports = ['pyodbc', 'sqlalchemy', 'apscheduler', 'requests', 'flask_cors', 'routes.kpi_routes', 'routes.material_routes', 'routes.order_validation', 'routes.dev_seed', 'routes.process_orders', 'routes.scada_routes', 'routes.reports_routes', 'routes.sap_sync', 'routes.system_logs', 'routes.auth_routes', 'routes.sync_interval_routes', 'models.kpi_model', 'models.material_model', 'models.order_validation', 'models.order_model', 'models.shift_report', 'models.milling_kpi_snapshot', 'models.packing_kpi_snapshot', 'models.process_order', 'models.process_order_pg', 'services.sync_scheduler', 'services.create_scada_table', 'services.process_order_sync', 'services.auto_validator', 'services.sap_confirmation', 'services.kpi_service', 'services.sap_sync_service', 'database', 'init_sync_settings', 'app_scheduler']
tmp_ret = collect_all('routes')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('models')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('services')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
