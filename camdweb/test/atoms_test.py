from ase import Atoms
from ase.build import bulk, molecule

from camdweb.material import Material
from camdweb.panels.atoms import plot_atoms, get_bonds


def test_1d():
    mat = Material('x', Atoms('H', [[2.5, 2.5, 0]],
                              cell=[5, 5, 1],
                              pbc=[False, False, True]))
    assert mat.length == 1.0


def test_plot():
    plot_atoms(Atoms('H', [[1, 1, 1]], cell=[2, 2, 2]))


def test_bonds_molecule():
    assert len(get_bonds(molecule('CH3CH2OH'))[0]) == 8


def test_bonds_bulk():
    assert len(get_bonds(bulk('Al'))[0]) == 12


def test_bonds_mixed():
    assert len(get_bonds(bulk('Al') * (2, 1, 1))[0]) == 2 * 12 - 1
