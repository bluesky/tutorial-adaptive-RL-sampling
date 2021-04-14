from bluesky_adaptive.recommendations import NoRecommendation


def naive_agent(x, y):
    """A simple naive agent"""
    return x + 1


class BadSeedRecommender:
    """
    Framework for recommendations from badseed
    This should be a one-in-one-out recommender.
    """

    def __init__(self, *args, num_samples, **kwargs):
        """Load the model, set up the necessary bits"""
        self.next_point = None
        self.num_samples = num_samples
        self.agent = self.build_agent(*args, **kwargs)

    def build_agent(self, *args, **kwargs):
        return naive_agent

    def tell(self, x, y):
        """Tell the recommnder about something new"""
        self.next_point = self.agent(x, y)

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


class RLRecommender(BadSeedRecommender):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def build_agent(self, *args, **kwargs):
        """Function to construct the RL agent from save points.

        Returns
        -------
        agent : Callable[float, float] -> int

           f(x, y) -> next_point

        """
        raise NotImplementedError


if True:
    import numpy as np
    from bluesky_adaptive.per_start import adaptive_plan
    from bluesky_adaptive.on_stop import recommender_factory
    from bluesky.callbacks.best_effort import BestEffortCallback
    from bluesky import RunEngine
    from ophyd.sim import hw

    hw = hw()
    bec = BestEffortCallback()

    def do_the_thing(det, key_of_goodness, sample_positions, max_shots=25):
        sample_positions = np.array(sample_positions)

        # we know that at the reccomender level we do not want to know anything
        # about the real motor positions.  This function converts from lab
        # space to notional "enviroment" space
        def motor_to_sample_indx(pos):
            pos = pos.compute().data
            return np.argmin(np.abs(sample_positions - pos))

        # Converesly, at the beamline we have to work in real coordinates, this function
        # converts from the "enviroment" coordinate system to
        def sample_indx_to_motor(indx):
            return sample_positions[int(indx)]

        # create the (pre-trained) reccomender.
        recommender = BadSeedRecommender(num_samples=len(sample_positions))
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
            independent_keys=[lambda motor: motor_to_sample_indx(motor)],
            dependent_keys=[key_of_goodness],
            target_keys=["motor"],
            target_transforms={"motor": sample_indx_to_motor},
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
            dets=[det],
            first_point={hw.motor: 1},
            to_recommender=cb,
            from_recommender=queue,
        )

    RE = RunEngine()
    RE(do_the_thing(hw.det, "int(motor % 2)", [0.5, 1, 1.25, 2, 3]), bec)
