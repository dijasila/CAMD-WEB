r"""
+---------------------+-----------+
|    ^                | OQMD refs |
|    |  *       *     | ...       |
|    |   \   * /      |           |
| ΔH,|    \   /       | C2DB refs |
| eV/|     \ /        | ...       |
| atm|      *         |           |
|    |                |           |
|     ------------>   |           |
|         A   B       |           |
|          1-x x      |           |
+---------------------+-----------+
"""

import json
import sys
from collections import defaultdict
from typing import Iterable

import plotly
import plotly.graph_objs as go
from ase.formula import Formula
from ase.phasediagram import PhaseDiagram

from cxdb.html import table
from cxdb.material import Material, Materials
from cxdb.c2db.asr_panel import read_result_file
from cxdb.panels.panel import Panel

HTML = """
<div class="row">
  <div class="col-6">
    {tbl0}
    <div id='chull' class='chull'></div>
  </div>
  <div class="col-6">
    {tbl1}
    {tbl2}
  </div>
</div>
"""

FOOTER = """
<script type='text/javascript'>
var graphs = {chull_json};
Plotly.newPlot('chull', graphs, {{}});
</script>
"""

OQMD = 'https://cmrdb.fysik.dtu.dk/oqmd123/row'


class ConvexHullPanel(Panel):
    title = 'Convex hull'

    def get_html(self,
                 material: Material,
                 materials: Materials) -> tuple[str, str]:
        tbl0 = table(None, materials.table(material, ['hform', 'ehull']))
        root = material.folder.parent.parent.parent
        name = ''.join(sorted(material._count))
        ch_file = root / f'convex-hulls/{name}.json'
        refs = read_result_file(ch_file)
        chull, tbl1, tbl2 = make_figure_and_tables(refs, verbose=False)
        html = HTML.format(tbl0=tbl0, tbl1=tbl1, tbl2=tbl2)
        if chull:
            return (html, FOOTER.format(chull_json=chull))
        return html, ''  # pragma: no cover


def make_figure_and_tables(refs: dict[str, tuple[dict[str, int],
                                                 float,
                                                 str]],
                           verbose: bool = True) -> tuple[str, str, str]:
    """Make convex-hull figure and tables.

    >>> refs = {'u1': ({'B': 1}, 0.0, 'OQMD'),
    ...         'u2': ({'B': 1, 'N': 1}, -0.5, 'OQMD'),
    ...         'u3': ({'N': 1}, 0.0, 'OQMD'),
    ...         '11': ({'B': 1, 'N': 1}, -0.2, 'C2DB')}
    >>> ch, tbl1, tbl2 = make_figure_and_tables(refs)
    Species: B, N
    References: 4
    0    B              0.000
    1    BN            -0.500
    2    N              0.000
    3    BN            -0.200
    Simplices: 2
    """
    tbl1 = []
    tbl2 = []
    labels = []
    for uid, (count, e, source) in refs.items():
        f = Formula.from_dict(count)
        hform = e / len(f)
        if source == 'OQMD':
            tbl1.append((hform, f'<a href={OQMD}/{uid}>{f:html}</a>'))
        else:
            assert source == 'C2DB'
            tbl2.append((hform, f'<a href={uid}>{f:html}</a>'))
        labels.append(f'{source}({uid})')

    try:
        pd = PhaseDiagram([(count, e) for count, e, source in refs.values()],
                          verbose=verbose)
    except ValueError:
        chull = ''  # only one species
    else:
        if len(pd.symbols) < 4:
            if len(pd.symbols) == 2:
                fig = plot_2d(pd, labels)
            else:
                fig = plot_3d(pd, labels)
            chull = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        else:
            chull = ''

    html1 = table(['Bulk crystals from OQMD123', ''],
                  [[link, f'{h:.2f} eV/atom'] for h, link in sorted(tbl1)])
    html2 = table(['Monolayers from C2DB', ''],
                  [[link, f'{h:.2f} eV/atom'] for h, link in sorted(tbl2)])

    return chull, html1, html2


def plot_2d(pd: PhaseDiagram,
            labels: list[str] | None = None) -> go.Figure:
    if labels is None:
        labels = [r[2] for r in pd.references]

    x, y = pd.points[:, 1:].T

    X = []
    Y = []
    for i, j in pd.simplices:
        X += [x[i], x[j], None]
        Y += [y[i], y[j], None]
    data = [go.Scatter(x=X, y=Y, mode='lines')]

    data.append(go.Scatter(
        x=x,
        y=y,
        text=labels,
        hovertemplate='%{text}: %{y} eV/atom',
        mode='markers'))

    delta = y.ptp() / 30
    ymin = y.min() - 2.5 * delta
    fig = go.Figure(data=data, layout_yaxis_range=[ymin, 0.1])

    A, B = pd.symbols
    fig.update_layout(
        xaxis_title=f'{A}<sub>1-x</sub>{B}<sub>x</sub>',
        yaxis_title='ΔH [eV/atom]',
        template='simple_white')

    return fig


def plot_3d(pd: PhaseDiagram,
            labels: list[str] | None = None) -> go.Figure:
    if labels is None:
        labels = [r[2] for r in pd.references]
    x, y, z = pd.points[:, 1:].T
    i, j, k = pd.simplices.T
    data = [go.Mesh3d(x=x, y=y, z=z, i=i, j=j, k=k, opacity=0.5)]
    data.append(
        go.Scatter3d(
            x=x, y=y, z=z,
            text=labels,
            hovertemplate='%{text}: %{z} eV/atom',
            mode='markers'))

    fig = go.Figure(data=data)
    A, B, C = pd.symbols
    fig.update_layout(scene=dict(xaxis_title=B,
                                 yaxis_title=C,
                                 zaxis_title='ΔH [eV/atom]'),
                      template='simple_white')

    return fig


def group_references(references: dict[str, tuple[str, ...]],
                     uids: Iterable[str],
                     check=True) -> dict[tuple[str, ...], list[str]]:
    """Group references into sets of convex hull candidates.

    >>> refs = {'1': ('A',),
    ...         '2': ('B',),
    ...         '3': ('A', 'B'),
    ...         'u1': ('A',),
    ...         'u2': ('A', 'B')}
    >>> group_references(refs, ['u1', 'u2'])
    {('A',): ['1', 'u1'], ('A', 'B'): ['1', '2', '3', 'u1', 'u2']}
    """
    index = defaultdict(set)
    for uid, symbols in references.items():
        if check and sorted(symbols) != list(symbols):
            print(symbols)
            raise ValueError
        for symbol in symbols:
            index[symbol].add(uid)
    chulls = {}
    for uid in uids:
        symbols = references[uid]
        if symbols in chulls:
            continue
        chull = set()
        for symbol in symbols:
            for uid2 in index[symbol]:
                if all(s in symbols for s in references[uid2]):
                    chull.add(uid2)
        chulls[symbols] = sorted(chull)
    return chulls


if __name__ == '__main__':
    # Example:
    # pyhton -m cxdb.panels.convex_hull A:0 B:0 AB:-0.5
    refs = []
    for arg in sys.argv[1:]:
        formula, energy = arg.split(':')
        refs.append((formula, float(energy)))
    pd = PhaseDiagram(refs)
    if len(pd.symbols) == 2:
        fig = plot_2d(pd)
    else:
        fig = plot_3d(pd)
    fig.show()
