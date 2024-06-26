from dataclasses import dataclass


@dataclass
class Pages:
    buttons: list[tuple[int, str]]
    page: int
    row_start: int
    row_end: int
    rows_found: int

    def summary(self, total_rows: int) -> str:
        s = '' if self.rows_found == 1 else 's'
        return (
            f'Found {self.rows_found} row{s} out of {total_rows}, '
            f'showing rows {self.row_start}-{self.row_end}')


def get_pages_object(page: int,
                     nrows: int,
                     limit: int = 25):
    return Pages(
        get_pages(page, nrows, limit),
        page,
        page * limit + 1,
        min((page + 1) * limit, nrows),
        nrows)


def get_pages(page: int,
              nrows: int,
              limit: int = 25,
              pad: int = 2) -> list[tuple[int, str]]:
    """Paging button helper.

    >>> for p in get_pages(5, 100, 9, 1):
    ...     print(p)
    (0, '«')
    (4, '<')
    (4, '37-45')
    (5, '46-54')
    (6, '55-63')
    (6, '>')
    (11, '»')
    """
    npages = nrows // limit + 1
    forward_buttons = [(min(page + 1, npages - 1), '>'),
                       (npages - 1, '»')]
    backward_buttons = [(0, '«'), (max(page - 1, 0), '<')]
    current_buttons = []
    for current_page in range(page - pad, page + pad + 1):
        if not 0 <= current_page < npages:
            continue
        r1 = current_page * limit + 1
        r2 = min((current_page + 1) * limit, nrows)
        current_buttons.append((current_page, f'{r1}-{r2}'))

    return backward_buttons + current_buttons + forward_buttons
