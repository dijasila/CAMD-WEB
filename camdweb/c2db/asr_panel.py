"""Hack to use webpanel() functions from ASR."""
from __future__ import annotations

import gzip
import importlib
from pathlib import Path

import matplotlib.pyplot as plt
from ase.db.core import KeyDescription
from ase.io.jsonio import decode
from camdweb.html import table, image
from camdweb.material import Material
from camdweb.panels.panel import Panel, PanelData, SkipPanel

HTML = """
<div class="row">
  <div class="col-6">
   {col1}
  </div>
  <div class="col-6">
   {col2}
  </div>
</div>
"""


def read_result_file(path: Path) -> dict:
    gz = path.with_suffix('.json.gz')
    if gz.is_file():
        with gzip.open(gz, 'rt') as fd:
            txt = fd.read()
    else:
        txt = path.read_text()
    dct = decode(txt)
    if 'kwargs' in dct:
        dct = dct['kwargs']['data']
    return dct


class Row:
    """Fake row object."""
    def __init__(self, material: Material):
        self.data = Data(material.folder)
        self.__dict__.update(material.columns)
        self.atoms = material.atoms
        self.cell = self.atoms.cell
        self.pbc = self.atoms.pbc
        self.symbols = self.atoms.symbols
        self.is_magnetic = getattr(material, 'magstate', '??') == 'FM'

    def toatoms(self):
        return self.atoms

    def get(self, name: str, default=None):
        if hasattr(self, name):
            return getattr(self, name)
        else:  # pragma: no cover
            return default

    def __contains__(self, key):
        return hasattr(self, key)

    def __getitem__(self, key):
        return getattr(self, key)


class Data:
    def __init__(self, folder: Path):
        self.folder = folder

    def get(self, name, default=None):
        try:
            dct = read_result_file(self.folder / name)
        except FileNotFoundError:
            return None
        dct = {key: val['kwargs']['data']
               if isinstance(val, dict) and 'kwargs' in val else val
               for key, val in dct.items()}
        return dct

    def __contains__(self, name):  # pragma: no cover
        assert name.startswith('results-asr.')
        p = self.folder / name
        return p.is_file() or p.with_suffix('.json.gz').is_file()

    def __getitem__(self, name):
        return self.get(name)


class ASRPanel(Panel):
    """Generic ASR-panel."""
    def __init__(self,
                 name: str):
        super().__init__()
        self.name = name
        mod = importlib.import_module(f'asr.{name}')
        self.webpanel = mod.webpanel
        self.result_class = mod.Result
        self.key_descriptions = {}
        for key, desc in getattr(self.result_class,
                                 'key_descriptions', {}).items():
            self.key_descriptions[key] = KeyDescription(key, desc)

    def get_data(self,
                 material: Material) -> PanelData:
        """Create row and result objects and call webpanel() function."""
        row = Row(material)
        dct = row.data.get(f'results-asr.{self.name}.json')
        if dct is None:
            raise SkipPanel
        if self.name == 'deformationpotentials' and 'defpots_soc' not in dct:
            raise SkipPanel  # pragma: no cover
        result = self.result_class(dct)
        (p, *_) = self.webpanel(result, row, self.key_descriptions)

        columns: list[list[str]] = [[], []]
        for i, column in enumerate(p['columns']):
            for thing in column:
                if thing is not None:  # pragma: no branch
                    html = thing2html(thing, material.folder)
                    columns[i].append(html)

        all_paths = []  # files to be created
        for desc in p.get('plot_descriptions', []):
            paths = [material.folder / filename
                     for filename in desc['filenames']]
            all_paths += paths
            for f in paths:
                if not f.is_file():
                    # Call plot-function:
                    desc['function'](row, *paths)
                    plt.close()
                    break

        assert all(path.is_file() for path in all_paths), all_paths

        return PanelData(
            HTML.format(col1='\n'.join(columns[0]),
                        col2='\n'.join(columns[1])),
            p['title'])


def thing2html(thing: dict, path: Path) -> str:
    """Convert webpanel() output to HTML."""
    if thing['type'] == 'figure':
        filename = thing['filename']
        html = image(path / filename)
    elif thing['type'] == 'table':
        html = table(thing.get('header'), thing['rows'])
    else:
        raise ValueError
    return html
