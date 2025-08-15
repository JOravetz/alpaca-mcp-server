#!/bin/bash
# Universal Python runner for Claude Code
# This ensures all Python scripts run in the correct uv environment

# Use uv to run Python with all dependencies available
exec uv run python "$@"