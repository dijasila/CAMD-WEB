import json

from cxdb.section import Section
from cxdb.material import Material
from cxdb.utils import table


class BaderSection(Section):
    title = 'Bader-charge analysis'

    def get_html(self, material: Material) -> tuple[str, str]:
        path = material.folder / 'bader.json'
        if not path.is_file():
            return ('', '')
        charges = json.loads(path.read_text())['charges']
        return table(['#', 'Chemical symbol', 'Charges [|e|]'],
                     [(n, s, f'{c:.2f}') for n, (s, c)
                      in enumerate(zip(material.atoms.symbols, charges))]), ''