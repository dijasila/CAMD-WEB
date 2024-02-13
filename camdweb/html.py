from __future__ import annotations

import abc
from pathlib import Path
from typing import Iterable, Sequence


def table(header: list[str] | None, rows: Sequence[Iterable]) -> str:
    """Create HTML table.

    Example:

    === =====
    A   B
    === =====
    1.2 hello
    2.0 hi!
    === =====

    >>> print(table(['A', 'B'], [[1.2, 'hello'], [2.0, 'hi!']]))
    <table class="table table-striped">
     <thead>
      <tr>
       <th>A</th>
       <th>B</th>
      </tr>
     </thead>
     <tbody>
      <tr>
       <td>1.2</td>
       <td>hello</td>
      </tr>
      <tr>
       <td>2.0</td>
       <td>hi!</td>
      </tr>
     </tbody>
    </table>
    """
    if header is None:
        head = ''
    else:
        head = (' <thead>\n  <tr>\n   <th>' +
                '</th>\n   <th>'.join(header) +
                '</th>\n  </tr>\n </thead>\n')
    return (
        f'<table class="table table-striped">\n{head} <tbody>\n  <tr>\n   ' +
        '\n  </tr>\n  <tr>\n   '.join(
            '\n   '.join(f'<td>{x}</td>' for x in row)
            for row in rows) +
        '\n  </tr>\n </tbody>\n</table>')


def image(path: Path | str, alt=None) -> str:
    """Create <img> tag.

    >>> image('abc/def.png', alt='Short description')
    '<img alt="Short description" src="/png/abc/def.png" />'
    """
    return f'<img alt="{alt or path}" src="/png/{path}" />'


class FormPart(abc.ABC):
    def __init__(self, text: str, name: str):
        self.text = text
        self.name = name

    @abc.abstractmethod
    def render(self, query: dict) -> str:
        raise NotImplementedError

    def get_filter_strings(self, query: dict) -> list[str]:
        val = query.get(self.name, '')
        if val:
            return [f'{self.name}={val}']
        return []


class Select(FormPart):
    def __init__(self, text, name, options, names=None):
        super().__init__(text, name)
        self.options = options
        self.names = names

    def render(self) -> str:
        """Render select block.

        >>> s = Select('Bla-bla', 'xyz', ['A', 'B', 'C'])
        >>> print(s.render())
        <label class="form-label">Bla-bla</label>
        <select name="xyz" class="form-select">
          <option value="A" selected>A</option>
          <option value="B">B</option>
          <option value="C">C</option>
        </select>
        """
        parts = [f'<label class="form-label">{self.text}</label>\n'
                 f'<select name="{self.name}" class="form-select">']
        names = self.names or self.options
        selected = ' selected'
        for val, txt in zip(self.options, names):
            parts.append(f'  <option value="{val}"{selected}>{txt}</option>')
            selected = ''
        parts.append('</select>')
        return '\n'.join(parts)


class Input(FormPart):
    def __init__(self, text, name, placeholder='...'):
        super().__init__(text, name)
        self.placeholder = placeholder

    def render(self) -> str:
        """Render input block.

        >>> s = Input('Bla-bla', 'xyz')
        >>> print(s.render())
        <label class="form-label">Bla-bla</label>
        <input
          class="form-control"
          type="text"
          name="xyz"
          value=""
          placeholder="..." />
        """
        parts = [
            f'<label class="form-label">{self.text}</label>',
            '<input',
            '  class="form-control"',
            '  type="text"',
            f'  name="{self.name}"',
            '  value=""',
            f'  placeholder="{self.placeholder}" />']
        return '\n'.join(parts)


class Range(FormPart):
    def __init__(self, text: str, name: str, nonnegative=False):
        super().__init__(text, name)
        self.nonnegative = nonnegative

    def render(self) -> str:
        """Render range block.

        >>> s = Range('Band gap', 'gap')
        >>> print(s.render())
        <label class="form-label">Band gap</label>
        <input
          class="form-control"
          type="text"
          name="from_gap"
          value="" />
        <input
          class="form-control"
          type="text"
          name="to_gap"
          value="" />
        """
        parts = [
            f'<label class="form-label">{self.text}</label>',
            '<input',
            '  class="form-control"',
            '  type="text"',
            f'  name="from_{self.name}"',
            '  value="" />',
            '<input',
            '  class="form-control"',
            '  type="text"',
            f'  name="to_{self.name}"',
            '  value="" />']
        return '\n'.join(parts)

    def get_filter_strings(self, query: dict) -> list[str]:
        filters = []
        fro = query.get(f'from_{self.name}', '')
        if fro:
            limit = float(fro)
            if not self.nonnegative or limit > 0.0:
                filters.append(f'{self.name}>={fro}')
        to = query.get(f'to_{self.name}', '')
        if to:
            filters.append(f'{self.name}<={to}')
        return filters


class RangeX(Range):
    def __init__(self, text, name, options, names=None):
        super().__init__(text, name)
        self.options = options
        self.names = names

    def render(self) -> str:
        parts = [
            f'<label class="form-label">{self.text}</label>',
            '<input',
            '  class="form-control"',
            '  type="text"',
            f'  name="from_{self.name}"',
            '  value="" />',
            '<input',
            '  class="form-control"',
            '  type="text"',
            f'  name="to_{self.name}"',
            '  value="" />']
        parts += [f'<select name="{self.name}" class="form-select">']
        names = self.names or self.options
        for val, txt in zip(self.options, names):
            selected = ' selected' if val == '' else ''
            parts.append(f'  <option value="{val}"{selected}>{txt}</option>')
        parts.append('</select>')
        return '\n'.join(parts)

    def get_filter_strings(self, query: dict) -> list[str]:
        filters = []
        x = query.get(self.name)
        fro = query.get(f'from_{self.name}', '')
        if fro:
            filters.append(f'{x}>={fro}')
        to = query.get(f'to_{self.name}', '')
        if to:
            filters.append(f'{x}<={to}')
        return filters


class RangeS(Range):
    def __init__(self, text, name, options, names=None):
        super().__init__(text, name)
        self.options = options
        self.names = names

    def render(self) -> str:
        names = self.names or self.options

        parts = [f'<select name="from_{self.name}" class="form-select">']
        for val, txt in zip(self.options, names):
            selected = ' selected' if val == '' else ''
            parts.append(f'  <option value="{val}"{selected}>{txt}</option>')
        parts.append('</select>')

        parts = [f'<select name="to_{self.name}" class="form-select">']
        for val, txt in zip(self.options, names):
            selected = ' selected' if val == '' else ''
            parts.append(f'  <option value="{val}"{selected}>{txt}</option>')
        parts.append('</select>')

        return '\n'.join(parts)

    def get_filter_strings(self, query: dict) -> list[str]:
        filters = []
        fro = query.get(f'from_{self.name}', '')
        if fro:
            filters.append(f'{self.name}>={fro}')
        to = query.get(f'to_{self.name}', '')
        if to:
            filters.append(f'{self.name}<={to}')
        return filters
