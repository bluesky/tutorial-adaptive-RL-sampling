import numpy


from bluesky_widgets.models.plot_builders import Images, call_or_eval
from bluesky_widgets.jupyter.figures import (
    widgets,
    _initialize_mpl,
    matplotlib,
    JupyterAxes,
    JupyterFigure as JupyterFigure_,
    ipympl,
    ipympl,
    Figure,
)


class SummedImages(Images):
    def _transform(self, run, field):
        result = call_or_eval({"array": field}, run, self.needs_streams, self.namespace)
        # If the data is more than 2D, take the middle slice from the leading
        # axis until there are only two axes.
        data = result["array"]
        if data.shape[0] == 0:
            placeholder = numpy.zeros(data.shape[1:])
            placeholder[0, 0] = 1
            result["array"] = placeholder
        else:
            mean = numpy.mean(data, 0)
            max_ = numpy.max(mean)
            min_ = numpy.min(mean)
            result["array"] = mean / (max_ - min_)
        return result


class JupyterFigure(JupyterFigure_):
    """
    A Jupyter view for a Figure model. This always contains one Figure.
    """

    def __init__(self, model: Figure):
        _initialize_mpl()
        widgets.HBox.__init__(self)
        self.model = model
        self.figure = matplotlib.figure.Figure()
        # TODO Let Figure give different options to subplots here,
        # but verify that number of axes created matches the number of axes
        # specified.
        self.axes_list = list(self.figure.subplots(3, 3, squeeze=False).ravel())
        self.figure.suptitle(model.title)
        self._axes = {}
        for axes_spec, axes in zip(model.axes, self.axes_list):
            self._axes[axes_spec.uuid] = JupyterAxes(model=axes_spec, axes=axes)
        # This updates the Figure's internal state, setting its canvas.
        canvas = ipympl.backend_nbagg.Canvas(self.figure)
        label = "Figure"
        # this will stash itself on the canvas
        ipympl.backend_nbagg.FigureManager(canvas, 0)
        self.figure.set_label(label)
        self.children = (self.figure.canvas,)

        model.events.title.connect(self._on_title_changed)

        # By "resizing" (even without actually changing the size) we bump the
        # ipympl machinery that sets up frontend--backend communication and
        # starting displaying data from the figure. Without this, the figure
        # *widget* displays instantly but the actual *plot* (the PNG data sent from
        # matplotlib) is not displayed until cell execution completes.
        _, _, width, height = self.figure.bbox.bounds
        self.figure.canvas.manager.resize(width, height)
        self.figure.canvas.draw_idle()

        # The Figure model does not currently allow axes to be added or
        # removed, so we do not need to handle changes in model.axes.
