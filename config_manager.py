import json
import os
from typing import Dict, Any

class ConfigManager:
    _instance = None
    _config = None
    _gui = None
    
    # Default configuration
    DEFAULT_CONFIG = {
        "movement_mode": "both",
        "active_profile": "Default",
        "profiles": {
            "Default": {
                "show_highlight": True,
                "highlight_duration": 750,
                "thresholds": {
                    "run": 0.6,
                    "bag": 0.6,
                    "kill": 0.75,
                    "chose": 0.7,
                    "overload": 0.7,
                    "died": 0.8,
                    "map": 0.95
                }
            }
        }
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self.load_config()
    
    def set_gui(self, gui) -> None:
        """Sets the GUI reference for logging"""
        self._gui = gui
    
    def log(self, msg: str) -> None:
        """Logs a message to both console and GUI if available"""
        print(msg)
        if self._gui and hasattr(self._gui, 'add_log_entry'):
            self._gui.add_log_entry(msg)
    
    def load_config(self) -> None:
        """Loads or creates the configuration file"""
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r') as f:
                    config_data = json.load(f)
                    # Check if config is empty or missing required fields
                    if not config_data or not config_data.get('profiles') or not config_data.get('active_profile'):
                        self._config = self.DEFAULT_CONFIG.copy()
                        with open('config.json', 'w') as f:
                            json.dump(self._config, f, indent=4)
                        self.log("[CONFIG] Created new config with defaults (empty/invalid config)")
                    else:
                        self._config = config_data
                        self.log("[CONFIG] Loaded existing config")
            else:
                self._config = self.DEFAULT_CONFIG.copy()
                with open('config.json', 'w') as f:
                    json.dump(self._config, f, indent=4)
                self.log("[CONFIG] Created new config with defaults (no file)")
        except Exception as e:
            self.log(f"[CONFIG] Error loading config: {e}")
            self._config = self.DEFAULT_CONFIG.copy()
            try:
                with open('config.json', 'w') as f:
                    json.dump(self._config, f, indent=4)
                self.log("[CONFIG] Created new config with defaults (after error)")
            except Exception as e:
                self.log(f"[CONFIG] Error saving default config: {e}")
    
    def save_config(self) -> None:
        """Saves the configuration to file"""
        try:
            import traceback
            stack = traceback.extract_stack()
            # Get the caller (excluding this function and internal Python calls)
            caller = None
            for frame in reversed(stack[:-1]):  # Exclude current function
                if not frame.filename.endswith(('config_manager.py', '<frozen importlib._bootstrap>', '<frozen importlib._bootstrap_external>')):
                    caller = frame
                    break
            
            if caller:
                self.log(f"[CONFIG] Save called from {caller.filename}:{caller.lineno} in {caller.name}")
            
            with open('config.json', 'w') as f:
                json.dump(self._config, f, indent=4)
                self.log("[CONFIG] Saved config")
        except Exception as e:
            self.log(f"[CONFIG] Error saving config: {e}")
            import traceback
            self.log(traceback.format_exc())
    
    def get(self, key: str, default: Any = None) -> Any:
        """Gets a value from the config"""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any, save: bool = False) -> None:
        """Sets a value in the config"""
        if self._config.get(key) != value:
            self._config[key] = value
            if save:
                self.save_config()
    
    def get_profile(self, profile_name=None) -> dict:
        """Gets a profile by name, or the active profile if no name is provided"""
        if profile_name is None:
            profile_name = self._config.get('active_profile', 'Default')
            
        if profile_name not in self._config['profiles']:
            return None
            
        return self._config['profiles'][profile_name]
        
    def set_profile(self, profile_name: str, profile_data: dict, save: bool = True) -> None:
        """Sets a profile's data"""
        # Create profiles dict if it doesn't exist
        if 'profiles' not in self._config:
            self._config['profiles'] = {}
            
        # Set profile data
        self._config['profiles'][profile_name] = profile_data
        
        if save:
            self.save_config()
            
    def delete_profile(self, profile_name: str) -> bool:
        """Deletes a profile from the config"""
        if profile_name == 'Standard':
            return False
            
        if profile_name in self._config.get('profiles', {}):
            del self._config['profiles'][profile_name]
            if self.get('active_profile') == profile_name:
                self._config['active_profile'] = 'Standard'
            self.save_config()
            return True
        return False
    
    def get_all_profiles(self) -> Dict:
        """Gets all profiles"""
        return self._config.get('profiles', {})
    
    def get_active_profile(self) -> str:
        """Gets the name of the active profile"""
        return self._config.get('active_profile', 'Default')
        
    def set_active_profile(self, profile_name: str) -> None:
        """Sets the active profile"""
        if (profile_name in self._config['profiles'] and 
            profile_name != self._config.get('active_profile')):
            self._config['active_profile'] = profile_name
            self.save_config()
            
    # Convenience methods that use set() internally
    def save_temtem_path(self, path: str) -> None:
        """Saves the Temtem executable path"""
        self.set('temtem_path', path, save=True)
    
    def save_movement_mode(self, mode: str) -> None:
        """Saves the movement mode"""
        self.set('movement_mode', mode, save=True)
    
    def save_highlight_setting(self, show_highlight: bool) -> None:
        """Saves the highlight circle visibility setting"""
        profile = self.get_profile()
        if profile.get('show_highlight') != show_highlight:
            profile['show_highlight'] = show_highlight
            self.set_profile(self.get_active_profile(), profile, save=True)
    
    def save_highlight_duration(self, duration: int) -> None:
        """Saves the highlight circle duration setting"""
        profile = self.get_profile()
        if profile.get('highlight_duration') != duration:
            profile['highlight_duration'] = duration
            self.set_profile(self.get_active_profile(), profile, save=True)
    
    def ensure_default_profile(self) -> None:
        """Ensures the Default profile exists and is set as active if no profile is set"""
        needs_save = False
        
        # Create profiles dict if it doesn't exist
        if 'profiles' not in self._config:
            self._config['profiles'] = {}
            needs_save = True
            
        # Check if Default profile exists
        if 'Default' not in self._config['profiles']:
            # Use Default profile from DEFAULT_CONFIG
            self._config['profiles']['Default'] = self.DEFAULT_CONFIG['profiles']['Default']
            needs_save = True
            
        # Set active profile if none is set
        if 'active_profile' not in self._config:
            self._config['active_profile'] = 'Default'
            needs_save = True
            
        if needs_save:
            self.save_config() 