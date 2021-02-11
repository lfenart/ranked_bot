#!/bin/sh
nohup dotnet run -p ./Api/Api.csproj > api.log &
echo $! > api_pid.txt
