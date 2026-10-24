from app.core.model import Model
from app.core.validation import inspect_inputs
from app.core.source_review import citation_reviews

SOURCE='https://doi.org/10.1016/j.jtbi.2017.11.024'
REFERENCE='Keeling MJ, Rohani P. Modeling Infectious Diseases in Humans and Animals. Princeton University Press, 2008.'

def test_review_is_visible_for_exact_citation_and_has_evidence():
    model=Model(source=SOURCE,reference=REFERENCE,variables=[{'name':'X','equation':'1'}])
    report=inspect_inputs(model)
    assert report['valid']  # A source concern is not a numerical syntax error.
    assert report['scientific_validation']=='not established'
    assert any(i['code']=='citation_mismatch' for i in report['issues'])
    review,=report['source_reviews']
    assert 'chondrogenesis' in review['resolved_title']
    assert review['evidence_url'].startswith('https://api.crossref.org/works/')
    assert len(review['evidence_sha256'])==64

def test_equation_edits_do_not_erase_wrong_citation_warning():
    model=Model(source=SOURCE,reference=REFERENCE,variables=[{'name':'X','equation':'2'}])
    assert citation_reviews(model)
    model.source='https://example.org/corrected-source'
    assert citation_reviews(model)==[]
    assert inspect_inputs(model)['scientific_validation']=='not established'

def test_unrelated_reference_is_not_matched_by_id_or_title():
    model=Model(id='cholera-sirw-model-epi',source=SOURCE,reference='Different work')
    assert citation_reviews(model)==[]
