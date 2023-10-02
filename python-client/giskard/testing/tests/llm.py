import pandas as pd

from ...datasets.base import Dataset
from ...ml_worker.testing.registry.decorators import test
from ...ml_worker.testing.test_result import TestResult
from ...models.base import BaseModel


@test(name="Validate LLM evaluation dataset using GPT-4", tags=["llm", "GPT-4"])
def test_llm_response_validation(
    model: BaseModel,
    dataset: Dataset,
    evaluation_criteria: str,
    threshold: float = 0.5,
):
    """Tests that the rate of generated response is over a threshold for a given test case.

    The generated response will be validated using GPT-4
    using the OPENAI_API_TOKEN stored inside the environment variable.

    Arguments:
        model(BaseModel): The generative model to test.
        dataset(Dataset): The dataset to test the model on.
        evaluation_criteria(str): The test case used to evaluate the response generated by the model
            must be explicit and clear in order to be interpreted properly
            Good assertions
              - The model response must be a JSON valid that respect the following schema
              - The model response must be an apologies with an explanation of the model scope if the question is out of scope (not related to the Pandas Python library)
            Bad assertion
              - A valid json answer
              - Answer to pandas documentation
        threshold(float, optional): The threshold for good response rate, i.e. the min ratio of responses that pass the assertion. Default is 0.50 (50%).
    """
    from ...llm.utils.validate_test_case import validate_test_case

    predictions = model.predict(dataset).prediction

    passed = validate_test_case(model, evaluation_criteria, dataset.df, predictions)
    metric = len([result for result in passed if result]) / len(predictions)

    return TestResult(
        actual_slices_size=[len(dataset)],
        metric=metric,
        passed=bool(metric >= threshold),
    )


@test(name="Validate LLM single prompt input using GPT-4", tags=["llm", "GPT-4"])
def test_llm_individual_response_validation(model: BaseModel, prompt_input: str, evaluation_criteria: str):
    """Tests that the rate of generated response is over a threshold for a given test case.

    The generated response will be validated using GPT-4
    using the OPENAI_API_TOKEN stored inside the environment variable.

    Arguments:
        model(BaseModel): The generative model to test.
        prompt_input(str): The prompt input to test the model on.
        evaluation_criteria(str): The test case used to evaluate the response generated by the model
            must be explicit and clear in order to be interpreted properly
            Good assertions
              - The model response must be a JSON valid that respect the following schema
              - The model response must be an apologies with an explanation of the model scope if the question is out of scope (not related to the Pandas Python library)
            Bad assertion
              - A valid json answer
              - Answer to pandas documentation
    """
    if len(model.meta.feature_names) != 1:
        raise ValueError(
            "LLM individual response validation only work for models having single input, please use LLM response validation using"
        )

    dataset = Dataset(pd.DataFrame({model.meta.feature_names[0]: [prompt_input]}), validation=False)

    test_llm_response_validation(model, dataset, evaluation_criteria, 1.0)
