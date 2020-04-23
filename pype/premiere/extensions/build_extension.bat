@echo off
rem You need https://github.com/Adobe-CEP/CEP-Resources/raw/master/ZXPSignCMD/4.1.1/win64/ZXPSignCmd.exe



set pwd="12PPROext581"
rem echo ">>> updating dependencies"
rem cd com.pype
rem npm install
rem cd ..

echo ">>> creating certificate ..."
.\ZXPSignCmd -selfSignedCert CZ Prague OrbiTools "Signing robot" %pwd% certificate.p12
echo ">>> building com.pype"
.\ZXPSignCmd -sign com.pype/ pype.zxp certificate.p12 %pwd%
echo ">>> building com.pype.rename"
.\ZXPSignCmd -sign com.pype.rename/ pype_rename.zxp certificate.p12 %pwd%