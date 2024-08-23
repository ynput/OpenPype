$PATH_OPENPYPE_DIR=$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath("$PSScriptRoot\..\..")

$PATH_ZXP_SIGN_SOFTWARE=$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath("$PSScriptRoot\zxp_sign_cmd\windows\win64\ZXPSignCmd.exe")
$PATH_ZXP_CERTIFICATE=$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath("$PSScriptRoot\sign_certificate.p12")

$HOSTS="aftereffects","photoshop"

foreach ($CURR_HOST in $HOSTS) {
    $HOST_PATH="$PATH_OPENPYPE_DIR\openpype\hosts\$CURR_HOST"
    $HOST_ZXP_SOURCE="$HOST_PATH\api\extension\"
    $HOST_ZXP_DEST="$HOST_PATH\api\extension.zxp"

    Write-Host "Generating ZXP for $CURR_HOST, destination: $HOST_ZXP_DEST"

    # First delete previous ZXP file (if exists)
    if (Test-Path $HOST_ZXP_DEST) {
        Remove-Item $HOST_ZXP_DEST -Force
    }

    # Generate and sign the ZXP file with the OpenPype certificate
    & $PATH_ZXP_SIGN_SOFTWARE -sign $HOST_ZXP_SOURCE $HOST_ZXP_DEST $PATH_ZXP_CERTIFICATE OpenPype
}
