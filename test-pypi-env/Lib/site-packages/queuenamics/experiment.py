from statistics import mean, stdev


class Experiment:

    def __init__(
        self,
        model_factory,
        replications,
        time,
        warmup=0
    ):
        if replications <= 0:
            raise ValueError(
                "replications must be greater than 0."
            )

        if time <= 0:
            raise ValueError(
                "time must be greater than 0."
            )

        if warmup < 0:
            raise ValueError(
                "warmup must be greater than or equal to 0."
            )

        self.model_factory = model_factory
        self.replications = replications
        self.time = time
        self.warmup = warmup
        self.results = []

    def run(self):
        self.results = []

        for replication in range(self.replications):
            model = self.model_factory(replication)

            if self.warmup > 0:
                model.run(self.warmup)
                model.reset_statistics()

            model.run(
                self.warmup + self.time
            )

            self.results.append(model)

        return self.results

    def values(self, extractor):
        if not self.results:
            raise RuntimeError(
                "Run the experiment before requesting results."
            )

        return [
            extractor(model)
            for model in self.results
        ]

    def mean(self, extractor):
        return mean(
            self.values(extractor)
        )

    def standard_deviation(self, extractor):
        values = self.values(extractor)

        if len(values) < 2:
            return 0.0

        return stdev(values)

    def confidence_interval(
        self,
        extractor,
        confidence=0.95
    ):
        values = self.values(extractor)

        if not 0 < confidence < 1:
            raise ValueError(
                "confidence must be between 0 and 1."
            )

        n = len(values)

        if n < 2:
            raise RuntimeError(
                "At least 2 replications are required "
                "for a confidence interval."
            )

        sample_mean = mean(values)
        sample_std = stdev(values)

        # Normal approximation.
        z = 1.96

        margin = z * sample_std / (n ** 0.5)

        return (
            sample_mean - margin,
            sample_mean + margin
        )
    
class ParameterSweep:

    def __init__(
        self,
        model_factory,
        parameters,
        replications,
        time,
        warmup=0
    ):
        if replications <= 0:
            raise ValueError(
                "replications must be greater than 0."
            )

        if time <= 0:
            raise ValueError(
                "time must be greater than 0."
            )

        if warmup < 0:
            raise ValueError(
                "warmup must be greater than or equal to 0."
            )

        if not parameters:
            raise ValueError(
                "parameters must not be empty."
            )

        self.model_factory = model_factory
        self.parameters = parameters
        self.replications = replications
        self.time = time
        self.warmup = warmup
        self.results = []

    def run(self):
        self.results = []

        parameter_names = list(self.parameters.keys())

        parameter_values = [
            list(values)
            for values in self.parameters.values()
        ]

        import itertools

        combinations = itertools.product(
            *parameter_values
        )

        for combination in combinations:

            parameter_set = dict(
                zip(
                    parameter_names,
                    combination
                )
            )

            experiment = Experiment(
                model_factory=lambda replication,
                params=parameter_set:
                    self.model_factory(
                        params,
                        replication
                    ),
                replications=self.replications,
                time=self.time,
                warmup=self.warmup
            )

            models = experiment.run()

            self.results.append({
                "parameters": parameter_set,
                "models": models
            })

        return self.results