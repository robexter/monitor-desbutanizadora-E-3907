import streamlit as st
from collections import deque
import time

st.set_page_config(page_title="Monitor Desbutanizadora", layout="wide")

st.title("📊 Monitoramento - Torre Desbutanizadora E-3907")

# ========================
# INPUTS (OPERADOR)
# ========================
st.sidebar.header("🎛️ Entrada de Dados")

refluxo = st.sidebar.number_input("Vazão de Refluxo (m³/h)", value=8500.0)
carga = st.sidebar.number_input("Vazão de Carga (m³/h)", value=12800.0)
pressao = st.sidebar.number_input("Pressão da Torre (kg/cm²)", value=12.0)
nivel = st.sidebar.number_input("Nível da Torre (%)", value=60.0)
temp_base = st.sidebar.number_input("Temperatura de Base (°C)", value=160.0)
nivel_topo_alto = st.sidebar.checkbox("Topo com nível alto travado")

# ========================
# HISTÓRICO
# ========================
if "press_hist" not in st.session_state:
    st.session_state.press_hist = deque(maxlen=20)
if "nivel_hist" not in st.session_state:
    st.session_state.nivel_hist = deque(maxlen=20)
if "temp_hist" not in st.session_state:
    st.session_state.temp_hist = deque(maxlen=20)

# Será preenchido após a simulação dos efeitos
# st.session_state.press_hist.append(pressao)
# st.session_state.nivel_hist.append(nivel)
# st.session_state.temp_hist.append(temp_base)

# ========================
# FUNÇÕES
# ========================
def variacao(lista):
    if len(lista) < 2:
        return 0
    return max(lista) - min(lista)

def tendencia(lista):
    if len(lista) < 2:
        return "➡️"
    if lista[-1] > lista[-2]:
        return "⬆️"
    elif lista[-1] < lista[-2]:
        return "⬇️"
    else:
        return "➡️"

def cor_alerta(valor, limite):
    if valor > limite:
        return "🔴"
    else:
        return "🟢"

# ========================
# LÓGICA DE CASCATA - EFEITOS DA VAZÃO ALTA
# ========================
def simular_efeitos_vazao_alta(refluxo, carga, pressao, nivel, temp_base, nivel_topo_alto, contador):
    """
    Simula os efeitos em cascata quando há vazão alta:
    1. Refluxo elevado aumenta PRESSÃO DO TOPO rapidamente
    2. Aumenta a pressão total na torre
    3. Desloca o nível para cima
    4. TEMPERATURA DA BASE REDUZ com vazão alta (resfriamento)
    """
    vazao_alta = refluxo > 8834 or carga > 13617
    refluxo_alto = refluxo > 8834
    
    # Fator de intensidade baseado nas vazões (quanto mais acima, mais intenso)
    fator_refluxo = max(0, (refluxo - 8834) / 8834) if refluxo > 8834 else 0
    fator_carga = max(0, (carga - 13617) / 13617) if carga > 13617 else 0
    fator_intensidade = max(fator_refluxo, fator_carga)
    
    # Efeitos progressivos com o tempo/contador
    tempo_decorrido = min(contador, 10)  # Efeito máximo após algumas iterações
    
    if vazao_alta:
        # 1. Aumenta nível do tambor de topo (overflow)
        nivel_topo_alto = True
        
        # 2. EFEITO PRINCIPAL: Refluxo elevado aumenta PRESSÃO DO TOPO
        if refluxo_alto:
            # Pressão do topo aumenta dramaticamente com refluxo alto
            fator_pressao_topo = fator_refluxo * 3.5 * (tempo_decorrido / 10)
            pressao = pressao + fator_pressao_topo
        else:
            # Carga alta também aumenta pressão mas menos intensamente
            delta_pressao = fator_carga * 1.5 * (tempo_decorrido / 10)
            pressao = pressao + delta_pressao
        
        # 3. Aumenta nível da torre (acúmulo de líquido)
        delta_nivel = fator_intensidade * 8 * (tempo_decorrido / 10)
        nivel_anterior = nivel
        nivel = min(100, nivel + delta_nivel)
        
        # 4. TEMPERATURA DA BASE - Tendência de REDUÇÃO com vazão alta
        # Refluxo elevado causa resfriamento na base da torre
        # Nível alto intensifica o efeito de resfriamento
        if refluxo_alto:
            # Refluxo elevado: redução significativa da temperatura
            delta_temp_refluxo = -fator_refluxo * 3 * (tempo_decorrido / 10)
        else:
            # Carga alta: redução moderada
            delta_temp_refluxo = -fator_carga * 1.5 * (tempo_decorrido / 10)
        
        # Efeito adicional do nível alto
        if nivel > 70:
            # Nível muito alto: resfriamento adicional intenso
            delta_temp_nivel = -2.5 * (tempo_decorrido / 10) * ((nivel - 70) / 30)
        elif nivel > 60:
            # Nível moderadamente alto: resfriamento moderado
            delta_temp_nivel = -1 * (tempo_decorrido / 10)
        else:
            # Nível normal: pequena redução
            delta_temp_nivel = -0.5 * (tempo_decorrido / 10)
        
        temp_base = temp_base + delta_temp_refluxo + delta_temp_nivel
    
    return pressao, nivel, temp_base, nivel_topo_alto

# Inicializar contador de ciclos sobrecarregados
if "ciclos_sobrecarga" not in st.session_state:
    st.session_state.ciclos_sobrecarga = 0

# Verificar se há vazão alta e incrementar contador
if refluxo > 8834 or carga > 13617:
    st.session_state.ciclos_sobrecarga += 1
else:
    st.session_state.ciclos_sobrecarga = max(0, st.session_state.ciclos_sobrecarga - 1)

# Aplicar efeitos da vazão alta
pressao_simulado, nivel_simulado, temp_base_simulado, nivel_topo_alto_simulado = simular_efeitos_vazao_alta(
    refluxo, carga, pressao, nivel, temp_base, nivel_topo_alto, st.session_state.ciclos_sobrecarga
)

# Adicionar valores simulados ao histórico
st.session_state.press_hist.append(pressao_simulado)
st.session_state.nivel_hist.append(nivel_simulado)
st.session_state.temp_hist.append(temp_base_simulado)

# ========================
# VARIAÇÕES
# ========================
press_var = variacao(st.session_state.press_hist)
nivel_var = variacao(st.session_state.nivel_hist)
temp_var = variacao(st.session_state.temp_hist)

# ========================
# CONDIÇÕES CRÍTICAS
# ========================
cond_pressao = press_var >= 0.5
cond_nivel = abs(nivel_simulado - 60) >= 3
cond_temp = temp_var >= 2
cond_topo = nivel_topo_alto_simulado

# ========================
# PRÉ-ALERTA
# ========================
st.markdown("---")
st.subheader("⚠️ Alertas")

alert_col1, alert_col2 = st.columns(2)

with alert_col1:
    if refluxo > 8834 or carga > 13617:
        st.warning("⚠️ POSSÍVEL INSTABILIDADE DETECTADA!")
        if refluxo > 8834:
            excesso_refluxo = refluxo - 8834
            percentual_refluxo = (excesso_refluxo / 8834) * 100
            st.error(f"🔴 REFLUXO ELEVADO: +{excesso_refluxo:.0f} m³/h ({percentual_refluxo:.1f}%)\n→ Pressão do topo aumentando!")
        if carga > 13617:
            excesso_carga = carga - 13617
            percentual_carga = (excesso_carga / 13617) * 100
            st.error(f"🔴 CARGA ELEVADA: +{excesso_carga:.0f} m³/h ({percentual_carga:.1f}%)\n→ Pressão aumentando!")
    else:
        st.info("✅ Condições operacionais normais")

# ========================
# CONDIÇÕES CRÍTICAS
# ========================
with alert_col2:
    if cond_pressao and cond_nivel and cond_temp and cond_topo:
        st.error("🚨 INUNDAÇÃO DA TORRE DETECTADA!")
    else:
        st.success("✓ Nenhuma falha crítica")

# ========================
# DASHBOARD
# ========================
st.subheader("📈 Painel de Monitoramento")

# Métricas principais em grade 2x2
col1, col2 = st.columns(2)

with col1:
    st.metric(
        "Refluxo (m³/h)",
        f"{refluxo:.1f}",
        f"{tendencia(st.session_state.press_hist)}"
    )
    st.caption(f"Variação: {variacao(st.session_state.press_hist):.2f}")
    st.caption("📌 **Restrição:** Máximo 8.834 m³/h")
    if refluxo > 8834:
        st.error(f"⚠️ ACIMA DO LIMITE: {refluxo:.1f} > 8.834")

with col2:
    st.metric(
        "Carga (m³/h)",
        f"{carga:.1f}",
        f"{tendencia(st.session_state.press_hist)}"
    )
    st.caption("📌 **Restrição:** Máximo 13.617 m³/h")
    if carga > 13617:
        excesso_carga = carga - 13617
        percentual_carga = (excesso_carga / 13617) * 100
        st.error(f"⚠️ ACIMA DO LIMITE: +{excesso_carga:.0f} m³/h ({percentual_carga:.1f}%)")
        st.warning("📈 Carga elevada causa aumento de pressão e nível")

st.markdown("---")

# Grupo interligado com borda azul
st.markdown(
    """
    <div style="border: 2px solid #1f77e4; border-radius: 8px; padding: 15px; background-color: rgba(31, 119, 228, 0.05);">
        <h4 style="color: #1f77e4; margin-top: 0;">🔗 Variáveis Interligadas (Instabilidade)</h4>
        <p style="color: #666; font-size: 12px; margin-bottom: 10px;">
            Pressão, Nível e Temperatura oscilam quando parâmetros estão fora de projeto.<br>.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

col3, col4 = st.columns(2)

with col3:
    st.metric(
        "Pressão do Topo (kg/cm²)",
        f"{pressao_simulado:.2f}",
        f"{tendencia(st.session_state.press_hist)}"
    )
    st.caption(f"{cor_alerta(press_var, 0.5)} Variação: {press_var:.2f}")
    if refluxo > 8834:
        st.error("🔴 PRESSÃO DO TOPO AUMENTANDO! Refluxo elevado causa backpressure")
    elif carga > 13617:
        st.error("🔴 PRESSÃO AUMENTANDO! Carga elevada causa aumento de pressão")

with col4:
    st.metric(
        "Nível (%)",
        f"{nivel_simulado:.1f}",
        f"{tendencia(st.session_state.nivel_hist)}"
    )
    st.caption(f"{cor_alerta(abs(nivel_simulado-60), 3)} Desvio: {abs(nivel_simulado-60):.2f}")
    if refluxo > 8834:
        st.warning("📈 Nível subindo por acúmulo de líquido")
    elif carga > 13617:
        st.warning("📈 Nível subindo por carga elevada")

# Temperatura dentro do grupo interligado
temp_col = st.columns(1)[0]
with temp_col:
    st.metric(
        "Temperatura Base (°C)",
        f"{temp_base_simulado:.1f}",
        f"{tendencia(st.session_state.temp_hist)}"
    )
    st.caption(f"{cor_alerta(temp_var, 2)} Variação: {temp_var:.2f}")
    if refluxo > 8834:
        if nivel_simulado > 70:
            st.warning("📉 Temperatura caindo - nível alto (>70%) + refluxo elevado")
        elif nivel_simulado > 60:
            st.warning("📉 Temperatura caindo - nível moderado + refluxo elevado")
        else:
            st.warning("📉 Temperatura caindo - refluxo elevado causa resfriamento")
    elif carga > 13617:
        if nivel_simulado > 70:
            st.warning("📉 Temperatura caindo - nível alto (>70%) + carga elevada")
        elif nivel_simulado > 60:
            st.warning("📊 Temperatura estável - nível moderado + carga elevada")
        else:
            st.warning("📈 Temperatura aumentando - carga elevada, refluxo inadequado")

# ========================
# AUTO UPDATE
# ========================
time.sleep(2)
st.rerun()