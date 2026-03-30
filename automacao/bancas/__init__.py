from automacao.bancas.fundatec import scrape_fundatec
from automacao.bancas.fepese import scrape_fepese
from automacao.bancas.fgv import scrape_fgv
from automacao.bancas.cebraspe import scrape_cebraspe
from automacao.bancas.legalle import scrape_legalle
from automacao.bancas.fafipa import scrape_fafipa
from automacao.bancas.cs_ufg import scrape_cs_ufg
from automacao.bancas.aocp import scrape_aocp
from automacao.bancas.fcc import scrape_fcc
from automacao.bancas.faurgs import scrape_faurgs
from automacao.bancas.lasalle import scrape_lasalle
from automacao.bancas.furb import scrape_furb
from automacao.bancas.objetiva import scrape_objetiva
from automacao.bancas.acafe import scrape_acafe
from automacao.bancas.ieses import scrape_ieses
from automacao.bancas.ameosc import scrape_ameosc
from automacao.bancas.amauc import scrape_amauc
from automacao.bancas.vunesp import scrape_vunesp
from automacao.bancas.quadrix import scrape_quadrix
from automacao.bancas.idecan import scrape_idecan
from automacao.bancas.ippec import scrape_ippec

ALL_BANCAS = [
    # RS
    scrape_fundatec,
    scrape_faurgs,
    scrape_lasalle,
    scrape_legalle,
    scrape_objetiva,
    # SC
    scrape_fepese,
    scrape_furb,
    scrape_acafe,
    scrape_ameosc,
    scrape_amauc,
    scrape_ieses,
    scrape_ippec,
    # PR
    scrape_fafipa,
    # RS/SC/PR
    scrape_aocp,
    scrape_cs_ufg,
    scrape_fcc,
    scrape_fgv,
    scrape_cebraspe,
    scrape_vunesp,
    scrape_quadrix,
    scrape_idecan,
]
