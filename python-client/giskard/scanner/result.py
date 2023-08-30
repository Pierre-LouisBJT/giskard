import tempfile
import mlflow
import pandas as pd
from mlflow import MlflowClient

from giskard.utils.analytics_collector import analytics, anonymize


class ScanResult:
    def __init__(self, issues):
        self.issues = issues

    def has_issues(self):
        return len(self.issues) > 0

    def __repr__(self):
        if not self.has_issues():
            return "<PerformanceScanResult (no issues)>"

        return f"<PerformanceScanResult ({len(self.issues)} issue{'s' if len(self.issues) > 1 else ''})>"

    def _ipython_display_(self):
        from IPython.core.display import display_html

        html = self._repr_html_()
        display_html(html, raw=True)

    def _repr_html_(self):
        return self.to_html(embed=True)

    def to_html(self, filename=None, embed=False):
        from ..visualization.widget import ScanResultWidget

        widget = ScanResultWidget(self)
        html = widget.render_html(embed=embed)

        if filename is not None:
            with open(filename, "w") as f:
                f.write(html)
            return

        return html

    def to_dataframe(self):
        df = pd.DataFrame(
            [
                {
                    "domain": issue.domain,
                    "metric": issue.metric,
                    "deviation": issue.deviation,
                    "description": issue.description,
                }
                for issue in self.issues
            ]
        )
        return df

    def generate_tests(self, with_names=False):
        tests = sum([issue.generate_tests(with_names=with_names) for issue in self.issues], [])
        return tests

    def generate_test_suite(self, name=None):
        from giskard import Suite

        suite = Suite(name=name or "Test suite (generated by automatic scan)")
        for test, test_name in self.generate_tests(with_names=True):
            suite.add_test(test, test_name)

        self._track_suite(suite, name)
        return suite

    def _track_suite(self, suite, name):
        tests_cnt = {}
        if suite.tests:
            for t in suite.tests:
                try:
                    name = t.giskard_test.meta.full_name
                    if name not in tests_cnt:
                        tests_cnt[name] = 1
                    else:
                        tests_cnt[name] += 1
                except:  # noqa
                    pass
        analytics.track(
            "scan:generate_test_suite",
            {"suite_name": anonymize(name), "tests_cnt": len(suite.tests), **tests_cnt},
        )

    @staticmethod
    def get_scan_summary_for_mlflow(scan_results):
        results_df = scan_results.to_dataframe()
        results_df.metric = results_df.metric.replace("=.*", "", regex=True)
        return results_df

    def to_mlflow(
        self,
        mlflow_client: MlflowClient = None,
        mlflow_run_id: str = None,
        summary: bool = True,
        model_artifact_path: str = "",
    ):
        results_df = self.get_scan_summary_for_mlflow(self)
        if model_artifact_path != "":
            model_artifact_path = "-for-" + model_artifact_path

        with tempfile.NamedTemporaryFile(
            prefix="giskard-scan-results" + model_artifact_path + "-", suffix=".html"
        ) as f:
            scan_results_local_path = f.name
            scan_results_artifact_name = scan_results_local_path.split("/")[-1]
            scan_summary_artifact_name = "scan-summary" + model_artifact_path + ".json" if summary else None
            self.to_html(scan_results_local_path)

            if mlflow_client is None and mlflow_run_id is None:
                mlflow.log_artifact(scan_results_local_path)
                if summary:
                    mlflow.log_table(results_df, artifact_file=scan_summary_artifact_name)
            elif mlflow_client and mlflow_run_id:
                mlflow_client.log_artifact(mlflow_run_id, scan_results_local_path)
                if summary:
                    mlflow_client.log_table(mlflow_run_id, results_df, artifact_file=scan_summary_artifact_name)
        return scan_results_artifact_name, scan_summary_artifact_name

    def to_wandb(self, **kwargs):
        """Log the scan results to the WandB run.

        Log the current scan results in an HTML format to the active WandB run.

        Parameters
        ----------
        **kwargs :
            Additional keyword arguments
            (see https://docs.wandb.ai/ref/python/init) to be added to the active WandB run.
        """
        from giskard.integrations.wandb.wandb_utils import wandb_run
        import wandb  # noqa library import already checked in wandb_run
        from ..utils.analytics_collector import analytics

        with wandb_run(**kwargs) as run:
            with tempfile.NamedTemporaryFile(prefix="giskard-scan-results-", suffix=".html") as f:
                try:
                    self.to_html(filename=f.name)
                    wandb_artifact_name = "Vulnerability scan results/" + f.name.split("/")[-1].split(".html")[0]
                    analytics.track(
                        "wandb_integration:scan_result",
                        {
                            "wandb_run_id": run.id,
                            "has_issues": self.has_issues(),
                            "issues_cnt": len(self.issues),
                        },
                    )
                except Exception as e:
                    analytics.track(
                        "wandb_integration:scan_result:error:unknown",
                        {
                            "wandb_run_id": run.id,
                            "error": str(e),
                        },
                    )
                    raise ValueError(
                        "An error occurred while logging the scan results into wandb. "
                        "Please submit the traceback as a GitHub issue in the following "
                        "repository for further assistance: https://github.com/Giskard-AI/giskard."
                    ) from e

                run.log({wandb_artifact_name: wandb.Html(open(f.name), inject=False)})
