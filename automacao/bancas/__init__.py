from automacao.bancas.fundatec import scrape_fundatec
from automacao.bancas.fepese import scrape_fepese
from automacao.bancas.fgv import scrape_fgv
from automacao.bancas.cebraspe import scrape_cebraspe
from automacao.bancas.legalle import scrape_legalle
from automacao.bancas.fafipa import scrape_fafipa
from automacao.bancas.cs_ufg import scrape_cs_ufg
from automacao.bancas.aocp import scrape_aocp

ALL_BANCAS = [
    scrape_fundatec,    # maior banca do RS
    scrape_fepese,      # maior banca de SC
    scrape_fgv,         # atuante em SC e PR (TCE SC, etc.)
    scrape_cebraspe,    # federal, forte no Sul
    scrape_legalle,     # RS (Badesul, municipios)
    scrape_fafipa,      # PR (Foz do Iguacu, municipios)
    scrape_cs_ufg,      # RS/SC (universidades federais)
    scrape_aocp,        # PR/SC/RS (federais e estaduais)
]
