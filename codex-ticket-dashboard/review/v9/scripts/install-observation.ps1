[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Manifest,
    [Parameter(Mandatory)][ValidatePattern('^[a-f0-9]{64}$')][string]$ManifestSha256,
    [ValidateSet('Preflight', 'Apply', 'Rollback')][string]$Mode = 'Preflight',
    [switch]$ExclusiveWritersConfirmed
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$taskRoot = [IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))
$taskRuntimeParent = Join-Path $taskRoot '.omo\probes\correction-runtime-20260908'
$taskSid = [Security.Principal.WindowsIdentity]::GetCurrent().User
function Get-Digest([string]$Path) {
    if (-not [IO.File]::Exists($Path)) { return 'ABSENT' }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Get-PathKey([string]$Path) {
    $hash = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($Path.ToLowerInvariant())))).Replace('-', '').ToLowerInvariant() }
    finally { $hash.Dispose() }
}
function Get-BytesDigest([byte[]]$Bytes) {
    $hash = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hash.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant() }
    finally { $hash.Dispose() }
}
function Assert-PreservedAccess([string]$Path, [string]$OriginalSddl) {
    $sections = [Security.AccessControl.AccessControlSections]::Access -bor [Security.AccessControl.AccessControlSections]::Owner -bor [Security.AccessControl.AccessControlSections]::Group
    $saved = [Security.AccessControl.RawSecurityDescriptor]::new($OriginalSddl)
    $current = [Security.AccessControl.RawSecurityDescriptor]::new((Get-Acl -LiteralPath $Path).Sddl)
    foreach ($descriptor in @($saved, $current)) {
        $descriptor.SetFlags($descriptor.ControlFlags -band (-bnot [Security.AccessControl.ControlFlags]::DiscretionaryAclAutoInherited))
    }
    if ($saved.GetSddlForm($sections) -ne $current.GetSddlForm($sections)) { throw 'INSTALL_ACCESS_ACL_DRIFT' }
}
function Restore-PreservedAccess([string]$Path, [string]$OriginalSddl) {
    $saved = [Security.AccessControl.RawSecurityDescriptor]::new($OriginalSddl)
    $current = [Security.AccessControl.RawSecurityDescriptor]::new((Get-Acl -LiteralPath $Path).Sddl)
    $identitySections = [Security.AccessControl.AccessControlSections]::Owner -bor [Security.AccessControl.AccessControlSections]::Group
    if ($saved.GetSddlForm($identitySections) -ne $current.GetSddlForm($identitySections)) { throw 'INSTALL_ACCESS_OWNER_GROUP_DRIFT' }
    $access = New-Object Security.AccessControl.FileSecurity
    $access.SetSecurityDescriptorSddlForm($OriginalSddl, [Security.AccessControl.AccessControlSections]::Access)
    if ($PSVersionTable.PSVersion.Major -ge 7) { [IO.FileSystemAclExtensions]::SetAccessControl([IO.FileInfo]::new($Path), $access) }
    else { [IO.File]::SetAccessControl($Path, $access) }
    Assert-PreservedAccess $Path $OriginalSddl
}
function Assert-LocalPath([string]$Path) {
    if ($Path -notmatch '^[A-Za-z]:[\\/]' -or $Path.Substring(2).Contains(':')) { throw 'INSTALL_PATH_INVALID' }
    $resolved = [IO.Path]::GetFullPath($Path)
    if ($resolved.TrimEnd('\') -ne $Path.Replace('/', '\').TrimEnd('\')) { throw 'INSTALL_PATH_NOT_CANONICAL' }
    $cursor = $resolved
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            $item = Get-Item -LiteralPath $cursor -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'INSTALL_REPARSE_REJECTED' }
        }
        $cursor = Split-Path $cursor -Parent
    }
    return $resolved
}
function Assert-OwnerOnly([string]$Path) {
    $acl = Get-Acl -LiteralPath $Path
    if (-not $acl.AreAccessRulesProtected -or $acl.GetOwner([Security.Principal.SecurityIdentifier]) -ne $taskSid) { throw 'INSTALL_ACL_INVALID' }
    $rules = @($acl.Access)
    if ($rules.Count -ne 1) { throw 'INSTALL_ACL_INVALID' }
    $rule = $rules[0]
    if ($rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]) -ne $taskSid -or
        $rule.AccessControlType -ne 'Allow' -or
        ($rule.FileSystemRights -band [Security.AccessControl.FileSystemRights]::FullControl) -ne [Security.AccessControl.FileSystemRights]::FullControl) { throw 'INSTALL_ACL_INVALID' }
}
function Set-OwnerOnly([string]$Path) {
    $item = Get-Item -LiteralPath $Path -Force
    if ($item.PSIsContainer) {
        $acl = New-Object Security.AccessControl.DirectorySecurity
    } else {
        $acl = New-Object Security.AccessControl.FileSecurity
    }
    $acl.SetOwner($taskSid)
    $acl.SetAccessRuleProtection($true, $false)
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($taskSid, 'FullControl', 'Allow'))
    if ($PSVersionTable.PSVersion.Major -ge 7) {
        if ($item.PSIsContainer) { [IO.FileSystemAclExtensions]::SetAccessControl([IO.DirectoryInfo]::new($Path), $acl) }
        else { [IO.FileSystemAclExtensions]::SetAccessControl([IO.FileInfo]::new($Path), $acl) }
    } else {
        if ($item.PSIsContainer) { [IO.Directory]::SetAccessControl($Path, $acl) }
        else { [IO.File]::SetAccessControl($Path, $acl) }
    }
    Assert-OwnerOnly $Path
}
function Open-PrivateFile([string]$Path, [IO.FileMode]$Mode = [IO.FileMode]::CreateNew) {
    if ([IO.File]::Exists($Path)) { Assert-OwnerOnly $Path }
    $acl = New-Object Security.AccessControl.FileSecurity
    $acl.SetOwner($taskSid)
    $acl.SetAccessRuleProtection($true, $false)
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($taskSid, 'FullControl', 'Allow'))
    if ($PSVersionTable.PSVersion.Major -ge 7) {
        return [IO.FileSystemAclExtensions]::Create([IO.FileInfo]::new($Path), $Mode, [Security.AccessControl.FileSystemRights]::FullControl, [IO.FileShare]::None, 4096, [IO.FileOptions]::None, $acl)
    }
    return [IO.FileStream]::new($Path, $Mode, [Security.AccessControl.FileSystemRights]::FullControl, [IO.FileShare]::None, 4096, [IO.FileOptions]::None, $acl)
}
function Write-PrivateText([string]$Path, [string]$Text) {
    Write-PrivateBytes $Path ([Text.Encoding]::UTF8.GetBytes($Text))
}
function Write-PrivateBytes([string]$Path, [byte[]]$Bytes) {
    $stream = Open-PrivateFile $Path ([IO.FileMode]::Create)
    try { $stream.Write($Bytes, 0, $Bytes.Length); $stream.Flush($true) }
    finally { $stream.Dispose() }
}
function Copy-PrivateFile([string]$Source, [string]$Target) {
    $output = Open-PrivateFile $Target
    try {
        $input = [IO.File]::OpenRead($Source)
        try { $input.CopyTo($output); $output.Flush($true) } finally { $input.Dispose() }
    } finally { $output.Dispose() }
}
function New-PrivateDirectory([string]$Path) {
    [void](Assert-LocalPath $Path)
    if ([IO.Directory]::Exists($Path)) { Assert-OwnerOnly $Path; return }
    $parent = Split-Path $Path -Parent
    New-PrivateDirectory $parent
    $acl = New-Object Security.AccessControl.DirectorySecurity
    $acl.SetOwner($taskSid)
    $acl.SetAccessRuleProtection($true, $false)
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($taskSid, 'FullControl', 'Allow'))
    if ($PSVersionTable.PSVersion.Major -ge 7) { [IO.FileSystemAclExtensions]::Create([IO.DirectoryInfo]::new($Path), $acl) }
    else { [void][IO.Directory]::CreateDirectory($Path, $acl) }
    Assert-OwnerOnly $Path
}
$taskManifestPath = Assert-LocalPath ([IO.Path]::GetFullPath($Manifest))
$taskManifestBytes = [IO.File]::ReadAllBytes($taskManifestPath)
if ((Get-BytesDigest $taskManifestBytes) -ne $ManifestSha256) { throw 'INSTALL_MANIFEST_DRIFT' }
$taskPlan = ([Text.UTF8Encoding]::new($false, $true).GetString($taskManifestBytes)).TrimStart([char]0xfeff) | ConvertFrom-Json
if ($taskPlan.schema_version -ne 1 -or $taskPlan.status -ne 'SOURCE_READY' -or
    $taskPlan.project_root -ne $taskRoot -or $taskPlan.project_id -ne 'prj_codex_ticket_dashboard' -or
    $taskPlan.purpose -notin @('IMMUTABLE_RUNTIME', 'PRODUCT_ACTIVATION', 'INSTALLER_SELF_CHECK')) { throw 'INSTALL_RELEASE_NOT_READY' }
$taskRuntime = Assert-LocalPath $taskPlan.runtime_root
if ((Split-Path $taskRuntime -Parent) -ne $taskRuntimeParent) { throw 'INSTALL_RUNTIME_OUT_OF_SCOPE' }
$taskSynthetic = $taskPlan.purpose -eq 'INSTALLER_SELF_CHECK'
if ($taskSynthetic -and $taskRuntime -ne (Join-Path $taskRuntimeParent 'installer-check-20260908')) { throw 'INSTALL_CHECK_ROOT_INVALID' }
$taskReceipt = Join-Path $taskRuntime 'installation'
$taskAllowed = @(
    (Join-Path $taskRoot 'config.toml'),
    (Join-Path $taskRoot 'docs\registration\prj_codex_ticket_dashboard-20260908-v1.json'),
    (Join-Path $taskRoot '.codex\hooks.json'),
    (Join-Path $taskRoot '.codex\config.toml'),
    (Join-Path $taskRoot '.omo\probes\correction-host-20260907\.codex\hooks.json'),
    (Join-Path $taskRoot '.omo\probes\correction-host-20260907\.codex\config.toml')
)
$taskFiles = @($taskPlan.files)
if ($taskFiles.Count -eq 0) { throw 'INSTALL_EMPTY_RELEASE' }
$taskSeen = @{}
$taskBytes = 0L
foreach ($file in $taskFiles) {
    $target = Assert-LocalPath $file.target
    if ($Mode -ne 'Rollback') { $source = Assert-LocalPath $file.source }
    $inRuntime = $target.StartsWith($taskRuntime + '\', [StringComparison]::OrdinalIgnoreCase)
    if ((-not $inRuntime -and $target -notin $taskAllowed) -or $target.StartsWith($taskReceipt + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'INSTALL_TARGET_OUT_OF_SCOPE' }
    if ($taskSynthetic -and $target -notin @((Join-Path $taskRuntime 'synthetic\existing.txt'), (Join-Path $taskRuntime 'synthetic\new.txt'))) { throw 'INSTALL_CHECK_TARGET_INVALID' }
    if ($taskPlan.purpose -eq 'IMMUTABLE_RUNTIME' -and -not $inRuntime) { throw 'INSTALL_RUNTIME_EXTERNAL_TARGET' }
    if ($taskSeen.ContainsKey($target)) { throw 'INSTALL_DUPLICATE_TARGET' }
    $taskSeen[$target] = $true
    if ($target.EndsWith('.pth', [StringComparison]::OrdinalIgnoreCase)) { throw 'INSTALL_PTH_FORBIDDEN' }
    if ($file.sha256 -notmatch '^[a-f0-9]{64}$' -or $file.before_sha256 -notmatch '^(ABSENT|[a-f0-9]{64})$') { throw 'INSTALL_HASH_INVALID' }
    if ($Mode -ne 'Rollback' -and (Get-Digest $source) -ne $file.sha256) { throw 'INSTALL_SOURCE_DRIFT' }
    if ($file.acl -notin @('owner-only', 'preserve') -or ($inRuntime -and -not $taskSynthetic -and $file.acl -ne 'owner-only')) { throw 'INSTALL_ACL_MODE_INVALID' }
    if ($file.rollback -notin @('restore', 'retain')) { throw 'INSTALL_ROLLBACK_MODE_INVALID' }
    if ($inRuntime -and -not $taskSynthetic -and ($file.before_sha256 -ne 'ABSENT' -or $file.rollback -ne 'retain')) { throw 'INSTALL_RUNTIME_IMMUTABLE' }
    if ($taskSynthetic -and (($file.before_sha256 -eq 'ABSENT' -and $file.acl -ne 'owner-only') -or ($file.before_sha256 -ne 'ABSENT' -and $file.acl -ne 'preserve'))) { throw 'INSTALL_CHECK_ACL_INVALID' }
    if (-not $inRuntime -and $file.before_sha256 -ne 'ABSENT' -and $file.acl -ne 'preserve') { throw 'INSTALL_EXISTING_ACL_PRESERVE_REQUIRED' }
    if ($target -eq $taskAllowed[1] -and ($file.before_sha256 -ne 'ABSENT' -or $file.rollback -ne 'retain')) { throw 'INSTALL_REGISTRATION_IMMUTABLE' }
    if (-not $inRuntime -and $file.before_sha256 -eq 'ABSENT' -and $file.acl -ne 'owner-only') { throw 'INSTALL_NEW_FILE_ACL_REQUIRED' }
    if ($Mode -ne 'Rollback' -and (Get-Digest $target) -ne $file.before_sha256) { throw 'INSTALL_TARGET_DRIFT' }
    if ($Mode -ne 'Rollback') { $taskBytes += (Get-Item -LiteralPath $source).Length }
}
if ($Mode -eq 'Preflight') {
    [pscustomobject]@{ status='PREFLIGHT_ONLY'; files=$taskFiles.Count; bytes=$taskBytes; manifest_sha256=$ManifestSha256 } | ConvertTo-Json -Compress
    return
}
if (-not $ExclusiveWritersConfirmed) { throw 'INSTALL_EXCLUSIVE_WRITERS_REQUIRED' }
if (-not ('ObservationInstallNamespace' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32.SafeHandles;
public static class ObservationInstallNamespace {
    [StructLayout(LayoutKind.Sequential)]
    private struct AttributeTag { public uint Attributes; public uint ReparseTag; }
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, ExactSpelling=true, SetLastError=true)]
    private static extern SafeFileHandle CreateFileW(string path, uint access, uint share, IntPtr security, uint disposition, uint flags, IntPtr template);
    [DllImport("kernel32.dll", SetLastError=true)]
    private static extern bool GetFileInformationByHandleEx(SafeFileHandle handle, int informationClass, out AttributeTag info, uint size);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, ExactSpelling=true, SetLastError=true)]
    private static extern uint GetFinalPathNameByHandleW(SafeFileHandle handle, StringBuilder path, uint size, uint flags);
    public static SafeFileHandle HoldDirectory(string path) {
        SafeFileHandle handle = CreateFileW(path, 0x80, 1, IntPtr.Zero, 3, 0x02200000, IntPtr.Zero);
        if (handle.IsInvalid) { handle.Dispose(); throw new IOException("INSTALL_NAMESPACE_OPEN_FAILED"); }
        AttributeTag info;
        StringBuilder final = new StringBuilder(32768);
        uint length = GetFinalPathNameByHandleW(handle, final, 32768, 0);
        if (!GetFileInformationByHandleEx(handle, 9, out info, 8) || (info.Attributes & 0x10) == 0 ||
            (info.Attributes & 0x400) != 0 || length == 0 || length >= 32768 ||
            !String.Equals(final.ToString(), "\\\\?\\" + path, StringComparison.OrdinalIgnoreCase)) {
            handle.Dispose(); throw new IOException("INSTALL_NAMESPACE_IDENTITY_INVALID");
        }
        return handle;
    }
}
'@
}
$taskNamespaceHandles = [Collections.Generic.Dictionary[string, Microsoft.Win32.SafeHandles.SafeFileHandle]]::new([StringComparer]::OrdinalIgnoreCase)
function Hold-ParentNamespace([string]$Path) {
    $ancestors = [Collections.Generic.Stack[string]]::new()
    $cursor = $Path
    while ($cursor) { $ancestors.Push($cursor); $cursor = Split-Path $cursor -Parent }
    foreach ($ancestor in $ancestors) {
        if (-not $taskNamespaceHandles.ContainsKey($ancestor)) {
            $taskNamespaceHandles.Add($ancestor, [ObservationInstallNamespace]::HoldDirectory($ancestor))
        }
    }
}
$taskLock = $null
try {
Hold-ParentNamespace $taskRuntimeParent
Assert-OwnerOnly $taskRuntimeParent
if ($Mode -eq 'Rollback') { Assert-OwnerOnly $taskRuntime; Assert-OwnerOnly $taskReceipt }
else { New-PrivateDirectory $taskRuntime; New-PrivateDirectory $taskReceipt }
Hold-ParentNamespace $taskReceipt
$taskLockPath = Join-Path $taskReceipt 'operation.lock'
$taskLock = Open-PrivateFile $taskLockPath ([IO.FileMode]::OpenOrCreate)
    $taskProtectedManifest = Join-Path $taskReceipt 'manifest.json'
    if ([IO.File]::Exists($taskProtectedManifest)) {
        Assert-OwnerOnly $taskProtectedManifest
        if ((Get-Digest $taskProtectedManifest) -ne $ManifestSha256) { throw 'INSTALL_PROTECTED_MANIFEST_DRIFT' }
    } elseif ($Mode -eq 'Rollback') { throw 'ROLLBACK_MANIFEST_COPY_MISSING' }
    else {
        $manifestStage = Join-Path $taskReceipt ('manifest.' + [Guid]::NewGuid().ToString('N') + '.staged')
        Write-PrivateBytes $manifestStage $taskManifestBytes
        if ((Get-Digest $manifestStage) -ne $ManifestSha256) { throw 'INSTALL_MANIFEST_COPY_DRIFT' }
        [IO.File]::Move($manifestStage, $taskProtectedManifest)
    }
    $taskReleasePin = Join-Path $taskReceipt 'manifest.sha256'
    if ([IO.File]::Exists($taskReleasePin)) {
        if ([IO.File]::ReadAllText($taskReleasePin) -ne $ManifestSha256) { throw 'INSTALL_RECEIPT_MANIFEST_DRIFT' }
    } elseif ($Mode -eq 'Rollback') { throw 'ROLLBACK_RECEIPT_MISSING' }
    else {
        Write-PrivateText $taskReleasePin $ManifestSha256
    }
    $taskIndex = 0
    if ($Mode -eq 'Rollback') { [array]::Reverse($taskFiles) }
    foreach ($file in $taskFiles) {
        $target = $file.target
        $key = Get-PathKey $target
        $backup = Join-Path $taskReceipt ($key + '.before')
        $aclBackup = Join-Path $taskReceipt ($key + '.acl')
        $marker = Join-Path $taskReceipt ($key + '.applied')
        if ($Mode -eq 'Rollback' -and ($file.rollback -eq 'retain' -or (-not [IO.File]::Exists($marker) -and -not [IO.File]::Exists($backup)))) { continue }
        $parent = Split-Path $target -Parent
        if ($Mode -ne 'Rollback' -and $target.StartsWith($taskRuntime + '\', [StringComparison]::OrdinalIgnoreCase)) { New-PrivateDirectory $parent }
        Hold-ParentNamespace $parent
        [void](Assert-LocalPath $target)
        if ($taskSynthetic -and [IO.File]::Exists($target)) { Assert-OwnerOnly $target }
        if ($Mode -eq 'Rollback') {
            if ((Get-Digest $target) -eq $file.before_sha256) { continue }
            if ((Get-Digest $target) -ne $file.sha256) { throw 'ROLLBACK_TARGET_DRIFT' }
            if ($file.before_sha256 -eq 'ABSENT') {
                [IO.File]::Delete($target)
            } else {
                if ((Get-Digest $backup) -ne $file.before_sha256) { throw 'ROLLBACK_BACKUP_DRIFT' }
                $restore = Join-Path $taskReceipt ($key + '.' + [Guid]::NewGuid().ToString('N') + '.restore')
                Copy-PrivateFile $backup $restore
                if ((Get-Digest $restore) -ne $file.before_sha256 -or (Get-Digest $target) -ne $file.sha256) { throw 'ROLLBACK_RECHECK_DRIFT' }
                [IO.File]::Replace($restore, $target, [NullString]::Value)
                $originalSddl = [IO.File]::ReadAllText($aclBackup)
                Restore-PreservedAccess $target $originalSddl
            }
            if ((Get-Digest $target) -ne $file.before_sha256) { throw 'ROLLBACK_VERIFY_FAILED' }
            continue
        }
        if ([IO.File]::Exists($marker) -or [IO.File]::Exists($backup)) { throw 'INSTALL_PRIOR_ATTEMPT_PRESENT' }
        if ((Get-Digest $target) -ne $file.before_sha256 -or (Get-Digest $file.source) -ne $file.sha256) { throw 'INSTALL_RECHECK_DRIFT' }
        $temporary = Join-Path $taskReceipt ($key + '.staged')
        Copy-PrivateFile $file.source $temporary
        if ((Get-Digest $temporary) -ne $file.sha256) { throw 'INSTALL_COPY_DRIFT' }
        if ($file.before_sha256 -ne 'ABSENT') {
            Write-PrivateText $aclBackup (Get-Acl -LiteralPath $target).Sddl
            Copy-PrivateFile $target $backup
            if ((Get-Digest $backup) -ne $file.before_sha256 -or (Get-Digest $target) -ne $file.before_sha256) { throw 'INSTALL_BACKUP_DRIFT' }
            [IO.File]::Replace($temporary, $target, [NullString]::Value)
            Restore-PreservedAccess $target ([IO.File]::ReadAllText($aclBackup))
        } else {
            Write-PrivateText $marker 'NEW_FILE_INTENT'
            [IO.File]::Move($temporary, $target)
        }
        if ($file.acl -eq 'owner-only') { Set-OwnerOnly $target }
        if ((Get-Digest $target) -ne $file.sha256) { throw 'INSTALL_VERIFY_FAILED' }
        Write-PrivateText $marker $file.sha256
        $taskIndex++
    }
    [pscustomobject]@{ status=$Mode.ToUpperInvariant() + '_FILES_COMPLETE'; manifest_sha256=$ManifestSha256; files=$taskFiles.Count; bytes=$taskBytes; trust='NOT_CHANGED'; processes='NOT_CHANGED' } | ConvertTo-Json -Compress
} finally {
    if ($null -ne $taskLock) { $taskLock.Dispose() }
    foreach ($handle in $taskNamespaceHandles.Values) { $handle.Dispose() }
}
