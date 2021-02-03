$dir = $Env:Temp
$urlR = "https://cran.r-project.org/bin/windows/base/old/4.0.4/R-4.0.4-win.exe"
$outputR = "$dir\R-win.exe"
$wcR = New-Object System.Net.WebClient
$wcR.DownloadFile($urlR, $outputR)
Start-Process -FilePath $outputR -ArgumentList "/S /v/qn"
