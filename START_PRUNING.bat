@echo off
title BN Easy Pruner Launcher
cls

echo ==========================================
echo   BN EASY PRUNER - STEP 1: GENERATE KEEP
echo ==========================================
echo.

:: Run the GUI Coordinate Generator
python bn_keep_gen.py

if not exist "keep.txt" (
    echo.
    echo [ERROR] keep.txt was not found. 
    echo Please enter coordinates and click the button in the GUI.
    pause
    exit /b
)

echo.
echo ==========================================
echo   BN EASY PRUNER - STEP 2: PRUNING DB
echo ==========================================
echo Target: map.sqlite3
echo Source: keep.txt
echo.

:: Run the original overmap_pruner engine with recommended arguments
:: Using --span 180 as default for BN
python overmap_pruner.py map.sqlite3 --keep-file keep.txt --span 180

if %errorlevel% neq 0 (
    echo.
    echo [ALERT] Pruning process failed. Please check the error message above.
) else (
    echo.
    echo [SUCCESS] Pruning complete. 'map.sqlite3.bak' has been created.
)

echo.
echo Press any key to exit.
pause >nul