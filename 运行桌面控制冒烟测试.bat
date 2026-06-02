@echo off
setlocal
chcp 65001 >nul
for %%I in ("%~dp0.") do set "PROJECT_ROOT=%%~fI"
set "PYTHON_EXE=%DESKTOP_CONTROL_PY_PYTHON%"
set "UV_EXE=%DESKTOP_CONTROL_PY_UV%"

if not defined UV_EXE (
  for /f "delims=" %%I in ('where uv 2^>nul') do (
    set "UV_EXE=%%I"
    goto :uv_found
  )
)
:uv_found

if not defined PYTHON_EXE (
  for /f "delims=" %%I in ('where python 2^>nul') do (
    set "PYTHON_EXE=%%I"
    goto :python_found
  )
)
:python_found

echo [desktop-control-py] Running real-machine desktop smoke test...
if defined UV_EXE (
  if defined PYTHON_EXE (
    "%UV_EXE%" run --python "%PYTHON_EXE%" --project "%PROJECT_ROOT%" desktop-control-py smoke-test
  ) else (
    "%UV_EXE%" run --project "%PROJECT_ROOT%" desktop-control-py smoke-test
  )
  exit /b %errorlevel%
)

if defined PYTHON_EXE (
  "%PYTHON_EXE%" -m desktop_control_py smoke-test
  exit /b %errorlevel%
)

echo [desktop-control-py] Python or uv was not found. Install uv and Python 3.11+, or set DESKTOP_CONTROL_PY_UV / DESKTOP_CONTROL_PY_PYTHON. 1>&2
exit /b 1
