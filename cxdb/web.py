"""Base web-app class."""
from __future__ import annotations

import sys
from pathlib import Path

from bottle import Bottle, request, template, TEMPLATE_PATH, static_file

from cxdb.material import Materials
from cxdb.session import Sessions
from cxdb.utils import Select, FormPart

TEMPLATE_PATH[:] = [str(Path(__file__).parent)]


class CXDBApp:
    title = 'CXDB'

    def __init__(self,
                 materials: Materials,
                 initial_columns: list[str],
                 root: Path | None = None):
        self.materials = materials
        self.root = root or Path()

        self.route()

        # For updating plots:
        self.callbacks = self.materials.get_callbacks()

        # User sessions (selected columns, sorting, filter string, ...)
        self.sessions = Sessions(initial_columns)

        self.form_parts: list[FormPart] = []

        # For selecting materials (A, AB, AB2, ...):
        self.form_parts.append(
            Select('Stoichiometry', 'stoichiometry',
                   [''] + self.materials.stoichiometries()))

        # For nspecies selection:
        maxnspecies = max(material.nspecies for material in self.materials)
        self.form_parts.append(
            Select('Number of chemical species', 'nspecies',
                   [''] + [str(i) for i in range(1, maxnspecies)]))

    def route(self):
        self.app = Bottle()
        self.app.route('/')(self.index)
        self.app.route('/material/<uid>')(self.material)
        self.app.route('/callback')(self.callback)
        self.app.route('/png/<uid>/<filename>')(self.png)
        self.app.route('/help')(self.help)

        for fmt in ['xyz', 'cif', 'json']:
            from functools import partial
            self.app.route(f'/material/<uid>/download/{fmt}')(
                partial(self.download, fmt=fmt))

    def download(self, uid: str, fmt: str) -> bytes | str:
        from io import StringIO, BytesIO
        from ase.io import write

        ase_fmt = fmt

        if fmt == 'xyz':
            # Only the extxyz writer includes cell, pbc etc.
            ase_fmt = 'extxyz'

        # (Can also query ASE's IOFormat for whether bytes or str,
        # in fact, ASE should make this easier.)
        buf: BytesIO | StringIO = BytesIO() if fmt == 'cif' else StringIO()

        atoms = self.materials[uid].atoms
        write(buf, atoms, format=ase_fmt)
        return buf.getvalue()

    def index(self) -> str:
        """Page showing table of selected materials."""
        query = request.query
        filter_string = self.get_filter_string(query)
        session = self.sessions.get(int(query.get('sid', '-1')))
        session.update(filter_string, query)
        search = '\n'.join(fp.render(query) for fp in self.form_parts)
        rows, header, pages, new_columns = self.materials.get_rows(session)

        return template('index.html',
                        title=self.title,
                        query=query,
                        search=search,
                        session=session,
                        pages=pages,
                        rows=rows,
                        header=header,
                        new_columns=new_columns)

    def get_filter_string(self, query: dict) -> str:
        """Generate filter string from URL query.

        Example::

            {'filter': Cu=1,gap>1.5',
             'stoichiometry': 'AB2',
             'nspecies': ''}

        will give the string "Cu=1,gap>1.5,stoichiometry=AB2".
        """
        filters = []
        filter = query.get('filter', '')
        if filter:
            filters.append(filter)
        for s in self.form_parts:
            filters += s.get_filter_strings(query)
        return ','.join(filters)

    def material(self, uid: str) -> str:
        """Page showing one selected material."""
        if uid == 'stop':  # pragma: no cover
            sys.stderr.close()
        material = self.materials[uid]
        panels = []
        footer = ''
        for panel in self.materials.panels:
            html1, html2 = panel.get_html(material, self.materials)
            if html1:
                panels.append((panel.title, html1))
                footer += html2
        return template('material.html',
                        title=uid,
                        panels=panels,
                        footer=footer)

    def callback(self) -> str:
        query = request.query
        name = query['name']
        uid = query['uid']
        material = self.materials[uid]
        return self.callbacks[name](material, int(query['data']))

    def help(self):
        return template('help.html')

    def png(self, uid: str, filename: str) -> bytes:
        material = self.materials[uid]
        return static_file(str(material.folder / filename), self.root)
