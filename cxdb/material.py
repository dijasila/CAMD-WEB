from __future__ import annotations

from collections.abc import Container
from math import nan
from pathlib import Path
from typing import Any, Sequence

from ase import Atoms
from ase.io import read

from cxdb.filter import Index, parse
from cxdb.paging import get_pages
from cxdb.panel import Panel
from cxdb.session import Session


class Material:
    def __init__(self, folder: Path, uid: str, atoms: Atoms):
        """Object representing a material and associated data.

        >>> mat = Material(Path(), 'x1', Atoms('H2O'))
        >>> mat.formula
        'OH2'
        >>> mat['formula']
        'OH<sub>2</sub>'
        >>> mat.stoichiometry
        'AB2'
        >>> mat.add_column('energy', -1.23456)
        >>> mat.energy, mat['energy']
        (-1.23456, '-1.235')
        """
        self.folder = folder
        self.uid = uid
        self.atoms = atoms

        formula = self.atoms.symbols.formula.convert('periodic')
        s11y, _, _ = formula.stoichiometry()

        self._count: dict[str, int] = formula.count()

        self._data: dict[str, Any] = {}
        self._html_reprs: dict[str, str] = {}
        self._values: dict[str, bool | int | float | str] = {}

        self.add_column('formula', formula.format(), formula.format('html'))
        self.add_column('stoichiometry', s11y.format(), s11y.format('html'))
        self.add_column('nspecies', len(self._count))
        self.add_column('uid', uid)

    @classmethod
    def from_file(cls, file: Path, uid: str) -> Material:
        atoms = read(file)
        assert isinstance(atoms, Atoms)
        return cls(file.parent, uid, atoms)

    def add_column(self,
                   name: str,
                   value: bool | int | float | str,
                   html: str | None = None) -> None:
        """Add data that can be used for filtering of materials."""
        self.add(name, value)
        self._values[name] = value
        if html is None:
            if isinstance(value, float):
                html = f'{value:.3f}'
            else:
                html = str(value)
        self._html_reprs[name] = html

    def add(self,
            name: str,
            value) -> None:
        """Add any kind of data."""
        assert name not in self._data, (name, self._data)
        self._data[name] = value

    def __getattr__(self, name: str) -> Any:
        """Get data by attribute."""
        return self._data[name]

    def __getitem__(self, name: str) -> str:
        """Get HTML string for data."""
        return self._html_reprs[name]

    def get(self, name: str, default: str = '') -> str:
        """Get HTML string for data."""
        return self._html_reprs.get(name, default)

    def check_columns(self, column_names: Container[str]) -> None:
        """Make sure we don't have unknown columns."""
        for name in self._values:
            assert name in column_names, name


class Materials:
    def __init__(self,
                 materials: list[Material],
                 panels: Sequence[Panel]):
        self.column_names = {
            'formula': 'Formula',
            'stoichiometry': 'Stoichiometry',
            'nspecies': 'Number of species',
            'uid': 'Unique ID'}

        for panel in panels:
            assert panel.column_names.keys().isdisjoint(self.column_names)
            self.column_names.update(panel.column_names)

        self._materials: dict[str, Material] = {}
        for material in materials:
            for panel in panels:
                panel.update_data(material)
            material.check_columns(self.column_names)
            self._materials[material.uid] = material

        self.index = Index([(mat._count, mat._values)
                            for mat in self._materials.values()])
        self.i2uid = {i: mat.uid for i, mat in enumerate(self)}

        self.panels = panels

    def __iter__(self):
        yield from self._materials.values()

    def get_callbacks(self):
        callbacks = {}
        for panel in self.panels:
            callbacks.update(panel.callbacks)
        return callbacks

    def stoichiometries(self) -> list[str]:
        """Construct list of stoichiometries present."""
        s = set()
        for material in self:
            s.add(material.stoichiometry)
        return list(s)

    def __getitem__(self, uid):
        return self._materials[uid]

    def get_rows(self,
                 session: Session) -> tuple[list[tuple[str, list[str]]],
                                            list[tuple[str, str]],
                                            list[tuple[int, str]],
                                            list[tuple[str, str]]]:
        """Filter rows for table.

        Example::

            rows, header, pages, new_columns = materials.get_rows(session)

        The returned values are:

        rows:
            list of rows, where each row is a tuple of uid and list of
            html-strings.

        header:
            list of (column name, column html-string) tuples.

        pages:
            stuff for pagination buttons (see get_pages() function).

        new_columns:
            list of (column name, columns html-string) tuples for columns not
            shown.
        """
        filter = session.filter
        func = parse(filter)
        rows = [self._materials[self.i2uid[i]] for i in func(self.index)]

        if rows and session.sort:
            missing = '' if session.sort in self.index.strings else nan

            def key(material):
                return material._values.get(session.sort, missing)

            rows = sorted(rows, key=key, reverse=session.direction == -1)

        page = session.page
        n = session.rows_per_page
        pages = get_pages(page, len(rows), n)
        rows = rows[n * page:n * (page + 1)]
        table = [(material.uid,
                  [material.get(name, '') for name in session.columns])
                 for material in rows]
        return (table,
                [(name, self.column_names[name]) for name in session.columns],
                pages,
                [(name, value) for name, value in self.column_names.items()
                 if name not in session.columns])
