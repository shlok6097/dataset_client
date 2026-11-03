@echo off
setlocal
echo ======================================================================
echo ExamApp Dataset Pipeline - Control Center
echo ======================================================================
echo.
echo Select an option:
echo   1. Resume generation from where it stopped (Default)
echo   2. Check how many are processed till now (Status)
echo   3. Check progress dry-run (See completed vs pending tasks)
echo   4. Retry failed tasks only
echo   5. Export SFT model training datasets (ChatML / Alpaca)
echo   6. Validate and repair local dataset files
echo   7. Exit
echo.

set /p choice="Enter choice [1-7] (Default 1): "
if "%choice%"=="" set choice=1

if "%choice%"=="1" (
    echo.
    echo Resuming dataset generation with multi-account optimization...
    python generate_dataset.py --workers 3 %*
) else if "%choice%"=="2" (
    echo.
    python check_status.py
) else if "%choice%"=="3" (
    echo.
    echo Checking task progress dry-run...
    python generate_dataset.py --dry-run
) else if "%choice%"=="4" (
    echo.
    echo Retrying failed tasks...
    python generate_dataset.py --retry-failed
) else if "%choice%"=="5" (
    echo.
    echo Exporting fine-tuning training datasets...
    python train_dataset_exporter.py
) else if "%choice%"=="6" (
    echo.
    echo Validating and repairing local JSONL files...
    python -c "from dataset_generator import run_pipeline; print(run_pipeline(mode='validate_only'))"
) else (
    echo Exiting.
)

echo.
pause

