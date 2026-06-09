#!/usr/bin/env python3
"""
Browser Data Migration Tool
Exports history, cookies, and bookmarks from DIA browser
Imports them into ChatGPT Atlas browser

Both browsers use Chromium's database format, making migration straightforward.
"""

import sqlite3
import json
import shutil
import os
from datetime import datetime
from pathlib import Path


class BrowserMigration:
    def __init__(self, source_browser="dia", target_browser="atlas",
                 source_profile=None, target_profile=None):
        self.home = Path.home()

        # Configure source browser path
        if source_browser.lower() == "dia":
            self.source_base = self._get_active_profile("dia")
        elif source_browser.lower() == "atlas":
            self.source_base = self._get_active_profile("atlas")
        elif source_browser.lower() == "brave":
            self.source_base = self._get_brave_profile(source_profile)
        else:
            # Custom path
            self.source_base = Path(source_browser)

        # Configure target browser path
        if target_browser.lower() == "dia":
            self.target_base = self._get_active_profile("dia")
        elif target_browser.lower() == "atlas":
            self.target_base = self._get_active_profile("atlas")
        elif target_browser.lower() == "brave":
            self.target_base = self._get_brave_profile(target_profile)
        else:
            # Custom path
            self.target_base = Path(target_browser)

        # Keep legacy names for backward compatibility
        self.dia_base = self.source_base
        self.atlas_base = self.target_base

        print(f"Source: {self.source_base}")
        print(f"Target: {self.target_base}")

    def _get_active_profile(self, browser):
        """Automatically detect the active profile for a browser"""
        if browser.lower() == "dia":
            base_path = self.home / "Library/Application Support/Dia/User Data"
            local_state = base_path / "Local State"

            # DIA typically uses Default profile
            default_profile = base_path / "Default"
            if default_profile.exists():
                return default_profile

            # Check Local State for active profile
            if local_state.exists():
                try:
                    with open(local_state, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                        if 'profile' in state and 'last_used' in state['profile']:
                            profile_name = state['profile']['last_used']
                            active_profile = base_path / profile_name
                            if active_profile.exists():
                                print(f"  → Detected active DIA profile: {profile_name}")
                                return active_profile
                except:
                    pass

            return default_profile

        elif browser.lower() == "atlas":
            base_path = self.home / "Library/Application Support/com.openai.atlas/browser-data/host"
            local_state = base_path / "Local State"

            # Try to find active profile from Local State
            if local_state.exists():
                try:
                    with open(local_state, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                        if 'profile' in state and 'last_used' in state['profile']:
                            profile_name = state['profile']['last_used']
                            active_profile = base_path / profile_name
                            if active_profile.exists():
                                print(f"  → Detected active Atlas profile: {profile_name}")
                                return active_profile
                except Exception as e:
                    print(f"  → Warning: Could not read Local State: {e}")

            # Fallback: Find the most recently modified user-* profile
            user_profiles = list(base_path.glob("user-*"))
            if user_profiles:
                # Sort by modification time, most recent first
                most_recent = max(user_profiles, key=lambda p: p.stat().st_mtime)
                print(f"  → Using most recent Atlas profile: {most_recent.name}")
                return most_recent

            # Final fallback to Default
            print("  → Falling back to Default profile")
            return base_path / "Default"

    def _get_brave_profile(self, profile_name=None):
        """Find a Brave Browser profile by display name, or return the last-used profile."""
        base_path = self.home / "Library/Application Support/BraveSoftware/Brave-Browser"
        local_state = base_path / "Local State"

        if local_state.exists():
            try:
                with open(local_state, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                info_cache = state.get('profile', {}).get('info_cache', {})

                if profile_name:
                    # Find the directory whose display name matches (case-insensitive)
                    for dir_name, info in info_cache.items():
                        if info.get('name', '').lower() == profile_name.lower():
                            profile_path = base_path / dir_name
                            if profile_path.exists():
                                print(f"  → Found Brave profile '{profile_name}': {dir_name}")
                                return profile_path
                    print(f"  → WARNING: Brave profile named '{profile_name}' not found.")
                    available = ', '.join(f"{d} ({i.get('name','?')})" for d, i in info_cache.items())
                    print(f"  → Available profiles: {available}")

                # Fall back to last-used profile
                last_used = state.get('profile', {}).get('last_used')
                if last_used:
                    profile_path = base_path / last_used
                    if profile_path.exists():
                        print(f"  → Using last-used Brave profile: {last_used}")
                        return profile_path
            except Exception as e:
                print(f"  → Warning: Could not read Brave Local State: {e}")

        # Final fallback
        print("  → Falling back to Brave Default profile")
        return base_path / "Default"

    def backup_database(self, db_path):
        """Create a backup of the database before modification"""
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(db_path, backup_path)
        print(f"Created backup: {backup_path}")
        return backup_path

    def export_history_to_json(self, output_file="browser_history_export.json"):
        """Export browser history to JSON (includes search terms)"""
        source_history = self.source_base / "History"

        if not source_history.exists():
            print(f"History database not found at {source_history}")
            return None

        conn = sqlite3.connect(str(source_history))
        cursor = conn.cursor()

        # Export URLs
        cursor.execute("""
            SELECT id, url, title, visit_count, typed_count, last_visit_time, hidden
            FROM urls
            ORDER BY last_visit_time DESC
        """)
        urls = cursor.fetchall()

        # Export visits
        cursor.execute("""
            SELECT id, url, visit_time, from_visit, transition, visit_duration
            FROM visits
            ORDER BY visit_time DESC
        """)
        visits = cursor.fetchall()

        # Export search terms
        cursor.execute("""
            SELECT keyword_id, url_id, term, normalized_term
            FROM keyword_search_terms
        """)
        search_terms = cursor.fetchall()

        conn.close()

        export_data = {
            "export_date": datetime.now().isoformat(),
            "source": str(self.source_base),
            "urls": [
                {
                    "id": row[0],
                    "url": row[1],
                    "title": row[2],
                    "visit_count": row[3],
                    "typed_count": row[4],
                    "last_visit_time": row[5],
                    "hidden": row[6]
                }
                for row in urls
            ],
            "visits": [
                {
                    "id": row[0],
                    "url_id": row[1],
                    "visit_time": row[2],
                    "from_visit": row[3],
                    "transition": row[4],
                    "visit_duration": row[5]
                }
                for row in visits
            ],
            "search_terms": [
                {
                    "keyword_id": row[0],
                    "url_id": row[1],
                    "term": row[2],
                    "normalized_term": row[3]
                }
                for row in search_terms
            ]
        }

        output_path = self.home / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        print(f"Exported {len(urls)} URLs, {len(visits)} visits, and {len(search_terms)} search terms to {output_path}")
        return output_path

    def export_cookies_to_json(self, output_file="browser_cookies_export.json"):
        """Export browser cookies to JSON"""
        source_cookies = self.source_base / "Cookies"

        if not source_cookies.exists():
            print(f"Cookies database not found at {source_cookies}")
            return None

        conn = sqlite3.connect(str(source_cookies))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT host_key, name, value, path, expires_utc, is_secure,
                   is_httponly, samesite, source_scheme, source_port
            FROM cookies
        """)
        cookies = cursor.fetchall()

        conn.close()

        export_data = {
            "export_date": datetime.now().isoformat(),
            "source": str(self.source_base),
            "cookies": [
                {
                    "host_key": row[0],
                    "name": row[1],
                    "value": row[2],
                    "path": row[3],
                    "expires_utc": row[4],
                    "is_secure": row[5],
                    "is_httponly": row[6],
                    "samesite": row[7],
                    "source_scheme": row[8],
                    "source_port": row[9]
                }
                for row in cookies
            ]
        }

        output_path = self.home / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        print(f"Exported {len(cookies)} cookies to {output_path}")
        return output_path

    def import_history_from_json(self, json_file="browser_history_export.json"):
        """Import history from JSON into target browser"""
        target_history = self.target_base / "History"

        if not target_history.exists():
            print(f"Target History database not found at {target_history}")
            return False

        # Backup first
        self.backup_database(target_history)

        # Load export data
        json_path = self.home / json_file
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        conn = sqlite3.connect(str(target_history))
        cursor = conn.cursor()

        # Get current max IDs to avoid conflicts
        cursor.execute("SELECT MAX(id) FROM urls")
        max_url_id = cursor.fetchone()[0] or 0

        cursor.execute("SELECT MAX(id) FROM visits")
        max_visit_id = cursor.fetchone()[0] or 0

        url_id_mapping = {}
        imported_urls = 0
        imported_visits = 0
        imported_search_terms = 0

        # Import URLs
        for url_data in data['urls']:
            # Check if URL already exists
            cursor.execute("SELECT id FROM urls WHERE url = ?", (url_data['url'],))
            existing = cursor.fetchone()

            if existing:
                url_id_mapping[url_data['id']] = existing[0]
                # Update visit count if higher
                cursor.execute("""
                    UPDATE urls
                    SET visit_count = MAX(visit_count, ?),
                        last_visit_time = MAX(last_visit_time, ?)
                    WHERE id = ?
                """, (url_data['visit_count'], url_data['last_visit_time'], existing[0]))
            else:
                new_id = max_url_id + 1
                cursor.execute("""
                    INSERT INTO urls (id, url, title, visit_count, typed_count, last_visit_time, hidden)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (new_id, url_data['url'], url_data['title'], url_data['visit_count'],
                      url_data['typed_count'], url_data['last_visit_time'], url_data['hidden']))
                url_id_mapping[url_data['id']] = new_id
                max_url_id = new_id
                imported_urls += 1

        # Import visits
        for visit_data in data['visits']:
            if visit_data['url_id'] in url_id_mapping:
                new_visit_id = max_visit_id + 1
                new_url_id = url_id_mapping[visit_data['url_id']]

                cursor.execute("""
                    INSERT INTO visits (id, url, visit_time, from_visit, transition, visit_duration)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (new_visit_id, new_url_id, visit_data['visit_time'],
                      visit_data['from_visit'], visit_data['transition'], visit_data['visit_duration']))
                max_visit_id = new_visit_id
                imported_visits += 1

        # Import search terms if available
        if 'search_terms' in data:
            for search_data in data['search_terms']:
                if search_data['url_id'] in url_id_mapping:
                    new_url_id = url_id_mapping[search_data['url_id']]

                    # Check if search term already exists
                    cursor.execute("""
                        SELECT COUNT(*) FROM keyword_search_terms
                        WHERE url_id = ? AND term = ?
                    """, (new_url_id, search_data['term']))

                    if cursor.fetchone()[0] == 0:
                        cursor.execute("""
                            INSERT INTO keyword_search_terms (keyword_id, url_id, term, normalized_term)
                            VALUES (?, ?, ?, ?)
                        """, (search_data['keyword_id'], new_url_id, search_data['term'],
                              search_data['normalized_term']))
                        imported_search_terms += 1

        conn.commit()
        conn.close()

        print(f"Imported {imported_urls} new URLs, {imported_visits} visits, and {imported_search_terms} search terms")
        return True

    def import_cookies_from_json(self, json_file="browser_cookies_export.json"):
        """Import cookies from JSON into target browser"""
        target_cookies = self.target_base / "Cookies"

        if not target_cookies.exists():
            print(f"Target Cookies database not found at {target_cookies}")
            return False

        # Backup first
        self.backup_database(target_cookies)

        # Load export data
        json_path = self.home / json_file
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        conn = sqlite3.connect(str(target_cookies))
        cursor = conn.cursor()

        imported_cookies = 0
        skipped_cookies = 0

        for cookie in data['cookies']:
            # Check if cookie already exists
            cursor.execute("""
                SELECT COUNT(*) FROM cookies
                WHERE host_key = ? AND name = ? AND path = ?
            """, (cookie['host_key'], cookie['name'], cookie['path']))

            if cursor.fetchone()[0] > 0:
                skipped_cookies += 1
                continue

            # Import cookie with current timestamp
            current_time = int(datetime.now().timestamp() * 1000000) + 11644473600000000  # Chrome epoch

            try:
                cursor.execute("""
                    INSERT INTO cookies (
                        creation_utc, host_key, top_frame_site_key, name, value, encrypted_value,
                        path, expires_utc, is_secure, is_httponly, last_access_utc, has_expires,
                        is_persistent, priority, samesite, source_scheme, source_port,
                        last_update_utc, source_type, has_cross_site_ancestor
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    current_time, cookie['host_key'], cookie['host_key'], cookie['name'],
                    cookie['value'], b'', cookie['path'], cookie['expires_utc'],
                    cookie['is_secure'], cookie['is_httponly'], current_time,
                    1 if cookie['expires_utc'] > 0 else 0, 1, 1, cookie['samesite'],
                    cookie['source_scheme'], cookie['source_port'], current_time, 0, 0
                ))
                imported_cookies += 1
            except sqlite3.IntegrityError:
                skipped_cookies += 1

        conn.commit()
        conn.close()

        print(f"Imported {imported_cookies} cookies, skipped {skipped_cookies} duplicates")
        return True

    def direct_copy_history(self):
        """Directly merge history databases (BROWSERS MUST BE CLOSED)"""
        dia_history = self.dia_base / "History"
        atlas_history = self.atlas_base / "History"

        if not dia_history.exists() or not atlas_history.exists():
            print("One or both History databases not found")
            return False

        # Backup Atlas database
        self.backup_database(atlas_history)

        # Attach DIA database and merge
        conn = sqlite3.connect(str(atlas_history))
        cursor = conn.cursor()

        cursor.execute(f"ATTACH DATABASE '{dia_history}' AS dia")

        # Get max IDs
        cursor.execute("SELECT MAX(id) FROM urls")
        max_url_id = cursor.fetchone()[0] or 0

        cursor.execute("SELECT MAX(id) FROM visits")
        max_visit_id = cursor.fetchone()[0] or 0

        # Copy URLs that don't exist
        cursor.execute(f"""
            INSERT INTO urls (id, url, title, visit_count, typed_count, last_visit_time, hidden)
            SELECT {max_url_id} + ROW_NUMBER() OVER (ORDER BY id), url, title, visit_count,
                   typed_count, last_visit_time, hidden
            FROM dia.urls
            WHERE url NOT IN (SELECT url FROM urls)
        """)

        urls_copied = cursor.rowcount
        print(f"Copied {urls_copied} new URLs")

        conn.commit()
        cursor.execute("DETACH DATABASE dia")
        conn.close()

        return True

    def list_bookmarks(self):
        """List bookmarks from both browsers"""
        bookmarks_files = [
            (self.source_base / "Bookmarks", "Source"),
            (self.target_base / "Bookmarks", "Target")
        ]

        for bookmark_file, browser_name in bookmarks_files:
            if bookmark_file.exists():
                with open(bookmark_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"\n{browser_name} Browser Bookmarks:")
                print(json.dumps(data, indent=2)[:500])  # Show first 500 chars
            else:
                print(f"{browser_name} Bookmarks file not found")

    def view_sample_data(self):
        """View sample data from source browser"""
        source_history = self.source_base / "History"

        if not source_history.exists():
            print(f"History database not found at {source_history}")
            return

        conn = sqlite3.connect(str(source_history))
        cursor = conn.cursor()

        # Show recent URLs
        print("\n" + "=" * 60)
        print("Recent URLs (last 10):")
        print("=" * 60)
        cursor.execute("""
            SELECT url, title, visit_count, datetime(last_visit_time/1000000-11644473600, 'unixepoch') as last_visit
            FROM urls
            ORDER BY last_visit_time DESC
            LIMIT 10
        """)
        for row in cursor.fetchall():
            print(f"\nTitle: {row[1]}")
            print(f"URL: {row[0]}")
            print(f"Visit count: {row[2]}")
            print(f"Last visit: {row[3]}")

        # Show search terms
        print("\n" + "=" * 60)
        print("Recent search terms (last 10):")
        print("=" * 60)
        cursor.execute("""
            SELECT DISTINCT term, COUNT(*) as count
            FROM keyword_search_terms
            GROUP BY term
            ORDER BY count DESC
            LIMIT 10
        """)
        for row in cursor.fetchall():
            print(f"'{row[0]}' - searched {row[1]} time(s)")

        # Show statistics
        print("\n" + "=" * 60)
        print("Statistics:")
        print("=" * 60)
        cursor.execute("SELECT COUNT(*) FROM urls")
        print(f"Total URLs: {cursor.fetchone()[0]}")

        cursor.execute("SELECT COUNT(*) FROM visits")
        print(f"Total visits: {cursor.fetchone()[0]}")

        cursor.execute("SELECT COUNT(*) FROM keyword_search_terms")
        print(f"Total search terms: {cursor.fetchone()[0]}")

        conn.close()


def main():
    print("Browser Migration Tool")
    print("=" * 60)

    print("\nSelect source browser:")
    print("1. DIA")
    print("2. ChatGPT Atlas")
    print("3. Brave Browser")
    print("4. Custom path")
    source_choice = input("Enter choice (default: 1): ").strip() or "1"

    source_profile = None
    if source_choice == "1":
        source = "dia"
    elif source_choice == "2":
        source = "atlas"
    elif source_choice == "3":
        source = "brave"
        source_profile = input("Enter Brave profile name (e.g. Work, Personal) or leave blank for last-used: ").strip() or None
    else:
        source = input("Enter source browser profile path: ").strip()

    print("\nSelect target browser:")
    print("1. DIA")
    print("2. ChatGPT Atlas")
    print("3. Brave Browser")
    print("4. Custom path")
    target_choice = input("Enter choice (default: 2): ").strip() or "2"

    target_profile = None
    if target_choice == "1":
        target = "dia"
    elif target_choice == "2":
        target = "atlas"
    elif target_choice == "3":
        target = "brave"
        target_profile = input("Enter Brave profile name (e.g. Work, Personal) or leave blank for last-used: ").strip() or None
    else:
        target = input("Enter target browser profile path: ").strip()

    print("\n" + "=" * 60)
    print("\nWARNING: Close both browsers before running migration!")
    print("=" * 60)

    migration = BrowserMigration(
        source_browser=source, target_browser=target,
        source_profile=source_profile, target_profile=target_profile
    )

    while True:
        print("\nOptions:")
        print("1. Export source browser history to JSON (includes search terms)")
        print("2. Export source browser cookies to JSON")
        print("3. Import history from JSON to target browser")
        print("4. Import cookies from JSON to target browser")
        print("5. Direct copy history (fast, requires closed browsers)")
        print("6. List bookmarks")
        print("7. Full migration (export + import)")
        print("8. View sample data from source browser")
        print("0. Exit")

        choice = input("\nEnter choice: ").strip()

        if choice == "1":
            migration.export_history_to_json()
        elif choice == "2":
            migration.export_cookies_to_json()
        elif choice == "3":
            migration.import_history_from_json()
        elif choice == "4":
            migration.import_cookies_from_json()
        elif choice == "5":
            migration.direct_copy_history()
        elif choice == "6":
            migration.list_bookmarks()
        elif choice == "7":
            print("\nStarting full migration...")
            migration.export_history_to_json()
            migration.export_cookies_to_json()
            migration.import_history_from_json()
            migration.import_cookies_from_json()
            print("\nFull migration complete!")
        elif choice == "8":
            migration.view_sample_data()
        elif choice == "0":
            break
        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()
