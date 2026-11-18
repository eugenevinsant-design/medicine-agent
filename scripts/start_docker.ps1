$exe = "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe"
if (-not (Test-Path $exe)) { Write-Output "NOT_FOUND: $exe"; exit 1 }
Start-Process $exe
Write-Output "STARTED: $exe"
for ($i = 1; $i -le 36; $i++) {
  Start-Sleep -Seconds 5
  docker info *> $null
  if ($LASTEXITCODE -eq 0) { Write-Output "DOCKER_READY after $($i*5)s"; exit 0 }
}
Write-Output 'DOCKER_NOT_READY'
exit 1
