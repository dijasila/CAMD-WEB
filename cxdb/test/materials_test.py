import pickle
from pathlib import Path

import pytest
from ase import Atoms
from cxdb.material import Material, Materials
from cxdb.panels.asr_panel import Row
from cxdb.panels.atoms import AtomsPanel
from cxdb.panels.panel import Panel
from cxdb.session import Session


@pytest.fixture(scope='module')
def material():
    atoms = Atoms('H2', [(0, 0, 0), (0.7, 0, 0)], pbc=True)
    atoms.center(vacuum=2)
    material = Material(Path(), 'x', atoms)
    return material


def test_materials(material):
    materials = Materials([material], [AtomsPanel()])
    s = Session(1, ['uid'])
    rows, header, pages, new_columns = materials.get_rows(s)
    assert (rows, header, pages, new_columns) == (
        [('x', ['x'])],
        [('uid', 'Unique ID')],
        [(0, 'previous'), (0, 'next'), (0, '1-1')],
        [('formula', 'Formula'),
         ('reduced_formula', 'Reduced formula'),
         ('stoichiometry', 'Stoichiometry'),
         ('nspecies', 'Number of species'),
         ('volume', 'Volume [Å<sup>3</sup>]')])
    s.update('volume>1,stoichiometry=A', {})
    rows, _, _, _ = materials.get_rows(s)
    assert len(rows) == 1
    s.update('stoichiometry=A', {})
    rows, _, _, _ = materials.get_rows(s)
    assert len(rows) == 1
    s.update('stoichiometry=AB', {})
    rows, _, _, _ = materials.get_rows(s)
    assert len(rows) == 0


def test_attribute_error(material):
    with pytest.raises(AttributeError):
        material.asdf


def test_pickle(material):
    pickle.loads(pickle.dumps(material))


def test_collision():
    class MyPanel(Panel):
        column_names = {'formula': '...'}

        def get_html(self, material, materials):
            return '', ''

    with pytest.raises(ValueError):
        panel = MyPanel()
        panel.get_html()
        Materials([], [panel])


def test_row(material):
    assert Row(material).toatoms().pbc.all()
