<#
.SYNOPSIS
    ExamApp Dataset Pipeline PowerShell Runner
.DESCRIPTION
    Convenient wrapper to resume dataset generation, check progress,
    generate specific question types, and export training data for model fine-tuning.
.EXAMPLE
    .\run_pipeline.ps1                 # Resumes generation from where it stopped
    .\run_pipeline.ps1 -DryRun         # Check progress without generating
    .\run_pipeline.ps1 -ExportTraining # Exports training datasets for LLM SFT
#>

param(
    [switch]$Status,
    [switch]$WatchLog,
    [switch]$DryRun,
    [switch]$RetryFailed,
    [switch]$ExportTraining,
    [switch]$ValidateOnly,
    [string]$Board = "",
    [string]$Class = "",
    [string]$Subject = "",
    [string]$Chapter = "",
    [string]$QuestionType = "",
    [int]$Workers = 3,
    [int]$MaxFailedRetries = 5
)

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "ExamApp Dataset Pipeline (Class 11 & 12 / 1st & 2nd PUC)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

if ($WatchLog) {
    Write-Host "`nStreaming dataset_generator.log in real time (Ctrl+C to exit)..." -ForegroundColor Yellow
    Get-Content dataset_generator.log -Wait -Tail 20
    exit
}

if ($ExportTraining) {
    Write-Host "`nExporting fine-tuning training datasets..." -ForegroundColor Yellow
    python train_dataset_exporter.py
    exit
}

if ($ValidateOnly) {
    Write-Host "`nValidating and repairing local dataset files..." -ForegroundColor Yellow
    python -c "from dataset_generator import run_pipeline; print(run_pipeline(mode='validate_only'))"
    exit
}

if ($Status) {
    python check_status.py
    exit
}

$cmdArgs = @("generate_dataset.py")

if ($DryRun) { $cmdArgs += "--dry-run" }
if ($RetryFailed) { $cmdArgs += "--retry-failed" }
if ($Board) { $cmdArgs += @("--board", $Board) }
if ($Class) { $cmdArgs += @("--class", $Class) }
if ($Subject) { $cmdArgs += @("--subject", $Subject) }
if ($Chapter) { $cmdArgs += @("--chapter", $Chapter) }
if ($QuestionType) { $cmdArgs += @("--question-type", $QuestionType) }
if ($Workers) { $cmdArgs += @("--workers", "$Workers") }
if ($MaxFailedRetries) { $cmdArgs += @("--max-failed-retries", "$MaxFailedRetries") }

Write-Host "Executing: python $($cmdArgs -join ' ')" -ForegroundColor Green
python @cmdArgs

