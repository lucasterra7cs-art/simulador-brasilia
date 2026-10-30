import streamlit as st
import random
import json
import os

# Configuração da página Web
st.set_page_config(
    page_title="Simulador de Brasília",
    page_icon="🏛️",
    layout="wide"
)

ARQUIVO_SAVE = "save_brasilia.json"

# ==========================================
# CLASSES DE MODELAGEM DO JOGO
# ==========================================

class Ministro:
    def __init__(self, nome, perfil, bonus_pop, bonus_econ, dano_cap_prisao, dano_econ_prisao):
        self.nome = nome
        self.perfil = perfil  # 'Superministro', 'Cacique', 'Técnico'
        self.bonus_pop = bonus_pop
        self.bonus_econ = bonus_econ
        self.dano_cap_prisao = dano_cap_prisao
        self.dano_econ_prisao = dano_econ_prisao

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class BlocoPartidario:
    def __init__(self, nome, tamanho, lealdade_base, perfil):
        self.nome = nome
        self.tamanho = tamanho
        self.lealdade = lealdade_base
        self.perfil = perfil  # 'Ideologico', 'Oposicao', 'Fisiologico'

    def calcular_apoio(self):
        if self.perfil == 'Oposicao':
            return min(self.lealdade, 30)
        elif self.perfil == 'Ideologico':
            return max(self.lealdade, 70)
        return self.lealdade

    def votos_garantidos(self):
        return int(self.tamanho * (self.calcular_apoio() / 100))

    def aplicar_decaimento(self):
        if self.perfil == 'Fisiologico':
            self.lealdade -= 8
        elif self.perfil == 'Ideologico':
            self.lealdade -= 2
        self.lealdade = max(0, min(100, self.lealdade))

    def to_dict(self):
        return {
            "nome": self.nome,
            "tamanho": self.tamanho,
            "lealdade_base": self.lealdade,
            "perfil": self.perfil
        }


class Ministerio:
    def __init__(self, nome, orcamento, risco_corrupcao, ministro_inicial, controlado_por=None):
        self.nome = nome
        self.orcamento = orcamento
        self.risco_corrupcao = risco_corrupcao
        self.ministro = ministro_inicial
        self.controlado_por = controlado_por  # Objeto BlocoPartidario ou None


class ProjetoLei:
    def __init__(self, nome, tipo, imp_pop, imp_econ):
        self.nome = nome
        self.tipo = tipo.upper()
        self.impacto_popularidade = imp_pop
        self.impacto_economia = imp_econ
        self.votos_necessarios = 308 if self.tipo == 'PEC' else 257

    def to_dict(self):
        return {
            "nome": self.nome,
            "tipo": self.tipo,
            "imp_pop": self.impacto_popularidade,
            "imp_econ": self.impacto_economia
        }


# ==========================================
# MOTOR PRINCIPAL DO GOVERNO
# ==========================================

class Governo:
    def __init__(self, perfil_escolhido=1):
        self.mes = 1
        self.ano = 1
        self.cpi_ativa = False
        self.risco_desinformacao = 0
        self.tensao_institucional = 10
        self.projetos_aprovados = []
        self.logs_turno = ["🎊 Cerimônia de posse concluída! Suba a rampa do Planalto e inicie seu mandato."]
        
        # Controle de Eventos Interativos e Mini-games
        self.fase_atual = "mandato"  # 'mandato', 'crise', 'impeachment', 'eleicao', 'gameover'
        self.crise_pendente = None
        self.dia_impeachment = 1
        self.motivo_gameover = ""

        # Configuração de Perfis Iniciais
        if perfil_escolhido == 1:
            self.nome_perfil = "🎤 O Populista"
            self.popularidade, self.economia, self.capital_politico, self.orcamento_livre = 70, 30, 50, 60
            lealdade_centrao = 40
        elif perfil_escolhido == 2:
            self.nome_perfil = "📈 O Reformista Liberal"
            self.popularidade, self.economia, self.capital_politico, self.orcamento_livre = 30, 75, 45, 140
            lealdade_centrao = 35
        elif perfil_escolhido == 3:
            self.nome_perfil = "🦊 A Raposa Política"
            self.popularidade, self.economia, self.capital_politico, self.orcamento_livre = 35, 45, 95, 85
            lealdade_centrao = 70
        else:
            self.nome_perfil = "🤠 O Forasteiro (Anti-Sistema)"
            self.popularidade, self.economia, self.capital_politico, self.orcamento_livre = 65, 45, 20, 50
            lealdade_centrao = 15

        self.blocos = [
            BlocoPartidario("Base Ideológica", 100, 80, 'Ideologico'),
            BlocoPartidario("Oposição", 130, 10, 'Oposicao'),
            BlocoPartidario("Bloco do Centrão", 283, lealdade_centrao, 'Fisiologico')
        ]

        # Ministros Iniciais (Superministros e Técnicos)
        paulo_moeda = Ministro("Paulo Moeda (Fiador do Mercado)", "Superministro", 0, 15, 30, 25)
        sergio_lei = Ministro("Sérgio Lei (Ex-Juiz Federal)", "Superministro", 15, 0, 35, 0)
        tecnico_saude = Ministro("Dra. Nísia (Técnica da Saúde)", "Técnico", 5, 0, 10, 5)
        tecnico_infra = Ministro("Eng. Tarcísio (Quadro Técnico)", "Técnico", 5, 5, 10, 5)
        tecnico_educ = Ministro("Prof. Camilo (Acadêmico)", "Técnico", 5, 0, 10, 5)

        self.ministerios = [
            Ministerio("Ministério da Fazenda", 5, 1, paulo_moeda),
            Ministerio("Ministério da Justiça", 4, 1, sergio_lei),
            Ministerio("Ministério da Saúde", 5, 4, tecnico_saude),
            Ministerio("Ministério da Infraestrutura", 4, 5, tecnico_infra),
            Ministerio("Ministério da Educação", 4, 3, tecnico_educ)
        ]

        # Aplica bônus inicial dos ministros
        for m in self.ministerios:
            self.popularidade = min(100, self.popularidade + m.ministro.bonus_pop)
            self.economia = min(100, self.economia + m.ministro.bonus_econ)

        self.projetos = [
            ProjetoLei("Reforma Tributária", "PEC", -5, 20),
            ProjetoLei("Reforma Administrativa", "PEC", -12, 15),
            ProjetoLei("Autonomia do Banco Central", "PL", -5, 12),
            ProjetoLei("Ampliar Auxílio Social", "PL", 18, -12),
            ProjetoLei("Marco do Saneamento e Privatizações", "PL", -4, 14),
            ProjetoLei("Reajuste Real do Salário Mínimo", "PL", 12, -8),
            ProjetoLei("PEC dos Precatórios (Furar Teto)", "PEC", 15, -20),
            ProjetoLei("Pacote Anticrime", "PL", 10, 0),
            ProjetoLei("Programa Mais Médicos e Hospitais", "PL", 12, -6),
            ProjetoLei("Nova Lei das Estatais", "PL", -4, 10)
        ]

    def limitar_status(self):
        self.popularidade = max(0, min(100, self.popularidade))
        self.economia = max(0, min(100, self.economia))
        self.capital_politico = max(0, min(100, self.capital_politico))
        self.tensao_institucional = max(0, min(100, self.tensao_institucional))

    def calcular_votos_totais(self):
        return sum(b.votos_garantidos() for b in self.blocos)

    def calcular_risco_corrupcao(self):
        risco_min = 5 + sum(
            m.risco_corrupcao * (3 if m.controlado_por and m.controlado_por.perfil == 'Fisiologico' else 1)
            for m in self.ministerios if m.controlado_por
        )
        return risco_min + self.risco_desinformacao

    # --- MECÂNICA DE LOTEAMENTO ---
    def alocar_ministerio(self, idx_min, idx_bloco):
        minist = self.ministerios[idx_min]
        bloco = self.blocos[idx_bloco]
        ministro_antigo = minist.ministro

        # Retira bônus do ministro demitido
        self.economia -= ministro_antigo.bonus_econ
        self.popularidade -= ministro_antigo.bonus_pop

        if bloco.perfil == 'Fisiologico':
            novo_min = Ministro(f"Indicado do {bloco.nome}", "Cacique", -3, -3, 10, 5)
            minist.risco_corrupcao = min(10, minist.risco_corrupcao + 2)
            msg_extra = f"⚠️ {ministro_antigo.nome} foi demitido! Um cacique assumiu e o risco de corrupção subiu."
        elif bloco.perfil == 'Ideologico':
            novo_min = Ministro(f"Militante da {bloco.nome}", "Técnico", 3, -3, 10, 5)
            msg_extra = f"Membro da {bloco.nome} assumiu a pasta."
        else:
            novo_min = Ministro(f"Dissidente da {bloco.nome}", "Cacique", 0, 0, 10, 5)
            msg_extra = f"Ala da oposição ganhou espaço na Esplanada."

        minist.ministro = novo_min
        minist.controlado_por = bloco
        self.economia += novo_min.bonus_econ
        self.popularidade += novo_min.bonus_pop

        aumento_lealdade = minist.orcamento * 10
        bloco.lealdade = min(100, bloco.lealdade + aumento_lealdade)
        self.limitar_status()
        self.logs_turno.insert(0, f"🤝 **{minist.nome}** entregue ao **{bloco.nome}** (+{aumento_lealdade}% Lealdade). {msg_extra}")

    # --- MECÂNICA DE VOTAÇÃO ---
    def pautar_votacao(self, idx_proj, emendas):
        projeto = self.projetos[idx_proj]
        if emendas > self.orcamento_livre:
            return False, "Orçamento insuficiente para liberar essas emendas!"

        self.orcamento_livre -= emendas
        if emendas > 0:
            boost = emendas * 2
            self.blocos[2].lealdade = min(100, self.blocos[2].lealdade + boost)

        votos = self.calcular_votos_totais()
        if votos >= projeto.votos_necessarios:
            self.popularidade += projeto.impacto_popularidade
            self.economia += projeto.impacto_economia
            self.capital_politico += 5
            self.tensao_institucional += 15
            self.projetos_aprovados.append(projeto)
            self.projetos.pop(idx_proj)
            self.limitar_status()
            msg = f"✅ **{projeto.nome} ({projeto.tipo}) APROVADO** por {votos} votos! (Tensão com STF +15%)."
            self.logs_turno.insert(0, msg)
            return True, msg
        else:
            derrota_margem = projeto.votos_necessarios - votos
            desgaste = max(10, min(25, derrota_margem // 2))
            self.capital_politico -= desgaste
            self.limitar_status()
            msg = f"❌ **{projeto.nome} REJEITADO** ({votos}/{projeto.votos_necessarios} votos). Governo sofre derrota (-{desgaste} Cap. Político)."
            self.logs_turno.insert(0, msg)
            if self.capital_politico <= 0:
                self.fase_atual = "impeachment"
                self.dia_impeachment = 1
            return False, msg

    # --- MECÂNICA DO STF ---
    def acao_stf(self):
        if self.tensao_institucional > 30:
            chance = (self.tensao_institucional // 2) + (20 if self.risco_desinformacao > 15 else 0)
            if random.randint(1, 100) <= chance:
                acoes = []
                if self.projetos_aprovados:
                    acoes.append("liminar")
                acoes.append("prisao")
                acao = random.choice(acoes)

                if acao == "liminar":
                    alvo = random.choice(self.projetos_aprovados)
                    self.popularidade -= alvo.impacto_popularidade
                    self.economia -= alvo.impacto_economia
                    self.capital_politico -= 15
                    self.projetos_aprovados.remove(alvo)
                    self.logs_turno.insert(0, f"👨‍⚖️ **DECISÃO DO STF:** Liminar suspendeu a lei **{alvo.nome}** por inconstitucionalidade! Bônus revertidos e -15 Cap. Político.")
                else:
                    alvo = random.choice(self.ministerios)
                    min_preso = alvo.ministro
                    bloco_afetado = alvo.controlado_por
                    self.capital_politico -= min_preso.dano_cap_prisao
                    self.economia -= min_preso.dano_econ_prisao
                    self.popularidade -= 10
                    
                    msg_bloco = ""
                    if bloco_afetado:
                        bloco_afetado.lealdade = max(0, bloco_afetado.lealdade - 25)
                        msg_bloco = f" O {bloco_afetado.nome} se rebelou (-25% Lealdade)."

                    alvo.controlado_por = None
                    alvo.ministro = Ministro("Secretário Interino", "Técnico", 0, -5, 5, 5)
                    self.logs_turno.insert(0, f"🚓 **MANDADO DO STF:** A PF prendeu **{min_preso.nome}** ({alvo.nome})! Impacto: -{min_preso.dano_cap_prisao} Cap. Político, -{min_preso.dano_econ_prisao}% Economia.{msg_bloco}")

                self.tensao_institucional = max(0, self.tensao_institucional - 30)

    # --- MOTOR DE CRISES ---
    def motor_de_crises(self):
        risco_total = self.calcular_risco_corrupcao()
        if random.randint(1, 100) <= risco_total:
            if self.risco_desinformacao > 15 and random.choice([True, False]):
                self.popularidade -= 15
                self.capital_politico -= 25
                msg_pf = "🚨 **OPERAÇÃO DA PF:** Quebra de sigilo desmantela o Gabinete Paralelo de Fake News! (-15% Pop, -25 Cap. Político)."
            else:
                self.popularidade -= 8
                self.capital_politico -= 12
                msg_pf = "🚨 **OPERAÇÃO DA PF:** Escândalo de desvio de verbas em ministério loteado! (-8% Pop, -12 Cap. Político)."
            
            self.blocos[2].lealdade = max(0, self.blocos[2].lealdade - 15)
            if not self.cpi_ativa:
                self.cpi_ativa = True
                msg_pf += " 💥 **A Oposição conseguiu assinaturas e instaurou uma CPI!**"
            self.logs_turno.insert(0, msg_pf)

        # Sorteio de Crise Externa Interativa (30% de chance ao virar o mês)
        if random.randint(1, 100) <= 30:
            crises_disponiveis = [
                {
                    "nome": "Greve Geral dos Caminhoneiros",
                    "descricao": "Rodovias bloqueadas em todo o país. Falta combustível nos postos e alimentos nos mercados.",
                    "escolhas": [
                        {"texto": "Subsidiar o Diesel com dinheiro do Tesouro", "pop": 5, "econ": 0, "cap": -5, "custo": 40},
                        {"texto": "Acionar Força Nacional e multar grevistas", "pop": -8, "econ": -15, "cap": 10, "custo": 0},
                        {"texto": "Ignorar e esperar o movimento perder força", "pop": -20, "econ": -25, "cap": -10, "custo": 0}
                    ]
                },
                {
                    "nome": "Crise Hídrica e Risco de Apagão",
                    "descricao": "Reservatórios atingiram níveis críticos. O Operador Nacional alerta para colapso de energia.",
                    "escolhas": [
                        {"texto": "Bandeira Vermelha Escassez (Repassar conta ao povo)", "pop": -15, "econ": -5, "cap": -5, "custo": 0},
                        {"texto": "Tesouro banca as termelétricas (Segurar tarifa)", "pop": 10, "econ": 0, "cap": -5, "custo": 50},
                        {"texto": "Decretar Racionamento Obrigatório na indústria", "pop": -10, "econ": -20, "cap": 0, "custo": 0}
                    ]
                },
                {
                    "nome": "Disparada do Dólar e Inflação de Alimentos",
                    "descricao": "Crise internacional faz investidores fugirem. O preço da cesta básica disparou nos supermercados.",
                    "escolhas": [
                        {"texto": "Intervir no câmbio e zerar impostos de importação", "pop": 4, "econ": 8, "cap": 0, "custo": 30},
                        {"texto": "Manter ortodoxia e deixar o dólar flutuar", "pop": -15, "econ": -5, "cap": 0, "custo": 0},
                        {"texto": "Atacar o presidente do Banco Central na TV", "pop": 12, "econ": -18, "cap": -5, "custo": 0}
                    ]
                }
            ]
            self.crise_pendente = random.choice(crises_disponiveis)
            self.fase_atual = "crise"

    # --- VIRADA DE TURNO ---
    def virar_turno(self):
        self.logs_turno = []  # Limpa o resumo para os acontecimentos do novo mês

        if self.mes >= 48:
            self.fase_atual = "eleicao"
            return

        self.mes += 1
        if self.mes % 12 == 1 and self.mes > 1:
            self.ano += 1
            self.orcamento_livre += 100
            self.logs_turno.append("🎆 **NOVO ANO ORÇAMENTÁRIO!** O Congresso aprovou a LOA (+100M em Orçamento Livre).")

        # 1. Ações do STF e Crises
        self.acao_stf()
        self.motor_de_crises()

        # 2. Sangramento de CPI
        if self.cpi_ativa:
            dano_cap = random.randint(5, 12)
            dano_pop = random.randint(2, 5)
            self.capital_politico -= dano_cap
            self.popularidade -= dano_pop
            self.logs_turno.append(f"📺 **CPI EM ANDAMENTO:** Depoimentos televisionados desgastam o governo (-{dano_cap} Cap. Político, -{dano_pop}% Pop).")

        # 3. Decaimento de Lealdade e Arrecadação
        for bloco in self.blocos:
            bloco.aplicar_decaimento()

        arrecadacao = int(self.economia * 0.2)
        self.orcamento_livre += arrecadacao
        self.logs_turno.append(f"💰 **Arrecadação Mensal:** +{arrecadacao}M entraram nos cofres públicos.")

        self.limitar_status()

        # 4. Verificação de Impeachment ou Renúncia Forçada
        if self.popularidade <= 0:
            self.fase_atual = "gameover"
            self.motivo_gameover = "Sua popularidade chegou a 0%. Milhões tomaram as ruas, a Esplanada foi cercada e você foi forçado a renunciar."
        elif self.capital_politico <= 0 and self.fase_atual != "crise":
            self.fase_atual = "impeachment"
            self.dia_impeachment = 1

    # --- PERSISTÊNCIA EM JSON ---
    def salvar_jogo(self):
        estado = {
            "nome_perfil": self.nome_perfil,
            "mes": self.mes,
            "ano": self.ano,
            "cpi_ativa": self.cpi_ativa,
            "risco_desinformacao": self.risco_desinformacao,
            "tensao_institucional": self.tensao_institucional,
            "popularidade": self.popularidade,
            "economia": self.economia,
            "capital_politico": self.capital_politico,
            "orcamento_livre": self.orcamento_livre,
            "logs_turno": self.logs_turno,
            "blocos": [b.to_dict() for b in self.blocos],
            "ministerios": [
                {
                    "nome": m.nome,
                    "orcamento": m.orcamento,
                    "risco_corrupcao": m.risco_corrupcao,
                    "ministro": m.ministro.to_dict(),
                    "controlado_por": m.controlado_por.nome if m.controlado_por else None
                } for m in self.ministerios
            ],
            "projetos": [p.to_dict() for p in self.projetos],
            "projetos_aprovados": [p.to_dict() for p in self.projetos_aprovados]
        }
        with open(ARQUIVO_SAVE, 'w', encoding='utf-8') as f:
            json.dump(estado, f, ensure_ascii=False, indent=4)

    @classmethod
    def carregar_jogo(cls):
        with open(ARQUIVO_SAVE, 'r', encoding='utf-8') as f:
            d = json.load(f)
        gov = cls(1)
        gov.nome_perfil = d["nome_perfil"]
        gov.mes = d["mes"]
        gov.ano = d["ano"]
        gov.cpi_ativa = d["cpi_ativa"]
        gov.risco_desinformacao = d["risco_desinformacao"]
        gov.tensao_institucional = d["tensao_institucional"]
        gov.popularidade = d["popularidade"]
        gov.economia = d["economia"]
        gov.capital_politico = d["capital_politico"]
        gov.orcamento_livre = d["orcamento_livre"]
        gov.logs_turno = d.get("logs_turno", ["💾 Jogo carregado com sucesso!"])
        gov.blocos = [BlocoPartidario(**b) for b in d["blocos"]]
        gov.projetos = [ProjetoLei(**p) for p in d["projetos"]]
        gov.projetos_aprovados = [ProjetoLei(**p) for p in d["projetos_aprovados"]]

        gov.ministerios = []
        for m_data in d["ministerios"]:
            min_obj = Ministro.from_dict(m_data["ministro"])
            bloco_dono = next((b for b in gov.blocos if b.nome == m_data["controlado_por"]), None)
            gov.ministerios.append(Ministerio(m_data["nome"], m_data["orcamento"], m_data["risco_corrupcao"], min_obj, bloco_dono))
        return gov


# ==========================================
# INTERFACE GRÁFICA (STREAMLIT)
# ==========================================

if "gov" not in st.session_state:
    st.session_state.gov = None

# 1. TELA INICIAL (SELEÇÃO DE PERFIL OU LOAD)
if st.session_state.gov is None:
    st.title("🏛️ Simulador de Brasília: Presidencialismo de Coalizão")
    st.markdown("Sobreviva a 48 meses de mandato negociando com o Congresso, gerenciando a Esplanada, enfrentando CPIs e equilibrando a relação com o STF.")
    st.divider()

    col_novo, col_load = st.columns([2, 1])

    with col_novo:
        st.subheader("📜 Iniciar Novo Mandato")
        perfis = {
            1: ("🎤 O Populista", "Alta aprovação nas ruas (70%), mas o mercado desconfia da sua gestão fiscal (Economia 30%)."),
            2: ("📈 O Reformista Liberal", "Caixa cheio (140M) e economia aquecida (75%), mas baixa popularidade inicial (30%)."),
            3: ("🦊 A Raposa Política", "Mestre dos bastidores. Começa com Capital Político no topo (95) e Centrão aliado (70%)."),
            4: ("🤠 O Forasteiro (Modo Difícil)", "Surfou a onda anti-sistema. Popular (65%), mas o Congresso quer te derrubar no mês 1 (Cap. Político 20).")
        }
        escolha = st.radio(
            "Escolha o arquétipo do seu Presidente:",
            options=list(perfis.keys()),
            format_func=lambda x: f"{perfis[x][0]} — {perfis[x][1]}"
        )
        if st.button("Vestir a Faixa Presidencial 🚀", type="primary", use_container_width=True):
            st.session_state.gov = Governo(escolha)
            st.rerun()

    with col_load:
        st.subheader("💾 Continuar Mandato")
        if os.path.exists(ARQUIVO_SAVE):
            st.info("Arquivo `save_brasilia.json` encontrado no sistema.")
            if st.button("Carregar Jogo Salvo 📂", use_container_width=True):
                st.session_state.gov = Governo.carregar_jogo()
                st.rerun()
        else:
            st.caption("Nenhum jogo salvo encontrado no momento.")

    st.stop()

gov = st.session_state.gov

# ==========================================
# CABEÇALHO DE MÉTRICAS (SEMPRE VISÍVEL)
# ==========================================
st.title(f"🏛️ Palácio do Planalto — Mês {gov.mes}/48 ({gov.ano}º Ano)")
st.caption(f"Perfil no Poder: **{gov.nome_perfil}**")

if gov.cpi_ativa:
    st.error("🚨 **ALERTA VERMELHO: CPI EM ANDAMENTO NO CONGRESSO!** O governo perde Capital Político e Popularidade todos os meses até enterrar a comissão.")

c1, c2, c3, c4, c5, c6 = st.columns(6)
votos_atuais = gov.calcular_votos_totais()

c1.metric("📊 Popularidade", f"{gov.popularidade}%")
c2.metric("📈 Economia", f"{gov.economia}%")
c3.metric("🔥 Cap. Político", f"{gov.capital_politico}/100")
c4.metric("💰 Orçamento Livre", f"R$ {gov.orcamento_livre}M")
c5.metric("🗳️ Base na Câmara", f"{votos_atuais}/513", delta="Maioria PEC" if votos_atuais >= 308 else ("Maioria PL" if votos_atuais >= 257 else "Minoria"))
c6.metric("⚖️ Tensão STF", f"{gov.tensao_institucional}%", delta="Risco Alto" if gov.tensao_institucional >= 60 else "Estável", delta_color="inverse")

st.divider()

# ==========================================
# TELAS DE EVENTOS ESPECIAIS (BLOQUEANTES)
# ==========================================

# A) TELA DE CRISE INTERATIVA
if gov.fase_atual == "crise" and gov.crise_pendente:
    crise = gov.crise_pendente
    st.warning(f"### 📰 PLANTÃO URGENTE: {crise['nome'].upper()}")
    st.write(crise["descricao"])
    st.markdown("**O país aguarda uma decisão imediata do Palácio do Planalto:**")

    for i, op in enumerate(crise["escolhas"]):
        custo_str = f"Custa R$ {op['custo']}M" if op['custo'] > 0 else "Sem custo direto ao Tesouro"
        impactos_str = f"(Pop: {op['pop']:+}% | Econ: {op['econ']:+}% | Cap: {op['cap']:+})"
        desabilitado = op['custo'] > gov.orcamento_livre

        if st.button(f"{op['texto']} — [{custo_str}] {impactos_str}", key=f"crise_{i}", disabled=desabilitado, use_container_width=True):
            gov.orcamento_livre -= op['custo']
            gov.popularidade += op['pop']
            gov.economia += op['econ']
            gov.capital_politico += op['cap']
            gov.limitar_status()
            gov.logs_turno.insert(0, f"📰 **Crise ({crise['nome']}):** Você escolheu '{op['texto']}'.")
            gov.crise_pendente = None
            
            if gov.capital_politico <= 0:
                gov.fase_atual = "impeachment"
                gov.dia_impeachment = 1
            elif gov.popularidade <= 0:
                gov.fase_atual = "gameover"
                gov.motivo_gameover = "A gestão desastrosa da crise zerou sua popularidade e levou à queda do governo."
            else:
                gov.fase_atual = "mandato"
            st.rerun()
    st.stop()

# B) MINI-GAME DE JULGAMENTO DO IMPEACHMENT
if gov.fase_atual == "impeachment":
    st.error("## 🚨 PROCESSO DE IMPEACHMENT ABERTO NA CÂMARA!")
    st.markdown(f"**Dia {gov.dia_impeachment} de 3 antes da votação no plenário.** Seu Capital Político zerou. Você precisa garantir pelo menos **172 votos** a seu favor para arquivar a denúncia (Votos atuais: **{votos_atuais}**).")

    if gov.dia_impeachment <= 3:
        col_i1, col_i2, col_i3 = st.columns(3)
        with col_i1:
            st.markdown("#### 💸 Emendas de Emergência")
            st.caption("O Centrão inflacionou o preço: 2M = +1% Lealdade.")
            gasto_imp = st.slider("Valor do pacote (Milhões):", 0, gov.orcamento_livre, min(20, gov.orcamento_livre))
            if st.button("Liberar Cofres", use_container_width=True):
                gov.orcamento_livre -= gasto_imp
                boost = gasto_imp // 2
                gov.blocos[2].lealdade = min(100, gov.blocos[2].lealdade + boost)
                gov.logs_turno.insert(0, f"🚨 **Impeachment (Dia {gov.dia_impeachment}):** Gasto de R$ {gasto_imp}M rendeu +{boost}% de lealdade no Centrão.")
                gov.dia_impeachment += 1
                st.rerun()

        with col_i2:
            st.markdown("#### 📺 Cadeia Nacional de TV")
            st.caption("Apela às ruas (-5% Econ, sorteia Popularidade).")
            if st.button("Fazer Pronunciamento", use_container_width=True):
                gov.economia = max(0, gov.economia - 5)
                ganho_pop = random.randint(-5, 15)
                gov.popularidade = max(0, min(100, gov.popularidade + ganho_pop))
                if gov.popularidade > 40:
                    gov.blocos[2].lealdade = min(100, gov.blocos[2].lealdade + 10)
                gov.logs_turno.insert(0, f"📺 **Impeachment (Dia {gov.dia_impeachment}):** Pronunciamento alterou popularidade em {ganho_pop:+}%.")
                gov.dia_impeachment += 1
                st.rerun()

        with col_i3:
            st.markdown("#### 🤝 Porteira Fechada")
            st.caption("+30% Lealdade no Centrão, mas explode o risco de corrupção futuro.")
            if st.button("Entregar Estatais e Cargos", use_container_width=True):
                gov.blocos[2].lealdade = min(100, gov.blocos[2].lealdade + 30)
                for m in gov.ministerios:
                    m.risco_corrupcao = min(10, m.risco_corrupcao + 3)
                gov.logs_turno.insert(0, f"🤝 **Impeachment (Dia {gov.dia_impeachment}):** Porteira fechada! +30% Lealdade no Centrão, mas risco de corrupção disparou.")
                gov.dia_impeachment += 1
                st.rerun()
    else:
        st.subheader("⚖️ O Plenário está votando o parecer...")
        st.write(f"Votos a favor do governo para barrar o processo: **{votos_atuais} / 172 necessários**.")
        if votos_atuais >= 172:
            st.success("✅ **VOCÊ SOBREVIVEU!** O pedido de Impeachment foi arquivado! Seu Capital Político voltou para 25.")
            if st.button("Retornar ao Palácio do Planalto", type="primary"):
                gov.capital_politico = 25
                gov.fase_atual = "mandato"
                st.rerun()
        else:
            st.error("❌ **IMPEACHMENT APROVADO!** A oposição alcançou 342 votos. Você perdeu o mandato e ficou inelegível por 8 anos.")
            if st.button("Sair pela porta dos fundos (Novo Jogo)"):
                st.session_state.gov = None
                st.rerun()
    st.stop()

# C) TELA DE ELEIÇÃO FINAL (MÊS 48)
if gov.fase_atual == "eleicao":
    st.balloons()
    st.header("🗳️ Eleições Presidenciais — Fim dos 4 Anos de Mandato!")
    st.write("Você sobreviveu aos 48 meses! Agora o Tribunal Superior Eleitoral (TSE) vai totalizar os votos com base na sua Popularidade (peso 70%) e Economia (peso 30%).")

    if "resultado_eleicao" not in st.session_state:
        fator_campanha = random.randint(-10, 10)
        voto_base = (gov.popularidade * 0.7) + (gov.economia * 0.3)
        st.session_state.resultado_eleicao = max(0.0, min(100.0, voto_base + fator_campanha))
        st.session_state.fator_campanha = fator_campanha

    votos_finais = st.session_state.resultado_eleicao
    st.metric("Seus Votos Válidos no 2º Turno", f"{votos_finais:.1f}%", delta=f"{st.session_state.fator_campanha:+}% nos debates finais")

    if votos_finais >= 50.1:
        st.success("🏆 **VITÓRIA ÉPICA! VOCÊ FOI REELEITO!** O povo aprovou sua gestão e lhe concedeu mais 4 anos no Planalto!")
    else:
        st.warning("📉 **DERROTA NAS URNAS.** Você completou o mandato sem cair, mas o desgaste falou mais alto e a oposição venceu a eleição.")

    if st.button("Jogar Novamente 🔄", type="primary"):
        del st.session_state.resultado_eleicao
        st.session_state.gov = None
        st.rerun()
    st.stop()

# D) TELA DE GAME OVER
if gov.fase_atual == "gameover":
    st.error("## 🚨 FIM DE JOGO: QUEDA DO GOVERNO")
    st.write(gov.motivo_gameover)
    if st.button("Voltar ao Menu Principal 🔄", type="primary"):
        st.session_state.gov = None
        st.rerun()
    st.stop()


# ==========================================
# PAINEL PRINCIPAL DO MANDATO (ABAS E LATERAL)
# ==========================================

col_principal, col_lateral = st.columns([2.3, 1])

with col_principal:
    aba_congresso, aba_esplanada, aba_bastidores = st.tabs([
        "⚖️ Congresso e Projetos de Lei",
        "🤝 Esplanada dos Ministérios",
        "🕵️ Bastidores (CPI, STF e Mídia)"
    ])

    # --- ABA 1: CONGRESSO E VOTAÇÕES ---
    with aba_congresso:
        st.subheader("Composição da Câmara dos Deputados (513 Assentos)")
        cols_b = st.columns(3)
        for i, b in enumerate(gov.blocos):
            with cols_b[i]:
                st.markdown(f"**{b.nome}** ({b.tamanho} dep.)")
                st.progress(b.lealdade / 100, text=f"Lealdade: {b.lealdade}% ({b.votos_garantidos()} votos)")

        st.divider()
        st.subheader("📋 Pauta Legislativa")
        if not gov.projetos:
            st.info("Todos os projetos da pauta foram aprovados!")
        else:
            opcoes_proj = [
                f"[{p.tipo}] {p.nome} (Exige {p.votos_necessarios} votos | Pop: {p.impacto_popularidade:+}% | Econ: {p.impacto_economia:+}%)"
                for p in gov.projetos
            ]
            idx_proj = st.selectbox("Selecione o Projeto para enviar ao Plenário:", range(len(opcoes_proj)), format_func=lambda x: opcoes_proj[x])
            emendas = st.slider("💰 Liberar Emendas Parlamentares de última hora (+2% Lealdade no Centrão por milhão):", 0, gov.orcamento_livre, 0)

            if st.button("Pautar Votação no Plenário 🗳️", type="primary"):
                sucesso, msg = gov.pautar_votacao(idx_proj, emendas)
                st.rerun()

    # --- ABA 2: ESPLANADA E SUPERMINISTROS ---
    with aba_esplanada:
        st.subheader("Loteamento da Esplanada e Superministros")
        st.caption(f"Risco total de operação da Polícia Federal neste mês: **{gov.calcular_risco_corrupcao()}%**")

        for i, m in enumerate(gov.ministerios):
            with st.expander(f"🏛️ **{m.nome}** — Ministro Atual: {m.ministro.nome} ({m.ministro.perfil})", expanded=True):
                c_info, c_acao = st.columns([2, 1])
                with c_info:
                    dono_str = m.controlado_por.nome if m.controlado_por else "Cota Pessoal do Presidente (Sem Partido)"
                    st.write(f"**Controle Político:** {dono_str}")
                    st.write(f"**Peso Orçamentário:** +{m.orcamento * 10}% Lealdade ao nomear | **Risco de Corrupção:** {m.risco_corrupcao}/10")
                    st.caption(f"Bônus do Ministro: Pop {m.ministro.bonus_pop:+}%, Econ {m.ministro.bonus_econ:+}% | Dano se preso pelo STF: -{m.ministro.dano_cap_prisao} Cap. Político")
                with c_acao:
                    bloco_escolhido = st.selectbox(
                        "Entregar pasta para:",
                        range(len(gov.blocos)),
                        format_func=lambda x: gov.blocos[x].nome,
                        key=f"sel_min_{i}"
                    )
                    if st.button("Nomear Indicado 🤝", key=f"btn_min_{i}", use_container_width=True):
                        gov.alocar_ministerio(i, bloco_escolhido)
                        st.rerun()

    # --- ABA 3: BASTIDORES (CPI, STF, FAKE NEWS) ---
    with aba_bastidores:
        st.subheader("Operações de Bastidores e Contenção de Crises")

        col_b1, col_b2, col_b3 = st.columns(3)

        with col_b1:
            st.markdown("#### 🛑 Enterrar CPI")
            st.write("Pague o pedágio exigido pelos caciques para esvaziar as sessões e encerrar a investigação.")
            st.caption("Custo: **R$ 60M** (+15% Lealdade no Centrão)")
            if st.button("Pagar Acordo (R$ 60M)", disabled=(not gov.cpi_ativa or gov.orcamento_livre < 60), use_container_width=True):
                gov.orcamento_livre -= 60
                gov.cpi_ativa = False
                gov.blocos[2].lealdade = min(100, gov.blocos[2].lealdade + 15)
                gov.logs_turno.insert(0, "🛑 **ACORDO DE BASTIDORES:** A base aliada esvaziou a comissão e a CPI foi arquivada!")
                st.rerun()

        with col_b2:
            st.markdown("#### 📱 Gabinete Paralelo")
            st.write("Dispare campanhas coordenadas nas redes para inflar sua aprovação rapidamente.")
            st.caption("Custo: **R$ 25M** | Ganho: +12% a +22% Pop | Risco PF +8% permanente e Tensão STF +25%")
            if st.button("Disparar Fake News (R$ 25M)", disabled=(gov.orcamento_livre < 25), use_container_width=True):
                gov.orcamento_livre -= 25
                ganho = random.randint(12, 22)
                gov.popularidade = min(100, gov.popularidade + ganho)
                gov.risco_desinformacao += 8
                gov.tensao_institucional = min(100, gov.tensao_institucional + 25)
                gov.logs_turno.insert(0, f"📱 **GABINETE PARALELO:** Redes inflamadas! Popularidade +{ganho}%, mas o STF abriu inquérito (+25% Tensão).")
                st.rerun()

        with col_b3:
            st.markdown("#### ☕ Jantar com o STF")
            st.write("Convide os ministros da Suprema Corte para apaziguar os ânimos e evitar liminares ou prisões.")
            st.caption("Custo: **15 Capital Político** | Reduz Tensão Institucional em -40%")
            if st.button("Promover Jantar (-15 Cap.)", disabled=(gov.tensao_institucional < 20 or gov.capital_politico < 15), use_container_width=True):
                gov.capital_politico -= 15
                gov.tensao_institucional = max(0, gov.tensao_institucional - 40)
                gov.logs_turno.insert(0, "☕ **DIPLOMACIA INSTITUCIONAL:** Jantar no Palácio da Alvorada reduziu a Tensão com o STF em -40%.")
                st.rerun()

# ==========================================
# COLUNA LATERAL (CONTROLE DE TURNO E DIÁRIO)
# ==========================================
with col_lateral:
    st.subheader("⏩ Controle de Mandato")
    if st.button("Passar o Mês (Virar Turno) 🗓️", type="primary", use_container_width=True):
        gov.virar_turno()
        st.rerun()

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if st.button("💾 Salvar Jogo", use_container_width=True):
            gov.salvar_jogo()
            st.toast("Progresso salvo em 'save_brasilia.json'!", icon="💾")
    with col_s2:
        if st.button("🚪 Renunciar", use_container_width=True):
            st.session_state.gov = None
            st.rerun()

    st.divider()
    st.subheader("📰 Diário Oficial e Notícias")
    for log in gov.logs_turno:
        st.markdown(f"- {log}")