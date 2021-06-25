import json
import re

import pandas as pd
import matplotlib.pyplot as plt


def read_pytest_benchmark_json(json_filepath):
    with open(json_filepath) as f:
        data = json.load(f)

    name_mapping = {
        "min": "min_seconds",
        "max": "max_seconds",
        "median": "median_seconds",
        "mean": "mean_seconds",
        "total": "total_seconds",
        "iqr": "iqr_seconds",
        "ops": "operations_per_second",
        "q1": "q1_seconds",
        "q3": "q3_seconds",
        "total": "total_test_time_seconds",
    }

    rows = []

    for benchmark in data["benchmarks"]:
        row = {}

        row["group"] = benchmark["group"]

        # Strip out parameters from the benchmark name, if present
        row["name"] = benchmark["fullname"].replace("[" + benchmark["param"] + "]", "")

        for name, val in benchmark["params"].items():
            row["param_{}".format(name)] = val

        for name, val in benchmark["extra_info"].items():
            row["info_{}".format(name)] = val

        # Copy over stats
        stats = benchmark["stats"]
        for (old_name, new_name) in name_mapping.items():
            row[new_name] = stats[old_name]

        # iterations is the number of iterations per round
        row["total_iterations"] = stats["rounds"] * stats["iterations"]

        rows.append(row)

    df = pd.DataFrame(rows)
    df["json_filepath"] = json_filepath
    return df


def plot(df, xaxis, yaxis, shade_between=None, label=None, label_by=None, axes=None):
    """Plot a dataframe.

    Parameters
    ----------

    df: pandas.DataFrame

    xaxis: Union[str, pandas.Series]

        The x-axis values.  If passed a string, assumes this is a
        column name of ``df``.  If passed a ``pandas.Series``, should
        be the same length as ``df``.

    yaxis: Union[str, pandas.Series]

        The y-axis values.  If passed a string, assumes this is a
        column name of ``df``.  If passed a ``pandas.Series``, should
        be the same length as ``df``.

    shade_between: Optional[tuple(Union[str, pandas.Series], Union[str, pandas.Series])]

        A region to shade some color.  If passed a string, assumes
        this is a column name of ``df``.  If passed a
        ``pandas.Series``, should be the same length as ``df``.

    label: Optional[str]

        The label for the plot.

    label_by: Optional[Union[str, pandas.Series]]

        Labels to apply to the dataset.  If passed a string, assumes
        this is a column name of ``df``.  If passed a
        ``pandas.Series``, should be the same length as ``df``.  Each
        unique value in the series or dataframe column is given a
        different color in the legend.

        If passed, this overrides the ``label`` option.

    axes: Optional[matplotlib.axes.Axes]

        The matplotlib axes in which to create the plot.  If None,
        will create a new figure.
    """

    # Parameter normalization
    if axes is None:
        fig, axes = plt.subplots()

    plot_df = {}

    plot_df["xaxis"] = df[xaxis] if isinstance(xaxis, str) else xaxis
    plot_df["yaxis"] = df[yaxis] if isinstance(yaxis, str) else yaxis

    if isinstance(label_by, str):
        plot_df["label"] = df[label_by]
    elif label is not None:
        plot_df["label"] = label
    else:
        plot_df["label"] = None

    if shade_between is not None:
        shade_low, shade_high = shade_between
        if isinstance(shade_low, str):
            shade_low = df[shade_low]
        if isinstance(shade_high, str):
            shade_high = df[shade_high]

        plot_df["shade_low"] = shade_low
        plot_df["shade_high"] = shade_high

    plot_df = pd.DataFrame(plot_df)

    # Prune out unplottable rows
    required_cols = [
        colname
        for colname in ["xaxis", "yaxis", "shade_low", "shade_high"]
        if colname in plot_df
    ]
    valid_rows = plot_df[required_cols].notna().all(axis=1)
    plot_df = plot_df[valid_rows]

    for label, group in plot_df.groupby("label"):
        group = group.sort_values("xaxis")
        (line,) = axes.plot(group.xaxis, group.yaxis, label=label)
        if "shade_low" in group.columns and "shade_high" in group.columns:
            axes.fill_between(
                group.xaxis,
                group.shade_low,
                group.shade_high,
                color=line.get_color(),
                alpha=0.5,
            )
