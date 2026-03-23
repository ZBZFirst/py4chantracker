# 4chan Thread Tracker

A Python tool to track and analyze 4chan threads across multiple boards in real-time.

## Features

- Track multiple 4chan boards simultaneously
- Monitor thread growth and status changes
- Store historical data in Excel format
- Fast append-only CSV delta logging (`history_deltas/*.csv`) between Excel snapshots
- Choose continuous runtime as fixed hours or run until manually stopped
- Track thread ranking positions over time
- Automatic backups and state persistence

## Installation

### Method 1: Install from source
```bash
# Clone the repository
git clone https://github.com/yourusername/4chan-tracker.git
cd 4chan-tracker

# Install the package
pip install -e .
