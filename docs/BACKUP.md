cat > backup/README.md << 'EOF'
# Backup Directory

This directory contains:

- `analysis_files/` - Old analysis outputs and JSON results
- `misc/` - Files that need review before deletion
- `old_logs/` - Archived log files

## Subdirectory Backups

Individual components have their own backup directories:
- `alpaca_mcp_server/tools/backup/` - Tool version history
- `alpaca_mcp_server/monitoring/backup/` - Service variants
- `alpaca_mcp_server/backup/` - Server backups

## Cleanup Policy

Review and remove backups after:
- 30 days for analysis files
- 60 days for code backups
- 90 days for logs

Last cleanup: [DATE]
EOF
