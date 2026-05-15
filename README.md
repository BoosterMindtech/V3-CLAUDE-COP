# HVACR Performance Analyser 🏭❄️🔥

Aplicación Streamlit para el análisis termodinámico en tiempo real de **chillers y bombas de calor comerciales**, con detección automática de fallos y alertas para frigoristas.

## Características principales

- ✅ Cálculo de **COP real y nominal** con comparativa
- ✅ **SEI (System Efficiency Index)** – % respecto al ciclo de Carnot ideal
- ✅ Detección automática de **superheat, subcooling, relación de compresión, eficiencia isentrópica**
- ✅ **Diagnóstico de fallos** con mensajes claros para el frigorista
- ✅ **Estimación de coste energético extra** por degradación
- ✅ **Diagrama P-h** del ciclo en tiempo real
- ✅ Histórico de mediciones y exportación CSV
- ✅ Informe descargable en formato Markdown
- ✅ Integración API con **ClimaCheck Online** (PAID + credenciales)
- ✅ Integración con **cualquier BMS/SCADA** vía REST API genérica
- ✅ Refrigerantes soportados: R134a, R410A, R32, R407C, R22

## Instalación

```bash
pip install -r requirements.txt
streamlit run hvacr_cop_app.py
```

## Datos de entrada mínimos

| Sensor | Descripción |
|--------|-------------|
| P_evap | Presión absoluta baja presión (bar) |
| P_cond | Presión absoluta alta presión (bar) |
| T_suction | Temperatura aspiración compresor (°C) |
| T_discharge | Temperatura descarga compresor (°C) |
| T_liquid_line | Temperatura salida condensador (°C) |
| W_comp | Potencia eléctrica compresor (kW) |

## Integración API ClimaCheck Online

Configurar en la barra lateral:
- URL base: `https://online.climacheck.com`
- PAID: ID de proyecto asignado por ClimaCheck
- Usuario/contraseña: credenciales API de ClimaCheck

## Integración BMS/SCADA genérica

Configurar el mapeo JSON de campos:
```json
{
  "P_evap_bar": "nombre_sensor_LP_en_tu_BMS",
  "P_cond_bar": "nombre_sensor_HP_en_tu_BMS",
  "T_comp_suction": "nombre_sensor_T_asp",
  "W_comp_kW": "nombre_sensor_potencia"
}
```

## Metodología

Basada en el **método interno IEA HPT Annex 52** (mismo que usa ClimaCheck):
- Las presiones medidas dan las temperaturas de saturación
- Las temperaturas medidas dan las entalpías en cada punto del ciclo
- Del balance energético se obtienen las capacidades y el COP
- El SEI compara con el rendimiento de Carnot para el mismo lift de temperatura

## Umbrales de diagnóstico

| Estado | Condición |
|--------|-----------|
| 🟢 OK | SEI >50%, COP >85% nominal, 5K<SH<20K, 3K<SC<12K |
| 🟡 Aviso | SEI 35-50%, SH 3-5K o >20K, SC <3K, PR >4.5 |
| 🔴 Fallo | SEI <35%, COP <70% nominal, PR >6, ηis <60% |
| 🆘 Crítico | SH <3K (golpe líquido), T_desc >120°C |

## Referencias

- ASHRAE Fundamentals Handbook 2001
- IEA HPT Annex 52 – ClimaCheck Internal Method
- NREL/TP-5500-75461 – AFDD for RTUs (Wheeler et al. 2020)
- ClimaCheck Online API Documentation
