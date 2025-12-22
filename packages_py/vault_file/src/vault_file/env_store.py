import os
import glob
from typing import Dict, Optional, List, Any, Callable, TypeVar
from dotenv import dotenv_values
from .domain import LoadResult
from .logger import get_logger
from .sensitive import mask_value

logger = get_logger()

T = TypeVar("T")
ComputedDefinition = Callable[['EnvStore'], Any]
Base64FileParser = Callable[['EnvStore'], Any]

class EnvKeyNotFoundError(Exception):
    pass

class EnvStore:
    _instance: Optional['EnvStore'] = None
    _store: Dict[str, str] = {}
    _initialized: bool = False
    _loaded_files: List[str] = []
    
    # Computed support
    _computed_definitions: Dict[str, ComputedDefinition] = {}
    _computed_cache: Dict[str, Any] = {}

    # Base64 file parsers support
    _base64_file_parsers: Dict[str, Base64FileParser] = {}

    def __new__(cls) -> 'EnvStore':
        if cls._instance is None:
            cls._instance = super(EnvStore, cls).__new__(cls)
        return cls._instance

    def load(
        self,
        location: str,
        pattern: str = ".env*",
        override: bool = False,
        computed_definitions: Optional[Dict[str, ComputedDefinition]] = None,
        base64_file_parsers: Optional[Dict[str, Base64FileParser]] = None
    ) -> LoadResult:
        """
        Loads environment variables from a file or directory.

        Args:
            location: Path to file or directory
            pattern: Glob pattern for directory loading
            override: Whether to override existing variables
            computed_definitions: Registry of computed value definitions
            base64_file_parsers: Registry of base64 file parsers
        """
        result = LoadResult()
        files_to_process = []

        if computed_definitions:
            self._computed_definitions.update(computed_definitions)

        if base64_file_parsers:
            self._base64_file_parsers.update(base64_file_parsers)

        if os.path.isfile(location):
            files_to_process.append(location)
        elif os.path.isdir(location):
            # Glob pattern match in directory
            search_path = os.path.join(location, pattern)
            files_to_process = sorted(glob.glob(search_path))
        else:
            result.errors.append({"error": f"Location not found: {location}"})
            return result

        for file_path in files_to_process:
            logger.debug(f"Loading file: {file_path}")
            try:
                # dotenv_values returns a dict of parsed values
                env_vars = dotenv_values(file_path)
                
                logger.debug(f"  status: SUCCESS")
                logger.debug(f"  vars_loaded: {len(env_vars)}")
                logger.trace(f"  keys: {list(env_vars.keys())}")
                
                for key, value in env_vars.items():
                    if value is None: continue 
                    
                    masked_val = mask_value(key, value)
                    exists_in_process = key in os.environ
                    
                    # Log injection
                    if exists_in_process and not override:
                        logger.debug(f"ENV SKIP: {key} (already set, override=false)")
                    elif exists_in_process:
                        existing_val = os.environ[key]
                        logger.debug(f"ENV OVERWRITE: {key} = {masked_val} (was: {mask_value(key, existing_val)})")
                    else:
                        logger.debug(f"ENV SET: {key} = {masked_val}")

                    # Update internal store
                    if override or key not in self._store:
                        self._store[key] = value
                    
                    # Update system env if override or not present
                    if override or not exists_in_process:
                        os.environ[key] = value
                        
                result.files_loaded.append(file_path)
                result.total_vars_loaded += len(env_vars)
                self._loaded_files.append(file_path)
                
            except Exception as e:
                logger.error(f"  status: FAILED")
                logger.error(f"  error: {str(e)}")
                result.errors.append({"file": file_path, "error": str(e)})

        # Clear cache on new load
        self._computed_cache.clear()

        # Process base64 file parsers after env files are loaded
        self._process_base64_file_parsers(result, override)

        self._initialized = True
        return result

    def _process_base64_file_parsers(self, result: LoadResult, override: bool) -> None:
        """
        Process registered base64 file parsers.
        Each parser returns data that gets flattened and merged into the store.
        """
        for prefix, parser in self._base64_file_parsers.items():
            logger.debug(f"Executing base64 parser: {prefix}")
            try:
                # Check for missing source var
                source_value = self.get(prefix)
                if not source_value:
                    logger.warn(f"  source_var: {prefix}")
                    logger.warn(f"  source_value: [UNDEFINED]")
                    logger.warn(f"  status: SKIPPED (source not set)")
                else:
                    logger.debug(f"  source_var: {prefix}")
                    logger.debug(f"  source_value: [PRESENT, {len(source_value)} bytes]")

                parsed = parser(self)

                if parsed is None:
                    continue
                
                logger.debug(f"  format_detected: unknown (parser handled decoding)")

                keys_injected = 0

                # If parsed result is a dict, flatten it with prefix
                if isinstance(parsed, dict):
                    flattened = self._flatten_object(parsed, prefix)

                    for key, value in flattened.items():
                        masked_val = mask_value(key, value)
                        exists_in_process = key in os.environ
                        
                        if exists_in_process and not override:
                            logger.debug(f"ENV SKIP: {key} (already set, override=false)")
                        elif exists_in_process:
                            existing_val = os.environ[key]
                            logger.debug(f"ENV OVERWRITE: {key} = {masked_val} (was: {mask_value(key, existing_val)})")
                            os.environ[key] = value
                            self._store[key] = value
                            keys_injected += 1
                        else:
                            logger.debug(f"ENV SET: {key} = {masked_val}")
                            os.environ[key] = value
                            self._store[key] = value
                            keys_injected += 1

                    result.files_loaded.append(f"base64:{prefix}")
                    result.total_vars_loaded += len(flattened)
                else:
                    # For non-dict values, store directly with prefix as key
                    key = prefix
                    value = str(parsed)
                    masked_val = mask_value(key, value)
                    exists_in_process = key in os.environ

                    if override or not exists_in_process:
                         logger.debug(f"ENV SET/OVERWRITE: {key} = {masked_val}")
                         self._store[key] = value
                         os.environ[key] = value
                         keys_injected += 1

                    result.files_loaded.append(f"base64:{prefix}")
                    result.total_vars_loaded += 1
                
                logger.debug(f"  status: SUCCESS")
                logger.debug(f"  keys_injected: {keys_injected}")

            except Exception as e:
                logger.error(f"  status: FAILED")
                logger.error(f"  error: {str(e)}")
                result.errors.append({"file": f"base64:{prefix}", "error": str(e)})

    def _flatten_object(
        self,
        obj: Dict[str, Any],
        prefix: str = ''
    ) -> Dict[str, str]:
        """
        Flatten a nested object into a flat key-value map.
        Keys are uppercased and joined with underscores.
        Example: { "database": { "host": "localhost" } } => { "DATABASE_HOST": "localhost" }
        """
        result: Dict[str, str] = {}

        for key, value in obj.items():
            new_key = f"{prefix}_{key}".upper() if prefix else key.upper()

            if value is None:
                # Skip None values
                continue
            elif isinstance(value, dict):
                # Recursively flatten nested dicts
                nested = self._flatten_object(value, new_key)
                result.update(nested)
            elif isinstance(value, list):
                # Handle lists by indexing
                for index, item in enumerate(value):
                    array_key = f"{new_key}_{index}"
                    if isinstance(item, dict):
                        nested = self._flatten_object(item, array_key)
                        result.update(nested)
                    else:
                        result[array_key] = str(item)
            else:
                # Convert primitive values to strings
                result[new_key] = str(value)

        return result

    def get(self, key: str) -> Optional[str]:
        # Priority: Internal Store -> System Env (Os.environ)
        # Spec says: Python checks internal first
        return self._store.get(key, os.environ.get(key))

    def get_or_throw(self, key: str) -> str:
        val = self.get(key)
        if val is None:
            raise EnvKeyNotFoundError(f"Environment variable '{key}' not found")
        return val

    def get_computed(self, key: str) -> Any:
        if key in self._computed_cache:
            return self._computed_cache[key]
            
        definition = self._computed_definitions.get(key)
        if not definition:
             raise KeyError(f"Computed value '{key}' not defined")
             
        value = definition(self)
        self._computed_cache[key] = value
        return value

    def get_all(self) -> Dict[str, str]:
        # Merge system env with internal store (internal takes precedence in this view to match get)
        # Or should it be all available? usually merge of both
        merged = os.environ.copy()
        merged.update(self._store)
        return merged

    def is_initialized(self) -> bool:
        return self._initialized

    def get_load_result(self) -> Dict[str, Any]:
        return {
            "loaded_files": self._loaded_files,
            "store_size": len(self._store)
        }

    def reset(self) -> None:
        self._store.clear()
        self._loaded_files.clear()
        self._computed_definitions.clear()
        self._computed_cache.clear()
        self._base64_file_parsers.clear()
        self._initialized = False

    @classmethod
    def on_startup(
        cls,
        location: str,
        pattern: str = ".env*",
        override: bool = False,
        computed_definitions: Optional[Dict[str, ComputedDefinition]] = None,
        base64_file_parsers: Optional[Dict[str, Base64FileParser]] = None
    ) -> 'EnvStore':
        """
        Initialize EnvStore with environment variables from files and optional parsers.

        Args:
            location: Path to file or directory
            pattern: Glob pattern for directory loading
            override: Whether to override existing variables
            computed_definitions: Registry of computed value definitions
            base64_file_parsers: Registry of base64 file parsers
        """
        logger.info('EnvStore.on_startup() called')
        logger.debug(f"  location: {location}")
        logger.debug(f"  pattern: {pattern}")
        logger.debug(f"  override: {override}")
        logger.debug(f"  computed_definitions: {list(computed_definitions.keys()) if computed_definitions else []}")
        logger.debug(f"  base64_file_parsers: {list(base64_file_parsers.keys()) if base64_file_parsers else []}")

        instance = cls()
        result = instance.load(location, pattern, override, computed_definitions, base64_file_parsers)

        logger.info('=== EnvStore Initialization Complete ===')
        logger.info(f"  files_processed: {len(result.files_loaded) + len(result.errors)}")
        logger.info(f"  files_succeeded: {len(result.files_loaded)}")
        logger.info(f"  files_failed: {len(result.errors)}")
        if result.errors:
            logger.warn(f"  errors: {result.errors}")

        return instance

# Global Accessor
env = EnvStore()
