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
    
    # Test 1: Auto-detection
    print("\n1. Auto-detection (no BUDDY_HOME env var)")
    buddy_home = get_buddy_home()
    print(f"   ✓ BUDDY_HOME: {buddy_home}")
    assert buddy_home.exists(), "BUDDY_HOME should exist"
    assert (buddy_home / "config").exists(), "config/ should exist in BUDDY_HOME"
    print("   ✓ config/ directory found")
    
    # Test 2: Path resolution - relative
    print("\n2. Relative path resolution")
    config_path = resolve_path("config/adapter_config_dev.yaml")
    print(f"   ✓ config/adapter_config_dev.yaml -> {config_path}")
    assert config_path.is_absolute(), "Should be absolute"
    assert str(buddy_home) in str(config_path), "Should contain BUDDY_HOME"
    
    # Test 3: Path resolution - absolute
    print("\n3. Absolute path resolution")
    abs_path = resolve_path("/tmp/test.txt")
    print(f"   ✓ /tmp/test.txt -> {abs_path}")
    assert abs_path == Path("/tmp/test.txt"), "Should remain absolute"
    
    # Test 4: From different directory
    print("\n4. Resolution from different working directory")
    original_cwd = os.getcwd()
    try:
        os.chdir("/tmp")
        print(f"   Current dir: {os.getcwd()}")
        config_path = resolve_path("config/test.yaml")
        print(f"   ✓ config/test.yaml -> {config_path}")
        assert str(buddy_home) in str(config_path), "Should still use BUDDY_HOME"
    finally:
        os.chdir(original_cwd)
    
    # Test 5: With BUDDY_HOME override
    print("\n5. BUDDY_HOME override (environment variable)")
    original = os.environ.get('BUDDY_HOME')
    try:
        os.environ['BUDDY_HOME'] = '/custom/path'
        # Need to reload module to get new env var
        import importlib
        from config import config_loader
        importlib.reload(config_loader)
        custom_home = config_loader.get_buddy_home()
        print(f"   ✓ BUDDY_HOME (override): {custom_home}")
        assert str(custom_home) == '/custom/path', "Should use env var"
    finally:
        if original:
            os.environ['BUDDY_HOME'] = original
        else:
            os.environ.pop('BUDDY_HOME', None)
        # Reload again to restore
        importlib.reload(config_loader)
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED")
    print("="*60)


if __name__ == "__main__":
    test_buddy_home()
