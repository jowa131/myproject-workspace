[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$installerPath = Join-Path $projectRoot 'scripts\install-observation.ps1'
$sourceText = Get-Content -LiteralPath $installerPath -Raw -Encoding UTF8
$start = $sourceText.IndexOf('function Assert-PreservedAccess', [StringComparison]::Ordinal)
$end = $sourceText.IndexOf('function Set-OwnerOnly', [StringComparison]::Ordinal)
if ($start -lt 0 -or $end -le $start) { throw 'TEST_INSTALLER_ACL_HELPERS_NOT_FOUND' }
Invoke-Expression $sourceText.Substring($start, $end - $start)

$testRoot = Join-Path ([IO.Path]::GetTempPath()) ('codex-installer-acl-' + [Guid]::NewGuid().ToString('N'))
$targetRoot = Join-Path $testRoot 'target'
$receiptRoot = Join-Path $testRoot 'receipt'
$target = Join-Path $targetRoot 'existing.txt'
$staged = Join-Path $receiptRoot 'staged.txt'
[void][IO.Directory]::CreateDirectory($testRoot)
[void][IO.Directory]::CreateDirectory($targetRoot)
[void][IO.Directory]::CreateDirectory($receiptRoot)
try {
    [IO.File]::WriteAllText($target, 'before', [Text.UTF8Encoding]::new($false))
    $originalAcl = Get-Acl -LiteralPath $target
    if ($originalAcl.AreAccessRulesProtected) { throw 'TEST_PRECONDITION_TARGET_NOT_INHERITED' }
    $originalSddl = $originalAcl.Sddl
    $originalDescriptor = [Security.AccessControl.RawSecurityDescriptor]::new($originalSddl)
    if ($originalDescriptor.DiscretionaryAcl.Count -eq 0) { throw 'TEST_PRECONDITION_DACL_EMPTY' }

    $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User
    $stagedAcl = New-Object Security.AccessControl.FileSecurity
    $stagedAcl.SetOwner($sid)
    $stagedAcl.SetAccessRuleProtection($true, $false)
    $stagedAcl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($sid, 'FullControl', 'Allow'))
    if ($PSVersionTable.PSVersion.Major -ge 7) {
        $stream = [IO.FileSystemAclExtensions]::Create([IO.FileInfo]::new($staged), [IO.FileMode]::CreateNew, [Security.AccessControl.FileSystemRights]::FullControl, [IO.FileShare]::None, 4096, [IO.FileOptions]::None, $stagedAcl)
        try {
            $bytes = [Text.UTF8Encoding]::new($false).GetBytes('after')
            $stream.Write($bytes, 0, $bytes.Length)
            $stream.Flush($true)
        } finally { $stream.Dispose() }
    } else {
        [IO.File]::WriteAllText($staged, 'after', [Text.UTF8Encoding]::new($false))
        [IO.File]::SetAccessControl($staged, $stagedAcl)
    }

    [IO.File]::Replace($staged, $target, [NullString]::Value)
    $emptyAccess = New-Object Security.AccessControl.FileSecurity
    $emptyAccess.SetSecurityDescriptorSddlForm('D:P', [Security.AccessControl.AccessControlSections]::Access)
    if ($PSVersionTable.PSVersion.Major -ge 7) { [IO.FileSystemAclExtensions]::SetAccessControl([IO.FileInfo]::new($target), $emptyAccess) }
    else { [IO.File]::SetAccessControl($target, $emptyAccess) }
    $replacedSddl = (Get-Acl -LiteralPath $target).Sddl
    if ($replacedSddl -ceq $originalSddl) { throw 'TEST_PRECONDITION_REPLACE_DID_NOT_DRIFT_ACL' }

    $driftDetected = $false
    try { Assert-PreservedAccess $target $originalSddl }
    catch {
        if ($_.Exception.Message -cne 'INSTALL_ACCESS_ACL_DRIFT') { throw }
        $driftDetected = $true
    }
    if (-not $driftDetected) { throw 'TEST_EXPECTED_ACL_DRIFT_NOT_DETECTED' }
    Restore-PreservedAccess $target $originalSddl
    Assert-PreservedAccess $target $originalSddl
    if ([IO.File]::ReadAllText($target) -cne 'after') { throw 'TEST_REPLACED_CONTENT_CHANGED' }
    Write-Output 'PASS: inherited Access restored after File.Replace; Owner and Group preserved'
} finally {
    if ([IO.File]::Exists($staged)) { [IO.File]::Delete($staged) }
    if ([IO.File]::Exists($target)) { [IO.File]::Delete($target) }
    if ([IO.Directory]::Exists($receiptRoot)) { [IO.Directory]::Delete($receiptRoot) }
    if ([IO.Directory]::Exists($targetRoot)) { [IO.Directory]::Delete($targetRoot) }
    if ([IO.Directory]::Exists($testRoot)) { [IO.Directory]::Delete($testRoot) }
}
