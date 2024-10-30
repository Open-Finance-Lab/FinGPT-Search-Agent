$curDir=$PSScriptRoot
$extensionPath= Join-Path $curDir "ChatBot-Fin\Extension-ChatBot-Fin\src"

$paths = @(
    "C:\Program Files\Google\Chrome\Application",
    "C:\Program Files (x86)\Google\Chrome\Application"
)

$foundPaths = @()

$ChromePath

foreach ($path in $paths) {
    if (Test-Path $path) {
        $ChromePath = $path
    }
}

#load extension
Write-Host $extensionPath
Start-Process $ChromePath "chrome.exe" -ArgumentList "--load-extension=$extensionPath"
Write-Host "FinGPT extension loaded onto Chrome"
