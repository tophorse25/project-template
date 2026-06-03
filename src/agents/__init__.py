"""Narrow-role agents operating on the shared knowledge base."""

from agents.change_detection import ChangeDetectionAgent
from agents.deep_research import DeepResearchAgent
from agents.discovery import DiscoveryAgent
from agents.pool_manager import PoolManager, theme_id_for
from agents.report_agent import ReportAgent

__all__ = [
    "ChangeDetectionAgent",
    "DeepResearchAgent",
    "DiscoveryAgent",
    "PoolManager",
    "ReportAgent",
    "theme_id_for",
]
