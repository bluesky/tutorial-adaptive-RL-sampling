import numpy
import functools

from bluesky_widgets.utils.dict_view import DictView
from bluesky_widgets.models.plot_builders import Images, call_or_eval
from bluesky_widgets.models.plot_specs import ArtistSpec
from bluesky_widgets.models.plot_specs import Axes
from bluesky_widgets.models.utils import RunManager
from bluesky_widgets.jupyter.figures import (
    widgets,
    _initialize_mpl,
    matplotlib,
    JupyterAxes,
    JupyterFigure as JupyterFigure_,
    ipympl,
    Figure,
)

from bluesky_widgets._matplotlib_axes import MatplotlibAxes as _MatplotlibAxes


class Annotation(ArtistSpec):
    "Describes an image (both data and style)"


class Label:
    def __init__(
        self,
        field,
        *,
        max_runs=1,
        label_maker=None,
        needs_streams=("primary",),
        namespace=None,
        axes=None,
    ):
        super().__init__()
        self._field = field
        self._namespace = namespace
        if axes is None:
            axes = Axes()
            figure = Figure((axes,), title="")
        else:
            figure = axes.figure
        self.axes = axes
        self.figure = figure
        # If the Axes' figure is not yet set, listen for it to be set.
        if figure is None:

            def set_figure(event):
                self.figure = event.value
                # This occurs at most once, so we can now stop listening.
                self.axes.events.figure.disconnect(set_figure)

            self.axes.events.figure.connect(set_figure)

        self._run_manager = RunManager(max_runs, needs_streams)
        self._run_manager.events.run_ready.connect(self._add_label)
        self.add_run = self._run_manager.add_run
        self.discard_run = self._run_manager.discard_run

    def _add_label(self, event):
        run = event.run
        func = functools.partial(self._transform, field=self.field)
        image = Annotation.from_run(func, run, label=self.field)
        self._run_manager.track_artist(image, [run])
        self.axes.artists.append(image)
        self.axes.title = self._label_maaker(run, self.field)

    def _transform(self, run, field):
        img = call_or_eval({"array": field}, run, self.needs_streams, self.namespace)
        count, *_ = img.shape
        return {"txt": f"Number Exposed {count}"}

    @property
    def namespace(self):
        return DictView(self._namespace or {})


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
        self.figure = matplotlib.figure.Figure(constrained_layout=True)
        # TODO Let Figure give different options to subplots here,
        # but verify that number of axes created matches the number of axes
        # specified.
        self.axes_list = list(
            self.figure.subplots(3, 3, squeeze=False).ravel()
        )
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


class MatplotlibAxes(_MatplotlibAxes):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type_map[Annotation] = self._construct_annotation

    def _construct_annotation(self, *, txt, label, style):
        artist = self.axes.annotate(
            txt,
            (0, 0),
            xycoord="axes fraction",
            xytext=(2, 2),
            textcoords="offset points",
            label=label,
            **style,
        )

        def update(*, txt):
            artist.set_text(txt)
            self.draw_idle()

        return artist, update
