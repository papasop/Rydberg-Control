$ErrorActionPreference = "Stop"

$PythonBin = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { "python" }
& $PythonBin reproduce.py --protocol all @args
exit $LASTEXITCODE
