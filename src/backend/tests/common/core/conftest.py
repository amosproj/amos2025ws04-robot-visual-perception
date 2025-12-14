# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import types
from typing import Any


class DummySessionOptions:
    def __init__(
        self, enable_mem_pattern: bool = False, graph_optimization_level: Any = None
    ) -> None:
        self.enable_mem_pattern = enable_mem_pattern
        self.graph_optimization_level = graph_optimization_level


class DummySession:
    def __init__(
        self,
        run_return: Any,
        input_name: str = "input",
        output_name: str = "output",
    ) -> None:
        self._inputs = [types.SimpleNamespace(name=input_name)]
        self._outputs = [types.SimpleNamespace(name=output_name)]
        self._run_return = run_return

    def get_inputs(self):
        return self._inputs

    def get_outputs(self):
        return self._outputs

    def run(self, _output_names, _inputs):
        return [self._run_return]
