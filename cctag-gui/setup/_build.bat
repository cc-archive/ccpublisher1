set VERSION=%1
set PRODGUID=%2
set PACKGUID=%3

.\bin\candle build.wxs
.\bin\light build.wixobj
