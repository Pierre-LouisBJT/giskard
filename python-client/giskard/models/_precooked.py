import numpy as np
import pandas as pd
from typing import Optional, Iterable

from .base import BaseModel, ModelType, ModelPredictionResults
from .. import Dataset


class PrecookedModel(BaseModel):
    """A dummy model for internal usage."""

    def __init__(
            self,
            data: Dataset,
            predictions: ModelPredictionResults,
            model_type: ModelType,
            feature_names: Optional[Iterable] = None,
            classification_labels: Optional[Iterable] = None,
    ):
        self._data = data
        self._predictions = predictions
        super().__init__(
            model_type=model_type, feature_names=feature_names, classification_labels=classification_labels
        )

    @classmethod
    def from_model(cls, model: BaseModel, dataset: Dataset):
        """Creates a PrecookedModel from an existing model and dataset."""
        predictions = model.predict(dataset)

        return cls(
            dataset,
            predictions,
            model.meta.model_type,
            model.meta.feature_names,
            model.meta.classification_labels,
        )

    def predict(self, dataset: Dataset) -> ModelPredictionResults:
        refs = pd.Series(np.arange(len(self._data)), index=self._data.df.index)
        idx = refs.loc[dataset.df.index]

        raw = np.asarray(self._predictions.raw)[idx]
        prediction = np.asarray(self._predictions.prediction)[idx]
        raw_prediction = np.asarray(self._predictions.raw_prediction)[idx]

        if hasattr(self._predictions, "probabilities"):
            probabilities = np.asarray(self._predictions.probabilities)[idx]
        else:
            probabilities = None

        if hasattr(self._predictions, "all_predictions"):
            all_predictions = np.asarray(self._predictions.all_predictions)[idx]
        else:
            all_predictions = None

        return ModelPredictionResults(
            raw=raw,
            prediction=prediction,
            raw_prediction=raw_prediction,
            probabilities=probabilities,
            all_predictions=all_predictions,
        )

    def model_predict(self, df: pd.DataFrame):
        raise NotImplementedError()

    def _predict_df(self, df: pd.DataFrame):
        raise NotImplementedError()
