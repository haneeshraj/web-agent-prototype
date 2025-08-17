import yaml
import os
from pathlib import Path
from typing import Dict, Any

class Config:
    """Configuration loader for the web information extractor agent."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize configuration loader.
        
        Args:
            config_path (str): Path to the configuration file
        """
        self.config_path = config_path
        self.config_data = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        config_file = Path(self.config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file {self.config_path} not found")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as file:
                config_data = yaml.safe_load(file)
                return config_data
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML configuration: {e}")
        except Exception as e:
            raise Exception(f"Error loading configuration file: {e}")
    
    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific agent.
        
        Args:
            agent_name (str): Name of the agent (e.g., 'classifier-agent')
            
        Returns:
            Dict[str, Any]: Agent configuration
        """
        try:
            return self.config_data['agent'][agent_name]
        except KeyError:
            raise KeyError(f"Agent '{agent_name}' not found in configuration")
    
    def get_model_config(self, agent_name: str = "classifier-agent") -> Dict[str, Any]:
        """
        Get model configuration for an agent.
        
        Args:
            agent_name (str): Name of the agent
            
        Returns:
            Dict[str, Any]: Model configuration with keys: model, max_tokens, temperature
        """
        agent_config = self.get_agent_config(agent_name)
        
        return {
            'model': agent_config.get('model', 'gemini-2.5-pro'),
            'max_tokens': agent_config.get('max_tokens', 2048),
            'temperature': agent_config.get('temperature', 0.3)
        }
    
    def get(self, key_path: str, default=None):
        """
        Get configuration value using dot notation.
        
        Args:
            key_path (str): Dot-separated path to the config value (e.g., 'agent.classifier-agent.model')
            default: Default value if key not found
            
        Returns:
            Any: Configuration value
        """
        keys = key_path.split('.')
        current = self.config_data
        
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
    
    def reload(self):
        """Reload configuration from file."""
        self.config_data = self._load_config()


# Singleton instance for easy access
_config_instance = None

def get_config(config_path: str = "config.yaml") -> Config:
    """
    Get the global configuration instance.
    
    Args:
        config_path (str): Path to configuration file
        
    Returns:
        Config: Configuration instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance


# Convenience functions
def get_model_config(agent_name: str = "classifier-agent") -> Dict[str, Any]:
    """Get model configuration for an agent."""
    return get_config().get_model_config(agent_name)

def get_agent_config(agent_name: str) -> Dict[str, Any]:
    """Get full configuration for an agent."""
    return get_config().get_agent_config(agent_name)