#!/usr/bin/env python3
"""
Test script per verificare BUDDY_HOME e path resolution
"""

import os
import sys
from pathlib import Path

# Add buddy to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config_loader import get_buddy_home, resolve_path


def test_buddy_home():
    """Test BUDDY_HOME detection"""
    print("="*60)
    print("TEST BUDDY_HOME")
    print("="*60)
    
    # Test 1: BUDDY_HOME obbligatorio
    print("\n1. BUDDY_HOME obbligatorio (must be set)")
    
    # Salva originale
    original = os.environ.get('BUDDY_HOME')
    
    # Test senza BUDDY_HOME - deve fallire
    if 'BUDDY_HOME' in os.environ:
        del os.environ['BUDDY_HOME']
    
    try:
        import importlib
        from config import config_loader
        importlib.reload(config_loader)
        buddy_home = config_loader.get_buddy_home()
        print("   ❌ ERRORE: Dovrebbe fallire senza BUDDY_HOME!")
        assert False, "Should raise ValueError"
    except ValueError as e:
        print(f"   ✓ Correttamente fallito: {e}")
    
    # Ripristina
    if original:
        os.environ['BUDDY_HOME'] = original
    else:
        os.environ['BUDDY_HOME'] = str(Path(__file__).parent.parent)
    
    importlib.reload(config_loader)
    
    # Test 2: Con BUDDY_HOME impostato
    print("\n2. BUDDY_HOME impostato correttamente")
    buddy_home = config_loader.get_buddy_home()
    print(f"   ✓ BUDDY_HOME: {buddy_home}")
    assert buddy_home.exists(), "BUDDY_HOME should exist"
    assert (buddy_home / "config").exists(), "config/ should exist in BUDDY_HOME"
    print("   ✓ config/ directory found")
    
    # Test 2: Con BUDDY_HOME impostato
    print("\n2. BUDDY_HOME impostato correttamente")
    buddy_home = config_loader.get_buddy_home()
    print(f"   ✓ BUDDY_HOME: {buddy_home}")
    assert buddy_home.exists(), "BUDDY_HOME should exist"
    assert (buddy_home / "config").exists(), "config/ should exist in BUDDY_HOME"
    print("   ✓ config/ directory found")
    
    # Test 3: Path resolution - relative
    print("\n3. Relative path resolution")
    config_path = config_loader.resolve_path("config/adapter_config_dev.yaml")
    print(f"   ✓ config/adapter_config_dev.yaml -> {config_path}")
    assert config_path.is_absolute(), "Should be absolute"
    assert str(buddy_home) in str(config_path), "Should contain BUDDY_HOME"
    
    # Test 4: Path resolution - absolute
    print("\n4. Absolute path resolution")
    abs_path = config_loader.resolve_path("/tmp/test.txt")
    print(f"   ✓ /tmp/test.txt -> {abs_path}")
    assert abs_path == Path("/tmp/test.txt"), "Should remain absolute"
    
    # Test 5: From different directory
    print("\n5. Resolution from different working directory")
    original_cwd = os.getcwd()
    try:
        os.chdir("/tmp")
        print(f"   Current dir: {os.getcwd()}")
        config_path = config_loader.resolve_path("config/test.yaml")
        print(f"   ✓ config/test.yaml -> {config_path}")
        assert str(buddy_home) in str(config_path), "Should still use BUDDY_HOME"
    finally:
        os.chdir(original_cwd)
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED")
    print("="*60)


if __name__ == "__main__":
    test_buddy_home()
