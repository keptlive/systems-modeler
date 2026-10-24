"""Original tiny fixtures plus an attributed SDXorg scalar equation excerpt."""
import math
import pytest
from app.core.mdl_parser import parse_mdl, MDLImportError
from app.core.model import Model
from app.core.simulator import simulate

# Equation/unit/control excerpt from SDXorg Teacup, James Houghton (2015).
# MIT license retained in tests/fixtures/sdxorg/LICENSE.
# https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/test/test-models/samples/teacup/teacup.mdl
TEACUP = """{UTF-8}
Characteristic Time=10 ~ Minutes [0,?] ~ |
Heat Loss to Room=(Teacup Temperature - Room Temperature) / Characteristic Time ~ Degrees Fahrenheit/Minute ~ |
Room Temperature=70 ~ Degrees Fahrenheit [-459.67,?] ~ |
Teacup Temperature=INTEG(-Heat Loss to Room,180) ~ Degrees Fahrenheit [32,212] ~ |
FINAL TIME=30 ~ Minute ~ |
INITIAL TIME=0 ~ Minute ~ |
SAVEPER=TIME STEP ~ Minute [0,?] ~ |
TIME STEP=0.125 ~ Minute [0,?] ~ |
"""

def test_actual_teacup_equations_match_analytic_cooling_and_preserve_source():
    imported=parse_mdl(TEACUP)
    assert imported["original_source"] == TEACUP
    assert imported["source_format"] == "vensim_mdl"
    assert any(d["code"]=="net_derivative_flow" for d in imported["diagnostics"])
    model=Model.model_validate(imported["model"])
    model.time_settings.integration_method="rk4"
    result=simulate(model)
    expected=[70+110*math.exp(-t/10) for t in result.time]
    assert result.values["Teacup Temperature"] == pytest.approx(expected,rel=1e-9,abs=1e-8)
    assert imported==parse_mdl(TEACUP)

def test_expression_initializer_and_case_insensitive_references():
    raw='''Base=10 ~ people ~ |
Population=INTEG(-population * rate, base * 2) ~ people ~ |
rate=0.1 ~ 1/year ~ |
INITIAL TIME=0 ~ year ~ |
FINAL TIME=2 ~ year ~ |
TIME STEP=0.25 ~ year ~ |
'''
    result=simulate(Model.model_validate(parse_mdl(raw)["model"]))
    assert result.values["Population"][0] == 20
    assert result.values["Population"][-1] < 20

def test_record_quotes_brace_comments_continuations_and_sketch():
    text='''{UTF-8}
{ comment includes = ~ | and nested { braces } }
"quoted name"=2 ~ unit ~ comment ~ unsupported |
'''
    with pytest.raises(MDLImportError,match="extra record"):
        parse_mdl(text)
    text='''{UTF-8}
"quoted name"=2 ~ unit ~ documentation with {ignored | ~ =} |
copy = "quoted name" + \\
 1 ~ unit ~ |
\\\\\\---/// Sketch information - do not modify
nonsense | not equations
'''
    parsed=parse_mdl(text)
    assert simulate(Model.model_validate(parsed["model"])).values["copy"][0]==3
    assert any(d["code"]=="display_metadata_omitted" for d in parsed["diagnostics"])
    assert parsed["original_source"]==text

def test_group_banner_and_condition_translation():
    text='''************************************
.Control
************************************~Simulation Control Parameters|
x=2 ~ ~ |
y=IF THEN ELSE(x=2 :AND: TIME>=0, 7, 9) ~ ~ |
'''
    parsed=parse_mdl(text)
    assert simulate(Model.model_validate(parsed["model"])).values["y"][0]==7
    assert any(d["code"]=="group_metadata_omitted" for d in parsed["diagnostics"])

def test_inline_lookup_clamps_and_interpolates_without_eval():
    text='''x=TIME ~ ~ |
y=WITH LOOKUP(x, ([(0,0)-(2,20)],(0,0),(1,10),(2,20))) ~ ~ |
INITIAL TIME=-1 ~ year ~ |
FINAL TIME=3 ~ year ~ |
TIME STEP=1 ~ year ~ |
'''
    parsed=parse_mdl(text)
    assert parsed["model"]["tables"][0]["interpolation"]=="continuous"
    assert simulate(Model.model_validate(parsed["model"])).values["y"]==[0,0,10,20,20]

@pytest.mark.parametrize("text",[
    "Region:North,South ~~|",
    "P[Region]=1 ~~|",
    ":MACRO: Something(x) ~~|",
    "x=DELAY1(1,2) ~~|",
    "x=PULSE(1,2) ~~|",
    "x=INTEG(1,2)+3 ~~|",
    "x= ~~|",
    "x=1 ~~",
    'x="unfinished ~~|',
    "x=1 ~~| {unfinished",
    "x=1 ~~| TIME STEP=bad ~~|",
    "x=1 ~~| SAVEPER=2 ~~| TIME STEP=1 ~~|",
    "x=WITH LOOKUP(TIME,((0,1),(0,2))) ~~|",
    "x=WITH LOOKUP(TIME,((0,1),(1,2))) + 2 ~~|",
    "x=1 ~~| X=2 ~~|",
    "P=INTEG(1,2) ~~| MDL net derivative P=2 ~~|",
    "x=__import__(3) ~~|",
    "x=SMOOTH N(1,2,0,3) ~~|",
    "x=1e999 ~~|",
    "x=1+WITH LOOKUP(TIME,((0,0),(1,1))) ~~|",
    "x=INTEG(WITH LOOKUP(TIME,((0,0),(1,1))),0) ~~|",
    "dt=3 ~~|",
])
def test_unsupported_or_invalid_records_never_import_as_success(text):
    with pytest.raises(MDLImportError) as exc:parse_mdl(text)
    assert exc.value.original_source==text
    assert exc.value.diagnostics[0]["severity"]=="error"

def test_resource_bounds_and_no_mutable_source():
    with pytest.raises(MDLImportError) as exc:parse_mdl("x"*2_000_001)
    assert exc.value.diagnostics[0]["code"]=="resource_limit"
    with pytest.raises(MDLImportError) as exc:parse_mdl("".join(f"x{i}=1 ~~|" for i in range(501)))
    assert exc.value.diagnostics[0]["code"]=="resource_limit"



def test_escaped_quotes_in_vensim_identifiers():
    # Official Vensim quoted-name escaping; same scanner semantics in records,
    # assignments and stock initializer argument splitting.
    quoted_name = '"a' + chr(92) + '"b"'
    source=quoted_name+"=2 ~~| Stock=INTEG(0, "+quoted_name+") ~~|"
    imported=parse_mdl(source)
    assert imported["model"]["variables"][0]["name"]=='a"b'
    result=simulate(Model.model_validate(imported["model"]))
    assert result.values["Stock"][0]==2
