from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

from dataclasses import dataclass, field
from enum import Enum

from ..datasets.base import Dataset
from .core import TestResultStatusEnum

if TYPE_CHECKING:
    from ..llm.evaluators.base import EvaluationResult

# Ensure backward compatibility of "from giskard.core.test_result import TestResultStatus"
TestResultStatus = TestResultStatusEnum


class TestMessageLevel(str, Enum):
    ERROR = "ERROR"
    INFO = "INFO"


@dataclass
class TestMessage:
    type: TestMessageLevel
    text: str

    def _repr_html_(self):
        return """
               <li style="color:{0};">{1}</li>
               """.format(
            "red" if self.type == TestMessageLevel.ERROR else "inherit", self.text
        )

    def __repr__(self):
        return f" - [{self.type}] {self.text}"


@dataclass
class PartialUnexpectedCounts:
    value: List[int]
    count: int


@dataclass
class TestResult:
    """
    Dataclass representing the result of a test

    :param passed: A boolean indicating whether the test passed or not
    :param messages: A list of TestMessage objects containing information about the test execution
    :param metric: A float representing the test metric
    """

    passed: bool = False
    messages: List[TestMessage] = field(default_factory=list, repr=False)
    props: Dict[str, str] = field(default_factory=dict, repr=False)
    metric_name: str = "Metric"
    metric: Optional[float] = None
    missing_count: int = 0
    missing_percent: float = 0
    unexpected_count: int = 0
    unexpected_percent: float = 0
    unexpected_percent_total: float = 0
    unexpected_percent_nonmissing: float = 0
    partial_unexpected_index_list: List[PartialUnexpectedCounts] = field(default_factory=list, repr=False)
    unexpected_index_list: List[int] = field(default_factory=list, repr=False)
    number_of_perturbed_rows: int = 0
    actual_slices_size: List[int] = field(default_factory=list, repr=False)
    reference_slices_size: List[int] = field(default_factory=list, repr=False)
    output_df: Optional[bytes] = None  # Legacy output, use output_ds instead as this will be removed in the future
    output_ds: List[Dataset] = field(default_factory=list, repr=False)
    evaluation_result: Optional[EvaluationResult] = None
    is_error: bool = False

    def _repr_html_(self):
        return """
               <h4><span style="color:{0};">{1}</span> Test {2}</h4>
               <p>Metric: {3}<p>
               <ul>{4}</ul>
               """.format(
            "green" if self.passed else "red",
            "✓" if self.passed else "𐄂",
            "succeeded" if self.passed else "failed",
            "No metric" if self.metric is None else str(round(self.metric, 2)),
            "".join([] if self.messages is None else [m._repr_html_() for m in self.messages]),
        )

    def __repr__(self):
        return """
               Test {0}
               Metric: {1}
               {2}
               """.format(
            "succeeded" if self.passed else "failed",
            "No metric" if self.metric is None else str(round(self.metric, 2)),
            "\n".join([] if self.messages is None else [m.__repr__() for m in self.messages]),
        )

    def __bool__(self):
        return self.passed
