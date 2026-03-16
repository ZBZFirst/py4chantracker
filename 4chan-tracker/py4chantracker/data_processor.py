#data_processor.py start file

import json
import time
from datetime import datetime
from typing import Dict, List, Tuple, Set
from collections import defaultdict
import html
import os

class ThreadData:
    """Represents a single thread's data."""

    def __init__(self, board: str, thread_id: int):
        self.board = board
        self.thread_id = thread_id
        self.board_index = 0  # Current ranking position
        self.board_index_history = []
        self.page = 1
        self.replies = 0
        self.last_modified = 0
        self.closed = 0
        self.archived = 0
        self.subject = ""
        self.comment = ""
        self.images = 0
        self.unique_ips = 0
        self.sticky = 0
        self.timestamp = 0
        self.name = ""
        self.trip = ""
        self.country = ""
        self.first_seen = 0
        self.last_seen = 0
        self.snapshots = 0

    def to_metadata_dict(self) -> Dict:
        """Convert to metadata dictionary."""
        return {
            'board': self.board,
            'thread_id': self.thread_id,
            'current_board_index': self.board_index,
            'page': self.page,
            'replies': self.replies,
            'last_modified': self.last_modified,
            'closed': self.closed,
            'archived': self.archived,
            'subject': self.subject,
            'comment': self.comment,
            'images': self.images,
            'unique_ips': self.unique_ips,
            'timestamp': self.timestamp,
            'datetime': datetime.fromtimestamp(self.timestamp).isoformat() if self.timestamp else '',
            'name': self.name,
            'trip': self.trip,
            'country': self.country,
            'sticky': self.sticky,
            'url': f"https://boards.4chan.org/{self.board}/thread/{self.thread_id}"
        }

    def to_history_dict(self) -> Dict:
        """Convert to history dictionary."""
        return {
            'board': self.board,
            'thread_id': self.thread_id,
            'board_index': self.board_index,
            'board_index_history': json.dumps(self.board_index_history) if self.board_index_history else '[]',
            'current_replies': self.replies,
            'current_page': self.page,
            'last_modified': self.last_modified,
            'last_modified_datetime': datetime.fromtimestamp(self.last_modified).isoformat() if self.last_modified else '',
            'snapshot_count': self.snapshots,
            'status': 'Archived' if self.archived else 'Closed' if self.closed else 'Open',
            'first_seen': datetime.fromtimestamp(self.first_seen).isoformat() if self.first_seen else '',
            'last_seen': datetime.fromtimestamp(self.last_seen).isoformat() if self.last_seen else '',
            'is_active': (time.time() - self.last_modified) <= 86400,  # 24 hours
            'url': f"https://boards.4chan.org/{self.board}/thread/{self.thread_id}",
            'subject': self.subject,
            'comment': self.comment,
            'images': self.images,
            'unique_ips': self.unique_ips,
            'created_timestamp': self.timestamp,
            'created_datetime': datetime.fromtimestamp(self.timestamp).isoformat() if self.timestamp else '',
            'name': self.name,
            'trip': self.trip,
            'country': self.country,
            'sticky': self.sticky
        }


class DataProcessor:
    """Processes 4chan API data and tracks thread history."""

    def __init__(self, boards: List[str]):
        self.boards = boards
        self.threads: Dict[str, Dict[int, ThreadData]] = defaultdict(dict)
        self.history: Dict[str, Dict[int, List[Dict]]] = defaultdict(lambda: defaultdict(list))
        # Tracks threads currently present in the latest catalog fetch per board
        # while preserving catalog order for stable exports.
        self.active_thread_ids: Dict[str, List[int]] = defaultdict(list)
        self._load_state()

    def _load_state(self):
        """Load existing state from JSON file."""
        try:
            if os.path.exists('thread_state.json'):
                with open('thread_state.json', 'r') as f:
                    data = json.load(f)

                for board in self.boards:
                    if board in data.get('threads', {}):
                        for thread_id_str, thread_data in data['threads'][board].items():
                            thread_id = int(thread_id_str)
                            thread = ThreadData(board, thread_id)

                            # Load all thread attributes
                            for key, value in thread_data.items():
                                if hasattr(thread, key):
                                    setattr(thread, key, value)

                            self.threads[board][thread_id] = thread

                    if board in data.get('history', {}):
                        self.history[board] = defaultdict(list, {
                            int(tid): snapshots
                            for tid, snapshots in data['history'][board].items()
                        })

                print(f"📂 Loaded {sum(len(b) for b in self.threads.values())} threads")
        except Exception as e:
            print(f"⚠️ Could not load state: {e}")

    def save_state(self):
        """Save current state to JSON file."""
        try:
            data = {
                'threads': {},
                'history': {},
                'timestamp': int(time.time())
            }

            for board in self.boards:
                # Save thread data
                data['threads'][board] = {
                    str(thread_id): {
                        'board_index': thread.board_index,
                        'board_index_history': thread.board_index_history,
                        'page': thread.page,
                        'replies': thread.replies,
                        'last_modified': thread.last_modified,
                        'closed': thread.closed,
                        'archived': thread.archived,
                        'subject': thread.subject,
                        'comment': thread.comment,
                        'images': thread.images,
                        'unique_ips': thread.unique_ips,
                        'sticky': thread.sticky,
                        'timestamp': thread.timestamp,
                        'name': thread.name,
                        'trip': thread.trip,
                        'country': thread.country,
                        'first_seen': thread.first_seen,
                        'last_seen': thread.last_seen,
                        'snapshots': thread.snapshots
                    }
                    for thread_id, thread in self.threads[board].items()
                }

                # Save history
                data['history'][board] = {
                    str(thread_id): snapshots
                    for thread_id, snapshots in self.history[board].items()
                }

            with open('thread_state.json', 'w') as f:
                json.dump(data, f, separators=(',', ':'))

            print("💾 Saved thread state")
        except Exception as e:
            print(f"❌ Error saving state: {e}")

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean HTML text."""
        if not text:
            return ""
        text = html.unescape(text)
        text = ' '.join(text.split())
        return text.strip()

    def process_catalog(self, board: str, catalog_data: List[Dict]) -> Tuple[List[Dict], List[ThreadData], List[ThreadData]]:
        """Process catalog data and return metadata, changed threads, and new threads."""
        current_time = int(time.time())
        metadata = []
        changed_threads = []
        new_threads = []
        current_catalog_thread_ids: List[int] = []
        seen_thread_ids: Set[int] = set()

        # Process in order with correct page numbers and board_index
        global_index = 0

        for page_num, page in enumerate(catalog_data, 1):  # Page numbers start at 1
            for thread_data in page.get('threads', []):
                thread_id = thread_data.get('no')
                if thread_id in seen_thread_ids:
                    continue
                seen_thread_ids.add(thread_id)
                current_catalog_thread_ids.append(thread_id)

                # Create or get thread
                if thread_id in self.threads[board]:
                    thread = self.threads[board][thread_id]
                    is_new = False
                else:
                    thread = ThreadData(board, thread_id)
                    thread.first_seen = current_time
                    is_new = True

                # Store old values for comparison
                old_replies = thread.replies
                old_page = thread.page
                old_board_index = thread.board_index

                # Update thread data
                thread.board_index = global_index  # This is the actual ranking!
                thread.page = page_num  # Correct page number
                thread.replies = thread_data.get('replies', 0)
                thread.last_modified = thread_data.get('last_modified', 0)
                thread.closed = thread_data.get('closed', 0)
                thread.archived = thread_data.get('archived', 0)
                thread.timestamp = thread_data.get('time', 0)
                thread.subject = self._clean_text(thread_data.get('sub', ''))
                thread.comment = self._clean_text(thread_data.get('com', ''))
                thread.name = self._clean_text(thread_data.get('name', ''))
                thread.images = thread_data.get('images', 0)
                thread.unique_ips = thread_data.get('unique_ips', 0)
                thread.sticky = thread_data.get('sticky', 0)
                thread.trip = thread_data.get('trip', '')
                thread.country = thread_data.get('country', '')
                thread.last_seen = current_time

                # Track board index changes
                if thread.board_index != old_board_index:
                    thread.board_index_history.append(thread.board_index)

                # Check for changes
                if not is_new and (thread.replies != old_replies or
                                   thread.page != old_page or
                                   thread.board_index != old_board_index):
                    changed_threads.append(thread)
                    thread.snapshots += 1

                # Add metadata
                metadata.append(thread.to_metadata_dict())

                # Save thread
                self.threads[board][thread_id] = thread

                if is_new:
                    new_threads.append(thread)
                    thread.snapshots = 1
                    thread.board_index_history = [thread.board_index]

                global_index += 1

        # Metadata should reflect only threads currently visible in the latest
        # catalog check for this board. History remains in self.threads/history.
        self.active_thread_ids[board] = current_catalog_thread_ids

        return metadata, changed_threads, new_threads

    def process_threads(self, board: str, threads_data: List[Dict]) -> List[ThreadData]:
        """Process threads.json data to update reply counts."""
        changed_threads = []

        # Track order from threads.json
        global_index = 0

        for page_data in threads_data:
            for thread_data in page_data.get('threads', []):
                thread_id = thread_data.get('no')

                if thread_id in self.threads[board]:
                    thread = self.threads[board][thread_id]
                    old_replies = thread.replies

                    # Update replies
                    thread.replies = thread_data.get('replies', 0)
                    thread.last_modified = thread_data.get('last_modified', 0)

                    # Track board_index based on threads.json order
                    if thread.board_index != global_index:
                        thread.board_index = global_index
                        thread.board_index_history.append(global_index)

                    if thread.replies != old_replies:
                        changed_threads.append(thread)
                        thread.snapshots += 1

                    thread.last_seen = int(time.time())

                global_index += 1

        return changed_threads

    def add_history(self, board: str, thread_id: int, snapshot: Dict):
        """Add a snapshot to thread history."""
        self.history[board][thread_id].append(snapshot)

    def get_metadata(self, board: str) -> List[Dict]:
        """Get current metadata for a board."""
        active_ids = self.active_thread_ids.get(board, [])
        return [
            self.threads[board][thread_id].to_metadata_dict()
            for thread_id in active_ids
            if thread_id in self.threads[board]
        ]

    def get_history(self, board: str) -> List[Dict]:
        """Get history data for a board."""
        history_data = []

        for thread_id, thread in self.threads[board].items():
            history_dict = thread.to_history_dict()

            # Add history arrays
            if thread_id in self.history[board]:
                snapshots = self.history[board][thread_id]
                history_dict['reply_history'] = json.dumps([s.get('replies', 0) for s in snapshots])
                history_dict['page_history'] = json.dumps([s.get('page', 1) for s in snapshots])
                history_dict['timestamp_history'] = json.dumps([
                    datetime.fromtimestamp(s.get('timestamp', 0)).isoformat()
                    for s in snapshots
                ])
            else:
                history_dict['reply_history'] = '[]'
                history_dict['page_history'] = '[]'
                history_dict['timestamp_history'] = '[]'

            history_data.append(history_dict)

        return history_data

        #end file
