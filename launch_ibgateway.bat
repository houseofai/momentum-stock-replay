@echo off
REM Launch IB Gateway with auto-login
REM IMPORTANT: Set IB_USERNAME and IB_PASSWORD environment variables before running
REM Example: set IB_USERNAME=your_username && set IB_PASSWORD=your_password && launch_ibgateway.bat

IF "%IB_USERNAME%"=="" (
    echo ERROR: IB_USERNAME environment variable not set
    echo Usage: set IB_USERNAME=your_username ^&^& set IB_PASSWORD=your_password ^&^& launch_ibgateway.bat
    exit /b 1
)

IF "%IB_PASSWORD%"=="" (
    echo ERROR: IB_PASSWORD environment variable not set
    echo Usage: set IB_USERNAME=your_username ^&^& set IB_PASSWORD=your_password ^&^& launch_ibgateway.bat
    exit /b 1
)

"C:\Jts\ibgateway\1037\ibgateway.exe" -J-DjtsConfigDir="C:\Jts\ibgateway\1037" username=%IB_USERNAME% password=%IB_PASSWORD% tradingmode=paper
