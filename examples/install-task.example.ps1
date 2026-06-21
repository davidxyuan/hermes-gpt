<#
.SYNOPSIS
    Example scheduled-task installer for hermes-gpt.
.DESCRIPTION
    Creates a logon task that runs your local start script.
    Replace paths for your own machine before using.
#>

$TaskName = 'Hermes GPT Bridge'
$ScriptPath = 'C:\Users\<YOU>\hermes-gpt\start-hermes-gpt.ps1'
$WorkingDir = 'C:\Users\<YOU>\hermes-gpt'

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-ExecutionPolicy Bypass -NoProfile -File `"$ScriptPath`"" -WorkingDirectory $WorkingDir
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Description 'Example hermes-gpt start task.' -Force
