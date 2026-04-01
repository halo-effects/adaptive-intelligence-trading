# Use Get-Process and then read command line from environment
$procs = Get-Process python -ErrorAction SilentlyContinue
foreach ($p in $procs) {
    $id = $p.Id
    try {
        $wmi = [System.Management.ManagementObject]::new("Win32_Process.Handle='$id'")
        $cmd = $wmi['CommandLine']
        Write-Output "PID=$id CMD=$cmd"
    } catch {
        Write-Output "PID=$id CMD=(unable to read)"
    }
}
