#tracker.py start file

import time
from datetime import datetime
from typing import Dict, List
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

        # Tracking
        self.last_growth_check = defaultdict(int)
        self.last_status_check = defaultdict(int)
        self.last_excel_save = 0
        self.running = False

    def check_growth(self, board: str) -> bool:
        """Check for thread growth using threads.json."""
        now = int(time.time())

        if (now - self.last_growth_check.get(board, 0)) < (self.growth_interval * 60):
            return False

        print(f"  📈 Checking /{board}/ growth...")

        threads_data = self.api.get_threads(board)
        if not threads_data:
            return False

        changed_threads = self.processor.process_threads(board, threads_data)

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

        if changed_threads:
            print(f"  ✅ /{board}/: {len(changed_threads)} threads updated")

        self.last_growth_check[board] = now
        return bool(changed_threads)

    def check_status(self, board: str) -> bool:
        """Check thread status using catalog.json."""
        now = int(time.time())

        if (now - self.last_status_check.get(board, 0)) < (self.status_interval * 60):
            return False

        print(f"  📋 Checking /{board}/ status...")

        catalog_data = self.api.get_catalog(board)
        if not catalog_data:
            return False

        metadata, changed_threads, new_threads = self.processor.process_catalog(board, catalog_data)

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

        total_changes = len(all_threads)
        if total_changes or metadata:
            print(f"  ✅ /{board}/: {len(metadata)} current, {len(self.processor.threads[board])} tracked, {total_changes} changes")

        self.last_status_check[board] = now
        return total_changes > 0

    def run_iteration(self):
        """Run one iteration of checks."""
        print(f"\n🔄 Iteration - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 40)

        any_changes = False

        # Check status for all boards
        for board in self.boards:
            if self.check_status(board):
                any_changes = True

        # Check growth for all boards
        for board in self.boards:
            if self.check_growth(board):
                any_changes = True

        # Save state
        self.processor.save_state()

        # Check if we should save to Excel
        now = time.time()
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

    def run_continuous(self, stop_event=None):
        """Run continuous tracking."""
        print("\n" + "="*60)
        print("⚡ 4CHAN TRACKER - MODULAR VERSION")
        print("="*60)
        print(f"Boards: {', '.join(self.boards)}")
        print(f"Growth check: {self.growth_interval} min")
        print(f"Status check: {self.status_interval} min")
        print(f"Excel save: {self.excel_save_interval} min")
        print("Press Ctrl+C to stop\n")

        self.running = True

        try:
            while not (stop_event and stop_event.is_set()):
                self.run_iteration()

                # Wait for next iteration
                print(f"\n⏳ Next check in {self.growth_interval} minute(s)...")
                for _ in range(self.growth_interval * 60):
                    if stop_event and stop_event.is_set():
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

            excel_int = input(f"Excel save interval (minutes, default {tracker.excel_save_interval}): ").strip()
            if excel_int:
                tracker.excel_save_interval = int(excel_int)
        except ValueError:
            print("Using default intervals")

        # Set up signal handling
        stop_event = threading.Event()

        def signal_handler(sig, frame):
            print("\n🛑 Received interrupt signal")
            stop_event.set()

        signal.signal(signal.SIGINT, signal_handler)

        # Run tracking
        tracker.run_continuous(stop_event)

    else:
        print("❌ Invalid choice")
        return

    print("\n" + "="*60)
    print("✅ TRACKER COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
#end file
