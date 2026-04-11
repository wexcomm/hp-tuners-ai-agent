"""
HP Tuners AI Agent
A comprehensive Python agent for ECU tuning and vehicle diagnostics
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .hp_tuners_agent import (
    ECUController,
    TCMController,
    TuneAnalyzer,
    SafetyValidator,
    HPTunersAgent,
    ECUParameters,
    TuneData
)

from .lfx_impala_controller import (
    LFXImpalaController,
    LFXSpecificPIDs
)

__all__ = [
    'ECUController',
    'TCMController',
    'TuneAnalyzer',
    'SafetyValidator',
    'HPTunersAgent',
    'LFXImpalaController',
    'ECUParameters',
    'TuneData',
    'LFXSpecificPIDs'
]