import sys
import os
import re
import time
import traceback
import threading
import base64
from datetime import datetime

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, QProgressBar, QComboBox, 
                            QGroupBox, QGridLayout, QFileDialog, QTextEdit, QSpinBox,
                            QCheckBox, QMessageBox, QRadioButton)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QPixmap

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import requests
import urllib3

# Desactivar advertencias de SSL para requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class WorkerThread(QThread):
    update_progress = pyqtSignal(int, str)
    update_status = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, identificacion, username, password, year_from, year_to, 
                 month_from, month_to, download_dir, headless=True, parent=None):
        QThread.__init__(self, parent)
        self.identificacion = identificacion
        self.username = username
        self.password = password
        self.year_from = year_from
        self.year_to = year_to
        self.month_from = month_from
        self.month_to = month_to
        self.download_dir = download_dir
        self.headless = headless
        self.is_running = True
    
    def stop(self):
        self.is_running = False
    
    def run(self):
        try:
            self.login_and_download_comprobantes()
            self.finished_signal.emit(True, "Proceso completado con éxito")
        except Exception as e:
            error_msg = f"Error durante la ejecución: {str(e)}\n{traceback.format_exc()}"
            self.update_status.emit(error_msg)
            self.finished_signal.emit(False, error_msg)
    
    def login_and_download_comprobantes(self):
        """
        Script para automatizar el inicio de sesión en CREMIL y la descarga de comprobantes de pago.
        """
        # Crear directorio de descarga si no existe
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
            self.update_status.emit(f"Directorio de descarga creado: {self.download_dir}")
        
        # Configurar opciones de Chrome
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--disable-extensions")
        # Permitir descargas en modo headless
        prefs = {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "profile.default_content_settings.popups": 0
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        self.update_status.emit("Iniciando navegador...")
        
        # Inicializar el driver
        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        except Exception as e:
            self.update_status.emit(f"Error al inicializar el driver: {str(e)}")
            raise

        try:
            # Abrir la página de inicio de sesión
            self.update_status.emit("Navegando a la página de inicio de sesión...")
            driver.get("https://www.cremil.gov.co/app/utils/login_form")
            self.update_status.emit("Página de inicio de sesión cargada correctamente")
            
            # Esperar a que el formulario de inicio de sesión sea visible
            self.update_status.emit("Esperando a que el formulario de inicio de sesión sea visible...")
            username_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "rn_LoginFormCremilv2_9_Username"))
            )
            
            # Ingresar credenciales
            self.update_status.emit(f"Ingresando nombre de usuario: {self.username}")
            username_field.send_keys(self.username)
            
            self.update_status.emit(f"Ingresando contraseña: {'*' * len(self.password)}")
            password_field = driver.find_element(By.ID, "rn_LoginFormCremilv2_9_Password")
            password_field.send_keys(self.password)
            self.update_status.emit("Credenciales ingresadas correctamente")
            
            # Hacer clic en el botón de inicio de sesión
            self.update_status.emit("Haciendo clic en el botón de inicio de sesión...")
            login_button = driver.find_element(By.ID, "rn_LoginFormCremilv2_9_Submit")
            login_button.click()
            self.update_status.emit("Botón de inicio de sesión presionado")
            
            # Esperar a que se complete el inicio de sesión
            self.update_status.emit("Esperando a que se complete el inicio de sesión...")
            time.sleep(8)
            
            # Verificar si el inicio de sesión fue exitoso
            if "account/overview" in driver.current_url:
                self.update_status.emit("Inicio de sesión exitoso")
            else:
                self.update_status.emit("Advertencia: No se ha detectado la URL de inicio de sesión exitoso")
            
            # Tomar una captura de pantalla después del inicio de sesión
            login_screenshot_path = os.path.join(self.download_dir, "cremil_logged_in.png")
            driver.save_screenshot(login_screenshot_path)
            self.update_status.emit(f"Captura de pantalla después del inicio de sesión guardada en: {login_screenshot_path}")
            
            # Navegar directamente a la página de comprobantes
            self.update_status.emit("Navegando directamente a la página de comprobantes...")
            driver.get("https://www.cremil.gov.co/app/descargarcomprobantes")
            self.update_status.emit("Navegación a la página de comprobantes realizada")
            
            # Esperar a que se cargue la página de comprobantes
            self.update_status.emit("Esperando a que se cargue la página de comprobantes...")
            time.sleep(10)
            
            # Tomar una captura de pantalla de la página de comprobantes
            comprobantes_screenshot_path = os.path.join(self.download_dir, "cremil_comprobantes.png")
            driver.save_screenshot(comprobantes_screenshot_path)
            self.update_status.emit(f"Captura de pantalla de la página de comprobantes guardada en: {comprobantes_screenshot_path}")
            
            # Modificar el campo numiden para usar el identificador personalizado
            self.update_status.emit(f"Modificando el número de identificación a: {self.identificacion}")
            driver.execute_script(f"document.getElementById('numiden').value = '{self.identificacion}'")
            
            # Guardar HTML de la página de comprobantes para análisis
            html_path = os.path.join(self.download_dir, "pagina_comprobantes.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            self.update_status.emit(f"HTML guardado en: {html_path}")
            
            # Descargar los comprobantes
            self.descargar_comprobantes(driver)
            
        except Exception as e:
            self.update_status.emit(f"Error durante la ejecución: {str(e)}")
            raise
        
        finally:
            driver.quit()
            self.update_status.emit("Navegador cerrado")
            
    def descargar_comprobantes(self, driver):
        """
        Método principal para descargar los comprobantes de pago
        """
        try:
            # Método 1: Descarga directa con Selenium y utilizando los URLs correctos
            self.update_status.emit("Método 1: Descargando mediante el navegador...")
            
            # Modificar el número de identificación en la tabla si es diferente
            if self.identificacion != "14835184":  # Si el usuario ingresó un ID diferente al predeterminado
                self.update_status.emit(f"Modificando número de identificación de 14835184 a {self.identificacion}...")
                # Encontrar todos los botones y modificar sus URLs
                buttons = driver.find_elements(By.CSS_SELECTOR, ".boton-estilo")
                for button in buttons:
                    url = button.get_attribute("data-url")
                    if url:
                        # Reemplazar numIdentificacion en la URL
                        new_url = url.replace("numIdentificacion=14835184", f"numIdentificacion={self.identificacion}")
                        # Actualizar el atributo data-url en el botón
                        driver.execute_script(f"arguments[0].setAttribute('data-url', '{new_url}')", button)
                
                self.update_status.emit(f"URLs actualizadas con el número de identificación {self.identificacion}")
            
            # Obtener todos los botones con sus URLs actualizadas
            buttons = driver.find_elements(By.CSS_SELECTOR, ".boton-estilo")
            total_buttons = len(buttons)
            
            if not buttons:
                self.update_status.emit("¡Advertencia! No se encontraron botones de descarga.")
                return
                
            self.update_status.emit(f"Se encontraron {total_buttons} comprobantes disponibles.")
            
            # Lista para guardar comprobantes filtrados
            filtered_comprobantes = []
            
            # Recolectar información de comprobantes y filtrar por fechas
            for idx, button in enumerate(buttons, 1):
                url = button.get_attribute("data-url")
                if not url:
                    continue
                    
                # Obtener datos de la fila
                row = button.find_element(By.XPATH, "./ancestor::tr")
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 3:
                    year_text = cells[0].text.strip()
                    month_name = cells[1].text.strip()
                    nomina_type = cells[2].text.strip()
                    
                    # Convertir año a entero
                    year = int(year_text) if year_text.isdigit() else 0
                    
                    # Convertir mes a número
                    months_map = {
                        "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6,
                        "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12
                    }
                    month_num = months_map.get(month_name, 0)
                    
                    # Verificar si está dentro del rango de fechas seleccionado
                    include = True
                    if self.year_from is not None and year < self.year_from:
                        include = False
                    if self.year_to is not None and year > self.year_to:
                        include = False
                    if self.month_from is not None and month_num < self.month_from and year == self.year_from:
                        include = False
                    if self.month_to is not None and month_num > self.month_to and year == self.year_to:
                        include = False
                    
                    if include:
                        # Extraer el consecutivo de la URL
                        match = re.search(r'numConsecutivo=(\d+)', url)
                        consecutivo = match.group(1) if match else f"consecutivo_{idx}"
                        
                        filtered_comprobantes.append({
                            "url": url,
                            "year": year,
                            "month_num": month_num,
                            "month_name": month_name,
                            "nomina_type": nomina_type,
                            "consecutivo": consecutivo,
                            "button": button
                        })
            
            # Descargar los comprobantes filtrados
            total = len(filtered_comprobantes)
            self.update_status.emit(f"Se descargarán {total} comprobantes según los filtros establecidos...")
            
            for idx, comp in enumerate(filtered_comprobantes, 1):
                if not self.is_running:
                    self.update_status.emit("Proceso cancelado por el usuario")
                    break
                
                url = comp["url"]
                year = comp["year"]
                month_num = comp["month_num"]
                month_name = comp["month_name"]
                nomina_type = comp["nomina_type"]
                consecutivo = comp["consecutivo"]
                
                filename = f"{self.identificacion}_{year}_{month_num:02d}_{nomina_type}_{consecutivo}.pdf"
                filepath = os.path.join(self.download_dir, filename)
                
                progress_pct = int((idx / total) * 100)
                self.update_progress.emit(progress_pct, f"Descargando {idx}/{total}: {year} - {month_name} - {nomina_type}")
                self.update_status.emit(f"Descargando comprobante: {year} - {month_name} - {nomina_type} (Consecutivo: {consecutivo})")
                
                success = False
                
                try:
                    # Configurar Chrome para guardar los PDF
                    driver.execute_script("window.open('');")
                    driver.switch_to.window(driver.window_handles[1])
                    
                    # Mostrar overlay y spinner en la interfaz original
                    driver.switch_to.window(driver.window_handles[0])
                    driver.execute_script('''
                        document.getElementById('overlay').style.display = 'block';
                        document.getElementById('spinner-container').style.display = 'block';
                        document.getElementById('txtloader').textContent = 'Descargando Comprobante...';
                    ''')
                    driver.switch_to.window(driver.window_handles[1])
                    
                    # Navegar a la URL del comprobante
                    driver.get(url)
                    self.update_status.emit(f"Esperando a que se cargue el PDF...")
                    
                    # Esperar a que se cargue el PDF (más tiempo para conexiones lentas)
                    time.sleep(12)
                    
                    # Verificar si es un PDF
                    if "pdf" in driver.current_url.lower() or "application/pdf" in driver.page_source.lower():
                        self.update_status.emit(f"PDF detectado, intentando extraer...")
                        
                        # Método 1.1: Intento directo desde el DOM
                        try:
                            pdf_content = driver.execute_script("return document.querySelector('embed').src;")
                            if pdf_content and pdf_content.startswith('data:application/pdf;base64,'):
                                # Extraer contenido base64
                                pdf_data = pdf_content.split(',')[1]
                                with open(filepath, 'wb') as f:
                                    f.write(base64.b64decode(pdf_data))
                                self.update_status.emit(f"✓ Comprobante guardado exitosamente en: {filepath}")
                                success = True
                            else:
                                self.update_status.emit(f"✗ No se pudo extraer el contenido PDF del embed")
                        except Exception as e:
                            self.update_status.emit(f"✗ Error al extraer desde embed: {str(e)}")
                            
                            # Método 1.2: Intentar con la URL directa si está en la barra de direcciones
                            try:
                                pdf_url = driver.current_url
                                if pdf_url.endswith('.pdf') or 'pdf' in pdf_url:
                                    self.update_status.emit(f"Intentando descargar directamente desde la URL del PDF...")
                                    
                                    # Usar requests con las cookies de sesión para descargar
                                    cookies = driver.get_cookies()
                                    cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                                    
                                    response = requests.get(pdf_url, cookies=cookies_dict, timeout=30, verify=False)
                                    if response.status_code == 200 and response.headers.get('content-type', '').lower().find('pdf') != -1:
                                        with open(filepath, 'wb') as f:
                                            f.write(response.content)
                                        self.update_status.emit(f"✓ Comprobante guardado exitosamente en: {filepath}")
                                        success = True
                                    else:
                                        self.update_status.emit(f"✗ Error al descargar, código: {response.status_code}")
                                else:
                                    self.update_status.emit(f"✗ La URL no es un PDF directo")
                            except Exception as e:
                                self.update_status.emit(f"✗ Error en descarga directa: {str(e)}")
                                
                                # Método 1.3: Intentar guardar como impresión PDF
                                try:
                                    self.update_status.emit(f"Intentando guardar como impresión PDF...")
                                    pdf = driver.execute_cdp_cmd("Page.printToPDF", {
                                        "printBackground": True,
                                        "preferCSSPageSize": True,
                                    })
                                    if pdf and "data" in pdf:
                                        with open(filepath, 'wb') as f:
                                            f.write(base64.b64decode(pdf["data"]))
                                        self.update_status.emit(f"✓ PDF guardado usando printToPDF en: {filepath}")
                                        success = True
                                    else:
                                        self.update_status.emit(f"✗ No se pudo imprimir a PDF")
                                except Exception as e:
                                    self.update_status.emit(f"✗ Error en impresión PDF: {str(e)}")
                    else:
                        # Si no es un PDF, guardar la página para análisis posterior
                        with open(f"{filepath}.html", 'w', encoding='utf-8') as f:
                            f.write(driver.page_source)
                        self.update_status.emit(f"✗ No se detectó contenido PDF. HTML guardado en: {filepath}.html")
                        
                        # Método 2: Intentar con requests directamente
                        if not success:
                            try:
                                self.update_status.emit(f"Método 2: Descargando mediante requests con cookies de sesión...")
                                cookies = driver.get_cookies()
                                cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                                
                                response = requests.get(url, cookies=cookies_dict, timeout=30, verify=False)
                                if response.status_code == 200:
                                    # Verificar si es un PDF por el tipo de contenido
                                    content_type = response.headers.get('content-type', '').lower()
                                    if 'pdf' in content_type or response.content[:4] == b'%PDF':
                                        with open(filepath, 'wb') as f:
                                            f.write(response.content)
                                        self.update_status.emit(f"✓ Comprobante guardado exitosamente en: {filepath}")
                                        success = True
                                    else:
                                        self.update_status.emit(f"✗ La respuesta no es un PDF (Content-Type: {content_type})")
                                        # Guardar la respuesta para análisis
                                        with open(f"{filepath}.response", 'wb') as f:
                                            f.write(response.content)
                                else:
                                    self.update_status.emit(f"✗ Error al descargar con requests. Código de estado: {response.status_code}")
                            except Exception as e:
                                self.update_status.emit(f"✗ Error durante la descarga con requests: {str(e)}")
                    
                    # Ocultar overlay y spinner
                    driver.switch_to.window(driver.window_handles[0])
                    driver.execute_script('''
                        document.getElementById('overlay').style.display = 'none';
                        document.getElementById('spinner-container').style.display = 'none';
                    ''')
                    
                    # Cerrar la pestaña y volver a la principal
                    driver.switch_to.window(driver.window_handles[1])
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    
                    # Verificar si se pudo descargar, si no intentar con el Método 3
                    if not success:
                        self.update_status.emit(f"Método 3: Haciendo clic en el botón directamente...")
                        try:
                            # Hacer clic en el botón directamente
                            button = comp["button"]
                            driver.execute_script("arguments[0].click();", button)
                            time.sleep(10)  # Esperar a que se descargue
                            
                            # Verificar si se descargó el archivo
                            if os.path.exists(filepath):
                                self.update_status.emit(f"✓ Comprobante descargado exitosamente mediante clic directo")
                                success = True
                            else:
                                self.update_status.emit(f"✗ No se detectó descarga automática del PDF")
                        except Exception as e:
                            self.update_status.emit(f"✗ Error durante el clic en el botón: {str(e)}")
                            
                except Exception as e:
                    self.update_status.emit(f"✗ Error durante la descarga: {str(e)}")
                    
                    # Intentar cerrar la pestaña adicional si quedó abierta
                    try:
                        if len(driver.window_handles) > 1:
                            driver.switch_to.window(driver.window_handles[1])
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
                    except:
                        pass
                    
                    # Ocultar overlay y spinner si hubo error
                    try:
                        driver.execute_script('''
                            document.getElementById('overlay').style.display = 'none';
                            document.getElementById('spinner-container').style.display = 'none';
                        ''')
                    except:
                        pass
                
                # Pequeña pausa entre descargas para no sobrecargar el servidor
                time.sleep(2)
            
            self.update_status.emit(f"Proceso de descarga completado. Se intentaron descargar {total} comprobantes.")
            
        except Exception as e:
            self.update_status.emit(f"Error durante la descarga de comprobantes: {str(e)}\n{traceback.format_exc()}")
            raise


class CremilApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.worker_thread = None
    
    def initUI(self):
        self.setWindowTitle("CREMIL - Descarga de Comprobantes de Pago")
        self.setGeometry(100, 100, 800, 700)
        
        # Widget principal
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Grupo de configuración
        config_group = QGroupBox("Configuración de la descarga")
        config_layout = QGridLayout()
        config_group.setLayout(config_layout)
        
        # Fila 1: Credenciales
        config_layout.addWidget(QLabel("Usuario:"), 0, 0)
        self.username_input = QLineEdit("14835184")
        config_layout.addWidget(self.username_input, 0, 1)
        
        config_layout.addWidget(QLabel("Contraseña:"), 0, 2)
        self.password_input = QLineEdit("Colombia2025*")
        self.password_input.setEchoMode(QLineEdit.Password)
        config_layout.addWidget(self.password_input, 0, 3)
        
        # Fila 2: Identificación
        config_layout.addWidget(QLabel("Número de identificación:"), 1, 0)
        self.id_input = QLineEdit()
        config_layout.addWidget(self.id_input, 1, 1, 1, 3)
        
        # Fila 3: Rango de años
        config_layout.addWidget(QLabel("Desde año:"), 2, 0)
        self.year_from = QSpinBox()
        self.year_from.setRange(2000, 2050)
        self.year_from.setValue(datetime.now().year - 1)
        config_layout.addWidget(self.year_from, 2, 1)
        
        config_layout.addWidget(QLabel("Hasta año:"), 2, 2)
        self.year_to = QSpinBox()
        self.year_to.setRange(2000, 2050)
        self.year_to.setValue(datetime.now().year)
        config_layout.addWidget(self.year_to, 2, 3)
        
        # Fila 4: Rango de meses
        config_layout.addWidget(QLabel("Desde mes:"), 3, 0)
        self.month_from = QComboBox()
        self.month_from.addItems(["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                               "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"])
        self.month_from.setCurrentIndex(0)  # Enero
        config_layout.addWidget(self.month_from, 3, 1)
        
        config_layout.addWidget(QLabel("Hasta mes:"), 3, 2)
        self.month_to = QComboBox()
        self.month_to.addItems(["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"])
        self.month_to.setCurrentIndex(11)  # Diciembre
        config_layout.addWidget(self.month_to, 3, 3)
        
        # Fila 5: Directorio de descarga
        config_layout.addWidget(QLabel("Directorio de descarga:"), 4, 0)
        self.download_dir = QLineEdit(os.path.join(os.path.expanduser("~"), "Descargas", "ComprobantesCreMil"))
        config_layout.addWidget(self.download_dir, 4, 1, 1, 2)
        self.browse_button = QPushButton("Examinar...")
        self.browse_button.clicked.connect(self.browse_directory)
        config_layout.addWidget(self.browse_button, 4, 3)
        
        # Fila 6: Modo navegador
        config_layout.addWidget(QLabel("Modo del navegador:"), 5, 0)
        self.mode_layout = QHBoxLayout()
        self.headless_radio = QRadioButton("Oculto (más rápido)")
        self.headless_radio.setChecked(True)
        self.visible_radio = QRadioButton("Visible (para depuración)")
        self.mode_layout.addWidget(self.headless_radio)
        self.mode_layout.addWidget(self.visible_radio)
        config_layout.addLayout(self.mode_layout, 5, 1, 1, 3)
        
        # Grupo de acciones
        actions_group = QGroupBox("Acciones")
        actions_layout = QHBoxLayout()
        actions_group.setLayout(actions_layout)
        
        # Botones
        self.start_button = QPushButton("Iniciar descarga")
        self.start_button.setMinimumHeight(40)
        self.start_button.clicked.connect(self.start_download)
        actions_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Detener")
        self.stop_button.setMinimumHeight(40)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_download)
        actions_layout.addWidget(self.stop_button)
        
        self.open_folder_button = QPushButton("Abrir carpeta destino")
        self.open_folder_button.setMinimumHeight(40)
        self.open_folder_button.clicked.connect(self.open_folder)
        actions_layout.addWidget(self.open_folder_button)
        
        # Grupo de progreso
        progress_group = QGroupBox("Progreso")
        progress_layout = QVBoxLayout()
        progress_group.setLayout(progress_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(25)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("Listo para iniciar")
        progress_layout.addWidget(self.progress_label)
        
        # Log de actividad
        log_group = QGroupBox("Registro de actividad")
        log_layout = QVBoxLayout()
        log_group.setLayout(log_layout)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        # Añadir todos los grupos al layout principal
        main_layout.addWidget(config_group)
        main_layout.addWidget(actions_group)
        main_layout.addWidget(config_group)
        main_layout.addWidget(actions_group)
        main_layout.addWidget(progress_group)
        main_layout.addWidget(log_group)
        
        # Inicializar
        self.log("Aplicación iniciada. Configure los parámetros y haga clic en 'Iniciar descarga'")
    
    def log(self, message):
        self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        # Desplazarse al final del log
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def update_progress_slot(self, value, text):
        self.progress_bar.setValue(value)
        self.progress_label.setText(text)
    
    def update_status_slot(self, message):
        self.log(message)
    
    def finished_slot(self, success, message):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if success:
            self.progress_label.setText("Descarga completada")
            QMessageBox.information(self, "Proceso completado", "La descarga de comprobantes ha finalizado con éxito.")
        else:
            self.progress_label.setText("Error en la descarga")
            QMessageBox.warning(self, "Error", f"El proceso falló: {message}")
    
    def browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Seleccionar directorio de destino", 
                                                   self.download_dir.text())
        if dir_path:
            self.download_dir.setText(dir_path)
    
    def open_folder(self):
        path = self.download_dir.text()
        if not os.path.exists(path):
            os.makedirs(path)
        
        # Abrir el explorador de archivos en la ruta especificada
        if sys.platform == 'win32':
            os.startfile(path)
        else:
            import subprocess
            subprocess.Popen(['xdg-open', path])
    
    def start_download(self):
        # Validar campos
        if not self.id_input.text():
            QMessageBox.warning(self, "Campos incompletos", "Por favor ingrese un número de identificación.")
            return
        
        if not self.download_dir.text():
            QMessageBox.warning(self, "Campos incompletos", "Por favor seleccione un directorio de descarga.")
            return
        
        # Configurar thread
        self.worker_thread = WorkerThread(
            identificacion=self.id_input.text(),
            username=self.username_input.text(), 
            password=self.password_input.text(),
            year_from=self.year_from.value(),
            year_to=self.year_to.value(),
            month_from=self.month_from.currentIndex() + 1,
            month_to=self.month_to.currentIndex() + 1,
            download_dir=self.download_dir.text(),
            headless=self.headless_radio.isChecked()
        )
        
        # Conectar señales
        self.worker_thread.update_progress.connect(self.update_progress_slot)
        self.worker_thread.update_status.connect(self.update_status_slot)
        self.worker_thread.finished_signal.connect(self.finished_slot)
        
        # Iniciar thread
        self.worker_thread.start()
        
        # Actualizar UI
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Iniciando proceso...")
        self.log("Proceso de descarga iniciado")
    
    def stop_download(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.log("Deteniendo el proceso...")
            self.worker_thread.stop()
            self.stop_button.setEnabled(False)
            self.progress_label.setText("Deteniendo...")


def main():
    app = QApplication(sys.argv)
    
    # Establecer estilo
    app.setStyle("Fusion")
    
    # Fuente por defecto
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    # Crear y mostrar la ventana principal
    window = CremilApp()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()