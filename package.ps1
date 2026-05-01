$ErrorActionPreference = "Stop"

if (Test-Path build) {
    Remove-Item -LiteralPath build -Recurse -Force
}

if (Test-Path dist) {
    Remove-Item -LiteralPath dist -Recurse -Force
}

python -m PyInstaller app.spec
