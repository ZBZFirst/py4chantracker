"""
Excel Manager for saving 4chan data
"""

import pandas as pd
import os
import shutil
import csv
from datetime import datetime
from typing import Dict, List
import warnings
warnings.filterwarnings('ignore')


class ExcelManager:
    """Manages Excel file operations."""

    def __init__(self, filename: str = "4chan_history.xlsx"):
        self.filename = filename
        self.backup_dir = "excel_backups"
        self.delta_dir = "history_deltas"
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.delta_dir, exist_ok=True)

    def append_history_rows(self, rows_by_board: Dict[str, List[Dict]]):
        """
        Fast append-only persistence for history deltas.
        This avoids opening/re-writing the full Excel file each iteration.
        """
        for board, rows in rows_by_board.items():
            if not rows:
                continue

            csv_path = os.path.join(self.delta_dir, f"{board}_history_deltas.csv")
            file_exists = os.path.exists(csv_path)

            try:
                with open(csv_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=[
                            "timestamp",
                            "board",
                            "thread_id",
                            "replies",
                            "page",
                            "last_modified",
                            "closed",
                            "archived"
                        ]
                    )
                    if not file_exists:
                        writer.writeheader()
                    writer.writerows(rows)
                print(f"    🧾 {board}_history_deltas.csv: +{len(rows)} rows")
            except Exception as e:
                print(f"    ⚠️ Failed delta append for /{board}/: {e}")

    def create_backup(self):
        """Create backup of current Excel file."""
        if os.path.exists(self.filename):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.backup_dir, f"backup_{timestamp}.xlsx")

            try:
                shutil.copy2(self.filename, backup_file)

                # Clean up old backups (keep last 10)
                backups = sorted([
                    f for f in os.listdir(self.backup_dir)
                    if f.startswith('backup_') and f.endswith('.xlsx')
                ])
                for old_backup in backups[:-10]:
                    try:
                        os.remove(os.path.join(self.backup_dir, old_backup))
                    except:
                        pass

                print(f"  📦 Backup created: {backup_file}")
            except Exception as e:
                print(f"  ⚠️ Could not create backup: {e}")

    def save_data(self, metadata_by_board: Dict[str, List[Dict]],
                  history_by_board: Dict[str, List[Dict]]):
        """Save all data to Excel file."""
        self.create_backup()

        try:
            with pd.ExcelWriter(self.filename, engine='openpyxl') as writer:
                # Save metadata sheets
                for board, metadata in metadata_by_board.items():
                    if metadata:
                        df = pd.DataFrame(metadata)
                        # Sort by current_board_index to maintain correct order
                        if 'current_board_index' in df.columns:
                            df = df.sort_values('current_board_index')
                        df.to_excel(writer, sheet_name=f"{board}_metadata", index=False)
                        print(f"    💾 {board}_metadata: {len(df)} threads")

                # Save history sheets
                for board, history in history_by_board.items():
                    if history:
                        df = pd.DataFrame(history)
                        # Sort by board_index
                        if 'board_index' in df.columns:
                            df = df.sort_values('board_index')
                        df.to_excel(writer, sheet_name=f"{board}_history", index=False)
                        print(f"    💾 {board}_history: {len(df)} threads")

                # Save summary
                summary_df = self._create_summary(metadata_by_board, history_by_board)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)

            print(f"  ✅ Excel file saved: {self.filename}")

        except Exception as e:
            print(f"  ❌ Error saving Excel: {e}")
            import traceback
            traceback.print_exc()

    def _create_summary(self, metadata_by_board: Dict[str, List[Dict]],
                       history_by_board: Dict[str, List[Dict]]) -> pd.DataFrame:
        """Create summary sheet."""
        summary_data = []

        all_boards = set(list(metadata_by_board.keys()) + list(history_by_board.keys()))

        for board in sorted(all_boards):
            metadata = metadata_by_board.get(board, [])
            history = history_by_board.get(board, [])

            current_threads = len(metadata)
            tracked_threads = len(history)

            # Calculate stats
            open_threads = sum(1 for m in metadata if not m.get('closed') and not m.get('archived'))
            closed_threads = sum(1 for m in metadata if m.get('closed') and not m.get('archived'))
            archived_threads = sum(1 for m in metadata if m.get('archived'))

            active_24h = sum(1 for h in history if h.get('is_active', False))

            avg_snapshots = 0
            if history:
                avg_snapshots = sum(h.get('snapshot_count', 0) for h in history) / len(history)

            total_replies = sum(m.get('replies', 0) for m in metadata)
            total_images = sum(m.get('images', 0) for m in metadata)

            summary_data.append({
                'Board': f"/{board}/",
                'Current Threads': current_threads,
                'Tracked Threads': tracked_threads,
                'Open': open_threads,
                'Closed': closed_threads,
                'Archived': archived_threads,
                'Active (24h)': active_24h,
                'Total Replies': total_replies,
                'Total Images': total_images,
                'Avg Snapshots': round(avg_snapshots, 1),
                'Last Update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

        return pd.DataFrame(summary_data) if summary_data else pd.DataFrame()
