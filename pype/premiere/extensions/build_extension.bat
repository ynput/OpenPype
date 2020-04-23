@echo off
rem You need https://github.com/Adobe-CEP/CEP-Resources/raw/master/ZXPSignCMD/4.1.1/win64/ZXPSignCmd.exe

rem You need https://partners.adobe.com/exchangeprogram/creativecloud/support/exman-com-line-tool.html

rem !!! make sure you run windows power shell as admin

set pwd="12PPROext581"

echo ">>> creating certificate ..."
.\ZXPSignCmd -selfSignedCert CZ Prague OrbiTools "Signing robot" %pwd% certificate.p12
echo ">>> building com.pype"
.\ZXPSignCmd -sign com.pype/ pype.zxp certificate.p12 %pwd%
echo ">>> building com.pype.rename"
.\ZXPSignCmd -sign com.pype.rename/ pype_rename.zxp certificate.p12 %pwd%

echo ">>> installing com.pype"
.\ExManCmd.exe /install .\pype.zxp
echo ">>> installing com.pype.rename"
.\ExManCmd.exe /install .\pype_rename.zxp
