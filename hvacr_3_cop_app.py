"""
HVACR Performance Analyser - Streamlit App
Metodologia ClimaCheck / IEA HPT Annex 52
v1.1 - Corregido: defaults coherentes, Tsat en tiempo real, calculo verificado
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import requests
import json
from datetime import datetime
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
import warnings
warnings.filterwarnings("ignore")

REFRIGERANT_DATA = {
    "R134a": {
        "name": "R134a (HFC-134a)",
        "sat_table": {
            -40:[0.517,148.1,374.0],-35:[0.661,155.4,377.4],-30:[0.844,162.7,380.7],
            -25:[1.064,170.1,384.0],-20:[1.327,177.6,387.2],-15:[1.640,185.2,390.4],
            -10:[2.007,192.8,393.4], -5:[2.437,200.6,396.4],  0:[2.931,208.5,399.2],
              5:[3.497,216.5,402.0], 10:[4.144,224.7,404.7], 15:[4.876,233.0,407.3],
             20:[5.700,241.5,409.8], 25:[6.623,250.1,412.1], 30:[7.652,258.9,414.3],
             35:[8.795,267.9,416.4], 40:[10.063,277.1,418.3],45:[11.461,286.5,420.0],
             50:[13.000,296.1,421.5],55:[14.688,306.0,422.8],60:[16.533,316.2,423.9],
        },
        "cp_vapor":0.92,"cp_liquid":1.46,"GWP":1430,
        "default_P_evap":5.0,"default_P_cond":10.0,
    },
    "R410A": {
        "name": "R410A (HFC blend)",
        "sat_table": {
            -40:[1.752,167.0,430.5],-35:[2.177,175.6,434.2],-30:[2.692,184.4,437.9],
            -25:[3.302,193.3,441.4],-20:[4.021,202.4,444.8],-15:[4.858,211.7,448.1],
            -10:[5.823,221.2,451.2], -5:[6.927,230.8,454.1],  0:[8.180,240.7,456.8],
              5:[9.593,250.8,459.3], 10:[11.178,261.1,461.6],15:[12.948,271.7,463.6],
             20:[14.913,282.6,465.3],25:[17.087,293.7,466.7],30:[19.482,305.1,467.8],
             35:[22.110,316.8,468.4],40:[24.988,328.9,468.6],45:[28.124,341.4,468.3],
             50:[31.539,354.3,467.4],
        },
        "cp_vapor":0.98,"cp_liquid":1.55,"GWP":2088,
        "default_P_evap":8.0,"default_P_cond":19.5,
    },
    "R32": {
        "name": "R32 (HFC-32)",
        "sat_table": {
            -40:[2.047,134.9,489.6],-30:[3.137,150.3,494.7],-20:[4.618,166.1,499.4],
            -10:[6.562,182.4,503.5],  0:[9.047,199.2,507.1],  5:[10.562,207.9,508.6],
             10:[12.263,216.7,509.8],15:[14.169,225.8,510.8], 20:[16.293,235.1,511.5],
             25:[18.649,244.6,511.8],30:[21.254,254.4,511.8], 35:[24.124,264.5,511.4],
             40:[27.276,275.0,510.5],45:[30.724,285.8,509.1], 50:[34.491,297.1,507.2],
        },
        "cp_vapor":0.87,"cp_liquid":1.71,"GWP":675,
        "default_P_evap":10.0,"default_P_cond":21.0,
    },
    "R407C": {
        "name": "R407C (HFC blend)",
        "sat_table": {
            -40:[1.024,155.1,420.2],-30:[1.635,168.8,426.6],-20:[2.469,182.9,432.7],
            -10:[3.582,197.3,438.4],  0:[5.036,212.0,443.7],  5:[5.891,219.5,446.2],
             10:[6.849,227.1,448.5], 15:[7.922,234.9,450.7], 20:[9.117,242.8,452.7],
             25:[10.445,250.9,454.5],30:[11.913,259.2,456.1],35:[13.530,267.7,457.5],
             40:[15.307,276.4,458.7],45:[17.254,285.3,459.7],50:[19.380,294.5,460.4],
        },
        "cp_vapor":0.90,"cp_liquid":1.52,"GWP":1774,
        "default_P_evap":5.0,"default_P_cond":11.9,
    },
    "R22": {
        "name": "R22 (HCFC-22, legacy)",
        "sat_table": {
            -40:[1.004,166.8,396.6],-30:[1.644,177.5,402.3],-20:[2.454,188.4,407.8],
            -10:[3.543,199.6,412.9],  0:[4.975,210.9,417.7],  5:[5.826,216.7,420.0],
             10:[6.768,222.6,422.2], 15:[7.811,228.6,424.3], 20:[8.963,234.7,426.3],
             25:[10.236,240.9,428.2],30:[11.635,247.3,430.0],35:[13.172,253.8,431.7],
             40:[14.854,260.5,433.2],45:[16.691,267.3,434.6],50:[18.688,274.3,435.8],
             55:[20.855,281.5,436.9],60:[23.200,288.9,437.7],
        },
        "cp_vapor":0.82,"cp_liquid":1.26,"GWP":1810,
        "default_P_evap":4.97,"default_P_cond":11.6,
    },
}

def T_sat_from_P(ref,P):
    t=sorted(ref["sat_table"].keys()); Ps=[ref["sat_table"][x][0] for x in t]
    if P<=Ps[0]: return float(t[0])
    if P>=Ps[-1]: return float(t[-1])
    for i in range(len(Ps)-1):
        if Ps[i]<=P<=Ps[i+1]:
            return t[i]+(t[i+1]-t[i])*(P-Ps[i])/(Ps[i+1]-Ps[i])

def interp_h(ref,P,idx):
    t=sorted(ref["sat_table"].keys()); Ps=[ref["sat_table"][x][0] for x in t]
    if P<=Ps[0]: return ref["sat_table"][t[0]][idx]
    if P>=Ps[-1]: return ref["sat_table"][t[-1]][idx]
    for i in range(len(Ps)-1):
        if Ps[i]<=P<=Ps[i+1]:
            v1,v2=ref["sat_table"][t[i]][idx],ref["sat_table"][t[i+1]][idx]
            return v1+(v2-v1)*(P-Ps[i])/(Ps[i+1]-Ps[i])

@dataclass
class Inp:
    refrigerant:str="R134a"; P_evap_bar:float=5.0; P_cond_bar:float=10.0
    T_comp_suction:float=23.0; T_comp_discharge:float=66.0; T_cond_out:float=36.0
    T_evap_in:float=-2.0; W_comp_kW:float=40.0
    T_sec_evap_in:float=12.0; T_sec_evap_out:float=7.0
    T_sec_cond_in:float=28.0; T_sec_cond_out:float=35.0
    flow_evap_ls:float=0.0; flow_cond_ls:float=0.0
    machine_type:str="Chiller"; nominal_capacity_kW:float=200.0; nominal_COP:float=5.0

@dataclass
class Res:
    T_evap_sat:float=0.0; T_cond_sat:float=0.0; superheat_K:float=0.0
    subcooling_K:float=0.0; pressure_ratio:float=0.0
    h1:float=0.0; h2:float=0.0; h3:float=0.0; h4:float=0.0
    Q_evap_kW:float=0.0; Q_cond_kW:float=0.0
    COP_cool:float=0.0; COP_heat:float=0.0
    SEI_cool:float=0.0; SEI_heat:float=0.0
    comp_efficiency_isentropic:float=0.0
    faults:List[str]=field(default_factory=list)
    warnings:List[str]=field(default_factory=list)
    fault_level:str="OK"

def calculate(inp:Inp)->Res:
    r=Res(); ref=REFRIGERANT_DATA[inp.refrigerant]
    r.T_evap_sat=T_sat_from_P(ref,inp.P_evap_bar)
    r.T_cond_sat=T_sat_from_P(ref,inp.P_cond_bar)
    r.pressure_ratio=inp.P_cond_bar/inp.P_evap_bar
    r.superheat_K =inp.T_comp_suction  - r.T_evap_sat
    r.subcooling_K=r.T_cond_sat        - inp.T_cond_out
    hve=interp_h(ref,inp.P_evap_bar,2)
    hvc=interp_h(ref,inp.P_cond_bar,2)
    hlc=interp_h(ref,inp.P_cond_bar,1)
    cv=ref["cp_vapor"]; cl=ref["cp_liquid"]
    r.h1=hve+cv*max(r.superheat_K,0)
    r.h3=hlc-cl*max(r.subcooling_K,0)
    r.h4=r.h3
    r.h2=hvc+cv*(inp.T_comp_discharge-r.T_cond_sat)
    dh=r.h2-r.h1; m=inp.W_comp_kW/dh if dh>0 else 0
    r.Q_evap_kW=m*(r.h1-r.h4); r.Q_cond_kW=m*(r.h2-r.h3)
    if inp.W_comp_kW>0:
        r.COP_cool=r.Q_evap_kW/inp.W_comp_kW
        r.COP_heat=r.Q_cond_kW/inp.W_comp_kW
    Tek=r.T_evap_sat+273.15; Tck=r.T_cond_sat+273.15
    if Tck>Tek:
        cc=Tek/(Tck-Tek); ch=Tck/(Tck-Tek)
        if cc>0: r.SEI_cool=min(r.COP_cool/cc*100,100); r.SEI_heat=min(r.COP_heat/ch*100,100)
    k=1.15; T1K=inp.T_comp_suction+273.15
    h2s=r.h1+cv*T1K*(r.pressure_ratio**((k-1)/k)-1)
    if (r.h2-r.h1)>0: r.comp_efficiency_isentropic=min(max((h2s-r.h1)/(r.h2-r.h1),0.3),0.95)
    _faults(inp,r); return r

def _faults(inp:Inp,r:Res):
    fs=[]; ws=[]; lv="OK"
    def up(l):
        nonlocal lv
        p={"OK":0,"WARNING":1,"FAULT":2,"CRITICAL":3}
        if p.get(l,0)>p.get(lv,0): lv=l
    if r.superheat_K<3:
        fs.append(f"🔴 CRITICO: Superheat {r.superheat_K:.1f} K (<3 K). Golpe de liquido — PARAR EQUIPO."); up("CRITICAL")
    elif r.superheat_K<5:
        ws.append(f"🟡 Superheat bajo ({r.superheat_K:.1f} K). Revisar valvula expansion."); up("WARNING")
    elif r.superheat_K>25:
        ws.append(f"🟡 Superheat alto ({r.superheat_K:.1f} K). Posible fuga de refrigerante."); up("WARNING")
    if r.subcooling_K<2:
        ws.append(f"🟡 Subcooling {r.subcooling_K:.1f} K (<2 K). Flash gas en linea liquido."); up("WARNING")
    elif r.subcooling_K>15:
        ws.append(f"🟡 Subcooling excesivo ({r.subcooling_K:.1f} K)."); up("WARNING")
    if r.pressure_ratio>6:
        fs.append(f"🔴 FALLO: Relacion compresion {r.pressure_ratio:.1f} >6. Condensador bloqueado."); up("FAULT")
    elif r.pressure_ratio>4.5:
        ws.append(f"🟡 Relacion compresion {r.pressure_ratio:.1f} >4.5. Revisar condensador."); up("WARNING")
    if inp.T_comp_discharge>120:
        fs.append(f"🔴 CRITICO: Ta descarga {inp.T_comp_discharge:.0f} °C >120 °C. PARAR EQUIPO."); up("CRITICAL")
    elif inp.T_comp_discharge>100:
        ws.append(f"🟡 Ta descarga alta ({inp.T_comp_discharge:.0f} °C)."); up("WARNING")
    if r.comp_efficiency_isentropic<0.55:
        fs.append(f"🔴 FALLO: Efic. isentropica {r.comp_efficiency_isentropic:.0%} <55%. Compresor danado."); up("FAULT")
    elif r.comp_efficiency_isentropic<0.65:
        ws.append(f"🟡 Efic. isentropica {r.comp_efficiency_isentropic:.0%} baja."); up("WARNING")
    if r.SEI_cool<35:
        fs.append(f"🔴 FALLO: SEI {r.SEI_cool:.1f}% <35%. Consumo energetico excesivo."); up("FAULT")
    elif r.SEI_cool<50:
        ws.append(f"🟡 SEI {r.SEI_cool:.1f}% bajo. Sistema fuera de rendimiento optimo."); up("WARNING")
    if inp.nominal_COP>0 and r.COP_cool>0:
        deg=(inp.nominal_COP-r.COP_cool)/inp.nominal_COP*100
        if deg>30:
            fs.append(f"🔴 FALLO: COP {r.COP_cool:.2f} es {deg:.0f}% inferior al nominal ({inp.nominal_COP:.2f})."); up("FAULT")
        elif deg>15:
            ws.append(f"🟡 COP {r.COP_cool:.2f} es {deg:.0f}% inferior al nominal."); up("WARNING")
    if inp.nominal_COP>0 and r.Q_evap_kW>0:
        exc=inp.W_comp_kW-r.Q_evap_kW/inp.nominal_COP
        if exc>5:
            ws.append(f"💶 Perdida: {exc:.1f} kW extra → ~{exc*4000/1000:.0f} MWh/año → ~€{exc*4000/1000*0.12:.0f}/año.")
    r.faults=fs; r.warnings=ws; r.fault_level=lv

def gauge(v,mn,mx,title,good,warn,unit=""):
    fig=go.Figure(go.Indicator(mode="gauge+number",value=v,
        title={"text":title,"font":{"size":13}},
        number={"suffix":unit,"font":{"size":20}},
        gauge={"axis":{"range":[mn,mx]},"bar":{"color":"#1f77b4","thickness":0.25},
               "steps":[{"range":[mn,warn[0]],"color":"#d62728"},
                        {"range":[warn[0],good[0]],"color":"#ff7f0e"},
                        {"range":[good[0],good[1]],"color":"#2ca02c"},
                        {"range":[good[1],warn[1]],"color":"#ff7f0e"},
                        {"range":[warn[1],mx],"color":"#d62728"}]}))
    fig.update_layout(height=200,margin=dict(t=40,b=10,l=20,r=20)); return fig

def ph_diag(r:Res,inp:Inp):
    ref=REFRIGERANT_DATA[inp.refrigerant]; t=sorted(ref["sat_table"].keys())
    Ps=[ref["sat_table"][x][0] for x in t]
    hl=[ref["sat_table"][x][1] for x in t]; hv=[ref["sat_table"][x][2] for x in t]
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=hl+hv[::-1],y=Ps+Ps[::-1],mode="lines",
        line=dict(color="#aaa",width=1.5,dash="dot"),name="Campana sat."))
    fig.add_trace(go.Scatter(
        x=[r.h1,r.h2,r.h3,r.h4,r.h1],
        y=[inp.P_evap_bar,inp.P_cond_bar,inp.P_cond_bar,inp.P_evap_bar,inp.P_evap_bar],
        mode="lines+markers+text",text=["1-Asp","2-Desc","3-Cond","4-Evap",""],
        textposition="top center",line=dict(color="#1f77b4",width=2),
        marker=dict(size=8),name="Ciclo real"))
    fig.update_layout(title="Diagrama P-h",xaxis_title="Entalpia (kJ/kg)",
        yaxis_title="Presion (bar abs)",yaxis_type="log",
        height=360,margin=dict(t=50,b=40,l=60,r=20))
    return fig

def main():
    st.set_page_config(page_title="HVACR Performance Analyser",page_icon="❄️",layout="wide")
    for k,v in [("history",[]),("last_res",None),("last_inp",None)]:
        if k not in st.session_state: st.session_state[k]=v

    st.title("❄️🔥 HVACR Performance Analyser")
    st.caption("Analisis termodinamico en tiempo real · Deteccion de fallos · Optimizacion energetica · v1.1")
    st.divider()

    with st.sidebar:
        st.header("⚙️ Configuracion")
        input_mode=st.radio("Modo entrada",["Manual","API ClimaCheck","API Generica (BMS/SCADA)"])
        st.divider()
        st.subheader("🏭 Maquina")
        mtype   =st.selectbox("Tipo equipo",["Chiller agua","Bomba de calor","Enfriadora aire"])
        refrig  =st.selectbox("Refrigerante",list(REFRIGERANT_DATA.keys()),
                              format_func=lambda x:REFRIGERANT_DATA[x]["name"])
        nom_cap =st.number_input("Capacidad nominal (kW)",10.0,5000.0,200.0,10.0)
        nom_cop =st.number_input("COP nominal diseno",1.0,12.0,5.0,0.1)
        ref=REFRIGERANT_DATA[refrig]
        Pe_def=ref["default_P_evap"]; Pc_def=ref["default_P_cond"]
        Tse=T_sat_from_P(ref,Pe_def); Tsc=T_sat_from_P(ref,Pc_def)
        st.info(f"**{refrig}** — Presiones por defecto:\n\n"
                f"Evap {Pe_def} bar → Tsat **{Tse:.1f} °C** → T_asp min: **{Tse+3:.1f} °C**\n\n"
                f"Cond {Pc_def} bar → Tsat **{Tsc:.1f} °C**")
        if input_mode=="API ClimaCheck":
            st.divider(); st.subheader("🔌 ClimaCheck Online")
            cc_url=st.text_input("URL","https://online.climacheck.com")
            cc_paid=st.text_input("PAID"); cc_user=st.text_input("Usuario")
            cc_pass=st.text_input("Contrasena",type="password")
        elif input_mode=="API Generica (BMS/SCADA)":
            st.divider(); st.subheader("🔌 API REST")
            gen_url=st.text_input("URL endpoint")
            api_key=st.text_input("API Key",type="password")
            fmap=st.text_area("Mapeo JSON",'{"P_evap_bar":"LP","P_cond_bar":"HP"}',height=80)
        st.caption("v1.1 · IEA HPT Annex 52 · ClimaCheck")

    tab1,tab2,tab3,tab4,tab5=st.tabs(["📡 Monitor","🔬 Analisis","📈 Historico","📋 Informe","📚 Ayuda"])

    with tab1:
        ref=REFRIGERANT_DATA[refrig]
        Pe_def=ref["default_P_evap"]; Pc_def=ref["default_P_cond"]

        inp=Inp(refrigerant=refrig,machine_type=mtype,
                nominal_capacity_kW=nom_cap,nominal_COP=nom_cop,
                P_evap_bar=Pe_def,P_cond_bar=Pc_def)

        if input_mode=="Manual":
            st.subheader("📥 Introduccion manual de datos de sensores")
            # Key suffix changes with refrigerant -> Streamlit resets all widgets on refrigerant change
            rk=refrig.replace(" ","_").replace("(","").replace(")","")
            c1,c2,c3=st.columns(3)

            with c1:
                st.markdown("**🔵 Evaporador — baja presion**")
                Pe=st.number_input("Presion evaporacion (bar abs)",0.5,60.0,Pe_def,0.1,key=f"Pe_{rk}")
                Tse=T_sat_from_P(ref,Pe)
                st.caption(f"Tsat evap = **{Tse:.1f} °C** → T_asp normal: **{Tse+5:.1f}–{Tse+12:.1f} °C**")
                T_asp_sug=round(Tse+7,1)
                Tasp=st.number_input("Ta aspiracion compresor (°C)",-50.0,80.0,T_asp_sug,0.5,key=f"Tasp_{rk}")
                SH=Tasp-Tse
                if SH<3: st.error(f"🔴 Superheat = {SH:.1f} K — CRITICO: riesgo de golpe de liquido")
                elif SH<5: st.warning(f"🟡 Superheat = {SH:.1f} K — bajo")
                elif SH>25: st.warning(f"🟡 Superheat = {SH:.1f} K — alto, posible fuga")
                else: st.success(f"✅ Superheat = {SH:.1f} K — normal")
                Tei_sug=round(Tse-4,1)
                Tevap_in=st.number_input("Ta entrada evaporador (°C)",-50.0,40.0,Tei_sug,0.5,key=f"Tei_{rk}")
                Taw_in =st.number_input("Ta agua fria retorno (°C)",-20.0,40.0,12.0,0.5,key=f"Tawi_{rk}")
                Taw_out=st.number_input("Ta agua fria impulsion (°C)",-20.0,35.0,7.0,0.5,key=f"Tawo_{rk}")
                Qe_ls  =st.number_input("Caudal evaporador l/s [0=no medido]",0.0,500.0,0.0,1.0,key=f"Qe_{rk}")

            with c2:
                st.markdown("**🔴 Condensador — alta presion**")
                Pc=st.number_input("Presion condensacion (bar abs)",0.5,80.0,Pc_def,0.1,key=f"Pc_{rk}")
                Tsc=T_sat_from_P(ref,Pc)
                st.caption(f"Tsat cond = **{Tsc:.1f} °C** → T_liq normal: **{Tsc-8:.1f}–{Tsc-2:.1f} °C**")
                PR=Pc/Pe
                if PR>6: st.error(f"🔴 Relacion compresion = {PR:.2f} — FALLO")
                elif PR>4.5: st.warning(f"🟡 Relacion compresion = {PR:.2f} — alta")
                else: st.success(f"✅ Relacion compresion = {PR:.2f} — OK")
                Tdesc_sug=round(Tsc+26,1)
                Tdesc=st.number_input("Ta descarga compresor (°C)",-50.0,160.0,Tdesc_sug,0.5,key=f"Tdes_{rk}")
                Tliq_sug=round(Tsc-4,1)
                Tliq=st.number_input("Ta salida condensador / linea liquido (°C)",-50.0,110.0,Tliq_sug,0.5,key=f"Tliq_{rk}")
                SC=Tsc-Tliq
                if SC<2: st.warning(f"🟡 Subcooling = {SC:.1f} K — bajo, flash gas posible")
                else: st.success(f"✅ Subcooling = {SC:.1f} K — OK")
                Tacw_in =st.number_input("Ta agua condensacion entrada (°C)",-20.0,70.0,28.0,0.5,key=f"Tacwi_{rk}")
                Tacw_out=st.number_input("Ta agua condensacion salida (°C)",-20.0,80.0,35.0,0.5,key=f"Tacwo_{rk}")
                Qc_ls   =st.number_input("Caudal condensador l/s [0=no medido]",0.0,500.0,0.0,1.0,key=f"Qc_{rk}")

            with c3:
                st.markdown("**⚡ Compresor y sistema**")
                W_sug=round(nom_cap/nom_cop,0)
                st.caption(f"Para COP={nom_cop} y cap={nom_cap} kW la potencia tipica es **{W_sug:.0f} kW**")
                Wcomp=st.number_input("Potencia electrica compresor (kW)",1.0,2000.0,W_sug,1.0,key="Wc")
                st.markdown("---")
                ts=st.text_input("Etiqueta",datetime.now().strftime("%Y-%m-%d %H:%M"))
                btn=st.button("🚀 Calcular COP y Diagnostico",type="primary",use_container_width=True)

            inp.P_evap_bar=Pe; inp.P_cond_bar=Pc
            inp.T_comp_suction=Tasp; inp.T_comp_discharge=Tdesc
            inp.T_cond_out=Tliq; inp.T_evap_in=Tevap_in; inp.W_comp_kW=Wcomp
            inp.T_sec_evap_in=Taw_in; inp.T_sec_evap_out=Taw_out
            inp.T_sec_cond_in=Tacw_in; inp.T_sec_cond_out=Tacw_out
            inp.flow_evap_ls=Qe_ls; inp.flow_cond_ls=Qc_ls
            do_calc=btn

        elif input_mode=="API ClimaCheck":
            do_calc=st.button("🔄 Obtener datos ClimaCheck y calcular",type="primary")
            if do_calc:
                try:
                    r=requests.get(f"{cc_url}/api/lastminute",params={"paid":cc_paid},
                                   auth=(cc_user,cc_pass),timeout=10)
                    if r.status_code==200:
                        d=r.json()
                        Tse_=T_sat_from_P(ref,float(d.get("P_evap",Pe_def)))
                        inp.P_evap_bar=float(d.get("P_evap",Pe_def))
                        inp.P_cond_bar=float(d.get("P_cond",Pc_def))
                        inp.T_comp_suction=float(d.get("T_suction",Tse_+7))
                        inp.T_comp_discharge=float(d.get("T_discharge",66))
                        inp.T_cond_out=float(d.get("T_liquid_line",36))
                        inp.W_comp_kW=float(d.get("W_comp",nom_cap/nom_cop))
                        inp.T_sec_evap_in=float(d.get("T_chw_return",12))
                        inp.T_sec_evap_out=float(d.get("T_chw_supply",7))
                        inp.T_sec_cond_in=float(d.get("T_cw_supply",28))
                        inp.T_sec_cond_out=float(d.get("T_cw_return",35))
                        st.success("✅ Datos recibidos")
                    else: st.error(f"Error {r.status_code}"); do_calc=False
                except Exception as e: st.error(str(e)); do_calc=False
        else:
            do_calc=st.button("🔄 Obtener datos BMS/SCADA y calcular",type="primary")
            if do_calc:
                try:
                    mapping=json.loads(fmap)
                    hdr={"Authorization":f"Bearer {api_key}"} if api_key else {}
                    r=requests.get(gen_url,headers=hdr,timeout=15)
                    if r.status_code==200:
                        d=r.json()
                        for f,k in mapping.items():
                            if k in d and hasattr(inp,f): setattr(inp,f,float(d[k]))
                        st.success("✅ Datos recibidos")
                    else: st.error(f"Error {r.status_code}"); do_calc=False
                except Exception as e: st.error(str(e)); do_calc=False

        if do_calc:
            res=calculate(inp)
            st.session_state.last_res=res; st.session_state.last_inp=inp
            st.session_state.history.append({
                "timestamp":datetime.now(),"COP_cool":res.COP_cool,"COP_heat":res.COP_heat,
                "SEI_cool":res.SEI_cool,"W_comp":inp.W_comp_kW,"Q_evap":res.Q_evap_kW,
                "superheat":res.superheat_K,"subcooling":res.subcooling_K,
                "pressure_ratio":res.pressure_ratio,"fault_level":res.fault_level,
            })
            if len(st.session_state.history)>500: st.session_state.history=st.session_state.history[-500:]

        if st.session_state.last_res is not None:
            res=st.session_state.last_res; inp=st.session_state.last_inp
            if res.fault_level=="OK":
                st.success("🟢 **SISTEMA OK** — Funcionamiento dentro de parametros normales.")
            elif res.fault_level=="WARNING":
                st.warning("🟡 **ATENCION** — Condiciones que requieren supervision.")
            elif res.fault_level=="FAULT":
                st.error("🔴 **FALLO DETECTADO** — Contactar al frigorista urgentemente.")
            else:
                st.error("🆘 **CRITICO — ACCION INMEDIATA** — Parar equipo y llamar al servicio tecnico AHORA.")

            st.markdown("### 📊 Indicadores clave")
            k1,k2,k3,k4,k5,k6=st.columns(6)
            k1.metric("COP Frio",f"{res.COP_cool:.2f}",f"{res.COP_cool-inp.nominal_COP:+.2f} vs nominal")
            k2.metric("COP Calor",f"{res.COP_heat:.2f}")
            k3.metric("SEI Frio",f"{res.SEI_cool:.1f}%")
            k4.metric("Q Frio",f"{res.Q_evap_kW:.1f} kW",f"{res.Q_evap_kW-inp.nominal_capacity_kW:+.0f} vs nominal")
            k5.metric("Q Calor",f"{res.Q_cond_kW:.1f} kW")
            k6.metric("Potencia",f"{inp.W_comp_kW:.1f} kW")

            st.markdown("### 🎯 Estado de parametros clave")
            g1,g2,g3,g4=st.columns(4)
            nom=inp.nominal_COP
            with g1: st.plotly_chart(gauge(res.COP_cool,0,nom*1.3,"COP Frio",(nom*0.85,nom*1.1),(nom*0.70,nom*1.15)),use_container_width=True)
            with g2: st.plotly_chart(gauge(res.SEI_cool,0,100,"SEI Frio (%)",(50,85),(35,90),"%"),use_container_width=True)
            with g3: st.plotly_chart(gauge(res.superheat_K,-5,40,"Superheat (K)",(5,20),(3,25),"K"),use_container_width=True)
            with g4: st.plotly_chart(gauge(res.subcooling_K,-2,20,"Subcooling (K)",(3,12),(2,15),"K"),use_container_width=True)

            if res.faults or res.warnings:
                st.markdown("### 🚨 Diagnostico")
                for f in res.faults: st.error(f)
                for w in res.warnings: st.warning(w)
                st.info("📞 Notificar al frigorista con este diagnostico y los valores medidos.")
            else:
                st.success("✅ No se detectan fallos. Sistema en buen estado.")

            st.markdown("### 📉 Diagrama P-h")
            st.plotly_chart(ph_diag(res,inp),use_container_width=True)

    with tab2:
        if st.session_state.last_res is None:
            st.info("Realiza un calculo en Monitor.")
        else:
            res=st.session_state.last_res; inp=st.session_state.last_inp
            ca,cb=st.columns(2)
            with ca:
                st.markdown("#### Temperaturas de saturacion")
                st.dataframe(pd.DataFrame({
                    "Parametro":["Tsat evaporacion","Tsat condensacion","Superheat","Subcooling","Relacion compresion"],
                    "Valor":[f"{res.T_evap_sat:.1f} °C",f"{res.T_cond_sat:.1f} °C",
                             f"{res.superheat_K:.1f} K",f"{res.subcooling_K:.1f} K",
                             f"{res.pressure_ratio:.2f}"],
                    "Estado":["✅","✅",
                              "✅" if 5<=res.superheat_K<=20 else ("⚠️" if 3<=res.superheat_K<=25 else "🔴"),
                              "✅" if 3<=res.subcooling_K<=12 else "⚠️",
                              "✅" if res.pressure_ratio<4.5 else ("⚠️" if res.pressure_ratio<6 else "🔴")],
                }),hide_index=True,use_container_width=True)
                st.markdown("#### Entalpias del ciclo (kJ/kg)")
                st.dataframe(pd.DataFrame({
                    "Punto":["1 Aspiracion","2 Descarga","3 Sal.Cond.","4 Ent.Evap."],
                    "h (kJ/kg)":[f"{res.h1:.1f}",f"{res.h2:.1f}",f"{res.h3:.1f}",f"{res.h4:.1f}"],
                    "Estado":["Vapor sobrecalentado","Vapor descarga alta P","Liquido subenfriado","Mezcla bifasica"],
                }),hide_index=True,use_container_width=True)
            with cb:
                Tek=res.T_evap_sat+273.15; Tck=res.T_cond_sat+273.15
                cc=Tek/(Tck-Tek) if Tck>Tek else 0
                ch=Tck/(Tck-Tek) if Tck>Tek else 0
                deg=(inp.nominal_COP-res.COP_cool)/inp.nominal_COP*100 if inp.nominal_COP>0 else 0
                st.markdown("#### Rendimiento")
                st.dataframe(pd.DataFrame({
                    "Indice":["COP Frio actual","COP Calor actual","COP Carnot frio","COP Carnot calor",
                              "SEI Frio","SEI Calor","COP Nominal","Degradacion","Efic. isentropica"],
                    "Valor":[f"{res.COP_cool:.2f}",f"{res.COP_heat:.2f}",f"{cc:.2f}",f"{ch:.2f}",
                             f"{res.SEI_cool:.1f}%",f"{res.SEI_heat:.1f}%",f"{inp.nominal_COP:.2f}",
                             f"{deg:.1f}%",f"{res.comp_efficiency_isentropic:.1%}"],
                }),hide_index=True,use_container_width=True)
                fig=go.Figure(go.Bar(
                    x=["COP Frio\nActual","COP Frio\nNominal","COP Carnot\nFrio","COP Calor\nActual","COP Carnot\nCalor"],
                    y=[res.COP_cool,inp.nominal_COP,cc,res.COP_heat,ch],
                    marker_color=["#1f77b4","#aec7e8","#98df8a","#d62728","#ff9896"],
                    text=[f"{v:.2f}" for v in [res.COP_cool,inp.nominal_COP,cc,res.COP_heat,ch]],
                    textposition="outside"))
                fig.update_layout(height=300,title="Comparativa COP",margin=dict(t=50,b=20))
                st.plotly_chart(fig,use_container_width=True)

    with tab3:
        st.markdown("### 📈 Historico")
        if not st.session_state.history:
            st.info("Realiza varios calculos para ver la evolucion.")
        else:
            df=pd.DataFrame(st.session_state.history)
            col1,col2=st.columns([3,1])
            with col2:
                if st.button("🗑️ Limpiar"): st.session_state.history=[]; st.rerun()
                st.download_button("⬇️ CSV",df.to_csv(index=False).encode(),"hvacr.csv","text/csv")
            with col1: st.markdown(f"**{len(df)} mediciones**")
            fig=make_subplots(rows=3,cols=1,shared_xaxes=True,
                subplot_titles=["COP Frio","SEI (%)","Potencia (kW)"])
            fig.add_trace(go.Scatter(x=df["timestamp"],y=df["COP_cool"],name="COP",line=dict(color="#2ca02c")),row=1,col=1)
            fig.add_trace(go.Scatter(x=df["timestamp"],y=df["SEI_cool"],name="SEI",line=dict(color="#1f77b4")),row=2,col=1)
            fig.add_trace(go.Scatter(x=df["timestamp"],y=df["W_comp"],name="kW",line=dict(color="#d62728")),row=3,col=1)
            fig.update_layout(height=480,margin=dict(t=60,b=20))
            st.plotly_chart(fig,use_container_width=True)
            st.dataframe(df.round(2),use_container_width=True)

    with tab4:
        st.markdown("### 📋 Informe para frigorista")
        if st.session_state.last_res is None:
            st.info("Realiza un calculo para generar el informe.")
        else:
            res=st.session_state.last_res; inp=st.session_state.last_inp
            now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            md=f"""# INFORME DIAGNOSTICO HVACR
**Fecha:** {now}  
**Equipo:** {inp.machine_type} | **Refrigerante:** {REFRIGERANT_DATA[inp.refrigerant]['name']}  
**Capacidad nominal:** {inp.nominal_capacity_kW:.0f} kW | **COP nominal:** {inp.nominal_COP:.2f}

---
## ESTADO: {res.fault_level}

{"### Fallos:"+chr(10)+"".join([f"- {f}{chr(10)}" for f in res.faults]) if res.faults else ""}
{"### Avisos:"+chr(10)+"".join([f"- {w}{chr(10)}" for w in res.warnings]) if res.warnings else ""}

---
## VALORES MEDIDOS
| Parametro | Valor |
|---|---|
| Presion evap | {inp.P_evap_bar:.2f} bar → Tsat {res.T_evap_sat:.1f} °C |
| Presion cond | {inp.P_cond_bar:.2f} bar → Tsat {res.T_cond_sat:.1f} °C |
| Ta aspiracion | {inp.T_comp_suction:.1f} °C (SH = {res.superheat_K:.1f} K) |
| Ta descarga | {inp.T_comp_discharge:.1f} °C |
| Ta liq. cond | {inp.T_cond_out:.1f} °C (SC = {res.subcooling_K:.1f} K) |
| Relacion compresion | {res.pressure_ratio:.2f} |
| Potencia compresor | {inp.W_comp_kW:.1f} kW |

## RENDIMIENTO CALCULADO
| Indice | Valor |
|---|---|
| COP Frio | {res.COP_cool:.2f} |
| COP Calor | {res.COP_heat:.2f} |
| SEI Frio | {res.SEI_cool:.1f}% |
| Q Frio | {res.Q_evap_kW:.1f} kW |
| Efic. isentropica | {res.comp_efficiency_isentropic:.1%} |

---
*HVACR Performance Analyser v1.1 · IEA HPT Annex 52*
"""
            st.markdown(md)
            st.download_button("⬇️ Descargar informe",md.encode(),"informe_hvacr.md","text/markdown",use_container_width=True)

    with tab5:
        st.markdown("""
### 📚 Ayuda — Como usar la app correctamente

#### Lo mas importante: la temperatura de aspiracion
Cada refrigerante a cada presion tiene una temperatura de saturacion fija.
Si la temperatura de aspiracion que introduces es igual o menor que esa Tsat,
el superheat es 0 o negativo y la app muestra **CRITICO** correctamente.

La app calcula y muestra la Tsat en tiempo real junto a cada campo de presion.
Siempre introduce T_aspiracion = Tsat_evap + superheat deseado (5–12 K es normal).

#### Valores tipicos para chiller R134a
| Condicion | P_evap | Tsat evap | T_asp (SH=7K) | P_cond | Tsat cond | T_desc |
|---|---|---|---|---|---|---|
| Invierno | 5.0 bar | 15.8°C | 22.8°C | 9.0 bar | 35.8°C | 62°C |
| Verano | 5.0 bar | 15.8°C | 22.8°C | 13.0 bar | 50.0°C | 76°C |
| Optimo | 5.0 bar | 15.8°C | 22.8°C | 10.0 bar | 39.8°C | 66°C |

#### Umbrales de diagnostico
| Parametro | OK | Aviso | Fallo | Critico |
|---|---|---|---|---|
| Superheat | 5–20 K | 3–5 / 20–25 K | >25 K | <3 K |
| Subcooling | 3–12 K | 2–3 / 12–15 K | <2 K | — |
| Relacion compresion | <4.5 | 4.5–6.0 | >6.0 | — |
| SEI Frio | >50% | 35–50% | <35% | — |
| Efic. isentropica | >70% | 60–70% | <60% | — |
| Ta descarga | <100°C | 100–120°C | — | >120°C |
| COP vs nominal | <15% degrad. | 15–30% | >30% | — |
""")

if __name__=="__main__":
    main()
