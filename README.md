# Browser Migration Tool

Migrate browsing data between DIA, ChatGPT Atlas, and Brave Browser (or between any Chromium-based browsers).

**Automatically detects the active browser profile - no need to know the user profile path!**

## Features

### Supported Data Types
- **Browser History** - URLs, visit counts, timestamps
- **Search History** - All keyword searches from the address bar
- **Cookies** - Login sessions, preferences, etc.
- **Visits** - Individual page visits with timing data

## Usage

### 1. Close Both Browsers
**IMPORTANT:** Always close both source and target browsers before running the migration to avoid database locks.

### 2. Run the Migration Tool

```bash
python3 ~/browser_migration.py
```

### 3. Select Browsers

The tool will ask you to select:
- **Source browser** (where to export from)
  - 1 = DIA (automatically detects active profile)
  - 2 = ChatGPT Atlas (automatically detects active profile)
  - 3 = Brave Browser (select by profile name, e.g. "Work")
  - 4 = Custom path

- **Target browser** (where to import to)
  - 1 = DIA (automatically detects active profile)
  - 2 = ChatGPT Atlas (automatically detects active profile)
  - 3 = Brave Browser (select by profile name, e.g. "Work")
  - 4 = Custom path

**Note:** The script automatically detects which profile is active by reading the browser's `Local State` file. For Brave, you can specify a profile by display name (e.g. "Work", "Personal") — leave blank to use the last-used profile.

### 4. Choose Migration Options

**Option 1:** Export source browser history to JSON
- Exports all URLs, visits, and search terms to `~/browser_history_export.json`

**Option 2:** Export source browser cookies to JSON
- Exports all cookies to `~/browser_cookies_export.json`

**Option 3:** Import history from JSON to target browser
- Merges exported history into target browser
- Handles duplicates automatically
- Updates visit counts

**Option 4:** Import cookies from JSON to target browser
- Merges exported cookies into target browser
- Skips duplicates

**Option 5:** Direct copy history (fast method)
- Directly merges databases without JSON export
- Faster but less flexible
- Both browsers MUST be closed

**Option 6:** List bookmarks
- View bookmarks from both browsers

**Option 7:** Full migration (recommended)
- Runs export + import automatically
- Migrates history, search terms, and cookies

**Option 8:** View sample data from source browser
- Preview recent URLs, search terms, and statistics
- Useful for verifying data before migration

## Examples

### DIA to Atlas
```
Source: 1 (DIA)
Target: 2 (Atlas)
Choice: 7 (Full migration)
```

### DIA to Brave (specific profile)
```
Source: 1 (DIA)
Target: 3 (Brave)
Brave profile name: Work
Choice: 7 (Full migration)
```

### DIA to DIA
```
Source: 1 (DIA)
Target: 1 (DIA)
Choice: 7 (Full migration)
```

### Preview Before Migrating
```
Source: 1 (DIA)
Target: 3 (Brave)
Brave profile name: Work
Choice: 8 (View sample data)
Choice: 7 (Full migration)
```

## Safety Features

- **Automatic Backups:** Creates timestamped backups before any modification
  - Format: `History.backup_YYYYMMDD_HHMMSS`
  - Saved in the same directory as the original database

- **Duplicate Detection:** Won't create duplicate entries
  - URLs are checked before importing
  - Cookies are checked by host_key + name + path
  - Search terms are checked by url_id + term

- **Non-Destructive:** Never deletes existing data
  - Only adds new entries or updates visit counts
  - Preserves all existing browser data

## Exported JSON Format

### History Export
```json
{
  "export_date": "2025-11-21T...",
  "source": "/Users/.../Dia/User Data/Default",
  "urls": [...],
  "visits": [...],
  "search_terms": [...]
}
```

### Cookies Export
```json
{
  "export_date": "2025-11-21T...",
  "source": "/Users/.../Dia/User Data/Default",
  "cookies": [...]
}
```

## Troubleshooting

### "Database is locked" Error
- Close both browsers completely
- Check Activity Monitor for any browser processes
- Wait a few seconds and try again

### "Database not found" Error
- Verify the browser is installed
- Check that you've run the browser at least once
- Try using option 3 (custom path) with the full path

### Import Shows 0 New URLs
- Data might already exist in target browser
- Check duplicate URLs using option 8 (view sample data)
- This is normal if you've run the migration before

## Technical Details

DIA, Atlas, and Brave all use Chromium's SQLite database format:

- **History database:** SQLite with tables for urls, visits, keyword_search_terms
- **Cookies database:** SQLite with encrypted_value field (empty for imported cookies)
- **Timestamps:** Chromium epoch (microseconds since 1601-01-01)

### Automatic Profile Detection

The script intelligently detects the active browser profile:

**For DIA:**
- Reads `Local State` to find `profile.last_used`
- Falls back to `Default` profile

**For Atlas:**
1. Reads `Local State` file to find `profile.last_used`
2. If not found, uses the most recently modified `user-*` profile
3. Falls back to `Default` as last resort

**For Brave:**
1. Reads `Local State`'s `profile.info_cache` to match a profile by display name
2. If no name given, falls back to `profile.last_used`
3. Falls back to `Default` as last resort

Brave profile data is located at:
`~/Library/Application Support/BraveSoftware/Brave-Browser/`

## Notes

- Search history is stored in the `keyword_search_terms` table
- Cookie encryption is browser-specific (imported cookies won't have encrypted values)
- Visit timestamps are preserved exactly
- Both browsers must be closed for safe migration
