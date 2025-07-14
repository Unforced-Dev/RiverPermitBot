# Flexible Monitoring System

The River Permit Bot now supports dynamic permit management through Telegram commands, replacing the previous hardcoded system.

## Features

### Dynamic Permit Configuration
- Permits are now stored in `data/permits_config.json` instead of being hardcoded
- Automatic migration from existing hardcoded permits on first run
- Supports adding/removing permits without code changes

### Automatic Division Discovery
- When adding a new permit, the bot automatically discovers valid divisions
- Tests multiple ranges: 1-20 (common), 300-400 (Green River range), 1000-1100 (higher numbers)
- Handles edge cases like permits with no divisions or unusual numbering

### Telegram Commands
All commands work only from the configured Telegram channel:

#### `/start-monitoring [permit-id] [permit-name]`
Adds a new permit to monitoring. The bot will:
1. Check if the permit is already being monitored
2. Discover valid divisions automatically
3. Add the permit to the configuration
4. Start monitoring immediately

**Example:**
```
/start-monitoring 621743 Rio Chama
```

#### `/stop-monitoring [permit-id]`
Removes a permit from monitoring.

**Example:**
```
/stop-monitoring 621743
```

#### `/list-permits`
Shows all currently monitored permits with their divisions.

#### `/help`
Shows available commands and usage.

## Technical Details

### PermitConfigManager Class
- Handles loading/saving permit configuration
- Provides methods for adding/removing permits
- Manages division discovery with rate limiting

### Division Discovery Process
1. Tests division IDs in multiple ranges
2. Makes API calls to verify validity
3. Uses proper rate limiting (0.3s between requests)
4. Checks response structure for expected data format
5. Stops early if enough divisions are found

### Backward Compatibility
- Existing permits (Green River, Rio Chama) are automatically migrated
- No changes needed to existing configuration
- State files remain compatible

### Error Handling
- Graceful handling of invalid permit IDs
- Proper error messages for users
- Network timeout protection
- Invalid division ID detection

## Configuration Files

### `data/permits_config.json`
Stores the dynamic permit configuration:
```json
{
  "250014": {
    "name": "Green River",
    "divisions": {
      "371": "Dearlodge",
      "380": "Gates of Lodore"
    }
  },
  "621743": {
    "name": "Rio Chama River",
    "divisions": {
      "1": "Rio Chama"
    }
  }
}
```

### `data/availability_state.json`
Unchanged - continues to track availability state for notifications.

## Usage Examples

### Adding a New Permit
1. Find the permit ID from Recreation.gov URL (e.g., `/permits/621743/`)
2. Send command: `/start-monitoring 621743 Rio Chama`
3. Bot will discover divisions and start monitoring

### Troubleshooting
- If division discovery fails, verify the permit ID is correct
- Check that the permit has active availability data
- Some permits may not use the division structure

### Migration Notes
- First run automatically migrates existing hardcoded permits
- No manual intervention required
- Logs show migration progress