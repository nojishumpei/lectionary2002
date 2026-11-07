"""Selection and reading-adapter checks; these do not require TeX or fonts."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('book_builder', HERE / 'build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class CatalogueSelection(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.patch = patch.object(builder, 'ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        for key, kind in [('AD/a01ot', 'Lectio Prima'), ('AD/a01ep', 'Lectio Secunda'),
                          ('AD/a01ga', 'Evangelium'), ('EA/pv1ot', 'Lectio Prima'),
                          ('EA/pv4ot', 'Lectio Prima'), ('EA/pvgep', 'Lectio Secunda'),
                          ('SA/sjaot', 'Lectio Prima'), ('SA/sjaep', 'Lectio Secunda'),
                          ('VO/e01ot', 'Lectio Prima')]:
            self.reading(key, kind)
        (self.root / 'index.md').write_text('''## Proprium de Tempore
### Tempus Adventus
| [I](files/AD/a01ot.pdf) | [II](files/AD/a01ep.pdf) | [G](files/AD/a01ga.pdf) |
| [Repeated link](files/AD/a01ep.pdf) |
### Triduum Paschale et Tempus Paschale
| [I](files/EA/pv1ot.pdf) | [II](files/EA/pvgep.pdf) |
| [I](files/EA/pv4ot.pdf) |
## Proprium de Sanctis
| [I](files/SA/sjaot.pdf) | [II](files/SA/sjaep.pdf) |
## Missæ votivæ
| [I](files/VO/e01ot.pdf) |
## Fontes
''')

    def reading(self, key, kind):
        path = self.root / 'files' / (key + '.tex')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\\title{Celebratio}\n\\readingtype{' + kind + '}\n')

    def keys(self):
        return [key for _, groups in builder.catalogue() for keys, _, _ in groups for key in keys]

    def test_funeral_sections_exclude_gospels(self):
        options = [('d01ot', 'Lectio Prima', ''),
                   ('d01ac', 'Lectio Prima', r'\massdesignation{Tempore Paschali}'),
                   ('d01ep', 'Lectio Secunda', ''),
                   ('d01ga', 'Evangelium', r'\tone{Tonus Antiquior}'),
                   ('d01ga_br', 'Evangelium', r'\tone{Tonus Antiquior}'),
                   ('d01gl', 'Evangelium', r'\tone{Tonus ad libitum}')]
        links = []
        for stem, kind, detail in options:
            self.reading(f'DE/{stem}', kind)
            with (self.root / 'files' / 'DE' / f'{stem}.tex').open('a') as source:
                source.write(detail + '\n')
            links.append(f'| [Reading](files/DE/{stem}.pdf) |')
        index = self.root / 'index.md'
        index.write_text(index.read_text().replace(
            '## Fontes', '## Missæ Defunctorum\n' + '\n'.join(links) + '\n## Fontes'))
        groups = dict(builder.catalogue())['Missæ Defunctorum']
        self.assertEqual([title for _, _, title in groups], [
            'Lectio Prima Extra Tempus Paschale', 'Lectio Prima Tempore Paschali',
            'Lectio Secunda'])
        self.assertEqual([keys for keys, _, _ in groups], [['DE/d01ot'], ['DE/d01ac'], ['DE/d01ep']])

    def test_scope_deduplication_and_pentecost_order(self):
        self.assertEqual(self.keys(), ['AD/a01ot', 'AD/a01ep',
                                       'EA/pv1ot', 'EA/pv4ot', 'EA/pvgep'])

    def test_new_catalogued_reading_is_selected(self):
        self.reading('AD/a02ot', 'Lectio Prima')
        index = self.root / 'index.md'
        index.write_text(index.read_text().replace(
            '### Triduum Paschale', '| [Added](files/AD/a02ot.pdf) |\n### Triduum Paschale'))
        self.assertEqual(self.keys()[2], 'AD/a02ot')

    def test_uncatalogued_reading_is_reported(self):
        self.reading('AD/a02ot', 'Lectio Prima')
        with self.assertRaisesRegex(ValueError, 'AD/a02ot'):
            self.keys()

    def test_pulpit_scope_and_tone_order(self):
        intro = self.root / 'files/AD/a01ga.tex'
        intro.unlink()
        rows = []
        for prefix, title, mass in (
            ('LT/ppag', 'Dominica in Palmis de Passione Domini', 'Ad Processionem'),
            ('LT/pasg', 'Dominica in Palmis de Passione Domini', ''),
            ('EA/pasg', 'Feria VI in Passione Domini', ''),
            ('SA/sjag', 'Ss. Ioachim et Annæ', ''),
            ('VO/e01g', 'De Sanctissima Eucharistia', ''),
        ):
            links = []
            for suffix, tone in zip('ael', ('Tonus Antiquior', 'Tonus Evangelii', 'Tonus ad libitum')):
                key = prefix + suffix
                path = self.root / 'files' / f'{key}.tex'
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f'\\title{{{title}}}\n\\readingtype{{Evangelium}}\n'
                                f'\\massdesignation{{{mass}}}\n\\yearcycle{{A}}\n'
                                f'\\scriptureref{{Mt~21:1--11}}\n\\tone{{{tone}}}\n')
                links.append(f'[G](files/{key}.pdf)')
            rows.append('| ' + ' | '.join(links) + ' |')
        (self.root / 'index.md').write_text('## Proprium de Tempore\n### Tempus Quadragesimæ\n' +
                                             '\n'.join(rows) + '\n## Fontes\n')
        groups = dict(builder.pulpit_selection())['Tempus Quadragesimæ']
        self.assertEqual([keys for _, keys, _, _ in groups], [['LT/ppage', 'LT/ppagl', 'LT/ppaga']])


class ReadingAdapter(unittest.TestCase):
    SOURCE = r'''\begin{document}
\gabcsnippet{
(c3) Fra(h)tres:(h.) (;) De(h)us(h) est.(h.) (::h+)
}
\nopagebreak[4]
\input{../common/conc2}
\end{document}
'''
    CONCLUSIONS = {
        name: builder.CHANT_SNIPPET.search(
            (HERE.parent / 'files' / 'common' / (name + '.tex')).read_text())[1].strip()
        for name in builder.CONCLUSION_NAMES
    }

    def test_joined_dialogue_keeps_the_last_word_on_its_staff(self):
        result = builder.book_reading(self.SOURCE, self.CONCLUSIONS)
        self.assertNotIn('conc2', result)
        self.assertNotIn('nopagebreak', result)
        self.assertNotIn('::h+', result)
        self.assertEqual(result.count(r'\gabcsnippet'), 1)
        self.assertIn('De(h)us(h) <nlba>est.(h.) (::)\n<c><sp>V/', result)
        self.assertIn('as.</nlba>(f.) (::) (z)', result)

    def test_explicitly_suppressed_dialogue_stays_suppressed(self):
        source = self.SOURCE.replace(r'\nopagebreak[4]', '').replace('::h+', '::')
        source = source.replace(r'\input', r'%\input')
        result = builder.book_reading(source, self.CONCLUSIONS)
        self.assertNotIn('<nlba>', result)
        self.assertIn('est.(h.) (::) (z)', result)

    def test_joined_gospel_dialogue_uses_the_main_score_clef(self):
        source = self.SOURCE.replace('conc2', 'concg2')
        with self.assertRaisesRegex(ValueError, 'Closing clef differs'):
            builder.book_reading(source, self.CONCLUSIONS)
        result = builder.book_reading(source.replace('(c3)', '(c4)'), self.CONCLUSIONS)
        self.assertEqual(result.count('(c4)'), 1)
        self.assertIn('Laus(hihh) ti(g)bi,(gh) Chri(h.)ste.</nlba>(h.) (::) (z)', result)

    def test_pulpit_intro_places_custos_at_the_double_bar(self):
        source = (HERE.parent / 'files/common/matt_e.tex').read_text(encoding='utf-8')
        result = builder.pulpit_intro(source)
        self.assertIn('tu(h)o.(h.) (::h+Z-)\n', result)
        self.assertEqual(result.replace('(::h+Z-)', '(::)'), source)

    def test_optional_commented_verse_cannot_supply_the_last_word(self):
        source = self.SOURCE.replace('est.(h.) (::h+)', 'est.(h.) (:)\n% A(h)men.(h.) (::h+)')
        result = builder.book_reading(source, self.CONCLUSIONS)
        self.assertIn('<nlba>est.(h.) (:)\n<c><sp>V/', result)
        self.assertIn('(::) (z)\n% A(h)men.(h.) (::h+)', result)


if __name__ == '__main__':
    unittest.main()
