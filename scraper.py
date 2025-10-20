import requests
from bs4 import BeautifulSoup
import json
import datetime
import re
from pathlib import Path
import sys
import time


class TelekinoAdvancedScraper:
    def __init__(self):
        self.base_url = "https://www.telekino.com.ar/Resultados"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })

    def scrape_all_draws(self):
        """Scrapea todos los sorteos disponibles"""
        try:
            print("🔄 Obteniendo página principal de Telekino...")
            response = self.session.get(self.base_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extraer sorteos disponibles del dropdown
            available_draws = self.extract_available_draws(soup)
            print(f"✅ Encontrados {len(available_draws)} sorteos en el selector")

            # Extraer datos del sorteo actual
            current_draw = self.extract_current_draw(soup)

            # Scrapear datos históricos de todos los sorteos
            historical_draws = self.scrape_historical_draws(available_draws)

            return {
                'current_draw': current_draw,
                'available_draws': available_draws,
                'historical_draws': historical_draws,
                'scraped_at': datetime.datetime.now().isoformat(),
                'source_url': self.base_url,
                'total_draws_scraped': len(historical_draws) + (1 if current_draw else 0)
            }

        except Exception as e:
            print(f"❌ Error general: {e}")
            import traceback
            traceback.print_exc()
            return None

    def extract_current_draw(self, soup):
        """Extrae los datos del sorteo actual mostrado en la página"""
        try:
            print("🔍 Extrayendo datos del sorteo actual...")

            # Extraer número de sorteo
            draw_number_elem = soup.find('strong', class_='fontSize2')
            draw_number = draw_number_elem.get_text().strip() if draw_number_elem else "No disponible"

            # Extraer fecha - buscar en diferentes ubicaciones
            date = "No disponible"
            date_patterns = [
                'strong.fontSize2',  # En el header principal
                'div.component strong.fontSize2',  # En componentes
                'td',  # En tablas
            ]

            for pattern in date_patterns:
                elements = soup.select(pattern)
                for elem in elements:
                    text = elem.get_text().strip()
                    if re.match(r'\d{1,2}/\d{1,2}/\d{4}', text):
                        date = text
                        break
                if date != "No disponible":
                    break

            # Extraer números de Telekino
            telekino_numbers = []
            number_elements = soup.find_all('strong', class_='tamNumTelekino2')
            for elem in number_elements:
                num_text = elem.get_text().strip()
                if num_text.isdigit():
                    telekino_numbers.append(int(num_text))

            # Extraer números de Rekino
            rekino_numbers = []
            rekino_elements = soup.find_all('strong', class_='fontSizeRekino2')
            for elem in rekino_elements:
                num_text = elem.get_text().strip()
                if num_text.isdigit():
                    rekino_numbers.append(int(num_text))

            # Extraer premios si están disponibles
            prizes = self.extract_prizes(soup)

            draw_data = {
                'numero_sorteo': draw_number,
                'fecha': date,
                'numeros_telekino': sorted(telekino_numbers),
                'numeros_rekino': sorted(rekino_numbers),
                'premios': prizes,
                'tipo': 'actual'
            }

            print(
                f"✅ Sorteo actual: #{draw_number} - {len(telekino_numbers)} números Telekino, {len(rekino_numbers)} números Rekino")
            return draw_data

        except Exception as e:
            print(f"❌ Error extrayendo sorteo actual: {e}")
            return None

    def extract_available_draws(self, soup):
        """Extrae la lista completa de sorteos disponibles del dropdown"""
        draws = []
        try:
            select = soup.find('select')
            if select:
                options = select.find_all('option')
                for option in options:
                    value = option.get('value', '').strip()
                    text = option.get_text().strip()
                    if value and text:
                        # Parsear el texto para extraer número, fecha y color
                        parts = text.split('/')
                        if len(parts) >= 3:
                            draw_info = {
                                'valor': value,
                                'numero': parts[0].strip(),
                                'fecha': parts[1].strip(),
                                'color': parts[2].strip(),
                                'texto_completo': text
                            }
                            draws.append(draw_info)

            # Ordenar por número de sorteo (más reciente primero)
            draws.sort(key=lambda x: int(x['numero']), reverse=True)

        except Exception as e:
            print(f"❌ Error extrayendo sorteos disponibles: {e}")

        return draws

    def scrape_historical_draws(self, available_draws):
        """Scrapea datos históricos de todos los sorteos disponibles"""
        historical_draws = {}
        max_draws = 10  # Límite para no sobrecargar el sitio

        print(f"🔄 Scrapeando hasta {max_draws} sorteos históricos...")

        for i, draw in enumerate(available_draws[:max_draws]):
            try:
                print(
                    f"📊 Obteniendo datos del sorteo #{draw['numero']} ({i + 1}/{min(len(available_draws), max_draws)})")

                # Hacer request para el sorteo específico
                draw_data = self.scrape_single_draw(draw['valor'])
                if draw_data:
                    historical_draws[draw['numero']] = draw_data

                # Esperar entre requests para no sobrecargar el servidor
                time.sleep(1)

            except Exception as e:
                print(f"❌ Error scrapeando sorteo #{draw['numero']}: {e}")
                continue

        print(f"✅ Obtenidos {len(historical_draws)} sorteos históricos")
        return historical_draws

    def scrape_single_draw(self, draw_value):
        """Scrapea un sorteo específico por su valor"""
        try:
            # Para sorteos históricos, necesitamos hacer un POST request con el valor seleccionado
            payload = {
                '__RequestVerificationToken': '',  # Esto podría ser necesario
                'drawId': draw_value
            }

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': self.base_url,
                'X-Requested-With': 'XMLHttpRequest'  # Si usa AJAX
            }

            # Intentar diferentes métodos de obtención
            draw_data = self.try_different_methods(draw_value)

            if draw_data:
                draw_data['tipo'] = 'historico'
                return draw_data
            else:
                # Si no podemos obtener los datos específicos, al menos devolver la info básica
                return {
                    'numero_sorteo': draw_value,
                    'fecha': 'No disponible',
                    'numeros_telekino': [],
                    'numeros_rekino': [],
                    'tipo': 'historico',
                    'nota': 'Datos no disponibles mediante scraping automático'
                }

        except Exception as e:
            print(f"❌ Error scrapeando sorteo individual {draw_value}: {e}")
            return None

    def try_different_methods(self, draw_value):
        """Intenta diferentes métodos para obtener datos del sorteo"""
        methods = [
            self.method_direct_request,
            self.method_form_submission,
            self.method_url_parameter,
        ]

        for method in methods:
            try:
                result = method(draw_value)
                if result and (result.get('numeros_telekino') or result.get('numeros_rekino')):
                    return result
            except Exception as e:
                print(f"⚠️ Método {method.__name__} falló: {e}")
                continue

        return None

    def method_direct_request(self, draw_value):
        """Método 1: Request directo con parámetros en URL"""
        try:
            url = f"{self.base_url}?sorteo={draw_value}"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return self.parse_draw_page(response.content, draw_value)
        except Exception as e:
            print(f"⚠️ method_direct_request falló: {e}")
        return None

    def method_form_submission(self, draw_value):
        """Método 2: Simular envío de formulario"""
        try:
            # Obtener token CSRF primero
            main_response = self.session.get(self.base_url)
            main_soup = BeautifulSoup(main_response.content, 'html.parser')

            token_elem = main_soup.find('input', {'name': '__RequestVerificationToken'})
            token = token_elem.get('value') if token_elem else ''

            payload = {
                '__RequestVerificationToken': token,
                'drawId': draw_value
            }

            response = self.session.post(self.base_url, data=payload, timeout=10)
            if response.status_code == 200:
                return self.parse_draw_page(response.content, draw_value)
        except Exception as e:
            print(f"⚠️ method_form_submission falló: {e}")
        return None

    def method_url_parameter(self, draw_value):
        """Método 3: Intentar con diferentes formatos de URL"""
        url_variants = [
            f"{self.base_url}/{draw_value}",
            f"{self.base_url}?id={draw_value}",
            f"{self.base_url}?numero={draw_value}",
            f"{self.base_url}?draw={draw_value}",
        ]

        for url in url_variants:
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    result = self.parse_draw_page(response.content, draw_value)
                    if result:
                        return result
            except Exception as e:
                continue

        return None

    def parse_draw_page(self, content, draw_value):
        """Parsea el contenido HTML de una página de sorteo"""
        try:
            soup = BeautifulSoup(content, 'html.parser')

            # Buscar número de sorteo en diferentes ubicaciones
            draw_number = draw_value
            number_elems = soup.find_all('strong', class_='fontSize2')
            for elem in number_elems:
                text = elem.get_text().strip()
                if text.isdigit():
                    draw_number = text
                    break

            # Buscar fecha
            date = "No disponible"
            for elem in soup.find_all(['strong', 'div', 'span']):
                text = elem.get_text().strip()
                if re.match(r'\d{1,2}/\d{1,2}/\d{4}', text):
                    date = text
                    break

            # Extraer números de Telekino
            telekino_numbers = []
            number_elements = soup.find_all('strong', class_='tamNumTelekino2')
            for elem in number_elements:
                num_text = elem.get_text().strip()
                if num_text.isdigit():
                    telekino_numbers.append(int(num_text))

            # Extraer números de Rekino
            rekino_numbers = []
            rekino_elements = soup.find_all('strong', class_='fontSizeRekino2')
            for elem in rekino_elements:
                num_text = elem.get_text().strip()
                if num_text.isdigit():
                    rekino_numbers.append(int(num_text))

            # Extraer premios
            prizes = self.extract_prizes(soup)

            return {
                'numero_sorteo': draw_number,
                'fecha': date,
                'numeros_telekino': sorted(telekino_numbers),
                'numeros_rekino': sorted(rekino_numbers),
                'premios': prizes
            }

        except Exception as e:
            print(f"❌ Error parseando página del sorteo: {e}")
            return None

    def extract_prizes(self, soup):
        """Extrae información de premios si está disponible"""
        prizes = {
            'telekino': [],
            'rekino': []
        }

        try:
            # Buscar tablas de premios de Telekino
            tables = soup.find_all('table')
            for table in tables:
                if 'VERDETelekino' in table.get('class', []):
                    rows = table.find_all('tr')[1:]  # Saltar header
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 3:
                            prize_info = {
                                'categoria': cols[0].get_text().strip(),
                                'ganadores': cols[1].get_text().strip(),
                                'premio': cols[2].get_text().strip()
                            }
                            prizes['telekino'].append(prize_info)
        except Exception as e:
            print(f"⚠️ Error extrayendo premios: {e}")

        return prizes


def save_data(data):
    """Guarda los datos en formato JSON"""
    output_dir = Path('telekino-data')
    output_dir.mkdir(exist_ok=True)

    # Datos principales
    with open(output_dir / 'resultados.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Backup con timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    with open(output_dir / f'backup_{timestamp}.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Datos individuales para cada sorteo (útil para la web)
    historical_dir = output_dir / 'historicos'
    historical_dir.mkdir(exist_ok=True)

    # Guardar datos del sorteo actual
    if data['current_draw']:
        with open(historical_dir / f"sorteo_{data['current_draw']['numero_sorteo']}.json", 'w', encoding='utf-8') as f:
            json.dump(data['current_draw'], f, ensure_ascii=False, indent=2)

    # Guardar datos históricos
    for draw_num, draw_data in data['historical_draws'].items():
        with open(historical_dir / f"sorteo_{draw_num}.json", 'w', encoding='utf-8') as f:
            json.dump(draw_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Datos guardados en telekino-data/")
    print(f"   - resultados.json (datos completos)")
    print(f"   - backup_{timestamp}.json (backup)")
    print(f"   - historicos/ (datos individuales por sorteo)")
    return True


def main():
    scraper = TelekinoAdvancedScraper()
    data = scraper.scrape_all_draws()

    if data and data['current_draw']:
        if save_data(data):
            print("\n📊 RESUMEN FINAL:")
            print(f"   ✅ Sorteo actual: #{data['current_draw']['numero_sorteo']}")
            print(f"   📅 Fecha: {data['current_draw']['fecha']}")
            print(f"   🎯 Números Telekino: {data['current_draw']['numeros_telekino']}")
            print(f"   🎰 Números Rekino: {data['current_draw']['numeros_rekino']}")
            print(f"   📋 Sorteos disponibles: {len(data['available_draws'])}")
            print(f"   🗃️  Sorteos históricos obtenidos: {len(data['historical_draws'])}")
            print(f"   ⏰ Última actualización: {data['scraped_at']}")
            sys.exit(0)
        else:
            print("❌ Error guardando datos")
            sys.exit(1)
    else:
        print("❌ No se pudieron obtener los datos")
        sys.exit(1)


if __name__ == "__main__":
    main()