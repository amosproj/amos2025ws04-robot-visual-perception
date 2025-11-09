# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from pydantic import BaseModel


class SDPModel(BaseModel):
    sdp: str
    type: str  # "offer"
