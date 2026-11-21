@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo === Auditoria Yukón V6 ===
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
for %%P in (aleatoria espacial20 espacial30 espacial30_buffer3) do (
 for %%R in (0 1) do (
  echo Reentrenamiento %%P repeticion %%R
  set "YUKON_MODE=run"
  set "YUKON_PROTOCOL=%%P"
  set "YUKON_REPLICA=%%R"
  call :execute
  if errorlevel 1 exit /b 1
 )
)
set "YUKON_MODE=aggregate"
python 02_codigo\analisis_final.py
if errorlevel 1 exit /b 1
python 02_codigo\calibracion_espacial_anidada.py
if errorlevel 1 exit /b 1
python 02_codigo\auditar_sensibilidad_v5.py
if errorlevel 1 exit /b 1
python 02_codigo\crear_documentos.py
if errorlevel 1 exit /b 1
python 02_codigo\verificar_entregables.py
pause
exit /b 0
:execute
python 02_codigo\analisis_final.py
exit /b %errorlevel%
