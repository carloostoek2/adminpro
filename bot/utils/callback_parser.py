"""
Callback Parser Utility - Safe parsing of Telegram callback data.

Provides type-safe parsing of callback data with validation and error handling.
Prevents common bugs from index-based string splitting.
"""
import logging
from typing import Dict, Optional, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CallbackData:
    """
    Typed callback data container with safe access.

    Attributes:
        action: Main action identifier (e.g., "admin")
        entity: Entity type (e.g., "user", "users")
        operation: Operation to perform (e.g., "view", "role", "expel")
        params: Dictionary of additional parameters
        raw: Original raw callback data string
    """
    action: str
    entity: str
    operation: str
    params: Dict[str, Any]
    raw: str

    def get_int(self, key: str, default: Optional[int] = None) -> Optional[int]:
        """
        Safely get a parameter as integer.

        Args:
            key: Parameter key
            default: Default value if key not found or invalid

        Returns:
            Integer value or default
        """
        value = self.params.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"⚠️ Cannot convert {key}={value} to int")
            return default

    def get_str(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Safely get a parameter as string.

        Args:
            key: Parameter key
            default: Default value if key not found

        Returns:
            String value or default
        """
        return self.params.get(key, default)

    def has(self, key: str) -> bool:
        """Check if parameter exists."""
        return key in self.params

    def __repr__(self) -> str:
        return f"CallbackData(action={self.action}, entity={self.entity}, operation={self.operation}, params={self.params})"


class CallbackParser:
    """
    Parser for Telegram callback data with type-safe access.

    Callback format: "prefix:entity:operation:param1:value1:param2:value2..."

    Examples:
        "admin:user:view:123:overview" -> action="admin", entity="user", operation="view", params={"user_id": "123", "tab": "overview"}
        "admin:user:role:confirm:123:vip" -> action="admin", entity="user", operation="role", params={"confirm": "123", "role": "vip"}
    """

    # Common parameter names for automatic detection
    PARAM_NAMES = {
        "user_id": 3,  # admin:user:view:{user_id}
        "page": 3,     # admin:users:page:{page}
        "filter": 4,   # admin:users:page:{page}:{filter}
        "tab": 4,      # admin:user:view:{user_id}:{tab}
        "role": 5,     # admin:user:role:confirm:{user_id}:{role}
        "confirm": 4,  # admin:user:role:confirm:{user_id}
        "expel": 4,    # admin:user:expel:confirm:{user_id}
        "block": 3,    # admin:user:block:{user_id}
    }

    @classmethod
    def parse(cls, callback_data: str, pattern: Optional[List[str]] = None) -> CallbackData:
        """
        Parse callback data string into typed CallbackData.

        Args:
            callback_data: Raw callback data from Telegram
            pattern: Optional list of parameter names for explicit mapping.
                     If None, uses automatic detection based on position.

        Returns:
            CallbackData object with parsed values

        Raises:
            ValueError: If callback_data is malformed (too short)
        """
        if not callback_data:
            raise ValueError("Callback data cannot be empty")

        parts = callback_data.split(":")

        if len(parts) < 3:
            raise ValueError(
                f"Invalid callback data format: '{callback_data}'. "
                f"Expected at least 3 parts separated by ':', got {len(parts)}"
            )

        # Extract base components
        action = parts[0]
        entity = parts[1]
        operation = parts[2]

        # Parse parameters
        params = cls._parse_params(parts, pattern)

        return CallbackData(
            action=action,
            entity=entity,
            operation=operation,
            params=params,
            raw=callback_data
        )

    @classmethod
    def _parse_params(cls, parts: List[str], pattern: Optional[List[str]]) -> Dict[str, str]:
        """
        Extract parameters from callback parts.

        Args:
            parts: Split callback data parts
            pattern: Optional parameter name list

        Returns:
            Dictionary of parameter names to values
        """
        params = {}

        if pattern:
            # Use explicit pattern mapping
            for i, name in enumerate(pattern, start=3):
                if i < len(parts):
                    params[name] = parts[i]
        else:
            # Auto-detect based on known patterns
            if len(parts) > 3:
                # Check for special keywords in parts
                if "confirm" in parts:
                    confirm_idx = parts.index("confirm")
                    if confirm_idx + 1 < len(parts):
                        params["confirm"] = parts[confirm_idx + 1]
                        # After confirm, next part might be role or other value
                        if confirm_idx + 2 < len(parts):
                            params["role"] = parts[confirm_idx + 2]
                    # User ID is before "confirm"
                    if confirm_idx > 3:
                        params["user_id"] = parts[confirm_idx - 1]
                elif "page" in parts[2]:
                    # admin:users:page:{page}:{filter}
                    if len(parts) > 3:
                        params["page"] = parts[3]
                    if len(parts) > 4:
                        params["filter"] = parts[4]
                else:
                    # Default: treat index 3 as user_id
                    if len(parts) > 3:
                        params["user_id"] = parts[3]
                    # Index 4 might be tab or other secondary parameter
                    if len(parts) > 4:
                        if parts[4] in ["overview", "subscription", "activity", "interests"]:
                            params["tab"] = parts[4]
                        elif parts[4] in ["all", "vip", "free"]:
                            params["filter"] = parts[4]
                        else:
                            params["extra"] = parts[4]

        return params

    @classmethod
    def parse_or_none(cls, callback_data: str, pattern: Optional[List[str]] = None) -> Optional[CallbackData]:
        """
        Parse callback data, returning None on error instead of raising.

        Args:
            callback_data: Raw callback data from Telegram
            pattern: Optional parameter name list

        Returns:
            CallbackData object or None if parsing fails
        """
        try:
            return cls.parse(callback_data, pattern)
        except (ValueError, IndexError) as e:
            logger.warning(f"⚠️ Failed to parse callback data '{callback_data}': {e}")
            return None


# Convenience functions for common patterns

def parse_user_view_callback(callback_data: str) -> Optional[CallbackData]:
    """
    Parse user detail view callback.

    Expected format: "admin:user:view:{user_id}:{tab}"
    """
    return CallbackParser.parse_or_none(callback_data, pattern=["user_id", "tab"])


def parse_user_role_callback(callback_data: str) -> Optional[CallbackData]:
    """
    Parse user role change callback.

    Expected formats:
    - "admin:user:role:{user_id}"
    - "admin:user:role:confirm:{user_id}:{role}"
    """
    return CallbackParser.parse_or_none(callback_data)


def parse_user_expel_callback(callback_data: str) -> Optional[CallbackData]:
    """
    Parse user expulsion callback.

    Expected formats:
    - "admin:user:expel:{user_id}"
    - "admin:user:expel:confirm:{user_id}"
    """
    return CallbackParser.parse_or_none(callback_data)


def parse_users_list_callback(callback_data: str) -> Optional[CallbackData]:
    """
    Parse users list callback.

    Expected formats:
    - "admin:users:list:{filter}"
    - "admin:users:page:{page}:{filter}"
    """
    return CallbackParser.parse_or_none(callback_data)
