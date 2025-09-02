# Changelog

## [2025-09-02] - P&L Dashboard Enhancements

### Added
- **Kokoro TTS Integration**: Jessica voice provides tiered congratulatory messages based on profit levels
  - Legendary ($10k+): Extremely enthusiastic messages
  - Epic ($5k-$10k): Very impressed messages  
  - Great ($2.5k-$5k): Encouraging messages
  - Good ($1k-$2.5k): Positive feedback
- **Enhanced Visual Effects**: 
  - Rainbow animated title
  - Golden victory banner with shimmer effect (#FFD700 gradient)
  - Confetti animation (150 pieces for legendary wins)
  - Money rain effect (30 emojis falling)
  - Trophy animation for big wins
  - Sparkles and fireworks displays
- **After-Hours Trade Detection**: Fixed P&L calculation to properly detect and include after-hours trades
- **Command Line Options**: Added --no-sound, --no-browser, and --date options to update_pnl_dashboard.py

### Fixed
- P&L dashboard showing $0.00 for after-hours trades (GEG trade at 5:09 PM and 5:12 PM EDT)
- Victory banner text now fits on single line (4.5rem font size)
- TTS timing synchronized with dashboard display
- Professional language in all messages (removed profanity and religious references)

### Changed
- Victory banner color from green to bright gold (#FFD700) with shadow for better visibility
- TTS playback now non-blocking and starts immediately when dashboard opens
- Font size reduced from 6rem to 4.5rem for "LEGENDARY WIN!" text

### Technical
- Added Kokoro ONNX TTS dependency
- Implemented tiered celebration system based on profit levels
- Enhanced update_pnl_dashboard.py with audio/visual synchronization
- Created comprehensive documentation in PNL_DASHBOARD_ENHANCEMENTS.md

### Performance
- Today's Results (September 2, 2025):
  - Total P&L: +$12,000.00 (GEG after-hours victory)
  - Win Rate: 100%
  - Volume: $462,000
  - Celebration Level: LEGENDARY