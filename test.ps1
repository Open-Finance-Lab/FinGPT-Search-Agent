Stop-Process -Name chrome -Force
#Chrome stopped
Write-Host "Chrome stopped"

#load extension
chrome --load-extension=ChatBot-Fin/Extension-ChatBot-Fin/src
Write-Host "FinGPT extension loaded onto Chrome"