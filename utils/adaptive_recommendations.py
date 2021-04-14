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

        def motor_to_sample_indx(pos):
            pos = pos.compute().data
            return np.argmin(np.abs(sample_positions - pos))

        def sample_indx_to_motor(indx):
            return sample_positions[int(indx)]

        recommender = BadSeedRecommender(num_samples=len(sample_positions))
        cb, queue = recommender_factory(
            adaptive_obj=recommender,
            independent_keys=[lambda motor: motor_to_sample_indx(motor)],
            dependent_keys=[key_of_goodness],
            target_keys=["motor"],
            target_transforms={"motor": sample_indx_to_motor},
            max_count=max_shots,
        )
        yield from adaptive_plan(
            [det], {hw.motor: 1}, to_recommender=cb, from_recommender=queue
        )

    RE = RunEngine()
    RE(do_the_thing(hw.det, "int(motor % 2)", [0.5, 1, 1.25, 2, 3]), bec)
