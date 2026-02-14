"""Unit tests for IPS (Intrusion Prevention System) tool.

Tests the GetIPSStatusTool implemented in Task 16:
- IPS status retrieval
- Threat statistics calculation
- Alert filtering and formatting
- Data formatting for AI consumption
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from unifi_mcp.tools.security import GetIPSStatusTool
from unifi_mcp.tools.base import ToolError


# Mock IPS configuration data
MOCK_IPS_CONFIG = [
    {
        "_id": "ips_config",
        "key": "ips",
        "enabled": True,
        "suppression_enabled": True,
        "suppression_mode": "auto",
        "signature_version": "5.0.123",
        "last_signature_update": "2025-10-08T10:30:00Z",
    }
]

# Mock IPS statistics data
MOCK_IPS_STATS = [
    {
        "action": "blocked",
        "category": "malware",
        "count": 15,
    },
    {
        "action": "alerted",
        "category": "exploit",
        "count": 8,
    },
    {
        "action": "blocked",
        "category": "trojan",
        "count": 3,
    },
    {
        "action": "alerted",
        "category": "malware",
        "count": 5,
    },
]

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
    },
]


@pytest.fixture
def mock_client():
    """Create a mock UniFi client."""
    client = MagicMock()
    client.get = AsyncMock()
    return client


class TestGetIPSStatusTool:
    """Tests for GetIPSStatusTool."""
    
    @pytest.mark.asyncio
    async def test_get_ips_status_basic(self, mock_client):
        """Test basic IPS status retrieval without alerts."""
        # Setup mock responses
        mock_client.get.side_effect = [
            {"data": MOCK_IPS_CONFIG},  # IPS settings
            {"data": MOCK_IPS_STATS},   # IPS statistics
        ]
        
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
        assert ips_status["key"] == "ips"
        assert ips_status["suppression_enabled"] == "yes"
        assert ips_status["suppression_enabled_bool"] is True
        assert ips_status["suppression_mode"] == "auto"
        assert ips_status["signature_version"] == "5.0.123"
        assert ips_status["last_signature_update"] == "2025-10-08T10:30:00Z"
        
        # Verify threat statistics
        threat_stats = ips_status["threat_statistics"]
        assert threat_stats["total_events"] == 31  # 15 + 8 + 3 + 5
        assert threat_stats["blocked_events"] == 18  # 15 + 3
        assert threat_stats["alerted_events"] == 13  # 8 + 5
        
        # Verify categories
        categories = threat_stats["categories"]
        assert categories["malware"] == 20  # 15 + 5
        assert categories["exploit"] == 8
        assert categories["trojan"] == 3
        
        # Verify no alerts included
        assert "recent_alerts" not in ips_status
        assert "total_alerts" not in ips_status
        
        # Verify API calls
        assert mock_client.get.call_count == 2
        mock_client.get.assert_any_call("/api/s/{site}/rest/setting/ips")
        mock_client.get.assert_any_call("/api/s/{site}/stat/ips/event")
    
    @pytest.mark.asyncio
    async def test_get_ips_status_with_alerts(self, mock_client):
        """Test IPS status retrieval with alerts included."""
        # Setup mock responses
        mock_client.get.side_effect = [
            {"data": MOCK_IPS_CONFIG},  # IPS settings
            {"data": MOCK_IPS_STATS},   # IPS statistics
            {"data": MOCK_ALERTS},      # Alerts
        ]
        
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
        
        # Verify first alert
        alert1 = ips_status["recent_alerts"][0]
        assert alert1["id"] == "alert1"
        assert alert1["key"] == "EVT_IPS_Alert"
        assert alert1["message"] == "Malware detected from 192.168.30.50"
        assert alert1["source_ip"] == "192.168.30.50"
        assert alert1["destination_ip"] == "8.8.8.8"
        assert alert1["signature_id"] == "2024001"
        assert alert1["category"] == "malware"
        
        # Verify second alert
        alert2 = ips_status["recent_alerts"][1]
        assert alert2["id"] == "alert2"
        assert alert2["key"] == "EVT_IPS_IDS_Threat"
        
        # Verify API calls
        assert mock_client.get.call_count == 3
        mock_client.get.assert_any_call("/api/s/{site}/rest/alarm")
    
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
            }
            for i in range(50)
        ]
        
        # Setup mock responses
        mock_client.get.side_effect = [
            {"data": MOCK_IPS_CONFIG},  # IPS settings
            {"data": MOCK_IPS_STATS},   # IPS statistics
            {"data": many_alerts},      # Many alerts
        ]
        
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
        disabled_config = [
            {
                "_id": "ips_config",
                "key": "ips",
                "enabled": False,
                "suppression_enabled": False,
                "suppression_mode": "",
                "signature_version": "5.0.123",
                "last_signature_update": "2025-10-08T10:30:00Z",
            }
        ]
        
        mock_client.get.side_effect = [
            {"data": disabled_config},  # IPS settings
            {"data": []},               # No statistics
        ]
        
        # Create tool and invoke
        tool = GetIPSStatusTool()
        result = await tool.invoke(mock_client, {"include_alerts": False})
        
        # Verify result
        assert result["success"] is True
        ips_status = result["data"]
        assert ips_status["enabled"] == "no"
        assert ips_status["enabled_bool"] is False
        
        # Verify empty statistics
        threat_stats = ips_status["threat_statistics"]
        assert threat_stats["total_events"] == 0
        assert threat_stats["blocked_events"] == 0
        assert threat_stats["alerted_events"] == 0
        assert threat_stats["categories"] == {}
    
    @pytest.mark.asyncio
    async def test_get_ips_status_no_config(self, mock_client):
        """Test IPS status when no configuration exists."""
        # Setup mock responses with empty config
        mock_client.get.side_effect = [
            {"data": []},               # No IPS settings
            {"data": MOCK_IPS_STATS},   # Statistics still available
        ]
        
        # Create tool and invoke
        tool = GetIPSStatusTool()
        result = await tool.invoke(mock_client, {"include_alerts": False})
        
        # Verify result - should handle gracefully
        assert result["success"] is True
        ips_status = result["data"]
        
        # Should have default values
        assert ips_status["enabled"] == "no"
        assert ips_status["enabled_bool"] is False
        assert ips_status["key"] == "ips"
        
        # But statistics should still be calculated
        threat_stats = ips_status["threat_statistics"]
        assert threat_stats["total_events"] == 31
    
    @pytest.mark.asyncio
    async def test_get_ips_status_api_error(self, mock_client):
        """Test IPS status retrieval with API error."""
        # Setup mock to raise exception
        mock_client.get.side_effect = Exception("Connection timeout")
        
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
        """Test threat statistics calculation with various event types."""
        # Create diverse statistics
        diverse_stats = [
            {"action": "blocked", "category": "malware", "count": 100},
            {"action": "blocked", "category": "exploit", "count": 50},
            {"action": "alerted", "category": "trojan", "count": 25},
            {"action": "alerted", "category": "malware", "count": 10},
            {"action": "unknown", "category": "other", "count": 5},
        ]
        
        # Setup mock responses
        mock_client.get.side_effect = [
            {"data": MOCK_IPS_CONFIG},
            {"data": diverse_stats},
        ]
        
        # Create tool and invoke
        tool = GetIPSStatusTool()
        result = await tool.invoke(mock_client, {"include_alerts": False})
        
        # Verify statistics
        threat_stats = result["data"]["threat_statistics"]
        assert threat_stats["total_events"] == 190  # 100 + 50 + 25 + 10 + 5
        assert threat_stats["blocked_events"] == 150  # 100 + 50
        assert threat_stats["alerted_events"] == 35  # 25 + 10
        
        # Verify categories
        categories = threat_stats["categories"]
        assert categories["malware"] == 110  # 100 + 10
        assert categories["exploit"] == 50
        assert categories["trojan"] == 25
        assert categories["other"] == 5
    
    @pytest.mark.asyncio
    async def test_alert_filtering(self, mock_client):
        """Test that only IPS-related alerts are included."""
        # Create mixed alerts
        mixed_alerts = [
            {"_id": "1", "key": "EVT_IPS_Alert", "msg": "IPS alert", "time": 1, "datetime": "2025-10-08T10:00:00Z", "subsystem": "ips", "src_ip": "", "dst_ip": "", "signature_id": "", "catname": ""},
            {"_id": "2", "key": "EVT_IDS_Threat", "msg": "IDS threat", "time": 2, "datetime": "2025-10-08T10:00:01Z", "subsystem": "ids", "src_ip": "", "dst_ip": "", "signature_id": "", "catname": ""},
            {"_id": "3", "key": "EVT_Intrusion_Detected", "msg": "Intrusion", "time": 3, "datetime": "2025-10-08T10:00:02Z", "subsystem": "security", "src_ip": "", "dst_ip": "", "signature_id": "", "catname": ""},
            {"_id": "4", "key": "EVT_AP_Lost", "msg": "AP lost", "time": 4, "datetime": "2025-10-08T10:00:03Z", "subsystem": "wlan", "src_ip": "", "dst_ip": "", "signature_id": "", "catname": ""},
            {"_id": "5", "key": "EVT_Threat_Blocked", "msg": "Threat blocked", "time": 5, "datetime": "2025-10-08T10:00:04Z", "subsystem": "security", "src_ip": "", "dst_ip": "", "signature_id": "", "catname": ""},
            {"_id": "6", "key": "EVT_Attack_Detected", "msg": "Attack", "time": 6, "datetime": "2025-10-08T10:00:05Z", "subsystem": "security", "src_ip": "", "dst_ip": "", "signature_id": "", "catname": ""},
        ]
        
        # Setup mock responses
        mock_client.get.side_effect = [
            {"data": MOCK_IPS_CONFIG},
            {"data": MOCK_IPS_STATS},
            {"data": mixed_alerts},
        ]
        
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
        mock_client.get.side_effect = [
            {"data": MOCK_IPS_CONFIG},
            {"data": MOCK_IPS_STATS},
            {"data": MOCK_ALERTS[:2]},  # Only IPS alerts
        ]
        
        # Create tool and invoke
        tool = GetIPSStatusTool()
        result = await tool.invoke(mock_client, {"include_alerts": True})
        
        # Verify result structure is AI-friendly
        assert result["success"] is True
        assert result["type"] == "ips_status"
        
        ips_status = result["data"]
        
        # Verify all expected fields are present
        assert "enabled" in ips_status
        assert "key" in ips_status
        assert "suppression_enabled" in ips_status
        assert "suppression_mode" in ips_status
        assert "threat_statistics" in ips_status
        assert "signature_version" in ips_status
        assert "last_signature_update" in ips_status
        assert "recent_alerts" in ips_status
        assert "total_alerts" in ips_status
        
        # Verify threat statistics structure
        threat_stats = ips_status["threat_statistics"]
        assert "total_events" in threat_stats
        assert "blocked_events" in threat_stats
        assert "alerted_events" in threat_stats
        assert "categories" in threat_stats
        
        # Verify alert structure
        for alert in ips_status["recent_alerts"]:
            assert "id" in alert
            assert "key" in alert
            assert "message" in alert
            assert "timestamp" in alert
            assert "datetime" in alert
            assert "severity" in alert
            assert "source_ip" in alert
            assert "destination_ip" in alert
            assert "signature_id" in alert
            assert "category" in alert


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
