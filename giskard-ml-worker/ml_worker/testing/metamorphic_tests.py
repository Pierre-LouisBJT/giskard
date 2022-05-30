import pandas as pd
from ai_inspector import ModelInspector

from generated.ml_worker_pb2 import SingleTestResult
from ml_worker.core.giskard_dataset import GiskardDataset
from ml_worker.core.ml import run_predict
from ml_worker.testing.abstract_test_collection import AbstractTestCollection
from ml_worker.testing.utils import apply_perturbation_inplace
from ml_worker.testing.utils import save_df, compress


class MetamorphicTests(AbstractTestCollection):
    @staticmethod
    def _predict_numeric_result(df, model: ModelInspector, output_proba=True, classification_label=None):
        if model.prediction_task == 'regression' or not output_proba:
            return run_predict(df, model).raw_prediction
        elif model.prediction_task == 'classification' and classification_label is not None:
            return run_predict(df, model).all_predictions[classification_label].values
        elif model.prediction_task == 'classification':
            return run_predict(df, model).probabilities

    @staticmethod
    def _prediction_ratio(prediction, perturbed_prediction):
        return abs(perturbed_prediction - prediction) / prediction if prediction else 0  # to be handled

    @staticmethod
    def _perturb_and_predict(df, model: ModelInspector, perturbation_dict, output_proba=True,
                             classification_label=None):
        results_df = pd.DataFrame()
        results_df["prediction"] = MetamorphicTests._predict_numeric_result(df, model, output_proba,
                                                                            classification_label)
        modified_rows = apply_perturbation_inplace(df, perturbation_dict)
        if len(modified_rows):
            results_df = results_df.iloc[modified_rows]
            results_df["perturbed_prediction"] = MetamorphicTests._predict_numeric_result(df.iloc[modified_rows], model,
                                                                                          output_proba,
                                                                                          classification_label)
        else:
            results_df["perturbed_prediction"] = results_df["prediction"]
        return results_df, len(modified_rows)

    def _compare_prediction(self, results_df, prediction_task, output_sensitivity=None, flag=None):
        if flag == 'INV':
            if prediction_task == 'classification':
                passed_idx = results_df.loc[
                    results_df['prediction'] == results_df['perturbed_prediction']].index.values

            elif prediction_task == 'regression':
                results_df['predict_difference_ratio'] = results_df.apply(
                    lambda x: self._prediction_ratio(x["prediction"], x["perturbed_prediction"]), axis=1)
                passed_idx = results_df.loc[results_df['predict_difference_ratio'] < output_sensitivity].index.values

        elif flag == 'INC':
            passed_idx = results_df.loc[
                results_df['prediction'] < results_df['perturbed_prediction']].index.values

        elif flag == 'DEC':
            passed_idx = results_df.loc[
                results_df['prediction'] > results_df['perturbed_prediction']].index.values

        failed_idx = results_df.loc[~results_df.index.isin(passed_idx)].index.values
        return passed_idx, failed_idx

    def _test_metamorphic(self,
                          flag,
                          df: GiskardDataset,
                          model,
                          perturbation_dict,
                          threshold: float,
                          classification_label=None,
                          output_sensitivity=None,
                          output_proba=True
                          ) -> SingleTestResult:
        results_df, modified_rows_count = self._perturb_and_predict(df.df,
                                                                    model,
                                                                    perturbation_dict,
                                                                    classification_label=classification_label,
                                                                    output_proba=output_proba)

        passed_idx, failed_idx = self._compare_prediction(results_df,
                                                          model.prediction_task,
                                                          output_sensitivity,
                                                          flag)
        failed_df = df.df.loc[failed_idx]
        passed_ratio = len(passed_idx) / modified_rows_count if modified_rows_count != 0 else 1

        output_df_sample = compress(save_df(failed_df))

        return self.save_results(SingleTestResult(
            total_nb_rows=len(df),
            number_of_perturbed_rows=modified_rows_count,
            metric=passed_ratio,
            passed=passed_ratio > threshold,
            output_df=output_df_sample))

    def test_metamorphic_invariance(self,
                                    df: GiskardDataset,
                                    model,
                                    perturbation_dict,
                                    threshold=1,
                                    output_sensitivity=None) -> SingleTestResult:
        """
        Summary: Tests if the model prediction is invariant when the feature values are perturbed

        Description: -
        For classification: Test if the predicted classification label remains the same after
        feature values perturbation.
        For regression: Check whether the predicted output remains the same at the output_sensibility
        level after feature values perturbation.

        The test is passed when the ratio of invariant rows is higher than the threshold

        Example : The test is passed when, after switching gender from male to female,
        more than 50%(threshold 0.5) of males have unchanged outputs

        Args:
            df(GiskardDataset):
                Dataset used to compute the test
            model(ModelInspector):
                Model used to compute the test
            perturbation_dict(dict):
                Dictionary of the perturbations. It provides the perturbed features as key and a perturbation lambda function as value
            threshold(float):
                Threshold of the ratio of invariant rows
            output_sensitivity(float):
                the threshold for ratio between the difference between perturbed prediction and actual prediction over
                the actual prediction for a regression model. We consider there is a prediction difference for
                regression if the ratio is above the output_sensitivity of 0.1

        Returns:
            total_nb_rows:
                total number of rows of dataframe
            number_of_perturbed_rows:
                number of perturbed rows
            metric:
                the ratio of invariant rows over the perturbed rows
            passed:
                TRUE if passed_ratio > threshold
            output_df:
                dataframe containing the non-invariant rows

        """

        return self._test_metamorphic(flag='INV',
                                      df=df,
                                      model=model,
                                      perturbation_dict=perturbation_dict,
                                      threshold=threshold,
                                      output_sensitivity=output_sensitivity,
                                      output_proba=False
                                      )

    def test_metamorphic_increasing(self,
                                    df: GiskardDataset,
                                    model,
                                    perturbation_dict,
                                    threshold=1,
                                    classification_label=None):
        """
        Summary: Tests if the model probability increases when the feature values are perturbed

        Description: -
        - For classification: Test if the model probability of a given classification_label is
        increasing after feature values perturbation.

        - For regression: Test if the model prediction is increasing after feature values perturbation.

        The test is passed when the percentage of rows that are increasing is higher than the threshold

        Example : For a credit scoring model, the test is passed when a decrease of wage by 10%,
         default probability is increasing for more than 50% of people in the dataset

        Args:
            df(GiskardDataset):
                Dataset used to compute the test
            model(ModelInspector):
                Model used to compute the test
            perturbation_dict(dict):
                Dictionary of the perturbations. It provides the perturbed features as key
                and a perturbation lambda function as value
            threshold(float):
                Threshold of the ratio of increasing rows
            classification_label(float):
                one specific label value from the target column

        Returns:
            total_nb_rows:
                total number of rows of dataframe
            number_of_perturbed_rows:
                number of perturbed rows
            metric:
                the ratio of increasing rows over the perturbed rows
            passed:
                TRUE if passed_ratio > threshold
            output_df:
                dataframe containing the rows whose probability doesn't increase after perturbation

        """
        if model.prediction_task == "classification" and classification_label not in model.classification_labels:
            raise Exception(
                f'"{classification_label}" is not part of model labels: {",".join(model.classification_labels)}')

        return self._test_metamorphic(flag='INC',
                                      df=df,
                                      model=model,
                                      perturbation_dict=perturbation_dict,
                                      classification_label=classification_label,
                                      threshold=threshold)

    def test_metamorphic_decreasing(self,
                                    df: GiskardDataset,
                                    model,
                                    perturbation_dict,
                                    threshold=1,
                                    classification_label=None
                                    ):
        """
        Summary: Tests if the model probability decreases when the feature values are perturbed

        Description: -
        - For classification: Test if the model probability of a given classification_label is
        decreasing after feature values perturbation.

        - For regression: Test if the model prediction is decreasing after feature values perturbation.

        The test is passed when the percentage of rows that are decreasing is higher than the threshold

        Example : For a credit scoring model, the test is passed when a increase of wage by 10%,
         default probability is decreasing for more than 50% of people in the dataset

        Args:
            df(GiskardDataset):
                Dataset used to compute the test
            model(ModelInspector):
                Model used to compute the test
            perturbation_dict(dict):
                Dictionary of the perturbations. It provides the perturbed features as key
                and a perturbation lambda function as value
            threshold(float):
                Threshold of the ratio of decreasing rows
            classification_label(float):
                one specific label value from the target column

        Returns:
            total_nb_rows:
                total number of rows of dataframe
            number_of_perturbed_rows:
                number of perturbed rows
            metric:
                the ratio of decreasing rows over the perturbed rows
            passed:
                TRUE if passed_ratio > threshold
            output_df:
                dataframe containing the rows whose probability doesn't decrease after perturbation

        """

        if model.prediction_task == "classification" and classification_label not in model.classification_labels:
            raise Exception(
                f'"{classification_label}" is not part of model labels: {",".join(model.classification_labels)}')
        return self._test_metamorphic(flag='DEC',
                                      df=df,
                                      model=model,
                                      perturbation_dict=perturbation_dict,
                                      classification_label=classification_label,
                                      threshold=threshold)
