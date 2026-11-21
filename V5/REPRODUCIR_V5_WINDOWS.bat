@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Preparando Yukón PCA V5...
py -m pip install -r requirements.txt || exit /b 1
py 02_codigo\construir_v5.py || exit /b 1
py 02_codigo\cartografia_qgis.py || exit /b 1
py 02_codigo\verificar_v5.py || exit /b 1
py 02_codigo\crear_informe_v5.py || exit /b 1
echo Experimentos y GeoTIFF V5 generados. Para exportar Word a PDF use la opcion Guardar como PDF.
pause
