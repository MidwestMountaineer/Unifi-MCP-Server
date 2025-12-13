"""Unit tests for IPS (Intrusion Prevention System) tool.

Tests the GetIPSStatusTool with v2 API support:
- IPS status retrieval via get_security_data
- Threat statistics calculation
- Alert filtering and formatting
- Data formatting for AI consumption
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from unifi_mcp.tools.security import GetIPSStatusTool
from unifi_mcp.tools.base import ToolError


# Mock IPS normalized data (as returned by get_security_data)
def create_ips_response(enabled=True, api_version="v1", controller_type="traditional"):
    """Create a mock get_security_data response for IPS status."""
    return {
        "data": {
            "enabled": enabled,
            "enabled_display": "yes" if enabled else "no",
            "protection_mode": "prevention" if enabled else "detection",
            "suppression_enabled": True,
            "suppression_mode": "auto",
            "signature_version": "5.0.123",
            "last_signature_update": "2025-10-08T10:30:00Z",
            "threat_statistics": {
                "total_events": 31,
                "blocked_events": 18,
                "alerted_events": 13,
                "categories": {
                    "malware": 20,
                    "exploit": 8,
                    "trojan": 3,
                },
            },
            "api_version": api_version,
        },
        "api_version": api_version,
        "controller_type": controller_type,
    }


# Mock alert data
MOCK_ALERTS = [
    {
        "_id": "alert1",
        "key": "EVT_IPS_Alert",
        "msg": "Malware detected from 192.168.30.50",
        "time": 1728380400,
        "datetime": "2025-10-08T10:00:00Z",
        "subsystem": "ips",
        "src_ip": "192.168.30.50",
        "dst_ip": "8.8.8.8",
        "signature_id": "2024001",
        "catname": "malware",
        "archived": False,
    },
    {
        "_id": "alert2",
        "key": "EVT_IPS_IDS_Threat",
        "msg": "Exploit attempt detected",
        "time": 1728380300,
        "datetime": "2025-10-08T09:58:20Z",
        "subsystem": "ids",
        "src_ip": "192.168.30.75",
        "dst_ip": "192.168.10.100",
        "signature_id": "2024002",
        "catname": "exploit",
        "archived": False,
    },
    {
        "_id": "alert3",
        "key": "EVT_AP_Disconnected",
        "msg": "Access point disconnected",
        "time": 1728380200,
        "datetime": "2025-10-08T09:56:40Z",
        "subsystem": "wlan",
        "src_ip": "",
        "dst_ip": "",
        "signature_id": "",
        "catname": "connectivity",
        "archived": False,
    },
]


@pytest.fixture
def mock_client():
    """Create a mock UniFi client with get_security_data support."""
    client = MagicMock()
    client.get = AsyncMock()
    client.get_security_data = AsyncMock()
    return client


class TestGetIPSStatusTool:
    """Tests for GetIPSStatusTool with v2 API support."""

    @pytest.mark.asyncio
    async def test_get_ips_status_basic(self, mock_client):
        """Test basic IPS status retrieval without alerts."""
        # Setup mock responses
        mock_client.get_security_data.return_value = create_ips_response(enabled=True)

        # Create tool and invoke without alerts
        tool = GetIPSStatusTool()
        result = await tool.invoke(mock_client, {"include_alerts": False})

        # Verify result structure
        assert result["success"] is True
        assert "data" in result

        # Verify IPS status
        ips_status = result["data"]
        assert ips_status["enabled"] == "yes"
        assert ips_status["enabled_bool"] is True

        # Verify get_security_data was called
        mock_client.get_security_data.assert_called_once_with("ips_status")

    @pytest.mark.asyncio
    async def test_get_ips_status_with_alerts(self, mock_client):
        """Test IPS status retrieval with alerts included."""
        # Setup mock responses
        mock_client.get_security_data.return_value = create_ips_response(enabled=True)
        mock_client.get.return_value = {"data": MOCK_ALERTS}

        # Create tool and invoke with alerts
        tool = GetIPSStatusTool()
        result = await tool.invoke(mock_client, {"include_alerts": True})

        # Verify result
        assert result["success"] is True
        ips_status = result["data"]

        # Verify alerts are included
        assert "recent_alerts" in ips_status
        assert "total_alerts" in ips_status

        # Should only include IPS-related alerts (2 out of 3)
        assert ips_status["total_alerts"] == 2
        assert len(ips_status["recent_alerts"]) == 2

    @pytest.mark.asyncio
    async def test_get_ips_status_alert_limit(self, mock_client):
        """Test IPS status with alert limit."""
        # Create more alerts
        many_alerts = [
            {
                "_id": f"alert{i}",
                "key": "EVT_IPS_Alert",
                "msg": f"Alert {i}",
                "time": 1728380000 + i,
                "datetime": f"2025-10-08T09:00:{i:02d}Z",
                "subsystem": "ips",
                "src_ip": f"192.168.30.{i}",
                "dst_ip": "8.8.8.8",
                "signature_id": f"202400{i}",
                "catname": "malware",
                "archived": False,
            }
            for i in range(50)
        ]

        # Setup mock responses
        mock_client.get_security_data.return_value = create_ips_response(enabled=True)
        mock_client.get.return_value = {"data": many_alerts}

        # Create tool and invoke with alert limit
        tool = GetIPSStatusTool()
        result = await tool.invoke(
            mock_client,
            {"include_alerts": True, "alert_limit": 10}
        )

        # Verify result
        assert result["success"] is True
        ips_status = result["data"]

        # Should limit to 10 alerts
        assert ips_status["total_alerts"] == 50
        assert len(ips_status["recent_alerts"]) == 10

    @pytest.mark.asyncio
    async def test_get_ips_status_disabled(self, mock_client):
        """Test IPS status when IPS is disabled."""
        # Setup mock responses with disabled IPS
        disabled_response = create_ips_response(enabled=False)
        disabled_response["data"]["threat_statistics"] = {
            "total_events": 0,
            "blocked_events": 0,
            "alerted_events": 0,
            "categories": {},
        }
        mock_client.get_security_data.return_value = disabled_response

        # Create tool and invoke
        tool = GetIPSStatusTool()
        result = await tool.invoke(mock_client, {"include_alerts": False})

        # Verify result
        assert result["success"] is True
        ips_status = result["data"]
        assert ips_status["enabled"] == "no"
        assert ips_status["enabled_bool"] is False

    @pytest.mark.asyncio
    async def test_get_ips_status_no_config(self, mock_client):
        """Test IPS status when no configuration exists."""
        # Setup mock responses with empty/default config
        empty_response = {
            "data": {
                "enabled": False,
                "enabled_display": "no",
                "protection_mode": "detection",
                "suppression_enabled": False,
                "suppression_mode": "",
                "signature_version": "",
                "last_signature_update": "",
                "threat_statistics": {
                    "total_events": 0,
                    "blocked_events": 0,
                    "alerted_events": 0,
                    "categories": {},
                },
                "api_version": "v1",
            },
            "api_version": "v1",
            "controller_type": "traditional",
        }
        mock_client.get_security_data.return_value = empty_response

        # Create tool and invoke
        tool = GetIPSStatusTool()
        result = await tool.invoke(mock_client, {"include_alerts": False})

        # Verify result - should handle gracefully
        assert result["success"] is True
        ips_status = result["data"]
        assert ips_status["enabled"] == "no"
        assert ips_status["enabled_bool"] is False

    @pytest.mark.asyncio
    async def test_get_ips_status_api_error(self, mock_client):
        """Test IPS status retrieval with API error."""
        # Setup mock to raise exception
        mock_client.get_security_data.side_effect = Exception("Connection timeout")

        # Create tool and invoke
        tool = GetIPSStatusTool()
        result = await tool.invoke(mock_client, {})

        # Should return error response (not raise exception)
        assert "error" in result
        assert result["error"]["code"] == "API_ERROR"
        assert "Failed to retrieve IPS status" in result["error"]["message"]
        assert "Connection timeout" in result["error"]["details"]
        assert len(result["error"]["actionable_steps"]) > 0

    @pytest.mark.asyncio
    async def test_threat_statistics_calculation(self, mock_client):
        """Test threat statistics from normalized response."""
        # Create response with specific statistics
        response = create_ips_response(enabled=True)
        response["data"]["threat_statistics"] = {
            "total_events": 190,
            "blocked_events": 150,
            "alerted_events": 35,
            "categories": {
                "malware": 110,
                "exploit": 50,
                "trojan": 25,
                "other": 5,
            },
        }
        mock_client.get_security_data.return_value = response

        # Create tool and invoke
        tool = GetIPSStatusTool()
        result = await tool.invoke(mock_client, {"include_alerts": False})

        # Verify statistics are passed through
        threat_stats = result["data"]["threat_statistics"]
        assert threat_stats["total_events"] == 190
        assert threat_stats["blocked_events"] == 150
        assert threat_stats["alerted_events"] == 35

    @pytest.mark.asyncio
    async def test_alert_filtering(self, mock_client):
        """Test that only IPS-related alerts are included."""
        # Create mixed alerts
        mixed_alerts = [
            {"_id": "1", "key": "EVT_IPS_Alert", "msg": "IPS alert", "time": 1, "datetime": "2025-10-08T10:00:00Z", "subsystem": "ips", "src_ip": "", "dst_ip": "", "signature_id": "", "catname": "", "archived": False},
            {"_id": "2", "key": "EVT_IDS_Threat", "msg": "IDS threat", "time": 2, "datetime": "2025-10-08T10:00:01Z", "subsystem": "ids", "src_ip": "", "dst_ip": "", "signature_id": "", "catname": "", "archived": False},
            {"_id": "3", "key": "EVT_Intrusion_Detected", "msg": "Intrusion", "time": 3, "datetime": "2025-10-08T10:00:02Z", "subsystem": "security", "src_ip": "", "dst_ip": "", "signature_id": "", "catname": "", "archived": False},
            {"_id": "4", "key": "EVT_AP_Lost", "msg": "AP lost", "time": 4, "datetime": "2025-10-08T10:00:03Z", "subsystem": "wlan", "src_ip": "", "dst_ip": "", "signature_id": "", "catname": "", "archived": False},
            {"_id": "5", "key": "EVT_Threat_Blocked", "msg": "Threat blocked", "time": 5, "datetime": "2025-10-08T10:00:04Z", "subsystem": "security", "src_ip": "", "dst_ip": "", "signature_id": "", "catname": "", "archived": False},
            {"_id": "6", "key": "EVT_Attack_Detected", "msg": "Attack", "time": 6, "datetime": "2025-10-08T10:00:05Z", "subsystem": "security", "src_ip": "", "dst_ip": "", "signature_id": "", "catname": "", "archived": False},
        ]

        # Setup mock responses
        mock_client.get_security_data.return_value = create_ips_response(enabled=True)
        mock_client.get.return_value = {"data": mixed_alerts}

        # Create tool and invoke
        tool = GetIPSStatusTool()
        result = await tool.invoke(mock_client, {"include_alerts": True})

        # Verify only IPS-related alerts are included
        # Should match: ips, ids, intrusion, threat, attack (5 out of 6)
        assert result["data"]["total_alerts"] == 5

        # Verify the non-IPS alert is excluded
        alert_ids = [alert["id"] for alert in result["data"]["recent_alerts"]]
        assert "4" not in alert_ids  # EVT_AP_Lost should be excluded

    @pytest.mark.asyncio
    async def test_data_formatting(self, mock_client):
        """Test that data is properly formatted for AI consumption."""
        # Setup mock responses
        mock_client.get_security_data.return_value = create_ips_response(enabled=True)
        mock_client.get.return_value = {"data": MOCK_ALERTS[:2]}  # Only IPS alerts

        # Create tool and invoke
        tool = GetIPSStatusTool()
        result = await tool.invoke(mock_client, {"include_alerts": True})

        # Verify result structure is AI-friendly
        assert result["success"] is True
        assert result["type"] == "ips_status"

        ips_status = result["data"]

        # Verify all expected fields are present
        assert "enabled" in ips_status
        assert "threat_statistics" in ips_status
        assert "recent_alerts" in ips_status
        assert "total_alerts" in ips_status

    @pytest.mark.asyncio
    async def test_v2_api_metadata(self, mock_client):
        """Test that v2 API metadata is included in response."""
        mock_client.get_security_data.return_value = create_ips_response(
            enabled=True, api_version="v2", controller_type="unifi_os"
        )

        tool = GetIPSStatusTool()
        result = await tool.invoke(mock_client, {"include_alerts": False})

        assert result["success"] is True
        assert result["api_version"] == "v2"
        assert result["controller_type"] == "unifi_os"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
