#!/usr/bin/env python3
"""
Test script for the new permit discovery functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from river_permit_bot import PermitConfigManager, RiverPermitMonitor
import json
import tempfile

def test_permit_config_manager():
    """Test the PermitConfigManager functionality"""
    print("Testing PermitConfigManager...")
    
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_config = f.name
    
    try:
        # Test initialization and migration
        manager = PermitConfigManager(temp_config)
        permits = manager.get_permits()
        print(f"✓ Loaded {len(permits)} permits from defaults")
        
        # Test adding a permit
        test_divisions = {1: "Test Division 1", 2: "Test Division 2"}
        success = manager.add_permit("123456", "Test Permit", test_divisions)
        print(f"✓ Add permit: {success}")
        
        # Test listing permits
        permit_list = manager.list_permits()
        print(f"✓ Permit list ({len(permit_list)} items):")
        for permit in permit_list:
            print(f"  - {permit}")
        
        # Test removing a permit
        success = manager.remove_permit("123456")
        print(f"✓ Remove permit: {success}")
        
        # Verify removal
        permits_after = manager.get_permits()
        print(f"✓ Permits after removal: {len(permits_after)}")
        
    finally:
        # Clean up
        if os.path.exists(temp_config):
            os.unlink(temp_config)
    
    print("PermitConfigManager tests completed!\n")

def test_permit_discovery():
    """Test permit discovery with a known permit"""
    print("Testing permit discovery...")
    
    # Create monitor instance
    monitor = RiverPermitMonitor()
    
    # Test with Green River permit (should find divisions 371, 380)
    print("Testing discovery for Green River permit (250014)...")
    divisions, errors = monitor.permit_manager.discover_divisions(
        "250014", monitor.session, "Green River"
    )
    
    if divisions:
        print(f"✓ Found {len(divisions)} divisions:")
        for div_id, div_name in divisions.items():
            print(f"  - {div_id}: {div_name}")
    else:
        print(f"✗ No divisions found. Errors: {errors}")
    
    print("Permit discovery test completed!\n")

def test_config_migration():
    """Test that the new system properly migrates from defaults"""
    print("Testing configuration migration...")
    
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_config = f.name
    
    try:
        # Create manager (should migrate from defaults)
        manager = PermitConfigManager(temp_config)
        
        # Verify the config file was created
        assert os.path.exists(temp_config), "Config file should be created"
        
        # Load and verify contents
        with open(temp_config, 'r') as f:
            config_data = json.load(f)
        
        print(f"✓ Config file created with {len(config_data)} permits")
        
        # Verify expected permits
        expected_permits = ["250014", "621743"]
        for permit_id in expected_permits:
            assert permit_id in config_data, f"Expected permit {permit_id} not found"
            print(f"✓ Found expected permit: {permit_id} ({config_data[permit_id]['name']})")
        
    finally:
        # Clean up
        if os.path.exists(temp_config):
            os.unlink(temp_config)
    
    print("Configuration migration test completed!\n")

def main():
    print("River Permit Bot - New Functionality Tests")
    print("=" * 50)
    
    try:
        test_permit_config_manager()
        test_config_migration()
        # Note: Skipping discovery test as it requires network access
        print("All tests completed successfully! 🎉")
        
    except Exception as e:
        print(f"Test failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())