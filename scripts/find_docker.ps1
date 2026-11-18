$paths = @('C:\Program Files\Docker\Docker\Docker Desktop.exe',
           "$env:LOCALAPPDATA\Docker\Docker Desktop.exe")
foreach ($p in $paths) { if (Test-Path $p) { Write-Output "FOUND: $p" } }
Get-ChildItem 'C:\Program Files','C:\Program Files (x86)' -Filter 'Docker Desktop.exe' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 3 -ExpandProperty FullName
Write-Output '--- processes ---'
Get-Process | Where-Object { $_.ProcessName -match 'Docker|docker' } | Select-Object ProcessName,Id | Format-Table -AutoSize
