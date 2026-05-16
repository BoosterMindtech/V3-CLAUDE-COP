# HVACR Performance Analyser — v1.1

App de análisis termodinámico en tiempo real para equipos de refrigeración y climatización (chillers, bombas de calor, enfriadoras).  
Calcula COP, SEI, diagnóstico de fallos y genera informes para técnicos frigoristas.

Metodología: IEA HPT Annex 52.

---

## Archivos necesarios

```
/home/hvacr/
├── hvacr_3_cop_app.py    <- la app
└── requirements.txt      <- dependencias
```

---

## Instalación

```bash
# Instalar dependencias
pip install -r requirements.txt

# Arrancar la app
streamlit run hvacr_3_cop_app.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true
```

Accede desde el navegador en: `http://tu-ip-vps:8501`

---

## Arranque automático con systemd

Crea el archivo `/etc/systemd/system/hvacr.service`:

```ini
[Unit]
Description=HVACR Performance Analyser
After=network.target

[Service]
User=hvacr
WorkingDirectory=/home/hvacr
ExecStart=/usr/local/bin/streamlit run hvacr_3_cop_app.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable hvacr
systemctl start hvacr
systemctl status hvacr
```

---

## Refrigerantes soportados

| Refrigerante | Tipo       | GWP  |
|--------------|------------|------|
| R134a        | HFC        | 1430 |
| R410A        | HFC blend  | 2088 |
| R32          | HFC        | 675  |
| R407C        | HFC blend  | 1774 |
| R22          | HCFC (legacy) | 1810 |

---

## Modos de entrada de datos

### Manual
Introduce los valores de los sensores directamente en pantalla:
- Presiones de evaporación y condensación (bar abs)
- Temperaturas de aspiración y descarga del compresor
- Temperatura de salida del condensador (línea de líquido)
- Potencia eléctrica del compresor (kW)
- Temperaturas y caudales del lado secundario (agua fría / agua de condensación)

La app calcula la temperatura de saturación en tiempo real para cada presión introducida y advierte si los valores son anómalos.

### API BMS/SCADA/GMAO
Conecta con cualquier sistema de gestión mediante una API REST genérica.

Configuración necesaria en el sidebar:
- **URL endpoint**: dirección del punto de datos (ej. `http://bms.empresa.com/api/datos`)
- **API Key**: clave de autenticación (se envía como `Bearer` token)
- **Mapeo JSON**: correspondencia entre los campos de la app y las claves del JSON devuelto por la API

Ejemplo de mapeo JSON:
```json
{
  "P_evap_bar": "LP",
  "P_cond_bar": "HP",
  "T_comp_suction": "T_ASP",
  "T_comp_discharge": "T_DESC",
  "T_cond_out": "T_LIQ",
  "W_comp_kW": "KW_COMP"
}
```

---

## Pestañas de la app

| Pestaña | Contenido |
|---------|-----------|
| 📡 Monitor | Introducción de datos, cálculo en tiempo real, gauges, diagnóstico y diagrama P-h |
| 🔬 Análisis | Tabla detallada de entalpías, temperaturas de saturación y comparativa de COP |
| 📈 Histórico | Evolución temporal de COP, SEI y potencia. Exportación a CSV |
| 📋 Informe | Informe completo para el técnico frigorista, descargable en Markdown |
| 📚 Ayuda | Valores de referencia, umbrales de diagnóstico y ejemplos |

---

## Diagnóstico automático de fallos

| Parámetro | OK | Aviso | Fallo | Crítico |
|---|---|---|---|---|
| Superheat | 5–20 K | 3–5 / 20–25 K | >25 K | <3 K |
| Subcooling | 3–12 K | 2–3 / 12–15 K | <2 K | — |
| Relación de compresión | <4.5 | 4.5–6.0 | >6.0 | — |
| SEI Frío | >50% | 35–50% | <35% | — |
| Eficiencia isentrópica | >70% | 60–70% | <60% | — |
| Tª descarga compresor | <100 °C | 100–120 °C | — | >120 °C |
| COP vs nominal | <15% degradación | 15–30% | >30% | — |

---

## Dependencias

```
streamlit>=1.32.0
pandas>=2.0.0
numpy>=1.24.0
plotly>=5.18.0
requests>=2.31.0
```

`json`, `datetime`, `dataclasses` y `warnings` vienen incluidos en Python estándar, no necesitan instalación separada.
