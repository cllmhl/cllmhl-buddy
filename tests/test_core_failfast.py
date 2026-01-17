"""
Test Fail-Fast behavior per moduli core/ e config/
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from core.brain import BuddyBrain
from core.event_router import EventRouter
from core.events import Event, EventType, EventPriority
from config.config_loader import ConfigLoader


class TestBrainFailFast:
    """Test fail-fast behavior per BuddyBrain"""
    
    def test_brain_fails_on_invalid_config(self):
        """Brain should fail-fast on invalid configuration"""
        invalid_config = {
            "model_id": None,  # Invalid
            "temperature": "not_a_number"  # Invalid
        }
        
        # Should raise when trying to initialize with invalid config
        with pytest.raises(Exception):
            with patch('core.brain.genai.Client') as mock_client:
                mock_client.return_value.chats.create.side_effect = ValueError("Invalid config")
                brain = BuddyBrain(api_key="test", config=invalid_config)
    
    def test_brain_handles_api_errors_with_logging(self):
        """Brain should log API errors with exc_info=True"""
        config = {
            "model_id": "test-model",
            "temperature": 0.7,
            "system_instruction": "Test"
        }
        
        with patch('core.brain.genai.Client') as mock_client:
            # Init succeeds
            mock_session = MagicMock()
            mock_client.return_value.chats.create.return_value = mock_session
            
            # But API call fails
            mock_session.send_message.side_effect = ConnectionError("Network error")
            
            brain = BuddyBrain(api_key="test", config=config)
            
            # Should return graceful message, not crash
            with patch('core.brain.logger') as mock_logger:
                result = brain._generate_response("test")
                assert "problema tecnico" in result.lower()
                # Verify logged with exc_info=True
                mock_logger.error.assert_called_once()
                call_kwargs = mock_logger.error.call_args[1]
                assert call_kwargs.get('exc_info') is True


class TestEventRouterFailFast:
    """Test fail-fast behavior per EventRouter"""
    
    def test_router_logs_full_queue_with_exc_info(self):
        """Router should log queue.Full with exc_info=True"""
        import queue
        from core.events import create_output_event
        
        router = EventRouter()
        
        # Create a queue with maxsize=1
        small_queue = queue.PriorityQueue(maxsize=1)
        
        # Register route
        router.register_route(EventType.SPEAK, small_queue, "test_adapter")
        
        # Fill the queue
        event1 = create_output_event(EventType.SPEAK, "test1", EventPriority.NORMAL)
        small_queue.put(event1, block=False)
        
        # Try to route another event - should trigger queue.Full
        event2 = create_output_event(EventType.SPEAK, "test2", EventPriority.NORMAL)
        
        with patch('core.event_router.logger') as mock_logger:
            routed = router.route_event(event2)
            
            assert routed == 0  # Failed to route
            assert router._stats['dropped'] == 1
            
            # Verify logged with exc_info=True
            mock_logger.error.assert_called_once()
            call_kwargs = mock_logger.error.call_args[1]
            assert call_kwargs.get('exc_info') is True


class TestConfigLoaderFailFast:
    """Test fail-fast behavior per ConfigLoader"""
    
    def test_load_nonexistent_file_raises(self):
        """ConfigLoader should raise on missing file, not return {}"""
        with pytest.raises(FileNotFoundError) as exc_info:
            ConfigLoader.load("nonexistent.yaml", validate_adapters=False)
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_load_invalid_yaml_raises(self, tmp_path):
        """ConfigLoader should raise on invalid YAML, not return {}"""
        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text("this: is: not: valid: yaml: [")
        
        with pytest.raises(Exception):  # yaml.YAMLError
            ConfigLoader.load(str(invalid_yaml), validate_adapters=False)
    
    def test_load_empty_file_raises(self, tmp_path):
        """ConfigLoader should raise on empty file, not return {}"""
        empty_yaml = tmp_path / "empty.yaml"
        empty_yaml.write_text("")
        
        with pytest.raises(ValueError) as exc_info:
            ConfigLoader.load(str(empty_yaml), validate_adapters=False)
        
        assert "empty" in str(exc_info.value).lower()
    
    def test_load_buddy_config_json_missing_file_raises(self):
        """load_buddy_config_json should raise on missing file, not return {}"""
        with pytest.raises(FileNotFoundError) as exc_info:
            ConfigLoader.load_buddy_config_json("nonexistent.json")
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_load_buddy_config_json_invalid_json_raises(self, tmp_path):
        """load_buddy_config_json should raise on invalid JSON, not return {}"""
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("{this is not valid json}")
        
        with pytest.raises(json.JSONDecodeError):
            ConfigLoader.load_buddy_config_json(str(invalid_json))
    
    def test_load_buddy_config_json_empty_raises(self, tmp_path):
        """load_buddy_config_json should raise on empty config, not return {}"""
        empty_json = tmp_path / "empty.json"
        empty_json.write_text("{}")
        
        with pytest.raises(ValueError) as exc_info:
            ConfigLoader.load_buddy_config_json(str(empty_json))
        
        assert "empty" in str(exc_info.value).lower()
    
    def test_load_logs_errors_with_exc_info(self, tmp_path):
        """ConfigLoader should log all errors with exc_info=True"""
        invalid_json = tmp_path / "bad.json"
        invalid_json.write_text("not json at all")
        
        with patch('config.config_loader.logger') as mock_logger:
            with pytest.raises(json.JSONDecodeError):
                ConfigLoader.load_buddy_config_json(str(invalid_json))
            
            # Verify logged with exc_info=True
            error_calls = [call for call in mock_logger.error.call_args_list]
            assert len(error_calls) > 0
            
            # Check last error call has exc_info=True
            last_call_kwargs = error_calls[-1][1]
            assert last_call_kwargs.get('exc_info') is True


class TestNoSilentReturns:
    """Verify no silent {} or None returns"""
    
    def test_config_loader_no_empty_dict_fallback(self):
        """ConfigLoader should never return {} as fallback"""
        # This test verifies the behavior, not implementation
        with pytest.raises(FileNotFoundError):
            result = ConfigLoader.load_buddy_config_json("missing.json")
            # Should NOT reach here
            assert False, "Should have raised, not returned {}"
    
    def test_brain_no_none_session_creates_fallback(self):
        """Brain with None session should return graceful message, not fail silently"""
        config = {"model_id": "test", "temperature": 0.7}
        
        with patch('core.brain.genai.Client') as mock_client:
            mock_client.return_value.chats.create.side_effect = Exception("API Down")
            
            brain = BuddyBrain(api_key="test", config=config)
            
            # chat_session should be None (API failed)
            assert brain.chat_session is None
            
            # But _generate_response should return graceful message
            result = brain._generate_response("test")
            assert isinstance(result, str)
            assert len(result) > 0
            assert "disponibile" in result.lower()  # Not silent!
