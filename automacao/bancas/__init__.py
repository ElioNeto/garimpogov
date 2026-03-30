from automacao.bancas.cebraspe import scrape_cebraspe
from automacao.bancas.fgv import scrape_fgv
from automacao.bancas.fcc import scrape_fcc
from automacao.bancas.vunesp import scrape_vunesp
from automacao.bancas.ibfc import scrape_ibfc
from automacao.bancas.cs_ufg import scrape_cs_ufg
from automacao.bancas.objetiva import scrape_objetiva

ALL_BANCAS = [
    scrape_cebraspe,
    scrape_fgv,
    scrape_fcc,
    scrape_vunesp,
    scrape_ibfc,
    scrape_cs_ufg,
    scrape_objetiva,
]
