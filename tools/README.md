# Buddy Tools

Utility scripts for managing and inspecting Buddy's data.

## check_db.py

Database inspection and management tool using MemoryStore.

### Usage

```bash
# Show all data (history and permanent memories)
python tools/check_db.py

# Show statistics only
python tools/check_db.py --stats

# Limit history records displayed
python tools/check_db.py --limit 10

# Reset all processed flags to 0 (marks all history as unprocessed)
python tools/check_db.py --reset

# Clear all permanent memories from ChromaDB (DESTRUCTIVE!)
python tools/check_db.py --clear
```

### Features

- **Statistics**: View counts of total, processed, and unprocessed history records, plus permanent memory count
- **History Display**: Show recent conversation history with processing status indicators (✅/⏳)
- **Memory Display**: Show all permanent memories stored in ChromaDB with metadata
- **Reset Flags**: Reset all SQLite history records to `processed=0` for reprocessing by Archivist
- **Clear Memories**: Remove all permanent memories from ChromaDB (requires confirmation)

### Safety Features

- **Confirmation prompts** for destructive operations
- `--reset` requires typing "yes"
- `--clear` requires typing "DELETE"
- Uses MemoryStore for consistent data access

## check_models.py

Validates Porcupine wake word model files are present and accessible.

```bash
python tools/check_models.py
```
