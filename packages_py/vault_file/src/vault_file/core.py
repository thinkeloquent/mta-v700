import base64
import json
import os
import re
import tempfile
from dataclasses import asdict
from typing import Dict, Any, Optional, Union, Tuple

import yaml
from dotenv import dotenv_values

from .domain import VaultHeader, VaultMetadata, VaultPayload
from .validators import validate_vault_data, VaultValidationError, VaultSerializationError
from .logger import get_logger

logger = get_logger()

class VaultFile:
    def __init__(
        self, 
        header: Optional[Union[VaultHeader, Dict[str, Any]]] = None,
        metadata: Optional[Union[VaultMetadata, Dict[str, Any]]] = None,
        payload: Optional[Union[VaultPayload, Dict[str, Any]]] = None
    ):
        if isinstance(header, dict):
            self.header = VaultHeader.from_dict(header)
        elif header is None:
            self.header = VaultHeader()
        else:
            self.header = header

        if isinstance(metadata, dict):
            self.metadata = VaultMetadata.from_dict(metadata)
        elif metadata is None:
            self.metadata = VaultMetadata()
        else:
            self.metadata = metadata

        if isinstance(payload, dict):
            self.payload = VaultPayload.from_dict(payload)
        elif payload is None:
            self.payload = VaultPayload()
        else:
            self.payload = payload

    def to_dict(self) -> Dict[str, Any]:
        return {
            "header": self.header.to_dict(),
            "metadata": self.metadata.to_dict(),
            "payload": self.payload.to_dict()
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'VaultFile':
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise VaultSerializationError(f"Invalid JSON: {e}")

        try:
            validate_vault_data(data)
        except VaultValidationError as e:
            raise VaultSerializationError(f"Validation failed: {e}")

        return cls(
            header=data.get("header"),
            metadata=data.get("metadata"),
            payload=data.get("payload")
        )

    BASE64_PREFIX = "data:application/json;base64,"

    # MIME type constants for format detection
    MIME_JSON = "application/json"
    MIME_YAML = "application/x-yaml"
    MIME_YAML_ALT = "text/x-yaml"
    MIME_PROPERTIES = "text/x-properties"
    MIME_PLAIN = "text/plain"

    SUPPORTED_MIME_TYPES = [MIME_JSON, MIME_YAML, MIME_YAML_ALT, MIME_PROPERTIES, MIME_PLAIN]

    @classmethod
    def from_base64_file(cls, data_uri: str) -> 'VaultFile':
        """
        Parse a VaultFile from a base64-encoded data URI.
        Format: data:application/json;base64,<BASE64 Encoded String>
        """
        logger.debug('Parsing VaultFile from base64 data URI')
        if not data_uri.startswith(cls.BASE64_PREFIX):
            raise VaultSerializationError(
                f"Invalid base64 data URI format. Expected prefix: {cls.BASE64_PREFIX}"
            )

        base64_data = data_uri[len(cls.BASE64_PREFIX):]

        try:
            json_str = base64.b64decode(base64_data).decode('utf-8')
            return cls.from_json(json_str)
        except VaultSerializationError:
            raise
        except Exception as e:
            raise VaultSerializationError(f"Failed to decode base64: {e}")

    def to_base64_file(self) -> str:
        """
        Serialize this VaultFile to a base64-encoded data URI.
        Format: data:application/json;base64,<BASE64 Encoded String>
        """
        json_str = self.to_json()
        base64_data = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
        return f"{self.BASE64_PREFIX}{base64_data}"

    @classmethod
    def decode_base64(cls, data_uri: str) -> Tuple[str, str]:
        """
        Decode a base64 data URI to raw string (without parsing).
        Extracts MIME type and returns decoded content.

        Args:
            data_uri: The data URI in format: data:<mime>;base64,<content>

        Returns:
            Tuple of (decoded content, MIME type)
        """
        pattern = r'^data:([^;]+);base64,(.+)$'
        match = re.match(pattern, data_uri)

        if not match:
            raise VaultSerializationError(
                "Invalid base64 data URI format. Expected: data:<mime>;base64,<content>"
            )

        mime_type = match.group(1)
        base64_data = match.group(2)

        try:
            content = base64.b64decode(base64_data).decode('utf-8')
            return content, mime_type
        except Exception as e:
            logger.error(f"Failed to decode base64: {e}")
            raise VaultSerializationError(f"Failed to decode base64: {e}")

    @classmethod
    def from_base64_auto(cls, data_uri: str) -> Tuple[Any, str]:
        """
        Auto-detect format from MIME type in data URI and parse accordingly.

        Args:
            data_uri: The data URI with MIME type

        Returns:
            Tuple of (parsed content, format name)
        """
        content, mime_type = cls.decode_base64(data_uri)
        logger.debug(f"Auto-detecting format for MIME: {mime_type}")

        if mime_type == cls.MIME_JSON:
            try:
                return json.loads(content), 'json'
            except json.JSONDecodeError as e:
                raise VaultSerializationError(f"Failed to parse JSON: {e}")

        elif mime_type in (cls.MIME_YAML, cls.MIME_YAML_ALT):
            try:
                return yaml.safe_load(content), 'yaml'
            except yaml.YAMLError as e:
                raise VaultSerializationError(f"Failed to parse YAML: {e}")

        elif mime_type in (cls.MIME_PROPERTIES, cls.MIME_PLAIN):
            try:
                # Parse as .env format using dotenv
                from io import StringIO
                return dict(dotenv_values(stream=StringIO(content))), 'properties'
            except Exception as e:
                raise VaultSerializationError(f"Failed to parse properties: {e}")

        else:
            raise VaultSerializationError(
                f"Unsupported MIME type: {mime_type}. Supported types: {', '.join(cls.SUPPORTED_MIME_TYPES)}"
            )

    @classmethod
    def from_yaml(cls, yaml_str: str) -> 'VaultFile':
        """
        Parse a VaultFile from a YAML string.
        The YAML should contain header, metadata, and payload structure.
        """
        try:
            data = yaml.safe_load(yaml_str)

            if not isinstance(data, dict):
                raise VaultSerializationError("YAML content must be an object")

            try:
                validate_vault_data(data)
            except VaultValidationError as e:
                raise VaultSerializationError(f"Validation failed: {e}")

            return cls(
                header=data.get("header"),
                metadata=data.get("metadata"),
                payload=data.get("payload")
            )

        except VaultSerializationError:
            raise
        except yaml.YAMLError as e:
            raise VaultSerializationError(f"Failed to parse YAML: {e}")
        except Exception as e:
            raise VaultSerializationError(f"Failed to parse YAML: {e}")

    @classmethod
    def from_property_file(cls, prop_str: str) -> 'VaultFile':
        """
        Parse a VaultFile from a property file string (.env format).
        Each line is key=value, which is stored in payload.content.
        """
        try:
            from io import StringIO
            parsed = dict(dotenv_values(stream=StringIO(prop_str)))

            # Create a VaultFile with the parsed properties as payload content
            return cls(
                header=None,  # auto-generate header
                metadata=VaultMetadata(data={}),  # empty metadata
                payload=VaultPayload(content=parsed)
            )

        except Exception as e:
            raise VaultSerializationError(f"Failed to parse property file: {e}")

    def to_yaml(self) -> str:
        """
        Serialize this VaultFile to YAML format.
        """
        return yaml.dump(self.to_dict(), default_flow_style=False)

    def save_to_disk(self, path: str) -> None:
        """Atomic write to disk"""
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        # Write to temp file first
        fd, temp_path = tempfile.mkstemp(dir=directory, text=True)
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(self.to_json())
            # Atomic rename
            os.replace(temp_path, path)
        except Exception as e:
            os.unlink(temp_path)
            raise e

    @classmethod
    def load_from_disk(cls, path: str) -> 'VaultFile':
        if not os.path.exists(path):
            raise FileNotFoundError(f"Vault file not found: {path}")

        with open(path, 'r') as f:
            content = f.read()

        return cls.from_json(content)

    def update(
        self,
        header: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None
    ) -> 'VaultFile':
        """
        Update this instance with partial data.
        Header fields are selectively updated, metadata.data and payload.content are replaced.
        Returns self for chaining.
        """
        if header:
            if 'id' in header:
                self.header.id = header['id']
            if 'version' in header:
                self.header.version = header['version']
            if 'created_at' in header:
                from datetime import datetime
                if isinstance(header['created_at'], str):
                    self.header.created_at = datetime.fromisoformat(header['created_at'])
                else:
                    self.header.created_at = header['created_at']

        if metadata and 'data' in metadata:
            self.metadata.data = metadata['data']

        if payload and 'content' in payload:
            self.payload.content = payload['content']

        return self

    def merge(self, other: 'VaultFile') -> 'VaultFile':
        """
        Deep merge another VaultFile into this instance.
        - Header: other's fields override this (except id)
        - Metadata.data: deep merged (other overrides conflicts)
        - Payload.content: replaced by other's content
        Returns self for chaining.
        """
        original_id = self.header.id

        # Merge header (preserve original id)
        self.header.version = other.header.version
        self.header.created_at = other.header.created_at
        self.header.id = original_id

        # Deep merge metadata.data
        self.metadata.data = self._deep_merge(self.metadata.data, other.metadata.data)

        # Replace payload content if other has content
        if other.payload.content is not None:
            self.payload.content = other.payload.content

        return self

    def merge_from_json(self, json_str: str) -> 'VaultFile':
        """
        Merge from JSON string into this instance.
        Returns self for chaining.
        """
        other = VaultFile.from_json(json_str)
        return self.merge(other)

    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge source into target. Source values override target on conflict."""
        result = dict(target)
        for key, val in source.items():
            if (
                isinstance(val, dict) and not isinstance(val, list) and
                key in result and isinstance(result[key], dict) and not isinstance(result[key], list)
            ):
                result[key] = self._deep_merge(result[key], val)
            else:
                result[key] = val
        return result
