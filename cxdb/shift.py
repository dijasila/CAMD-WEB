from textwrap import wrap

import matplotlib.pyplot as plt
import numpy as np

from cxdb.material import Material, Materials
from cxdb.panel import Panel
from cxdb.asr_panel import read_result_file

HTML = """
<img alt="DOS for {uid}" src="/png/{uid}/dos.png" />
"""


class ShiftPanel(Panel):
    title = 'Shift current spectrum (RPA)'

    def get_html(self,
                 material: Material,
                 materials: Materials) -> tuple[str, str]:
        self.make_figures(material)
        return (HTML.format(uid=material.uid), '')

    def make_figures(self, material):
        data = read_result_file(material.folder / 'results-asr.shift.json')

        # Make the table
        sym_chi = data.get('symm')
        table = []
        for pol in sorted(sym_chi.keys()):
            relation = sym_chi[pol]
            if pol == 'zero':
                if relation != '':
                    pol = 'Others'
                    relation = '0=' + relation
                else:
                    continue

            if (len(relation) == 3):
                relation_new = ''
            else:
                # relation_new = '$'+'$\n$'.join(wrap(relation, 40))+'$'
                relation_new = '\n'.join(wrap(relation, 50))
            table.append((pol, relation_new))

        # Make the figure list
        npan = len(sym_chi) - 1
        files = [material.folder / f'shift{ii + 1}.png' for ii in range(npan)]
        plot_shift(data, 1.2, files, nd=2)

        # 'header': ['Element', 'Relations']


def plot_shift(data, gap, filenames, nd=2):
    # Plot the data and add the axis labels
    sym_chi = data['symm']
    if len(sym_chi) == 1:
        raise ValueError  # CentroSymmetric
    sigma = data['sigma']
    if not sigma:
        return
    w_l = data['freqs']

    axes = []

    for filename, pol in zip(filenames, sorted(sigma.keys())):
        # Make the axis and add y=0 axis
        shift_l = sigma[pol]
        ax = plt.figure().add_subplot(111)
        ax.axhline(y=0, color='k')

        # Add the bandgap
        if gap is not None:
            ax.axvline(x=gap, color='k', ls='--')

        # Plot the data
        ax.plot(w_l, np.real(shift_l), '-', c='C0',)

        # Set the axis limit
        ax.set_xlim(0, np.max(w_l))
        relation = sym_chi.get(pol)
        if not (relation is None):
            figtitle = '$' + '$\n$'.join(wrap(relation, 40)) + '$'
            ax.set_title(figtitle)
        ax.set_xlabel(r'Energy [eV]')
        polstr = f'{pol}'
        if nd == 2:
            ax.set_ylabel(r'$\sigma^{(2)}_{' + polstr + r'}$ [nm$\mu$A/V$^2$]')
        else:
            ax.set_ylabel(r'$\sigma^{(2)}_{' + polstr + r'} [$\mu$A/V$^2$]')
        ax.ticklabel_format(axis='both', style='plain', scilimits=(-2, 2))

        # Remove the extra space and save the figure
        plt.tight_layout()
        plt.savefig(filename)
        axes.append(ax)
        plt.close()
