set VERSION=%1
set PRODGUID=%2
set PACKGUID=%3

copy c:\python24\msvc*.dll ..\dist

.\bin\candle build.wxs
.\bin\light build.wixobj
