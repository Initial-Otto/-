@echo off
title NPC Agent System - Magic Tower
cd /d "%~dp0"
echo Starting Magic Tower Game...
python magic_tower_game.py
echo.
echo Game exited. Press any key to close...
pause >nul
