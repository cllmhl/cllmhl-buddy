#!/usr/bin/env python3
"""
Database inspection and management tool using MemoryStore.

Usage:
    python check_db.py              # Show all data
    python check_db.py --stats      # Show statistics only
    python check_db.py --reset      # Reset all processed flags to 0
    python check_db.py --clear      # Clear all permanent memories (WARNING!)
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path to import infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.memory_store import MemoryStore

# Memory configuration (matching config YAML structure)
MEMORY_CONFIG = {
    'sqlite_path': "data/system.db",
    'chroma_path': "data/memory",
    'reinforce_threshold': 0.3,
    'model_id': "gemini-flash-lite-latest",
    'temperature': 0.1,
    'system_instruction': """
        Sei un "Editor di Memoria". 
        Il tuo compito è unire due informazioni riguardanti lo stesso argomento in una singola frase coerente e concisa.

        REGOLE:
        - Mantieni TUTTI i dettagli fattuali di entrambe le frasi.
        - Non ripetere concetti (Deduplica).
        - Usa la terza persona (es. "L'utente...").
        - Non aggiungere informazioni inventate.
        - Sii breve e conciso.
        INPUT A (Memoria Esistente): {old_fact}
        INPUT B (Nuova Informazione): {new_fact}

        OUTPUT (Solo la frase unita):
    """
}


def show_stats(store):
    """Display database statistics."""
    print("\n" + "=" * 60)
    print("📊 DATABASE STATISTICS")
    print("=" * 60)
    
    stats = store.get_memory_stats()
    print(f"\nSQLite History:")
    print(f"  Total records:       {stats['total_history']}")
    print(f"  Processed:           {stats['processed_history']}")
    print(f"  Unprocessed:         {stats['unprocessed_history']}")
    
    print(f"\nChromaDB Permanent Memories:")
    print(f"  Total memories:      {stats['permanent_memories']}")


def show_history(store, limit=100):
    """Display recent history records."""
    print("\n" + "=" * 60)
    print(f"📜 HISTORY (Last {limit} records)")
    print("=" * 60)
    
    history = store.get_all_history(limit=limit)
    if not history:
        print("\nNo history records found.")
        return
    
    for record in history:
        id_, role, content, session_id, ts, processed = record
        status = "✅" if processed else "⏳"
        session = f" [Session: {session_id}]" if session_id else ""
        print(f"\n{status} ID {id_} | {role}{session} | {ts}")
        print(f"  {content[:200]}{'...' if len(content) > 200 else ''}")


def show_permanent_memories(store):
    """Display all permanent memories."""
    print("\n" + "=" * 60)
    print("🧠 PERMANENT MEMORIES (ChromaDB)")
    print("=" * 60)
    
    memories = store.get_all_permanent_memories()
    
    if not memories['ids']:
        print("\nNo permanent memories found.")
        return
    
    for i, mem_id in enumerate(memories['ids']):
        doc = memories['documents'][i] if i < len(memories['documents']) else "N/A"
        meta = memories['metadatas'][i] if i < len(memories['metadatas']) else {}
        
        print(f"\nID: {mem_id}")
        print(f"  Document: {doc}")
        print(f"  Category: {meta.get('category', 'N/A')}")
        print(f"  Importance: {meta.get('importance', 'N/A')}")
        print(f"  Timestamp: {meta.get('ts', 'N/A')}")
        print(f"  Reinforcements: {meta.get('reinforcement_count', 0)}")
        print(f"  Access count: {meta.get('access_count', 0)}")


def reset_processed_flags(store):
    """Reset all processed flags to 0."""
    print("\n⚠️  WARNING: This will mark all history records as unprocessed!")
    confirmation = input("Type 'yes' to confirm: ")
    
    if confirmation.lower() != 'yes':
        print("❌ Operation cancelled.")
        return
    
    count = store.reset_all_processed_flags()
    print(f"✅ Reset {count} records to processed=0")


def clear_permanent_memories(store):
    """Clear all permanent memories from ChromaDB."""
    print("\n🚨 DANGER: This will DELETE ALL permanent memories!")
    print("This action cannot be undone.")
    confirmation = input("Type 'DELETE' to confirm: ")
    
    if confirmation != 'DELETE':
        print("❌ Operation cancelled.")
        return
    
    count = store.clear_all_permanent_memories()
    print(f"✅ Deleted {count} permanent memories")


def main():
    parser = argparse.ArgumentParser(
        description='Inspect and manage Buddy memory databases',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python check_db.py              # Show all data
  python check_db.py --stats      # Show statistics only
  python check_db.py --reset      # Reset processed flags
  python check_db.py --clear      # Clear permanent memories
        """
    )
    
    parser.add_argument('--stats', action='store_true', 
                       help='Show database statistics only')
    parser.add_argument('--reset', action='store_true',
                       help='Reset all processed flags to 0')
    parser.add_argument('--clear', action='store_true',
                       help='Clear all permanent memories (DESTRUCTIVE!)')
    parser.add_argument('--limit', type=int, default=100,
                       help='Limit number of history records to show (default: 100)')
    
    args = parser.parse_args()
    
    # Initialize MemoryStore
    print(f"Initializing MemoryStore...")
    print(f"  SQLite: {MEMORY_CONFIG['sqlite_path']}")
    print(f"  ChromaDB: {MEMORY_CONFIG['chroma_path']}")
    print(f"  Reinforce threshold: {MEMORY_CONFIG['reinforce_threshold']}")
    
    try:
        store = MemoryStore.initialize("INSERISCI",MEMORY_CONFIG)
    except Exception as e:
        print(f"❌ Error initializing MemoryStore: {e}")
        return 1
    
    try:
        # Handle management operations
        if args.reset:
            reset_processed_flags(store)
            return 0
        
        if args.clear:
            clear_permanent_memories(store)
            return 0
        
        # Show data
        show_stats(store)
        
        if not args.stats:
            show_history(store, limit=args.limit)
            show_permanent_memories(store)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        store.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())