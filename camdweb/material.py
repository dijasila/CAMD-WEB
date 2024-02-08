from __future__ import annotations

from pathlib import Path

import numpy as np
from ase import Atoms
from ase.io import read

from camdweb.utils import fft


class Material:
    def __init__(self,
                 uid: str,
                 folder: Path | None = None,
                 atoms: Atoms | None = None):
        """Object representing a material and associated data.

        >>> mat = Material('x1', atoms=Atoms('H2O'))
        >>> mat.formula
        'OH2'
        >>> mat.stoichiometry
        'AB2'
        """
        self.uid = uid
        self.folder = folder or Path()
        self.atoms = atoms or Atoms()

        # Get number-of-atoms dicts:
        self.count, formula, reduced, stoichiometry = fft(self.atoms.numbers)

        self.columns = {
            'uid': uid,
            'natoms': sum(self.count.values()),
            'nspecies': len(self.count),
            'formula': formula,
            'reduced': reduced,
            'stoichiometry': stoichiometry}
        pbc = self.atoms.pbc
        dims = pbc.sum()
        if dims > 0:
            vol = abs(np.linalg.det(self.atoms.cell[pbc][:, pbc]))
            name = ['length', 'area', 'volume'][dims - 1]
            self.columns[name] = vol

    def __getattr__(self, name):
        return self.columns[name]

    @classmethod
    def from_file(cls, file: Path, uid: str) -> Material:
        atoms = read(file)
        assert isinstance(atoms, Atoms)
        return cls(uid, file.parent, atoms)
