from cxdb.utils import Range


def test_range():
    r = Range('ABC', 'x')
    ','.join(r.get_filter_strings({})) == ''
    ','.join(r.get_filter_strings({'to_x': '1'})) == 'x<=1'
    ','.join(r.get_filter_strings({'from_x': '1'})) == 'x>=1'
    ','.join(r.get_filter_strings({'from_x': '1', 'to_x': '2'})) == 'x>=1,x<=2'
