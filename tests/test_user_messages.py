"""
Tests for User Message Providers (UserStartMessages, UserFlowMessages).

Uses semantic assertions to test INTENT not exact wording,
making tests resilient to message variations.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from bot.services.message import LucienVoiceService


# ============================================================================
# TEST CLASS: UserStartMessages
# ============================================================================


class TestUserStartMessages:
    """Test suite for UserStartMessages provider."""

    @pytest.mark.parametrize("hour,expected_period", [
        (9, "morning"),    # 9 AM
        (15, "afternoon"), # 3 PM
        (22, "evening")    # 10 PM
    ])
    def test_greeting_time_aware(self, assert_time_aware, hour, expected_period):
        """Test greeting adapts to time of day."""
        # Mock datetime to specific hour
        mock_datetime = datetime(2026, 1, 24, hour, 0, 0, tzinfo=timezone.utc)

        with patch('bot.services.message.user_start.datetime') as mock_dt:
            mock_dt.now.return_value = mock_datetime

            service = LucienVoiceService()
            text, keyboard = service.user.start.greeting(
                first_name="Juan",
                is_admin=False,
                is_vip=False
            )

            # Validate time-appropriate greeting
            assert_time_aware(text, expected_period)

    def test_greeting_admin_redirect(self):
        """Test admin greeting redirects to /admin without keyboard."""
        service = LucienVoiceService()
        text, keyboard = service.user.start.greeting(
            first_name="Admin",
            is_admin=True,
            is_vip=False
        )

        # Admin should be redirected to /admin
        assert "/admin" in text.lower()

        # No keyboard for admin (they use /admin command)
        assert keyboard is None

    def test_greeting_vip_shows_days(self):
        """Test VIP greeting shows days remaining."""
        service = LucienVoiceService()
        text, keyboard = service.user.start.greeting(
            first_name="VIPUser",
            is_admin=False,
            is_vip=True,
            vip_days_remaining=15
        )

        # Must show days remaining
        assert "15" in text

        # Should mention VIP status or exclusive access
        text_lower = text.lower()
        vip_indicators = ["vip", "exclusivo", "privilegio", "círculo"]
        assert any(indicator in text_lower for indicator in vip_indicators)

        # No keyboard for VIP (already has access)
        assert keyboard is None

    def test_greeting_free_has_options_keyboard(self):
        """Test free user greeting has options keyboard."""
        service = LucienVoiceService()
        text, keyboard = service.user.start.greeting(
            first_name="FreeUser",
            is_admin=False,
            is_vip=False
        )

        # Must have keyboard with 2 options
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) == 2  # 2 rows

        # Check buttons exist (text can vary)
        button_texts = [
            row[0].text for row in keyboard.inline_keyboard
        ]
        assert len(button_texts) == 2

        # Callback data should be present
        callback_data = [
            row[0].callback_data for row in keyboard.inline_keyboard
        ]
        assert all(data for data in callback_data)

    def test_greeting_variations_distribution(self, assert_greeting_present):
        """Test greeting uses multiple variations (not always same text)."""
        service = LucienVoiceService()

        # Generate 30 greetings (catches all variants with >99% confidence)
        greetings = []
        for _ in range(30):
            text, _ = service.user.start.greeting(
                first_name="Test",
                is_admin=False,
                is_vip=False
            )
            greetings.append(text)

            # All must have greeting
            assert_greeting_present(text)

        # Should have at least 2 unique variations
        # (Use >=2 not ==3 to handle <1% randomness edge case)
        unique_greetings = set(greetings)
        assert len(unique_greetings) >= 2, \
            f"Expected variations, got {len(unique_greetings)} unique from 30 iterations"

    def test_deep_link_activation_success_celebratory(self):
        """Test deep link activation success has celebratory tone."""
        service = LucienVoiceService()
        text, keyboard = service.user.start.deep_link_activation_success(
            plan_name="Plan Mensual",
            expiry_date="2026-02-24 06:00",
            invite_link="https://t.me/+ABC123"
        )

        # Celebratory indicators
        text_lower = text.lower()
        celebratory = ["activado", "activada", "bienvenido", "felicidades", "éxito"]
        assert any(word in text_lower for word in celebratory), \
            "Success message should be celebratory"

        # Must show plan details
        assert "Plan Mensual" in text or "mensual" in text_lower

        # Must show expiry date
        assert "2026-02-24" in text or "24" in text

        # Must show invite link
        assert "https://t.me/+ABC123" in text

        # Should have keyboard to join channel
        assert keyboard is not None

    @pytest.mark.parametrize("error_type,expected_keywords", [
        ("invalid", ["inválido", "válido"]),
        ("used", ["usado", "utilizado"]),
        ("expired", ["expirado", "caducado", "vencido"]),
        ("no_plan", ["plan", "disponible"])
    ])
    def test_deep_link_activation_error_types(self, error_type, expected_keywords):
        """Test deep link activation errors have appropriate messaging."""
        service = LucienVoiceService()
        text = service.user.start.deep_link_activation_error(error_type=error_type)

        # Check for expected keywords (any one of them)
        text_lower = text.lower()
        has_keyword = any(keyword in text_lower for keyword in expected_keywords)
        assert has_keyword, \
            f"Error type '{error_type}' should mention: {expected_keywords}"

    @pytest.mark.parametrize("method_name,kwargs", [
        ("greeting", {
            "first_name": "Test",
            "is_admin": False,
            "is_vip": False
        }),
        ("deep_link_activation_success", {
            "plan_name": "Plan Test",
            "expiry_date": "2026-02-24 06:00",
            "invite_link": "https://t.me/+TEST"
        }),
        ("deep_link_activation_error", {
            "error_type": "invalid"
        })
    ])
    def test_all_messages_maintain_lucien_voice(self, assert_lucien_voice, method_name, kwargs):
        """Test all UserStartMessages maintain Lucien's voice."""
        service = LucienVoiceService()
        method = getattr(service.user.start, method_name)

        result = method(**kwargs)

        # Extract text (method returns tuple or str)
        text = result[0] if isinstance(result, tuple) else result

        # Validate voice characteristics
        assert_lucien_voice(text)
