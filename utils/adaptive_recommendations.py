from collections import Counter

from bluesky_adaptive.recommendations import NoRecommendation


class BadSeedRecommender:
    """
    Framework for recommendations from badseed
    This should be a one-in-one-out recommender.
    """

    def __init__(self, num_samples, agent):
        """Load the model, set up the necessary bits"""
        self.next_point = None
        self.num_samples = num_samples
        self.seen_count = Counter()
        self.agent = agent

    def tell(self, x, y):
        """Tell the recommnder about something new"""
        # print(f"in tell {x}, {y}")
        self.seen_count[x] += 1
        (snr,) = y
        if snr > 500:
            target = 10
        else:
            target = 1
        if self.seen_count[x] == 1:
            self.next_point = (x + 1) % self.num_samples
        else:
            self.next_point = self.agent(x, max(target - self.seen_count[x], 0))

    def tell_many(self, xs, ys):
        for x, y in zip(xs, ys):
            self.tell(x, y)

    def ask(self, n, tell_pending=True):
        """Ask the recommender for a new command"""
        if n != 1:
            raise NotImplementedError
        if self.next_point is None or self.next_point >= self.num_samples:
            raise NoRecommendation

        return (self.next_point,)


class NaiveAgent:
    """A simple naive agent that cycles samples sequentially in environment space"""

    def __init__(self, num_samples):
        """

        Parameters
        ----------
        num_samples : int
            Total number of samples in the "environment" space
        """
        self.num_samples = num_samples

    def __call__(self, x, y):
        """Continuous cycling of sample indicies regardless of goodness (y)"""
        # print(f"called {x}, {y}")
        return (x + 1) % self.num_samples


class CheatingAgent:
    """A simple naive agent that cycles samples sequentially in environment space"""

    def __init__(self, num_samples):
        """

        Parameters
        ----------
        num_samples : int
            Total number of samples in the "environment" space
        """
        self.num_samples = num_samples

    def __call__(self, x, y):
        """Continuous cycling of sample indicies regardless of goodness (y)"""
        # print(f"called {x}, {y}")
        if y > 0:
            return x
        else:
            return (x + 1) % self.num_samples


class RLAgent:
    def __init__(self, num_samples, path):
        """

        Parameters
        ----------
        num_samples : int
            Total number of samples in the "environment" space
        path : Path, str
            Output path of agent to load from
        """
        from tf_agent import load_agent

        self.num_samples = num_samples
        self.agent = load_agent(path)

    def useful_counts_remaining(self, y):
        """
        This is the function that will need to be adjusted outside the simulator to convert
        the dependent variable into a useful counts remaining.
        """
        return y

    def __call__(self, x, y):
        """
        Cycles continuously according to RL recommender
        Parameters
        ----------
        x : int
            "Environment" space position
        y : int
            degree of badness

        Returns
        -------

        """
        badness = self.useful_counts_remaining(y)
        change = self.agent.act(
            [float(bool(badness)), float(badness)], independent=True
        )
        return (x + change) % self.num_samples


def bad_seed_plan(sample_selector, det, snr, sample_positions, agent, max_shots=50):
    sample_positions = np.array(sample_positions)

    # we know that at the reccomender level we do not want to know anything
    # about the real motor positions.  This function converts from lab
    # space to notional "enviroment" space
    def motor_to_sample_indx(pos):
        # print("in convert forward")
        pos = pos.compute().data
        return np.argmin(np.abs(sample_positions - pos))

    # Converesly, at the beamline we have to work in real coordinates, this function
    # converts from the "enviroment" coordinate system to
    def sample_indx_to_motor(indx):
        # print("in convert back")
        return sample_positions[int(indx)]

    # create the (pre-trained) reccomender.
    recommender = BadSeedRecommender(num_samples=len(sample_positions), agent=agent)
    # set up the machinery to:
    #  - unpack and reduce the raw data
    #  - pass the reduced data into the recommendation engine (tell)
    #  - get the recommended next step back from the recommendation engine (ask)
    #  - translate back to physical units
    #
    #  The two return values are:
    #
    #   cb : where the collected data should be sent
    #   queue : where the plan should query to get the next step
    cb, queue = recommender_factory(
        adaptive_obj=recommender,
        independent_keys=[
            lambda sample_selector: motor_to_sample_indx(sample_selector)
        ],
        dependent_keys=[snr],
        target_keys=[sample_selector.name],
        target_transforms={sample_selector.name: sample_indx_to_motor},
        max_count=max_shots,
    )

    # The adaptive plan takes in:
    #
    #   dets : the detectors to be read
    #   first_point : where to start the scan
    #   to_recommender : the call back from above
    #   from_recommender : the queue from above
    #
    #  This takes care of running data collection, moving as instructed by the
    #  recommendation.
    yield from adaptive_plan(
        dets=[detector],
        first_point={sample_selector: 1},
        to_recommender=cb,
        from_recommender=queue,
    )


if __name__ == "__main__":
    import numpy as np
    from bluesky_adaptive.per_start import adaptive_plan
    from bluesky_adaptive.on_stop import recommender_factory
    from bluesky.callbacks.best_effort import BestEffortCallback
    from bluesky import RunEngine
    from simulated_hardware import sample_selector, detector

    bec = BestEffortCallback()

    RE = RunEngine()
    RE(
        bad_seed_plan(
            sample_selector,
            detector,
            "detector_signal_to_noise",
            list(range(9)),
            CheatingAgent(9),
        ),
        bec,
    )
