@echo off
rem See node.cmd: PATH is extended for this process only.
set "PATH=%~dp0..\tools\node;%PATH%"
"%~dp0..\tools\node\npm.cmd" %*
