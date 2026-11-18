"""
Bot que revisa la agenda de licencias de conducir de la Municipalidad de Iquique
y avisa por Telegram cuando aparece una fecha disponible.

Corre solo en GitHub Actions (no necesita tu computador prendido).
Tus datos privados (RUT, clave, token de Telegram) van en los "Secrets" del
repositorio, nunca escritos en este archivo.
"""

import datetime as dt
import os
import sys

import requests
from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

BASE = "https://www.proexsi.cl/iquique/oirs/agendaelectronica/frontoffice"
URL_LOGIN = f"{BASE}/default.aspx"
URL_RESERVAR = f"{BASE}/pages/frmAgendaReservar.aspx"

# Unidades de atención que se revisan (código del sitio: nombre para el mensaje)
UNIDADES = {
    "LIC": "Licencias de Conducir",
    "LIC02": "Licencias de Conducir (tardes)",
}

# Cuántos meses revisar, partiendo por el actual (3 = este mes y los 2 siguientes)
MESES_A_REVISAR = int(os.getenv("MESES_A_REVISAR", "3"))

NOMBRE_MES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
              "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

RUT = os.environ["RUT"]
CLAVE = os.environ["CLAVE"]
TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
MODO_PRUEBA = os.getenv("MODO_PRUEBA", "false").strip().lower() == "true"


def telegram(texto: str) -> None:
    """Envía un mensaje a tu Telegram."""
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": texto[:4000], "disable_web_page_preview": True},
        timeout=30,
    )
    r.raise_for_status()


def meses_siguientes(n: int):
    """Entrega (mes, año) desde el mes actual en Chile, n meses seguidos."""
    hoy = dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).date()
    mes, anio = hoy.month, hoy.year
    for _ in range(n):
        yield mes, anio
        mes += 1
        if mes == 13:
            mes, anio = 1, anio + 1


def iniciar_sesion(page) -> None:
    page.goto(URL_LOGIN, wait_until="networkidle")
    page.fill('input[placeholder^="Rut"]', RUT)
    page.fill('input[type="password"]', CLAVE)
    page.press('input[type="password"]', "Enter")
    try:
        page.wait_for_url("**/pages/**", timeout=30000)
    except PWTimeout:
        raise RuntimeError("No se pudo iniciar sesión. Revisa los Secrets RUT y CLAVE.")


def buscar(page, mes: int, anio: int, unidad: str):
    """Hace la búsqueda del formulario. Devuelve cuántas agendas aparecen,
    o None si ese año todavía no aparece en el sitio."""
    page.goto(URL_RESERVAR, wait_until="networkidle")
    anios = [a.strip() for a in page.locator('[id="cmbAño"] option').all_inner_texts()]
    if str(anio) not in anios:
        return None
    page.select_option("#cmbMes", str(mes))
    page.select_option('[id="cmbAño"]', label=str(anio))
    page.select_option("#cmbUnidadA", unidad)
    page.click("#btnConsultar")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    return page.locator('tr[id^="grid_listaDeAgendas_"]').count()


def leer_fechas(page, i: int):
    """Abre 'Ver Fechas' de la agenda número i y devuelve (nombre, texto)."""
    fila = page.locator('tr[id^="grid_listaDeAgendas_"]').nth(i)
    nombre = " ".join(fila.inner_text().replace("Ver Fechas", "").split())
    fila.get_by_text("Ver Fechas").first.click()
    page.wait_for_selector("#listaDeFechas .jscroll-added", timeout=30000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    texto = page.locator("#listaDeFechas").inner_text().strip()
    return nombre, texto


def revisar():
    hallazgos, resumen = [], []
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        page = navegador.new_page(locale="es-CL")
        page.set_default_timeout(30000)

        iniciar_sesion(page)

        for unidad, nombre_unidad in UNIDADES.items():
            for mes, anio in meses_siguientes(MESES_A_REVISAR):
                etiqueta = f"{NOMBRE_MES[mes]} {anio}"
                n = buscar(page, mes, anio, unidad)
                if n is None:
                    continue
                if n == 0:
                    resumen.append(f"• {nombre_unidad}, {etiqueta}: sin agenda abierta")
                    continue
                for i in range(n):
                    if i > 0:
                        buscar(page, mes, anio, unidad)
                    nombre_agenda, texto = leer_fechas(page, i)
                    if not texto or "No existen fechas" in texto:
                        resumen.append(f"• {nombre_unidad}, {etiqueta}: sin fechas")
                    else:
                        resumen.append(f"• {nombre_unidad}, {etiqueta}: ¡HAY FECHAS!")
                        hallazgos.append(f"📅 {nombre_agenda} ({etiqueta}):\n{texto[:700]}")

        navegador.close()
    return hallazgos, resumen


def main():
    try:
        hallazgos, resumen = revisar()
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr)
        if MODO_PRUEBA:
            telegram(f"⚠️ El bot de la licencia falló:\n{e}")
        sys.exit(1)

    print("\n".join(resumen))

    if hallazgos:
        telegram(
            "🚨 ¡Hay horas disponibles para la licencia en Iquique!\n\n"
            + "\n\n".join(hallazgos)
            + f"\n\nReserva rápido aquí: {URL_LOGIN}"
        )
    elif MODO_PRUEBA:
        telegram("✅ Bot funcionando. Por ahora no hay fechas:\n" + "\n".join(resumen))


if __name__ == "__main__":
    main()
