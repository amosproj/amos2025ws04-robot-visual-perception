# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from typing import Dict, List
from aiortc import RTCPeerConnection, RTCDataChannel

# Keep the same global names
pcs: List[RTCPeerConnection] = []
_datachannels: Dict[int, RTCDataChannel] = {}
