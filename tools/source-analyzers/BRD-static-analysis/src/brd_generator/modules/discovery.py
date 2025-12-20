import os
from pathlib import Path
from typing import List, Dict, Set
from enum import Enum
from pydantic import BaseModel

class FileType(str, Enum):
    MODEL = "model"
    CONTROLLER = "controller"
    SERVICE = "service"
    UTILITY = "utility"
    CONFIG = "config"
    TEST = "test"
    UNKNOWN = "unknown"

class SourceFile(BaseModel):
    path: str
    name: str
    extension: str
    file_type: FileType
    language: str

class DiscoveryEngine:
    """
    Scans directories and classifies files based on heuristics.
    """
    def __init__(self, root_path: str, ignore_patterns: List[str] = None):
        self.root_path = Path(root_path)
        self.ignore_patterns = set(ignore_patterns or [])
        # Basic ignore list
        self.ignore_patterns.update({'.git', '__pycache__', 'node_modules', 'dist', 'build', 'venv', '.env'})

    def scan(self) -> List[SourceFile]:
        discovered_files = []
        
        for root, dirs, files in os.walk(self.root_path):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignore_patterns]
            
            for file in files:
                if file.startswith('.'): continue
                
                file_path = Path(root) / file
                if self._should_ignore(file_path):
                    continue
                
                source_file = self._classify_file(file_path)
                if source_file:
                    discovered_files.append(source_file)
                    
        return discovered_files

    def _should_ignore(self, path: Path) -> bool:
        # Simple containment check, could be enhanced with glob matching
        parts = set(path.parts)
        return not self.ignore_patterns.isdisjoint(parts)

    def _classify_file(self, path: Path) -> SourceFile:
        ext = path.suffix.lower()
        name = path.name.lower()
        parent = path.parent.name.lower()
        
        language = "unknown"
        if ext in ['.py']: language = "python"
        elif ext in ['.js', '.mjs', '.cjs']: language = "javascript"
        elif ext in ['.ts', '.tsx']: language = "typescript"
        elif ext in ['.rs']: language = "rust"
        else: return None # Skip unsupported files for now

        file_type = FileType.UNKNOWN
        
        # Heuristics
        if 'test' in name or 'spec' in name or 'tests' in path.parts:
            file_type = FileType.TEST
        elif 'model' in name or 'schema' in name or 'entity' in name or 'models' in path.parts:
            file_type = FileType.MODEL
        elif 'controller' in name or 'route' in name or 'api' in name or 'view' in path.parts:
            file_type = FileType.CONTROLLER
        elif 'service' in name or 'manager' in name:
            file_type = FileType.SERVICE
        elif 'util' in name or 'helper' in name or 'common' in path.parts:
            file_type = FileType.UTILITY
        elif 'config' in name or 'setting' in name:
            file_type = FileType.CONFIG

        return SourceFile(
            path=str(path),
            name=path.name,
            extension=ext,
            file_type=file_type,
            language=language
        )
