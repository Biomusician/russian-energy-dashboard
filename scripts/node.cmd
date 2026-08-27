@echo off
rem Node is deliberately not on the machine PATH (see CLAUDE.md). Prepending it here
rem scopes it to this process only, which is what npm/npx shims and package scripts need
rem in order to find `node` at all.
set "PATH=%~dp0..\tools\node;%PATH%"
"%~dp0..\tools\node\node.exe" %*
