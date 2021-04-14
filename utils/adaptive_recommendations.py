from bluesky_adaptive.recommendations import NoRecommendation

def nieve_agent(x, y):
    """A simple naive agent"""
    return x + 1


def environment_to_motor_position(env):
    """Converts integer environment variable to motor position"""
    pass


def motor_position_to_environment(pos):
    """Converts motor position to integer environment variable"""
    pass


class BadSeedRecommender:
    """
    Framework for recommendations from badseed
    This should be a one-in-one-out recommender.
    """

    def __init__(self, *args, **kwargs):
        """Load the model, set up the necessary bits"""
        self.next_point = None
        self.agent = self.build_agent(*args, **kwargs)

    def build_agent(self, *args, **kwargs):
        raise nieve_agent

    def _preprocessing(self, x, y):
        return environment_to_motor_position(x), y

    def _postprocessing(self, x):
        return motor_position_to_environment(x)

    def tell(self, x, y):
        """Tell the recommnder about something new"""
        x, y = self._preprocessing(x, y)
        self.next_point = self.agent(x, y)

    def ask(self, n, tell_pending=True):
        """Ask the recommender for a new command"""
        if n != 1:
            raise NotImplementedError
        if self.next_point is None:
            raise NoRecommendation
        return self._postprocessing(self.next_point)


class RLRecommender(BadSeedRecommender):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def build_agent(self, *args, **kwargs):
        """Function to construct the RL agent from save points. Returns a callable f(x,y)."""
        raise NotImplementedError


if __name__ == "__main__":
    import bluesky_adaptive
    import bluesky.plan_stubs as bps
    from bluesky_adaptive.per_event import adaptive_plan, recommender_factory
    from bluesky import RunEngine
    from ophyd.sim import hw

    hw = hw()

    def do_the_thing(det, det_key, key_of_goodness):
        recommender = BadSeedRecommender()
        cb, queue = recommender_factory(
            recommender,
            independent_keys=["motor"],
            dependent_keys=[det_key, key_of_goodness],
            max_count=90,
        )
        yield from adaptive_plan(
            [det], {hw.motor: 1}, to_recommender=cb, from_recommender=queue
        )

        RE = RunEngine()
        RE(do_the_thing(hw.img, "img"), print)
