from giskard.scanner.prediction.prediction_bias_detectors.overconfidence import OverconfidenceBiasDetector
from giskard.scanner.prediction.prediction_bias_detectors.borderline import BorderlineBiasDetector

from giskard.scanner.prediction.metrics import OverconfidenceMAE, BorderlineMAE


def test_prediction_biais_detector(german_credit_model, german_credit_data):
    res = OverconfidenceBiasDetector(metrics=[OverconfidenceMAE()]).run(german_credit_model, german_credit_data)
    res2 = BorderlineBiasDetector(metrics=[BorderlineMAE()]).run(german_credit_model, german_credit_data)

    print(res, res2)

# from giskard.scanner.performance.model_bias_detector import ModelBiasDetector
# def test_data_leakage(german_credit_model, german_credit_data):
#     mbd = ModelBiasDetector(metrics=["dataleakage"]).run(german_credit_model, german_credit_data)
#     print(mbd)
