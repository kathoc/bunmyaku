param(
    [switch]$Update,
    [string]$Tools = 'auto',
    [Alias('Home')][string]$InstallHome,
    [switch]$DryRun
)

# Keep preferences and temporary variables out of the caller's scope.
& {
    param(
        [switch]$Update,
        [string]$Tools = 'auto',
        [string]$InstallHome,
        [switch]$DryRun
    )
    $ErrorActionPreference = 'Stop'
    $pythonCommand = $null
    foreach ($candidate in @('python', 'python3', 'py')) {
        $command = Get-Command $candidate -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -eq $command) { continue }
        try {
            & $command.Source -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>$null
            if ($LASTEXITCODE -eq 0) {
                $pythonCommand = $command.Source
                break
            }
        } catch {
            continue
        }
    }
    if ($null -eq $pythonCommand) {
        throw 'Python 3.11 or newer is required. Install Python, then run this command again.'
    }

    $temporary = Join-Path ([System.IO.Path]::GetTempPath()) ('bunmyaku-' + [guid]::NewGuid().ToString('N'))
    $previousProtocol = [System.Net.ServicePointManager]::SecurityProtocol
    try {
        # Windows PowerShell 5.1 may otherwise negotiate an older TLS version.
        [System.Net.ServicePointManager]::SecurityProtocol = $previousProtocol -bor [System.Net.SecurityProtocolType]::Tls12
        New-Item -ItemType Directory -Path $temporary | Out-Null
        $archive = Join-Path $temporary 'source.zip'
        Write-Host 'Downloading bunmyaku from github.com/kathoc/bunmyaku ...'
        Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/kathoc/bunmyaku/archive/refs/heads/main.zip' -OutFile $archive -TimeoutSec 180
        $extract = @'
from pathlib import Path, PurePosixPath
import sys
import zipfile

root = Path(sys.argv[1])
destination = root / 'source'
prefix = 'bunmyaku-main/'
with zipfile.ZipFile(root / 'source.zip') as archive:
    selected = []
    seen = set()
    total = 0
    for entry in archive.infolist():
        if entry.is_dir() or not entry.filename.startswith(prefix):
            continue
        name = entry.filename[len(prefix):]
        if name != 'install.py' and not name.startswith('src/jlangbase/'):
            continue
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
            raise SystemExit('Unsafe archive path')
        if (entry.external_attr >> 16) & 0o170000 == 0o120000:
            raise SystemExit('Archive symlinks are not supported')
        normalized = str(path).casefold()
        if normalized in seen:
            raise SystemExit('Duplicate archive entry')
        seen.add(normalized)
        total += entry.file_size
        if total > 64 * 1024 * 1024 or len(seen) > 4096:
            raise SystemExit('Archive exceeds installation limits')
        selected.append((entry, path))
    if not {'install.py', 'src\\jlangbase\\distribution.py'} <= seen:
        # PurePosixPath retains forward slashes even on Windows.
        if not {'install.py', 'src/jlangbase/distribution.py'} <= seen:
            raise SystemExit('Archive is missing the installer')
    for entry, path in selected:
        target = destination.joinpath(*path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as output:
            output.write(archive.read(entry))
'@
        & $pythonCommand -c $extract $temporary
        if ($LASTEXITCODE -ne 0) { throw 'Could not unpack the installer.' }

        $installerArguments = @((Join-Path $temporary 'source/install.py'), '--tools', $Tools)
        if ($Update) { $installerArguments += '--update' }
        if ($DryRun) { $installerArguments += '--dry-run' }
        if ($InstallHome) { $installerArguments += @('--home', $InstallHome) }
        & $pythonCommand @installerArguments
        if ($LASTEXITCODE -ne 0) { throw "Installation failed (exit code $LASTEXITCODE)." }
    } finally {
        [System.Net.ServicePointManager]::SecurityProtocol = $previousProtocol
        if (Test-Path -LiteralPath $temporary) {
            Remove-Item -LiteralPath $temporary -Recurse -Force
        }
    }
} @PSBoundParameters
