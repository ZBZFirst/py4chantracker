#tracker.py start file

import time
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict
import threading
import signal

from .api_client import FourChanAPIClient
from .data_processor import DataProcessor, ThreadData
from .excel_manager import ExcelManager

class FourChanTracker:
    """Main tracker that orchestrates all components."""

    def __init__(self, boards=None):
        self.boards = boards or ['x', 'b', 'pol', 's', 'gif', 'int']

        # Initialize components
        self.api = FourChanAPIClient()
        self.processor = DataProcessor(self.boards)
        self.excel = ExcelManager()

        # Configuration
        self.growth_interval = 1    # minutes (threads.json)
        self.status_interval = 5    # minutes (catalog.json)
        self.excel_save_interval = 15  # minutes
        self.state_save_interval = 5  # minutes

        # Tracking
        self.last_growth_check = defaultdict(int)
        self.last_status_check = defaultdict(int)
        now = time.time()
        self.last_excel_save = now
        self.last_state_save = now
        self.running = False

    def check_growth(self, board: str) -> List[Dict]:
        """Check for thread growth using threads.json."""
        now = int(time.time())

        if (now - self.last_growth_check.get(board, 0)) < (self.growth_interval * 60):
            return []

        print(f"  📈 Checking /{board}/ growth...")

        threads_data = self.api.get_threads(board)
        if not threads_data:
            return []

        changed_threads = self.processor.process_threads(board, threads_data)
        delta_rows = []

        # Add to history
        current_time = now
        for thread in changed_threads:
            snapshot = {
                'timestamp': current_time,
                'replies': thread.replies,
                'page': thread.page,
                'last_modified': thread.last_modified,
                'closed': thread.closed,
                'archived': thread.archived
            }
            self.processor.add_history(board, thread.thread_id, snapshot)
            delta_rows.append({
                'timestamp': current_time,
                'board': board,
                'thread_id': thread.thread_id,
                'replies': thread.replies,
                'page': thread.page,
                'last_modified': thread.last_modified,
                'closed': thread.closed,
                'archived': thread.archived
            })

        if changed_threads:
            print(f"  ✅ /{board}/: {len(changed_threads)} threads updated")

        self.last_growth_check[board] = now
        return delta_rows

    def check_status(self, board: str) -> Tuple[List[Dict], bool]:
        """Check thread status using catalog.json."""
        now = int(time.time())

        if (now - self.last_status_check.get(board, 0)) < (self.status_interval * 60):
            return [], False

        print(f"  📋 Checking /{board}/ status...")

        catalog_data = self.api.get_catalog(board)
        if not catalog_data:
            return [], False

        metadata, changed_threads, new_threads = self.processor.process_catalog(board, catalog_data)
        delta_rows = []

        # Add to history
        current_time = now
        all_threads = changed_threads + new_threads
        for thread in all_threads:
            snapshot = {
                'timestamp': current_time,
                'replies': thread.replies,
                'page': thread.page,
                'last_modified': thread.last_modified,
                'closed': thread.closed,
                'archived': thread.archived
            }
            self.processor.add_history(board, thread.thread_id, snapshot)
            delta_rows.append({
                'timestamp': current_time,
                'board': board,
                'thread_id': thread.thread_id,
                'replies': thread.replies,
                'page': thread.page,
                'last_modified': thread.last_modified,
                'closed': thread.closed,
                'archived': thread.archived
            })

        total_changes = len(all_threads)
        if total_changes or metadata:
            print(f"  ✅ /{board}/: {len(metadata)} current, {len(self.processor.threads[board])} tracked, {total_changes} changes")

        self.last_status_check[board] = now
        return delta_rows, True

    def run_iteration(self):
        """Run one iteration of checks."""
        print(f"\n🔄 Iteration - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 40)

        any_changes = False
        delta_rows_by_board = defaultdict(list)
        status_checked_boards = set()

        # Check status for all boards
        for board in self.boards:
            status_rows, status_checked = self.check_status(board)
            if status_checked:
                status_checked_boards.add(board)
            if status_rows:
                any_changes = True
                delta_rows_by_board[board].extend(status_rows)

        # Check growth for all boards
        for board in self.boards:
            # Skip growth right after a successful catalog check for this board.
            # Catalog processing already updates replies/page/index and captures
            # a snapshot for changed/new threads.
            if board in status_checked_boards:
                continue
            growth_rows = self.check_growth(board)
            if growth_rows:
                any_changes = True
                delta_rows_by_board[board].extend(growth_rows)

        now = time.time()

        if any_changes:
            self.excel.append_history_rows(delta_rows_by_board)

        # Save state less frequently to reduce disk churn on low-resource devices
        if (now - self.last_state_save) >= (self.state_save_interval * 60):
            self.processor.save_state()
            self.last_state_save = now

        # Check if we should save a full Excel snapshot
        if any_changes and (now - self.last_excel_save) >= (self.excel_save_interval * 60):
            print(f"\n💾 Saving to Excel...")

            # Get all data
            metadata_by_board = {}
            history_by_board = {}

            for board in self.boards:
                metadata_by_board[board] = self.processor.get_metadata(board)
                history_by_board[board] = self.processor.get_history(board)

            # Save to Excel
            self.excel.save_data(metadata_by_board, history_by_board)

            self.last_excel_save = now
            print(f"⏭️ Next Excel save in {self.excel_save_interval} minutes")
        else:
            mins_since = (now - self.last_excel_save) / 60
            mins_left = max(0, self.excel_save_interval - mins_since)
            print(f"⏭️ Excel save in {mins_left:.1f} minutes")

        return any_changes

    def run_continuous(self, stop_event=None, max_runtime_hours: float = 0):
        """Run continuous tracking."""
        print("\n" + "="*60)
        print("⚡ 4CHAN TRACKER - MODULAR VERSION")
        print("="*60)
        print(f"Boards: {', '.join(self.boards)}")
        print(f"Growth check: {self.growth_interval} min")
        print(f"Status check: {self.status_interval} min")
        print(f"State save: {self.state_save_interval} min")
        print(f"Excel save: {self.excel_save_interval} min")
        if max_runtime_hours and max_runtime_hours > 0:
            print(f"Run duration: {max_runtime_hours:g} hour(s)")
        else:
            print("Run duration: Until stopped")
        print("Press Ctrl+C to stop\n")

        self.running = True
        start_time = time.time()
        max_runtime_seconds = max_runtime_hours * 3600 if max_runtime_hours > 0 else 0

        try:
            while not (stop_event and stop_event.is_set()):
                if max_runtime_seconds and (time.time() - start_time) >= max_runtime_seconds:
                    print("\n⏱️ Max runtime reached. Stopping tracker...")
                    break

                self.run_iteration()

                # Wait for next iteration
                print(f"\n⏳ Next check in {self.growth_interval} minute(s)...")
                for _ in range(self.growth_interval * 60):
                    if stop_event and stop_event.is_set():
                        break
                    if max_runtime_seconds and (time.time() - start_time) >= max_runtime_seconds:
                        break
                    time.sleep(1)

        except KeyboardInterrupt:
            print("\n\n🛑 Stopping tracker...")
        finally:
            self.running = False

            # Final save
            print("💾 Final save...")
            self.processor.save_state()

            # Final Excel save
            metadata_by_board = {}
            history_by_board = {}
            for board in self.boards:
                metadata_by_board[board] = self.processor.get_metadata(board)
                history_by_board[board] = self.processor.get_history(board)

            self.excel.save_data(metadata_by_board, history_by_board)
            print("✅ Tracker stopped")


def main():
    """Main execution function."""
    print("="*60)
    print("📊 4CHAN TRACKER - MODULAR VERSION")
    print("="*60)

    tracker = FourChanTracker()

    print("\nChoose operation:")
    print("1. Initial scan")
    print("2. Continuous tracking")

    choice = input("\nEnter choice (1 or 2): ").strip()

    if choice == "1":
        print("\n🚀 Running initial scan...")
        for board in tracker.boards:
            tracker.check_status(board)
            tracker.check_growth(board)

        # Save initial data
        tracker.processor.save_state()

        metadata_by_board = {}
        history_by_board = {}
        for board in tracker.boards:
            metadata_by_board[board] = tracker.processor.get_metadata(board)
            history_by_board[board] = tracker.processor.get_history(board)

        tracker.excel.save_data(metadata_by_board, history_by_board)
        print("\n✅ Initial scan complete!")

    elif choice == "2":
        # Configure intervals
        try:
            growth = input(f"Growth interval (minutes, default {tracker.growth_interval}): ").strip()
            if growth:
                tracker.growth_interval = int(growth)

            status = input(f"Status interval (minutes, default {tracker.status_interval}): ").strip()
            if status:
                tracker.status_interval = int(status)

            state_int = input(f"State save interval (minutes, default {tracker.state_save_interval}): ").strip()
            if state_int:
                tracker.state_save_interval = int(state_int)

            excel_int = input(f"Excel save interval (minutes, default {tracker.excel_save_interval}): ").strip()
            if excel_int:
                tracker.excel_save_interval = int(excel_int)

            runtime = input("Run duration in hours (blank = until stopped): ").strip()
            max_runtime_hours = float(runtime) if runtime else 0
        except ValueError:
            print("Using default intervals")
            max_runtime_hours = 0

        # Set up signal handling
        stop_event = threading.Event()

        def signal_handler(sig, frame):
            print("\n🛑 Received interrupt signal")
            stop_event.set()

        signal.signal(signal.SIGINT, signal_handler)

        # Run tracking
        tracker.run_continuous(stop_event, max_runtime_hours=max_runtime_hours)

    else:
        print("❌ Invalid choice")
        return

    print("\n" + "="*60)
    print("✅ TRACKER COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
#end file
