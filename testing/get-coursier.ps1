$wc = New-Object System.Net.WebClient

$coursier_url = "https://github.com/coursier/coursier/releases/download/v2.0.5/cs-x86_64-pc-win32.exe"
$coursier_dest = "C:\coursier\cs.exe"
$coursier_hash ="d63d497f7805261e1cd657b8aaa626f6b8f7264cdb68219b2e6be9dd882033a9"

New-Item -Path "C:\" -Name "coursier" -ItemType "directory"
$wc.DownloadFile($coursier_url, $coursier_dest)
if ((Get-FileHash $coursier_dest -Algorithm SHA256).Hash -ne $coursier_hash) {
    throw "Invalid coursier file"
}
