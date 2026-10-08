"""
Soul Heart - Demo (arquivo unico)

SALAS ESTILO (plataforma): 1, 2 (tutorial), 5 (mini-boss), 6 (parkour)
SALAS ESTILO (top-down): 3, 4
Sala 7 (chefe final) continua placeholder.

SALA 4 = LABIRINTO GRANDE (a camera acompanha): ache o bau com a chave da porta de cima
  (ele fica visivel, num beco bem longe da entrada) e fuja das torres dos saloes.
  Um beco na BORDA do mapa tem uma parede SECRETA (igual as outras): bata com Q pra abrir.
  Ela leva a uma sala toda escura: procure a trilha de luzes ate o bau (+5 vida, +1 dano).
VIDA: barra unica, comeca com 15.

VOLTAR ENTRE SALAS: toda sala (menos a 1) tem uma porta de volta. Aperte E perto dela.
  A sala 6 tem duas entradas (sala 5 e porta grande da sala 3): a porta de volta
  leva pra sala de onde voce veio.

CONTROLES
  Plataforma: A/D mover | SHIFT correr | ESPACO pular (segure = pulo alto)
              Q atacar (W/CIMA + Q = pra cima | S/BAIXO + Q no ar = pra baixo -> POGO)
  Top-down:   WASD/setas mover | Q ataca na direcao que voce esta olhando
  E interagir (portas, bau)
  PARRY: bata (Q) na hora em que o golpe inimigo te alcanca (investida do peao/torre,
         tiro do bispo). Anula o dano, atordoa o inimigo (leva dano em dobro) e
         reflete projeteis de volta.
  F1 mostra/esconde as HITBOXES (caixas verdes) - util pra alinhar sprites

SPRITES
  Rode o jogo uma vez: ele cria a pasta "assets/" e o arquivo
  assets/SPRITES_FALTANDO.txt com o nome de CADA sprite que o codigo usa.
  Procure por ">>> SPRITE" neste arquivo pra ver onde cada um entra.
  Sem sprite, o jogo desenha retangulos (nunca quebra).
"""
import asyncio
import json
import pygame
import sys
import os
import random
import math


pygame.init()

# ============================================================
# config
# ============================================================
LARGURA_TELA, ALTURA_TELA = 800, 600
FPS = 60

# ---------- fisica - plataforma (plataforma) ----------
GRAVIDADE = 0.9
VEL_QUEDA_MAX = 18
FORCA_PULO = -16
FORCA_POGO = -18
VEL_HORIZONTAL = 5
VEL_CORRIDA = 8
COYOTE = 0.10          # tempo extra pra pular depois de sair da borda
BUFFER_PULO = 0.12     # aperta pulo um pouco antes de pousar e ele pula assim que tocar o chao
CORTE_PULO = 0.45      # soltar o pulo no meio da subida corta a altura

# ---------- fisica - top-down (Isaac / Deltarune) ----------
VEL_TOPDOWN = 4
VEL_TOPDOWN_CORRIDA = 7

# ---------- combate ----------
DANO_ESPADA = 3
ALCANCE_ESPADA = 40
COOLDOWN_ATAQUE = 0.35
TEMPO_INVENCIVEL = 0.8
DANO_ESPINHO = 2
DURACAO_ATAQUE = 0.15   # quanto tempo o golpe dura (a animacao de ataque se ajusta a isso)

# ---------- parry (aparar golpes inimigos atacando na hora certa) ----------
JANELA_PARRY = 0.12           # s do INICIO do golpe em que a espada "apara" (o golpe dura 0.15s)
INVENCIVEL_PARRY = 0.6        # i-frames depois de um parry
TEMPO_ATORDOADO_PARRY = 1.6   # quanto tempo o inimigo aparado fica atordoado
MULT_DANO_ATORDOADO = 2       # dano que o atordoado leva = DANO_ESPADA * isso

# ---------- teclas ----------
TECLA_ATAQUE = pygame.K_q
TECLA_PULO = pygame.K_SPACE
TECLA_INTERAGIR = pygame.K_e
TECLA_CORRER = (pygame.K_LSHIFT, pygame.K_RSHIFT)

# ---------- efeitos de "game feel" (hitstop = congela um instante, tremor = shake) ----------
FX = {"hitstop": 0.0, "tremor": 0.0, "mag": 0}


def hitstop(t):
    FX["hitstop"] = max(FX["hitstop"], t)


def tremer(t, mag=4):
    FX["tremor"] = max(FX["tremor"], t)
    FX["mag"] = max(mag, FX["mag"] if FX["tremor"] > 0 else 0)


# ============================================================
# sprites - SISTEMA DE SPRITES
# ============================================================
# COMO USAR
#   1) Rode o jogo: ele cria a pasta "assets/" (ao lado deste arquivo) e o
#      arquivo assets/SPRITES_FALTANDO.txt com TODOS os sprites que o codigo
#      sabe usar, o nome exato de cada arquivo e o que ele representa.
#   2) Coloque os PNGs nas pastas. Nao precisa ter todos: o que faltar
#      continua sendo desenhado como retangulo colorido.
#   3) Animacao = arquivos numerados:   jogador/andar_0.png, andar_1.png ...
#      Imagem unica (sem animacao)   =  jogador/andar.png
#   4) Desenhe os sprites virados pra DIREITA (o codigo espelha pra esquerda).
#   5) O sprite e alinhado pela BASE-CENTRO da hitbox. Se ficar deslocado, ajuste
#      "offset" / "tamanho" em SPRITE_AJUSTE (a hitbox NAO muda). F1 = ver hitboxes.
PASTA_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals()
                            else os.getcwd(), "assets")
MOSTRAR_SPRITES_FALTANDO = True     # imprime no console quantos sprites ja existem
FPS_ANIM_PADRAO = 10                # velocidade padrao das animacoes (quadros por segundo)
DEBUG = {"hitbox": False}           # F1 liga/desliga

# >>> AJUSTE AQUI o tamanho e a posicao dos sprites de cada personagem <<<
#   tamanho = (largura, altura) pra escalar o PNG na tela, ou None = tamanho original do PNG
#   offset  = (dx, dy) pra empurrar o sprite (+dx direita, +dy baixo)
#   modo    = "baixo" (base do sprite na base da hitbox) | "centro" | "esticar" (cabe na hitbox)
SPRITE_AJUSTE = {
    "jogador":       {"tamanho": None, "offset": (0, 0)},   # hitbox 34x54
    "peao":          {"tamanho": None, "offset": (0, 0)},   # hitbox 36x46
    "bispo":         {"tamanho": None, "offset": (0, 0)},   # hitbox 34x48
    "rastejante":    {"tamanho": None, "offset": (0, 0)},   # hitbox 46x30
    "voador":        {"tamanho": None, "offset": (0, 0)},   # hitbox 38x30
    "torre_boss":    {"tamanho": None, "offset": (0, 0)},   # hitbox 70x100
    "torre_orbital": {"tamanho": None, "offset": (0, 0), "modo": "centro"},   # hitbox 34x34
}
PX_POR_VIDA = 12                    # largura (px) de cada ponto de vida na barra do HUD
DESENHAR_CORDA_LAMPARINA = True     # False se o sprite da lamparina ja tiver a corda/corrente

# animacoes que, se faltarem, usam outra no lugar (o ultimo recurso e sempre "idle")
FALLBACK_ANIM_JOGADOR = {
    "parry": "ataque_frente",
    "andar": "idle", "correr": "andar", "pulo": "idle", "queda": "pulo", "dano": "idle",
    "ataque_frente": "idle", "ataque_cima": "ataque_frente", "ataque_baixo": "ataque_frente",
    "td_idle_lado": "idle", "td_idle_cima": "td_idle_lado", "td_idle_baixo": "td_idle_lado",
    "td_andar_lado": "andar", "td_andar_cima": "td_andar_lado", "td_andar_baixo": "td_andar_lado",
    "td_ataque_lado": "ataque_frente", "td_ataque_cima": "td_ataque_lado", "td_ataque_baixo": "td_ataque_lado",
}

DESCRICAO_SPRITES = {
    "jogador/idle": "parado (plataforma). Ultimo recurso de TODAS as animacoes do jogador",
    "jogador/andar": "andando (plataforma)",
    "jogador/correr": "correndo com SHIFT (plataforma)",
    "jogador/pulo": "SUBINDO no pulo (plataforma)",
    "jogador/queda": "CAINDO (plataforma)",
    "jogador/dano": "tomando dano / sendo empurrado",
    "jogador/ataque_frente": "golpe de espada pra frente (dura 0.15s - os quadros se ajustam sozinhos)",
    "jogador/ataque_cima": "golpe pra CIMA (W + Q)",
    "jogador/ataque_baixo": "golpe pra BAIXO no ar (S + Q) = o POGO",
    "jogador/td_idle_lado": "top-down: parado olhando pro lado",
    "jogador/td_idle_cima": "top-down: parado olhando pra cima",
    "jogador/td_idle_baixo": "top-down: parado olhando pra baixo",
    "jogador/td_andar_lado": "top-down: andando pro lado",
    "jogador/td_andar_cima": "top-down: andando pra cima",
    "jogador/td_andar_baixo": "top-down: andando pra baixo",
    "jogador/td_ataque_lado": "top-down: golpe pro lado",
    "jogador/td_ataque_cima": "top-down: golpe pra cima",
    "jogador/td_ataque_baixo": "top-down: golpe pra baixo",
    "efeitos/golpe_frente": "EFEITO do corte da espada pra frente (esticado na hitbox do golpe)",
    "efeitos/golpe_cima": "efeito do corte pra cima",
    "efeitos/golpe_baixo": "efeito do corte pra baixo",
    "efeitos/parry": "brilho do PARRY (toca 1 vez, ~0.4s, centralizado no ponto do impacto)",
    "jogador/parry": "pose do jogador ao dar um PARRY (toca ~0.25s; se faltar usa ataque_frente)",
    "efeitos/projetil": "bolinha que o bispo atira (14x14)",
    "peao/idle": "peao parado (ultimo recurso do peao)",
    "peao/andar": "peao girando em volta do jogador",
    "peao/aviso": "peao se preparando pra atacar (pisca)",
    "peao/investida": "peao investindo",
    "peao/descanso": "peao cansado depois da investida",
    "bispo/idle": "bispo parado", "bispo/andar": "bispo andando", "bispo/atirar": "bispo prestes a atirar",
    "rastejante/idle": "bichinho do chao (sala 2)", "rastejante/andar": "bichinho andando",
    "voador/idle": "inseto voador (sala 6)", "voador/voar": "inseto batendo asa",
    "torre_boss/idle": "torre (mini-boss) parada/dormindo", "torre_boss/andar": "torre patrulhando",
    "torre_boss/aviso": "torre se preparando pra investir", "torre_boss/investida": "torre investindo",
    "torre_boss/atordoado": "torre atordoada na parede (hora de bater)",
    "torre_boss/salto_aviso": "torre agachando pro salto", "torre_boss/salto": "torre no ar",
    "torre_orbital/idle": "pecas de torre que giram na sala 4",
    "objetos/espinho": "1 modulo de espinho (repete pela largura da area de espinhos)",
    "objetos/lamparina": "lamparina do POGO (30x30)",
    "objetos/pedra": "pedras da sala 3 (esticado na hitbox)",
    "itens/coracao": "coracao que cura", "itens/chave": "chave pequena",
    "itens/bau_fechado": "bau fechado (40x30)", "itens/bau_aberto": "bau aberto",
    "portas/porta_normal": "porta comum (90x150)", "portas/porta_trancada": "porta comum trancada",
    "portas/escada_normal": "escada/porta do topo (90x30)", "portas/escada_trancada": "escada trancada",
    "portas/escada_baixo_normal": "escada/porta de baixo, pra voltar (90x30)",
    "portas/escada_baixo_trancada": "escada de baixo trancada",
    "portas/grande_normal": "porta grande (30x150)", "portas/grande_trancada": "porta grande trancada",
    "cenario/pedra": "tile de pedra 100x100 (chao e paredes). Varie: pedra_0, pedra_1, pedra_2...",
    "cenario/plataforma": "plataforma fina (esticada no tamanho dela)",
    "cenario/bloco_central": "bloco do meio da sala 4",
    "cenario/parede_labirinto": "parede do labirinto da sala 4 (esticada no tamanho de cada parede)",
    "cenario/parede_secreta": "parede secreta do labirinto (sala 4) - quebra com 1 golpe",
        "cenario/fundo_sala4s": "fundo da sala secreta (800x600; fica escuro, so o bau e iluminado)",
    "cenario/pedestal": "pedestal do bau na sala secreta (80x26)",
    "objetos/luz_guia": "luzinha da trilha de luzes da sala secreta (30x30)",
    "portas/secreta_normal": "porta secreta da sala 4 (60x110, aparece quando a parede rachada quebra)",
    "cenario/arvore": "arvore da sala 1 (base do sprite fica no chao)",
    "cenario/fundo_sala1": "fundo da sala 1 (800x600 ou mais largo: rola com a camera)",
    "cenario/fundo_sala2": "fundo da sala 2", "cenario/fundo_sala3": "fundo da sala 3 (800x600)",
    "cenario/fundo_sala4": "fundo da sala 4 (800x600)", "cenario/fundo_sala5": "fundo da sala 5 (mini-boss)",
    "cenario/fundo_sala6": "fundo da sala 6 (parkour)",
    "ui/barra_vida_fundo": "fundo da barra de vida (esticado; largura = vida maxima x 12px, altura 20)",
    "ui/barra_vida_cheia": "parte cheia da barra de vida (esticada e recortada pela vida atual)",
    "ui/menu_fundo": "fundo do menu (800x600)", "ui/game_over_fundo": "fundo da tela de game over (800x600)",
}

SPRITES_ESPERADOS = {}      # nome -> True se encontrou arquivo, False se nao
_cache_img = {}
_cache_frames = {}
_cache_deriv = {}


def _agora():
    return pygame.time.get_ticks() / 1000


def carregar_imagem(rel, tamanho=None):
    """Carrega assets/<rel>. Devolve None se o arquivo nao existir."""
    chave = (rel, tamanho)
    if chave in _cache_img:
        return _cache_img[chave]
    img = None
    caminho = os.path.join(PASTA_ASSETS, rel)
    if os.path.isfile(caminho):
        try:
            img = pygame.image.load(caminho)
            if pygame.display.get_surface():
                img = img.convert_alpha()
            if tamanho:
                img = pygame.transform.scale(img, tamanho)
        except pygame.error:
            img = None
    _cache_img[chave] = img
    return img


def carregar_frames(nome, tamanho=None):
    """nome_0.png, nome_1.png, ... (animacao)  ou  nome.png (imagem unica)."""
    chave = (nome, tamanho)
    if chave in _cache_frames:
        return _cache_frames[chave]
    frames, i = [], 0
    while True:
        img = carregar_imagem(f"{nome}_{i}.png", tamanho)
        if img is None:
            break
        frames.append(img)
        i += 1
    if not frames:
        img = carregar_imagem(f"{nome}.png", tamanho)
        if img is not None:
            frames.append(img)
    SPRITES_ESPERADOS[nome] = bool(frames)
    _cache_frames[chave] = frames
    return frames


def _derivada(tipo, img, extra, fn):
    """Cache de versoes derivadas (espelhada, branca, redimensionada)."""
    chave = (tipo, id(img), extra)
    r = _cache_deriv.get(chave)
    if r is None:
        r = fn(img)
        _cache_deriv[chave] = r
    return r


def _flash(img):
    f = img.copy()
    f.fill((110, 110, 110, 0), special_flags=pygame.BLEND_RGB_ADD)
    return f


class Animacao:
    """Uma sequencia de quadros (uma pasta/nome). Se nao houver arquivo, .existe = False."""

    def __init__(self, nome, tamanho=None, fps=FPS_ANIM_PADRAO, loop=True, duracao=None):
        self.nome = nome
        self.frames = carregar_frames(nome, tamanho)
        if duracao and self.frames:
            fps = len(self.frames) / duracao      # encaixa todos os quadros na duracao
        self.fps, self.loop = fps, loop
        self.inicio = _agora()

    @property
    def existe(self):
        return bool(self.frames)

    def reiniciar(self):
        self.inicio = _agora()

    def frame(self):
        if not self.frames:
            return None
        i = int((_agora() - self.inicio) * self.fps)
        return self.frames[i % len(self.frames)] if self.loop else self.frames[min(i, len(self.frames) - 1)]


def desenhar_sprite(tela, img, alvo, modo="baixo", flip=False, offset=(0, 0), flash=False):
    """Desenha 'img' em relacao ao Rect 'alvo' (ja em coordenadas de tela)."""
    if flip:
        img = _derivada("flip", img, None, lambda i: pygame.transform.flip(i, True, False))
    if flash:
        img = _derivada("flash", img, None, _flash)
    if modo == "esticar":
        tam = tuple(alvo.size)
        img = _derivada("esc", img, tam, lambda i: pygame.transform.scale(i, tam))
        pos = alvo.topleft
    elif modo == "centro":
        pos = img.get_rect(center=alvo.center).topleft
    else:
        pos = img.get_rect(midbottom=alvo.midbottom).topleft
    tela.blit(img, (pos[0] + offset[0], pos[1] + offset[1]))


class Animador:
    """Um conjunto de animacoes (uma por estado) de uma entidade.
    estados = {"idle": {}, "ataque": {"duracao": 0.15, "loop": False}, ...}"""

    def __init__(self, pasta, estados, tamanho=None, offset=(0, 0), modo="baixo", fallback=None):
        self.anims = {est: Animacao(f"{pasta}/{est}", tamanho, **cfg) for est, cfg in estados.items()}
        self.offset, self.modo = offset, modo
        self.fallback = fallback or {}
        self.pedido = None

    def _resolver(self, estado):
        vistos = set()
        while estado and estado not in vistos:
            a = self.anims.get(estado)
            if a and a.existe:
                return a
            vistos.add(estado)
            estado = self.fallback.get(estado, "idle" if estado != "idle" else None)
        return None

    def resetar(self):
        self.pedido = None

    def desenhar(self, tela, estado, alvo, flip=False, flash=False):
        """Devolve False se nao ha sprite pra esse estado (a classe desenha o retangulo)."""
        anim = self._resolver(estado)
        if anim is None:
            return False
        if estado != self.pedido:
            self.pedido = estado
            anim.reiniciar()
        desenhar_sprite(tela, anim.frame(), alvo, self.modo, flip, self.offset, flash)
        return True


def desenhar_centro(tela, anim, rect):
    """Objetos simples (item, projetil, lamparina): sprite centralizado no rect."""
    img = anim.frame()
    if img is None:
        return False
    tela.blit(img, img.get_rect(center=rect.center))
    return True


def desenhar_esticado(tela, anim, rect):
    """Sprite redimensionado pra ocupar o rect inteiro."""
    img = anim.frame()
    if img is None:
        return False
    tam = tuple(rect.size)
    tela.blit(_derivada("esc", img, tam, lambda i: pygame.transform.scale(i, tam)), rect.topleft)
    return True


def desenhar_fundo(tela, img, cor, camera_x=0, largura_sala=None):
    """Fundo da sala. Se a imagem for mais larga que a tela, rola junto com a camera."""
    tela.fill(cor)
    if img is None:
        return
    largura_sala = largura_sala or LARGURA_TELA
    extra = img.get_width() - LARGURA_TELA
    prog = camera_x / (largura_sala - LARGURA_TELA) if largura_sala > LARGURA_TELA else 0
    tela.blit(img, (-int(extra * prog) if extra > 0 else 0, 0))


_hud_anims = {}


def _hud_anim(nome):
    if nome not in _hud_anims:
        _hud_anims[nome] = Animacao(f"ui/{nome}")
    return _hud_anims[nome]


def preparar_assets():
    """Cria as pastas em assets/ e escreve assets/SPRITES_FALTANDO.txt."""
    for n in ("barra_vida_fundo", "barra_vida_cheia"):
        _hud_anim(n)
    gerar_tile_pedra(0, 0)
    carregar_frames("cenario/plataforma")
    # registra TODOS os sprites conhecidos (as salas ainda nao foram criadas aqui),
    # senao a lista e as pastas saem incompletas
    for nome in DESCRICAO_SPRITES:
        carregar_frames(nome)
    total = len(SPRITES_ESPERADOS)
    achados = sum(1 for v in SPRITES_ESPERADOS.values() if v)
    try:
        for pasta in {os.path.dirname(n) for n in SPRITES_ESPERADOS}:
            os.makedirs(os.path.join(PASTA_ASSETS, pasta), exist_ok=True)
        linhas = ["SPRITES DO JOGO", "=" * 60,
                  "Cada item vira um arquivo PNG dentro da pasta assets/.",
                  "  animado : assets/<nome>_0.png, <nome>_1.png, <nome>_2.png ...",
                  "  unico   : assets/<nome>.png",
                  "Desenhe virado pra DIREITA. Ajuste tamanho/posicao em SPRITE_AJUSTE no codigo.",
                  f"Encontrados: {achados}/{total}", ""]
        for nome in sorted(SPRITES_ESPERADOS, key=lambda n: (os.path.dirname(n), n)):
            marca = "[OK]   " if SPRITES_ESPERADOS[nome] else "[FALTA]"
            desc = DESCRICAO_SPRITES.get(nome, "")
            linhas.append(f"{marca} {nome:<28} {desc}")
        with open(os.path.join(PASTA_ASSETS, "SPRITES_FALTANDO.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(linhas) + "\n")
    except OSError:
        pass
    if MOSTRAR_SPRITES_FALTANDO:
        print(f"[sprites] {achados}/{total} encontrados. O que falta: {os.path.join(PASTA_ASSETS, 'SPRITES_FALTANDO.txt')}")

# ============================================================
# game_state
# ============================================================
class EstadoJogo:
    def __init__(self):
        self.sala_atual = "sala1"
        self.veio_de = {}          # {"sala6": "sala3", ...} de onde voce chegou em cada sala
        self.chave_pequena = 0
        self.chave_grande = 0
        self.chave_labirinto = 0   # chave do bau escondido da sala 4 (abre a porta de cima)
        self.flags = {
            "sala3_limpa": False,
            "sala4_bau_pego": False,
            "sala4_bau_secreto": False,
            "sala5_miniboss_derrotado": False,
        }

# ============================================================
# visual_helpers
# ============================================================
TAMANHO_TILE = 100
_tiles_pedra = {}


def gerar_tile_pedra(tile_x, tile_y, cor1=(35, 38, 52), cor2=(28, 30, 44),
                      cor_rachadura=(10, 11, 18), seed_base=42):
    chave = (tile_x, tile_y, cor1, cor2)
    if chave in _tiles_pedra:
        return _tiles_pedra[chave]

    # >>> SPRITE AQUI: tile de pedra 100x100 -> assets/cenario/pedra_0.png, pedra_1.png ...
    # (com varios arquivos ele alterna entre eles; sem arquivo usa a pedra desenhada por codigo)
    variantes = carregar_frames("cenario/pedra", (TAMANHO_TILE, TAMANHO_TILE))
    if variantes:
        return variantes[(tile_x * 7 + tile_y * 13) % len(variantes)]

    surf = pygame.Surface((TAMANHO_TILE, TAMANHO_TILE))
    rng = random.Random((tile_x * 92821) ^ (tile_y * 68917) ^ seed_base)
    cor_base = cor1 if (tile_x + tile_y) % 2 == 0 else cor2
    surf.fill(cor_base)
    pygame.draw.rect(surf, cor_rachadura, surf.get_rect(), width=2)

    for _ in range(rng.randint(1, 3)):
        x1 = rng.randint(10, TAMANHO_TILE - 10)
        y1 = rng.randint(10, TAMANHO_TILE - 10)
        pontos = [(x1, y1)]
        for _ in range(rng.randint(2, 4)):
            x1 += rng.randint(-15, 15)
            y1 += rng.randint(-15, 15)
            pontos.append((x1, y1))
        if len(pontos) > 1:
            pygame.draw.lines(surf, cor_rachadura, False, pontos, 1)

    _tiles_pedra[chave] = surf
    return surf


def desenhar_bloco_pedra(tela, rect, camera_x, camera_y=0):
    """Preenche um retangulo do mundo com tiles de pedra (recortado no rect)."""
    r = rect.move(-camera_x, -camera_y)
    tela.set_clip(r.clip(tela.get_rect()))
    for ty in range(rect.top // TAMANHO_TILE, (rect.bottom - 1) // TAMANHO_TILE + 1):
        for tx in range(rect.left // TAMANHO_TILE, (rect.right - 1) // TAMANHO_TILE + 1):
            tela.blit(gerar_tile_pedra(tx, ty), (tx * TAMANHO_TILE - camera_x, ty * TAMANHO_TILE - camera_y))
    tela.set_clip(None)


def desenhar_plataforma_fina(tela, rect, camera_x, camera_y=0):
    r = rect.move(-camera_x, -camera_y)
    # >>> SPRITE AQUI: plataforma fina -> assets/cenario/plataforma.png (esticada no tamanho dela)
    fr = carregar_frames("cenario/plataforma")
    if fr:
        tela.blit(_derivada("esc", fr[0], tuple(r.size), lambda i: pygame.transform.scale(i, r.size)), r.topleft)
        return
    pygame.draw.rect(tela, (60, 62, 80), r)
    pygame.draw.rect(tela, (90, 95, 120), r, width=2)


def criar_vinheta(largura_tela, altura_tela, forca=180):
    surf = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
    max_dist = math.hypot(largura_tela / 2, altura_tela / 2)
    passo = 6
    for bx in range(0, largura_tela, passo):
        for by in range(0, altura_tela, passo):
            cx, cy = bx - largura_tela / 2, by - altura_tela / 2
            dist = math.hypot(cx, cy) / max_dist
            alpha = int(max(0, (dist - 0.4)) * forca)
            pygame.draw.rect(surf, (0, 0, 0, min(alpha, forca)), (bx, by, passo, passo))
    return surf


def criar_particulas_neblina(qtd, largura_mundo, altura_max, cor=(120, 140, 180)):
    particulas = []
    for _ in range(qtd):
        particulas.append({
            "x": random.uniform(0, largura_mundo),
            "y": random.uniform(0, altura_max),
            "raio": random.uniform(25, 80),
            "vel": random.uniform(0.1, 0.4),
            "alpha": random.randint(10, 28),
            "cor": cor,
        })
    return particulas


def desenhar_neblina(tela, particulas, largura_mundo, largura_tela, altura_tela, camera_x, camera_y=0):
    for p in particulas:
        p["x"] += p["vel"]
        if p["x"] - p["raio"] > largura_mundo:
            p["x"] = -p["raio"]
        x, y = p["x"] - camera_x, p["y"] - camera_y
        if -p["raio"] < x < largura_tela + p["raio"] and -p["raio"] < y < altura_tela + p["raio"]:
            surf = pygame.Surface((int(p["raio"] * 2), int(p["raio"] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*p["cor"], p["alpha"]), (p["raio"], p["raio"]), p["raio"])
            tela.blit(surf, (x - p["raio"], y - p["raio"]))


def desenhar_moldura_rabiscada(tela, rect, cor, seed=1, amplitude=3, passo=14, largura=3):
    rng = random.Random(seed)

    def gerar_pontos(p1, p2):
        x1, y1 = p1
        x2, y2 = p2
        dist = math.hypot(x2 - x1, y2 - y1)
        passos = max(2, int(dist // passo))
        pontos = []
        for i in range(passos + 1):
            t = i / passos
            bx, by = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
            if 0 < i < passos:
                if x1 == x2:
                    bx += rng.randint(-amplitude, amplitude)
                else:
                    by += rng.randint(-amplitude, amplitude)
            pontos.append((bx, by))
        return pontos

    cantos = [(rect.left, rect.top), (rect.right, rect.top),
              (rect.right, rect.bottom), (rect.left, rect.bottom)]
    for i in range(4):
        pygame.draw.lines(tela, cor, False, gerar_pontos(cantos[i], cantos[(i + 1) % 4]), largura)


def desenhar_sparkle(tela, x, y, tamanho, alpha, cor=(255, 255, 255)):
    surf = pygame.Surface((tamanho * 2 + 4, tamanho * 2 + 4), pygame.SRCALPHA)
    c = (*cor, max(0, min(255, int(alpha))))
    meio = tamanho + 2
    pygame.draw.line(surf, c, (2, meio), (tamanho * 2 + 2, meio), 2)
    pygame.draw.line(surf, c, (meio, 2), (meio, tamanho * 2 + 2), 2)
    tela.blit(surf, (x - meio, y - meio), special_flags=pygame.BLEND_RGBA_ADD)


def desenhar_hud(tela, jogador, estado_jogo, fonte):
    """HUD: barra de vida unica. Cada ponto de vida = PX_POR_VIDA pixels."""
    largura = jogador.vida_max * PX_POR_VIDA
    x, y, altura = 20, 16, 20
    fundo = pygame.Rect(x, y, largura, altura)
    vida = max(0, jogador.vida)
    cheia = pygame.Rect(x, y, int(largura * vida / jogador.vida_max), altura)

    # >>> SPRITE AQUI: HUD -> assets/ui/barra_vida_fundo.png e barra_vida_cheia.png
    if not desenhar_esticado(tela, _hud_anim("barra_vida_fundo"), fundo):
        pygame.draw.rect(tela, (34, 10, 14), fundo, border_radius=4)
    img = _hud_anim("barra_vida_cheia").frame()
    if img:
        tam = (largura, altura)
        img = _derivada("esc", img, tam, lambda i: pygame.transform.scale(i, tam))
        tela.set_clip(cheia)
        tela.blit(img, (x, y))
        tela.set_clip(None)
    elif cheia.width > 0:
        pygame.draw.rect(tela, (205, 45, 55), cheia, border_radius=4)
        pygame.draw.rect(tela, (240, 110, 115), (cheia.x + 2, cheia.y + 2, max(0, cheia.width - 4), 4),
                         border_radius=2)
    pygame.draw.rect(tela, (235, 235, 240), fundo, width=2, border_radius=4)

    txt = fonte.render(f"{vida}/{jogador.vida_max}", True, (255, 255, 255))
    sombra = fonte.render(f"{vida}/{jogador.vida_max}", True, (20, 10, 10))
    pos = txt.get_rect(center=fundo.center)
    tela.blit(sombra, pos.move(1, 1))
    tela.blit(txt, pos)

    y_extra = 48
    if estado_jogo.chave_pequena > 0:
        txt = fonte.render(f"Chaves: {estado_jogo.chave_pequena}", True, (230, 230, 235))
        tela.blit(txt, (30, y_extra))
        y_extra += 22
    if estado_jogo.chave_labirinto > 0:
        txt3 = fonte.render("Chave do labirinto", True, (200, 150, 230))
        tela.blit(txt3, (30, y_extra))
        y_extra += 22
    if estado_jogo.chave_grande > 0:
        txt2 = fonte.render(f"Chave grande: {estado_jogo.chave_grande}", True, (230, 190, 120))
        tela.blit(txt2, (30, y_extra))


def mover_com_colisao(ent, dx, dy, obstaculos):
    """Move uma entidade (x, y, largura, altura, rect) eixo por eixo,
    parando nos obstaculos. Usado no top-down por jogador e inimigos."""
    ent.x += dx
    r = ent.rect
    for o in obstaculos:
        if r.colliderect(o):
            if dx > 0:
                ent.x = o.left - ent.largura
            elif dx < 0:
                ent.x = o.right
            r = ent.rect
    ent.y += dy
    r = ent.rect
    for o in obstaculos:
        if r.colliderect(o):
            if dy > 0:
                ent.y = o.top - ent.altura
            elif dy < 0:
                ent.y = o.bottom
            r = ent.rect

_FONTE_FX = {}

_luzes = {}


def criar_luz(raio, intensidade=255, cor=(255, 255, 255)):
    """Mancha de luz redonda (centro forte, borda suave). Cache por (raio, intensidade, cor)."""
    raio = max(2, int(raio))
    chave = (raio, intensidade, cor)
    if chave not in _luzes:
        surf = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
        for r in range(raio, 0, -1):
            a = int(intensidade * (1 - r / raio) ** 0.6)
            pygame.draw.circle(surf, (*cor, a), (raio, raio), r)
        _luzes[chave] = surf
    return _luzes[chave]


def aplicar_escuridao(tela, luzes, alpha=250):
    """Escurece a tela inteira e 'fura' a escuridao onde tem luz.
    luzes = [(x, y, raio, intensidade 0-255), ...] em coordenadas de tela."""
    esc = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
    esc.fill((0, 0, 0, alpha))
    for x, y, raio, intens in luzes:
        raio = int(raio)
        if raio < 2 or intens <= 0:
            continue
        esc.blit(criar_luz(raio, int(intens)), (int(x) - raio, int(y) - raio), special_flags=pygame.BLEND_RGBA_SUB)
    tela.blit(esc, (0, 0))


class TextosFlutuantes:
    """Textos que sobem e somem (+VIDA, +DANO, CHAVE!...)."""

    def __init__(self, tamanho=38):
        self.fonte = pygame.font.Font(None, tamanho)
        self.itens = []

    def adicionar(self, txt, x, y, cor=(255, 255, 255), atraso=0.0):
        self.itens.append({"txt": txt, "x": x, "y": y, "cor": cor, "t0": _agora() + atraso})

    def desenhar(self, tela, cam_x=0, cam_y=0):
        agora = _agora()
        self.itens = [t for t in self.itens if agora - t["t0"] < 1.6]
        for t in self.itens:
            k = agora - t["t0"]
            if k < 0:
                continue
            img = self.fonte.render(t["txt"], True, t["cor"])
            sombra = self.fonte.render(t["txt"], True, (15, 8, 15))
            alpha = int(255 * min(1.0, (1.6 - k) / 0.6))
            img.set_alpha(alpha)
            sombra.set_alpha(alpha)
            pos = img.get_rect(center=(int(t["x"] - cam_x), int(t["y"] - k * 40 - cam_y)))
            tela.blit(sombra, pos.move(2, 2))
            tela.blit(img, pos)

# ============================================================
# player
# ============================================================
class Jogador:
    """O cavaleiro. Dois modos de movimento: 'plataforma' 
    e 'topdown'. A sala decide qual chamar por frame."""

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.largura, self.altura = 34, 54

        self.vel_x = 0
        self.vel_y = 0
        self.no_chao = False
        self.olhando_direita = True
        self.face = (1, 0)          # direcao que o cavaleiro olha (usada no top-down)

        self.vida = 60
        self.vida_max = 60
        self.dano_bonus = 0         # +dano (bau secreto da sala 4)
        self.invencivel_timer = 0

        # feel do pulo
        self.coyote = 0
        self.buffer_pulo = 0
        self.pulando = False
        self._apoio = None
        self.ultimo_seguro = (x, y)  # pra voltar depois de cair em espinhos

        # knockback
        self.knock_timer = 0
        self.knock = (0, 0)
        self.knock_novo = False

        # ataque
        self.atacando_timer = 0
        self.cooldown_ataque_timer = 0
        self.hitbox_ataque = None
        self.dir_ataque = "dir"     # "dir" | "esq" | "cima" | "baixo"
        self.pogo_usado = False     # so 1 pogo por golpe
        self.acertados = set()      # ids de inimigos ja acertados neste golpe

        # parry
        self.parryados = set()      # ids de ataques ja aparados neste golpe
        self.parry_fx = []          # efeitos visuais de parry em andamento
        self.parry_pose = 0         # tempo restante da pose de parry (sprite)
        self.parrys = 0             # quantos parrys o jogador ja deu (pode virar contador/conquista)

        # ---- sprites ----
        self.modo = "plataforma"    # "plataforma" | "topdown" (definido pelos metodos de movimento)
        self.correndo = False
        self.movendo = False
        # >>> SPRITE AQUI (JOGADOR): PNGs em assets/jogador/  (lista completa em assets/SPRITES_FALTANDO.txt)
        #   plataforma: idle, andar, correr, pulo, queda, dano, ataque_frente, ataque_cima, ataque_baixo
        #   top-down:   td_idle_/td_andar_/td_ataque_ + lado, cima, baixo
        _atq = {"duracao": DURACAO_ATAQUE, "loop": False}
        self.animador = Animador("jogador", {
            "idle": {}, "andar": {}, "correr": {"fps": 14}, "pulo": {"loop": False}, "queda": {},
            "dano": {"loop": False}, "parry": {"duracao": 0.25, "loop": False},
            "ataque_frente": _atq, "ataque_cima": _atq, "ataque_baixo": _atq,
            "td_idle_lado": {}, "td_idle_cima": {}, "td_idle_baixo": {},
            "td_andar_lado": {}, "td_andar_cima": {}, "td_andar_baixo": {},
            "td_ataque_lado": _atq, "td_ataque_cima": _atq, "td_ataque_baixo": _atq,
        }, fallback=FALLBACK_ANIM_JOGADOR, **SPRITE_AJUSTE["jogador"])
        # >>> SPRITE AQUI (EFEITO DO GOLPE): assets/efeitos/golpe_frente, golpe_cima, golpe_baixo
        self.efeito_golpe = Animador("efeitos", {"golpe_frente": _atq, "golpe_cima": _atq, "golpe_baixo": _atq},
                                     modo="esticar")

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.largura, self.altura)

    @property
    def dano_ataque(self):
        return DANO_ESPADA + self.dano_bonus

    # ---------------- vida ----------------
    def receber_dano(self, dano, origem=None):
        """origem = (x, y) de onde veio o golpe (gera knockback)."""
        if self.invencivel_timer > 0:
            return False
        self.vida = max(0, self.vida - dano)
        self.invencivel_timer = TEMPO_INVENCIVEL
        if origem is not None:
            cx, cy = self.x + self.largura / 2, self.y + self.altura / 2
            dx, dy = cx - origem[0], cy - origem[1]
            d = math.hypot(dx, dy) or 1
            self.knock = (dx / d, dy / d)
            self.knock_timer = 0.18
            self.knock_novo = True
        hitstop(0.07)
        tremer(0.25, 5)
        return True

    def curar(self, quantidade):
        self.vida = min(self.vida_max, self.vida + quantidade)

    def atualizar_timers(self, dt):
        for nome in ("invencivel_timer", "cooldown_ataque_timer", "knock_timer", "coyote", "buffer_pulo", "parry_pose"):
            v = getattr(self, nome)
            if v > 0:
                setattr(self, nome, v - dt)
        if self.atacando_timer > 0:
            self.atacando_timer -= dt
            self.hitbox_ataque = self._calc_hitbox()   # o golpe acompanha o jogador
        else:
            self.hitbox_ataque = None

    # ---------------- parry ----------------
    @property
    def parry_ativo(self):
        """True nos primeiros JANELA_PARRY segundos do golpe."""
        return self.atacando_timer > 0 and (DURACAO_ATAQUE - self.atacando_timer) <= JANELA_PARRY

    def aparar(self, atacante):
        """PARRY POR ATAQUE: chamado pelas salas pra cada inimigo/projetil, DEPOIS dele
        se mover e ANTES de ele causar dano. Se a espada (na janela do parry) encostar
        num ataque 'parryavel', o golpe e anulado. Devolve True se aparou.
        O atacante precisa ter: .parryavel, .rect e .ser_aparado(jogador)."""
        hb = self.hitbox_ataque
        if not (hb and self.parry_ativo and getattr(atacante, "parryavel", False)):
            return False
        if id(atacante) in self.parryados or not hb.colliderect(atacante.rect):
            return False
        self.parryados.add(id(atacante))
        atacante.ser_aparado(self)
        self.invencivel_timer = max(self.invencivel_timer, INVENCIVEL_PARRY)
        self.cooldown_ataque_timer = min(self.cooldown_ataque_timer, 0.08)   # libera o contra-ataque
        self.parry_pose = 0.25
        self.parrys += 1
        cx, cy = atacante.rect.center
        # >>> SPRITE AQUI: brilho do parry (assets/efeitos/parry_N.png, toca 1 vez)
        self.parry_fx.append({"x": cx, "y": cy, "t0": _agora(),
                              "anim": Animacao("efeitos/parry", loop=False, duracao=0.4)})
        hitstop(0.14)
        tremer(0.2, 5)
        return True

    def _desenhar_parry_fx(self, tela, camera_x, camera_y):
        agora = _agora()
        self.parry_fx = [f for f in self.parry_fx if agora - f["t0"] < 0.4]
        for f in self.parry_fx:
            px, py = int(f["x"] - camera_x), int(f["y"] - camera_y)
            if desenhar_centro(tela, f["anim"], pygame.Rect(px - 1, py - 1, 2, 2)):
                continue
            k = (agora - f["t0"]) / 0.4                       # 0 -> 1
            raio = int(12 + 46 * k)
            cor = (255, 240, 170)
            pygame.draw.circle(tela, cor, (px, py), raio, max(1, int(5 * (1 - k))))
            for i in range(8):                               # faiscas
                a = i * math.pi / 4 + 0.4
                p1 = (px + math.cos(a) * raio * 0.6, py + math.sin(a) * raio * 0.6)
                p2 = (px + math.cos(a) * raio * 1.2, py + math.sin(a) * raio * 1.2)
                pygame.draw.line(tela, cor, p1, p2, 2)
            if "fonte" not in _FONTE_FX:
                _FONTE_FX["fonte"] = pygame.font.Font(None, 30)
            txt = _FONTE_FX["fonte"].render("PARRY!", True, cor)
            tela.blit(txt, txt.get_rect(center=(px, py - raio - 14)))

    # ---------------- ataque ----------------
    def _calc_hitbox(self):
        x, y, w, h = int(self.x), int(self.y), self.largura, self.altura
        a = ALCANCE_ESPADA
        d = self.dir_ataque
        if d == "dir":
            return pygame.Rect(x + w, y + 10, a, h - 20)
        if d == "esq":
            return pygame.Rect(x - a, y + 10, a, h - 20)
        if d == "cima":
            return pygame.Rect(x - 8, y - a, w + 16, a)
        return pygame.Rect(x - 8, y + h, w + 16, a)

    def tentar_atacar(self, teclas=None, topdown=False):
        """Q. Plataforma: CIMA+Q ataca pra cima, BAIXO+Q no ar ataca pra baixo
        (pogo). Top-down: ataca pra onde o cavaleiro esta olhando."""
        if self.cooldown_ataque_timer > 0:
            return False
        if topdown:
            fx, fy = self.face
            if fx > 0:
                d = "dir"
            elif fx < 0:
                d = "esq"
            elif fy < 0:
                d = "cima"
            else:
                d = "baixo"
        else:
            d = "dir" if self.olhando_direita else "esq"
            if teclas is not None:
                if teclas[pygame.K_UP] or teclas[pygame.K_w]:
                    d = "cima"
                elif (teclas[pygame.K_DOWN] or teclas[pygame.K_s]) and not self.no_chao:
                    d = "baixo"
        self.dir_ataque = d
        self.atacando_timer = DURACAO_ATAQUE
        self.cooldown_ataque_timer = COOLDOWN_ATAQUE
        self.pogo_usado = False
        self.acertados = set()
        self.parryados = set()
        self.animador.resetar()       # reinicia a animacao de ataque
        self.efeito_golpe.resetar()
        self.hitbox_ataque = self._calc_hitbox()
        return True

    # ---------------- plataforma ----------------
    def atualizar_plataforma(self, teclas, colisores, dt=1 / 60):
        self.modo = "plataforma"
        self.correndo = False
        if self.knock_novo:
            self.vel_y = -7
            self.knock_novo = False
            self.pulando = False

        if self.knock_timer > 0:
            self.vel_x = 6 if self.knock[0] >= 0 else -6
        else:
            self.vel_x = 0
            correndo = any(teclas[t] for t in TECLA_CORRER)
            self.correndo = correndo
            vel_h = VEL_CORRIDA if correndo else VEL_HORIZONTAL
            if teclas[pygame.K_LEFT] or teclas[pygame.K_a]:
                self.vel_x = -vel_h
                self.olhando_direita = False
                self.face = (-1, 0)
            if teclas[pygame.K_RIGHT] or teclas[pygame.K_d]:
                self.vel_x = vel_h
                self.olhando_direita = True
                self.face = (1, 0)

        self.x += self.vel_x
        for p in colisores:
            if self.rect.colliderect(p):
                if self.vel_x > 0:
                    self.x = p.left - self.largura
                elif self.vel_x < 0:
                    self.x = p.right

        self.vel_y = min(self.vel_y + GRAVIDADE, VEL_QUEDA_MAX)
        self.y += self.vel_y
        self.no_chao = False
        self._apoio = None
        for p in colisores:
            if self.rect.colliderect(p):
                if self.vel_y > 0:
                    self.y = p.top - self.altura
                    self.vel_y = 0
                    self.no_chao = True
                    self._apoio = p
                elif self.vel_y < 0:
                    self.y = p.bottom
                    self.vel_y = 0

        if self.no_chao:
            self.coyote = COYOTE
            self.pulando = False
            p = self._apoio
            # so guarda como "ponto seguro" se estiver bem no meio da plataforma
            if p and p.left + 10 <= self.x and self.x + self.largura <= p.right - 10:
                self.ultimo_seguro = (self.x, self.y)

        if self.buffer_pulo > 0 and self.coyote > 0:
            self._pular()

    def _pular(self):
        self.vel_y = FORCA_PULO
        self.no_chao = False
        self.coyote = 0
        self.buffer_pulo = 0
        self.pulando = True

    def pular(self):
        """Pulo imediato (usado por salas antigas, ex: sala 7)."""
        if self.no_chao or self.coyote > 0:
            self._pular()
            return True
        return False

    def pedir_pulo(self):
        self.buffer_pulo = BUFFER_PULO

    def soltar_pulo(self):
        if self.pulando and self.vel_y < 0:
            self.vel_y *= CORTE_PULO
        self.pulando = False

    def pogo(self):
        """Nail-bounce: ataque pra baixo acertou algo 'pogavel'."""
        self.vel_y = FORCA_POGO
        self.no_chao = False
        self.pulando = False
        self.coyote = 0
        self.pogo_usado = True
        hitstop(0.03)

    # ---------------- top-down ----------------
    def atualizar_topdown(self, teclas, obstaculos=()):
        self.modo = "topdown"
        self.movendo = False
        if self.knock_timer > 0:
            mover_com_colisao(self, self.knock[0] * 7, self.knock[1] * 7, obstaculos)
            return
        dx = dy = 0
        if teclas[pygame.K_LEFT] or teclas[pygame.K_a]:
            dx -= 1
        if teclas[pygame.K_RIGHT] or teclas[pygame.K_d]:
            dx += 1
        if teclas[pygame.K_UP] or teclas[pygame.K_w]:
            dy -= 1
        if teclas[pygame.K_DOWN] or teclas[pygame.K_s]:
            dy += 1
        if dx or dy:
            self.movendo = True
            correndo = any(teclas[t] for t in TECLA_CORRER)
            vel = VEL_TOPDOWN_CORRIDA if correndo else VEL_TOPDOWN
            n = math.hypot(dx, dy)          # diagonal nao fica mais rapida
            if dx:
                self.olhando_direita = dx > 0
                self.face = (1 if dx > 0 else -1, 0)
            else:
                self.face = (0, 1 if dy > 0 else -1)
            mover_com_colisao(self, vel * dx / n, vel * dy / n, obstaculos)

    # ---------------- sprite / desenho ----------------
    def _estado_anim(self):
        """Qual animacao tocar agora (nome do arquivo em assets/jogador/)."""
        if self.modo == "plataforma":
            if self.knock_timer > 0:
                return "dano"
            if self.parry_pose > 0:
                return "parry"
            if self.atacando_timer > 0:
                return {"dir": "ataque_frente", "esq": "ataque_frente",
                        "cima": "ataque_cima", "baixo": "ataque_baixo"}[self.dir_ataque]
            if not self.no_chao:
                return "pulo" if self.vel_y < 0 else "queda"
            if self.vel_x != 0:
                return "correr" if self.correndo else "andar"
            return "idle"
        # top-down
        if self.knock_timer > 0:
            return "dano"
        if self.parry_pose > 0:
            return "parry"
        if self.atacando_timer > 0:
            return "td_ataque_" + {"dir": "lado", "esq": "lado", "cima": "cima", "baixo": "baixo"}[self.dir_ataque]
        lado = "lado" if self.face[0] != 0 else ("cima" if self.face[1] < 0 else "baixo")
        return ("td_andar_" if self.movendo else "td_idle_") + lado

    def _flip_sprite(self, estado):
        """Os sprites sao desenhados virados pra DIREITA; espelha quando olha pra esquerda."""
        if estado == "parry":
            return self.dir_ataque == "esq"
        if self.modo == "plataforma":
            if estado == "ataque_frente":
                return self.dir_ataque == "esq"
            return not self.olhando_direita
        if estado.endswith("_lado"):
            if estado.startswith("td_ataque"):
                return self.dir_ataque == "esq"
            return self.face[0] < 0
        return (not self.olhando_direita) if estado == "dano" else False

    def desenhar(self, tela, camera_x, camera_y):
        r = pygame.Rect(int(self.x - camera_x), int(self.y - camera_y), self.largura, self.altura)
        estado = self._estado_anim()
        piscando = self.invencivel_timer > 0 and int(self.invencivel_timer * 20) % 2 == 0

        # >>> SPRITE AQUI: personagem (assets/jogador/<estado>_N.png)
        if not self.animador.desenhar(tela, estado, r, flip=self._flip_sprite(estado), flash=piscando):
            # sem sprite: retangulo provisorio
            cor = (255, 200, 200) if piscando else (255, 100, 100)
            pygame.draw.rect(tela, cor, r)
            fx, fy = self.face
            ex = r.centerx + fx * 9 - 3
            ey = r.top + 14 + (fy * 8 if fy else 0)
            pygame.draw.rect(tela, (30, 20, 30), (ex, ey, 6, 6))

        # >>> SPRITE AQUI: efeito do golpe (assets/efeitos/golpe_frente|cima|baixo_N.png)
        if self.hitbox_ataque:
            hb = self.hitbox_ataque.move(-camera_x, -camera_y)
            nome = {"dir": "golpe_frente", "esq": "golpe_frente",
                    "cima": "golpe_cima", "baixo": "golpe_baixo"}[self.dir_ataque]
            if not self.efeito_golpe.desenhar(tela, nome, hb, flip=(self.dir_ataque == "esq")):
                pygame.draw.rect(tela, (255, 255, 255), hb, width=2)
            if DEBUG["hitbox"]:
                pygame.draw.rect(tela, (255, 255, 0), hb, 1)
        if DEBUG["hitbox"]:
            pygame.draw.rect(tela, (0, 255, 0), r, 1)
        self._desenhar_parry_fx(tela, camera_x, camera_y) #SOCORROOOOOOOOOOOOOOOOOOOOOOO

# ============================================================
# entities
# ============================================================
class Inimigo:
    """Base pra qualquer inimigo com vida (com knockback)."""

    def __init__(self, x, y, largura, altura, vida, dano_contato, cor=(180, 180, 190)):
        self.x, self.y = x, y
        self.largura, self.altura = largura, altura
        self.vida = vida
        self.vida_max = vida
        self.dano_contato = dano_contato
        self.cor = cor
        self.vivo = True
        self.invencivel_timer = 0
        self.kx = self.ky = 0
        self.drop_feito = False
        self.olhando_direita = True
        self.atordoado_timer = 0     # >0 = atordoado (inofensivo e leva dano em dobro)

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.largura, self.altura)

    @property
    def perigoso(self):
        return self.vivo and self.atordoado_timer <= 0

    @property
    def parryavel(self):
        """True enquanto o inimigo esta no meio de um ATAQUE que o jogador pode aparar.
        Sobrescreva nos inimigos que tem ataque (peao, torre...)."""
        return False

    def ser_aparado(self, jogador):
        """Chamado quando o jogador apara o ataque. Padrao: atordoa e empurra."""
        self.atordoado_timer = TEMPO_ATORDOADO_PARRY
        self.empurrar(self.rect.centerx - jogador.rect.centerx,
                      self.rect.centery - jogador.rect.centery, 8)

    def receber_dano(self, dano):
        if self.invencivel_timer <= 0:
            if self.atordoado_timer > 0:
                dano *= MULT_DANO_ATORDOADO      # atordoado (parry) leva dano em dobro
            self.vida -= dano
            self.invencivel_timer = 0.15
            if self.vida <= 0:
                self.vivo = False
            return True
        return False

    def empurrar(self, dx, dy, forca):
        d = math.hypot(dx, dy) or 1
        self.kx, self.ky = dx / d * forca, dy / d * forca

    def aplicar_knock(self, obstaculos=()):
        """Retorna True enquanto o inimigo esta sendo empurrado."""
        if abs(self.kx) + abs(self.ky) > 0.3:
            mover_com_colisao(self, self.kx, self.ky, obstaculos)
            self.kx *= 0.82
            self.ky *= 0.82
            return True
        self.kx = self.ky = 0
        return False

    def atualizar_timers(self, dt):
        if self.invencivel_timer > 0:
            self.invencivel_timer -= dt
        if self.atordoado_timer > 0:
            self.atordoado_timer -= dt

    def desenhar_sprite(self, tela, camera_x, camera_y, estado="idle", flip=False):
        """Tenta desenhar o sprite (self.animador). Devolve False se nao tiver -
        ai a classe desenha o retangulo provisorio."""
        animador = getattr(self, "animador", None)
        if animador is None:
            return False
        r = self.rect.move(-camera_x, -camera_y)
        ok = animador.desenhar(tela, estado, r, flip=flip, flash=self.invencivel_timer > 0)
        if ok and DEBUG["hitbox"]:
            pygame.draw.rect(tela, (0, 255, 0), r, 1)
        return ok

    def desenhar_barra_vida(self, tela, camera_x, camera_y):
        x, y = self.x - camera_x, self.y - camera_y - 10
        pct = max(0, self.vida / self.vida_max)
        pygame.draw.rect(tela, (40, 10, 10), (x, y, self.largura, 5))
        pygame.draw.rect(tela, (200, 40, 40), (x, y, self.largura * pct, 5))


# ---------------- inimigos top-down ----------------
class Peao(Inimigo):
    """Guarda do castelo (sala 3). Gira em volta do jogador a uma distancia
    fixa (orbita). A sala libera UM peao por vez pra atacar: ele pisca (aviso),
    investe em linha reta, e depois fica parado um instante (hora de bater)
    antes de voltar pra roda. Estado "dormindo" = so enfeite (sala 3, na volta)."""
 
    RAIO_ORBITA = 170
    VEL_ORBITA = 3.6        # velocidade pra alcancar o ponto da roda
    VEL_ANGULAR = 1.1       # rad/s - quao rapido gira em volta (negativo = outro sentido)
    TEMPO_AVISO = 0.55
    VEL_INVESTIDA = 10
    TEMPO_INVESTIDA = 0.4
    TEMPO_DESCANSO = 0.9
 
    def __init__(self, x, y):
        super().__init__(x, y, 36, 46, vida=random.randint(5, 7), dano_contato=4, cor=(210, 210, 220))
        self.estado = "orbitar"   # orbitar | aviso | investida | descanso | dormindo
        self.timer = 0
        self.ang = None
        self.dir_invest = (0, 0)
        # >>> SPRITE AQUI (PEAO): assets/peao/idle, andar, aviso, investida, descanso, dormindo
        self.animador = Animador("peao", {"idle": {}, "andar": {}, "aviso": {}, "investida": {}, "descanso": {},
                                          "dormindo": {}},
                                 fallback={"aviso": "andar", "investida": "aviso", "descanso": "idle",
                                           "dormindo": "descanso"},
                                 **SPRITE_AJUSTE["peao"])
 
    @property
    def atacando(self):
        return self.estado in ("aviso", "investida")
 
    @property
    def parryavel(self):
        return self.vivo and self.estado == "investida"      # so a investida pode ser aparada
 
    def ser_aparado(self, jogador):
        super().ser_aparado(jogador)
        self.estado, self.timer = "descanso", TEMPO_ATORDOADO_PARRY   # fica tonto (sprite peao/descanso)
 
    def pedir_ataque(self):
        if self.vivo and self.estado == "orbitar":
            self.estado, self.timer = "aviso", self.TEMPO_AVISO
            return True
        return False
 
    def atualizar(self, jogador, dt, obstaculos=(), projeteis=None):
        if not self.vivo or self.estado == "dormindo":
            return
        self.atualizar_timers(dt)
        jx, jy = jogador.rect.center
        cx, cy = self.rect.center
        self.olhando_direita = jx > cx
 
        if self.aplicar_knock(obstaculos):     # levou golpe: cancela o ataque
            if self.atacando:
                self.estado = "orbitar"
            self.ang = None
            return
        if self.ang is None:
            self.ang = math.atan2(cy - jy, cx - jx)
 
        if self.estado == "orbitar":
            self.ang += self.VEL_ANGULAR * dt
            tx = min(max(jx + math.cos(self.ang) * self.RAIO_ORBITA, 50), LARGURA_TELA - 50)
            ty = min(max(jy + math.sin(self.ang) * self.RAIO_ORBITA, 50), ALTURA_TELA - 50)
            dx, dy = tx - cx, ty - cy
            d = max(1, math.hypot(dx, dy))
            passo = min(self.VEL_ORBITA, d)
            mover_com_colisao(self, dx / d * passo, dy / d * passo, obstaculos)
 
        elif self.estado == "aviso":
            self.timer -= dt
            if self.timer <= 0:
                dx, dy = jx - cx, jy - cy
                d = max(1, math.hypot(dx, dy))
                self.dir_invest = (dx / d, dy / d)
                self.estado, self.timer = "investida", self.TEMPO_INVESTIDA
 
        elif self.estado == "investida":
            self.timer -= dt
            mover_com_colisao(self, self.dir_invest[0] * self.VEL_INVESTIDA,
                              self.dir_invest[1] * self.VEL_INVESTIDA, obstaculos)
            if self.timer <= 0:
                self.estado, self.timer = "descanso", self.TEMPO_DESCANSO
 
        elif self.estado == "descanso":
            self.timer -= dt
            if self.timer <= 0:
                self.estado = "orbitar"
                self.ang = None
 
    def desenhar_barra_vida(self, tela, camera_x, camera_y):
        if self.estado != "dormindo":          # dorminhoco nao mostra barra de vida
            super().desenhar_barra_vida(tela, camera_x, camera_y)
 
    def desenhar(self, tela, camera_x, camera_y):
        if not self.vivo:
            return
        r = self.rect.move(-camera_x, -camera_y)
        # >>> SPRITE AQUI: peao (assets/peao/...)
        est_anim = {"orbitar": "andar"}.get(self.estado, self.estado)
        if self.desenhar_sprite(tela, camera_x, camera_y, est_anim, flip=not self.olhando_direita):
            if self.estado == "aviso":            # "!" continua (feedback de gameplay)
                pygame.draw.rect(tela, (255, 120, 80), (r.centerx - 2, r.top - 42, 5, 16))
                pygame.draw.rect(tela, (255, 120, 80), (r.centerx - 2, r.top - 22, 5, 5))
            self.desenhar_barra_vida(tela, camera_x, camera_y)
            return
        cor = self.cor
        if self.invencivel_timer > 0:
            cor = (255, 255, 255)
        elif self.estado == "aviso" and int(self.timer * 16) % 2 == 0:
            cor = (255, 150, 90)              # piscando: vai atacar!
        elif self.estado == "dormindo":
            cor = (105, 105, 135)             # escuro: dormindo
        elif self.estado == "descanso":
            cor = (150, 150, 175)             # cansado
        pygame.draw.rect(tela, cor, r, border_radius=6)
        pygame.draw.circle(tela, cor, (r.centerx, r.top), 12)
        if self.estado == "aviso":            # "!" em cima da cabeca
            pygame.draw.rect(tela, (255, 120, 80), (r.centerx - 2, r.top - 42, 5, 16))
            pygame.draw.rect(tela, (255, 120, 80), (r.centerx - 2, r.top - 22, 5, 5))
        self.desenhar_barra_vida(tela, camera_x, camera_y)

class Projetil:
    """Bolinha disparada pelo bispo (tipo as lagrimas inimigas do Isaac)."""

    def __init__(self, x, y, vx, vy, dano=2, dono=None):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.raio = 7
        self.dano = dano
        self.vivo = True
        self.dono = dono            # quem atirou (pra devolver o projetil no parry)
        self.refletido = False      # True = agora machuca INIMIGOS, nao o jogador
        # >>> SPRITE AQUI: assets/efeitos/projetil.png (bolinha do bispo, ~14x14)
        self.anim = Animacao("efeitos/projetil")

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.raio), int(self.y - self.raio), self.raio * 2, self.raio * 2)

    @property
    def parryavel(self):
        return self.vivo and not self.refletido

    def ser_aparado(self, jogador):
        """Parry reflete o projetil de volta em quem atirou, com dano em dobro."""
        self.refletido = True
        self.dano = jogador.dano_ataque * MULT_DANO_ATORDOADO
        alvo = self.dono.rect.center if (self.dono and self.dono.vivo) else None
        dx, dy = (alvo[0] - self.x, alvo[1] - self.y) if alvo else (-self.vx, -self.vy)
        d = math.hypot(dx, dy) or 1
        self.vx, self.vy = dx / d * 7, dy / d * 7

    def atualizar(self, obstaculos, largura, altura):
        self.x += self.vx
        self.y += self.vy
        if not (10 < self.x < largura - 10 and 10 < self.y < altura - 10):
            self.vivo = False
        elif any(self.rect.colliderect(o) for o in obstaculos):
            self.vivo = False

    def desenhar(self, tela):
        if desenhar_centro(tela, self.anim, self.rect):
            return
        cor, cor2 = ((255, 220, 90), (255, 250, 200)) if self.refletido else ((230, 90, 110), (255, 200, 210))
        pygame.draw.circle(tela, cor, (int(self.x), int(self.y)), self.raio)
        pygame.draw.circle(tela, cor2, (int(self.x), int(self.y)), self.raio - 3)


class Bispo(Inimigo):
    """Mantem distancia, anda em volta do jogador e atira projeteis.
    TODO: trocar pelo sprite de bispo."""

    def __init__(self, x, y):
        super().__init__(x, y, 34, 48, vida=5, dano_contato=2, cor=(190, 190, 235))
        self.timer_tiro = random.uniform(1.0, 2.0)
        self.lado = random.choice((-1, 1))
        # >>> SPRITE AQUI (BISPO): assets/bispo/idle, andar, atirar
        self.animador = Animador("bispo", {"idle": {}, "andar": {}, "atirar": {}},
                                 fallback={"atirar": "andar"}, **SPRITE_AJUSTE["bispo"])

    def atualizar(self, jogador, dt, obstaculos=(), projeteis=None):
        if not self.vivo:
            return
        self.atualizar_timers(dt)
        if self.aplicar_knock(obstaculos):
            return
        cx, cy = self.rect.center
        dx = jogador.rect.centerx - cx
        dy = jogador.rect.centery - cy
        dist = max(1, math.hypot(dx, dy))
        self.olhando_direita = dx > 0
        if dist < 190:
            vx, vy = -dx / dist * 1.5, -dy / dist * 1.5
        elif dist > 300:
            vx, vy = dx / dist * 1.5, dy / dist * 1.5
        else:
            vx, vy = -dy / dist * 1.2 * self.lado, dx / dist * 1.2 * self.lado
        mover_com_colisao(self, vx, vy, obstaculos)

        self.timer_tiro -= dt
        if self.timer_tiro <= 0 and projeteis is not None:
            self.timer_tiro = 2.2
            projeteis.append(Projetil(cx, cy, dx / dist * 4.5, dy / dist * 4.5, dono=self))

    def desenhar(self, tela, camera_x, camera_y):
        if not self.vivo:
            return
        r = self.rect.move(-camera_x, -camera_y)
        # >>> SPRITE AQUI: bispo (assets/bispo/...)
        est_anim = "atirar" if self.timer_tiro < 0.4 else "andar"
        if self.desenhar_sprite(tela, camera_x, camera_y, est_anim, flip=not self.olhando_direita):
            self.desenhar_barra_vida(tela, camera_x, camera_y)
            return
        cor = self.cor
        if self.invencivel_timer > 0:
            cor = (255, 255, 255)
        elif self.timer_tiro < 0.4:
            cor = (255, 150, 170)     # aviso: vai atirar
        pygame.draw.rect(tela, cor, r, border_radius=6)
        pygame.draw.polygon(tela, cor, [(r.centerx, r.top - 16), (r.left + 4, r.top + 4), (r.right - 4, r.top + 4)])
        self.desenhar_barra_vida(tela, camera_x, camera_y)


# ---------------- inimigos de plataforma ----------------
class TorreMiniBoss(Inimigo):
    """Mini-boss da sala 5 (plataforma, de plataforma).
    Ciclo: patrulha -> AVISO (pisca) -> INVESTIDA -> se bater na parede fica
    ATORDOADO (inofensivo, hora de bater). A cada 3 ciclos faz um SALTO com
    tremor de terra. Da pra fazer pogo nela. TODO: sprite da torre."""

    def __init__(self, x, chao_y, x_min, x_max):
        super().__init__(x, chao_y - 100, 70, 100, vida=24, dano_contato=4, cor=(150, 150, 165))
        self.chao_y = chao_y
        self.x_min, self.x_max = x_min, x_max
        self.vel_y = 0
        self.estado = "dormindo"
        self.timer = 0
        self.direcao = -1
        self.ciclos = 0
        self.parry_no_pouso = False   # aparada no salto: termina de cair e fica atordoada
        # >>> SPRITE AQUI (TORRE / MINI-BOSS): assets/torre_boss/idle, andar, aviso, investida,
        #     atordoado, salto_aviso, salto
        self.animador = Animador("torre_boss", {
            "idle": {}, "andar": {}, "aviso": {}, "investida": {}, "atordoado": {},
            "salto_aviso": {}, "salto": {},
        }, fallback={"aviso": "andar", "investida": "aviso", "atordoado": "idle",
                     "salto_aviso": "aviso", "salto": "investida"}, **SPRITE_AJUSTE["torre_boss"])

    @property
    def ativo(self):
        return self.estado != "dormindo"

    @property
    def perigoso(self):
        return self.vivo and self.estado not in ("dormindo", "atordoado") and self.atordoado_timer <= 0

    @property
    def parryavel(self):
        return self.vivo and self.estado in ("investida", "salto") and not self.parry_no_pouso

    def ser_aparado(self, jogador):
        self.atordoado_timer = TEMPO_ATORDOADO_PARRY + 0.4
        tremer(0.3, 6)
        if self.estado == "salto":
            self.parry_no_pouso = True          # ainda no ar: atordoa quando pousar
        else:
            self.estado, self.timer = "atordoado", TEMPO_ATORDOADO_PARRY + 0.4

    def _virar_pro_jogador(self, jogador):
        self.direcao = 1 if jogador.rect.centerx > self.rect.centerx else -1

    def atualizar(self, jogador, dt):
        if not self.vivo:
            return
        self.atualizar_timers(dt)
        self.timer -= dt

        if self.estado == "dormindo":
            if abs(jogador.x - self.x) < 520:
                self.estado, self.timer = "patrulha", 1.8

        elif self.estado == "patrulha":
            self._virar_pro_jogador(jogador)
            self.x += 1.6 * self.direcao
            if self.timer <= 0:
                self.ciclos += 1
                self.estado = "salto_aviso" if self.ciclos % 3 == 0 else "aviso"
                self.timer = 0.5 if self.estado == "salto_aviso" else 0.65

        elif self.estado == "aviso":
            self._virar_pro_jogador(jogador)
            if self.timer <= 0:
                self.estado, self.timer = "investida", 1.4

        elif self.estado == "investida":
            self.x += 11 * self.direcao
            if self.x <= self.x_min or self.x + self.largura >= self.x_max:
                self.estado, self.timer = "atordoado", 1.4
                tremer(0.3, 6)
            elif self.timer <= 0:
                self.estado, self.timer = "patrulha", 1.5

        elif self.estado == "atordoado":
            if self.timer <= 0:
                self.estado, self.timer = "patrulha", 1.5

        elif self.estado == "salto_aviso":
            self._virar_pro_jogador(jogador)
            if self.timer <= 0:
                self.estado = "salto"
                self.vel_y = -17

        elif self.estado == "salto":
            self.vel_y += GRAVIDADE
            self.y += self.vel_y
            self.x += 5 * self.direcao
            if self.y + self.altura >= self.chao_y:
                self.y = self.chao_y - self.altura
                self.vel_y = 0
                tremer(0.35, 7)
                if self.parry_no_pouso:
                    self.parry_no_pouso = False
                    self.estado, self.timer = "atordoado", TEMPO_ATORDOADO_PARRY
                else:
                    self.estado, self.timer = "patrulha", 1.3

        self.x = max(self.x_min, min(self.x, self.x_max - self.largura))

    def desenhar(self, tela, camera_x, camera_y):
        if not self.vivo:
            return
        r = self.rect.move(-camera_x, -camera_y)
        # >>> SPRITE AQUI: torre mini-boss (assets/torre_boss/...)
        est_anim = {"dormindo": "idle", "patrulha": "andar"}.get(self.estado, self.estado)
        if self.desenhar_sprite(tela, camera_x, camera_y, est_anim, flip=self.direcao < 0):
            self.desenhar_barra_vida(tela, camera_x, camera_y)
            return
        cor = self.cor
        if self.invencivel_timer > 0:
            cor = (230, 150, 150)
        elif self.estado in ("aviso", "salto_aviso") and int(self.timer * 16) % 2 == 0:
            cor = (255, 130, 90)
        elif self.estado == "atordoado":
            cor = (105, 105, 140)
        pygame.draw.rect(tela, cor, r, border_radius=4)
        for i in range(4):
            pygame.draw.rect(tela, cor, (r.x + i * 18, r.y - 14, 12, 14))
        self.desenhar_barra_vida(tela, camera_x, camera_y)


# ---------------- objetos ----------------
class TorreObstaculo:
    """Peca de torre da sala 4 - so causa dano ao encostar. Orbita um ponto."""

    def __init__(self, centro_x, centro_y, raio, angulo_inicial, vel_angular,
                 cor=(140, 60, 70), cor_contorno=None):
        self.centro_x, self.centro_y = centro_x, centro_y
        self.raio = raio
        self.angulo = angulo_inicial
        self.vel_angular = vel_angular
        self.largura, self.altura = 34, 34
        self.dano_contato = 3
        self.cor = cor
        self.cor_contorno = cor_contorno
        self.x, self.y = 0, 0
        self._atualizar_posicao()
        # >>> SPRITE AQUI: assets/torre_orbital/idle.png (pecas que giram na sala 4)
        self.animador = Animador("torre_orbital", {"idle": {}}, **SPRITE_AJUSTE["torre_orbital"])

    def _atualizar_posicao(self):
        self.x = self.centro_x + math.cos(self.angulo) * self.raio - self.largura / 2
        self.y = self.centro_y + math.sin(self.angulo) * self.raio - self.altura / 2

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.largura, self.altura)

    def atualizar(self, dt):
        self.angulo += self.vel_angular * dt
        self._atualizar_posicao()

    def desenhar(self, tela, camera_x, camera_y):
        r = self.rect.move(-camera_x, -camera_y)
        if self.animador.desenhar(tela, "idle", r):
            if DEBUG["hitbox"]:
                pygame.draw.rect(tela, (0, 255, 0), r, 1)
            return
        pygame.draw.rect(tela, self.cor, r, border_radius=4)
        if self.cor_contorno:
            pygame.draw.rect(tela, self.cor_contorno, r, width=2, border_radius=4)
        for i in range(3):
            pygame.draw.rect(tela, self.cor, (r.x + i * 10, r.y - 8, 6, 8))


class Espinhos:
    """Espinhos: dao dano, levam o jogador de volta ao ultimo ponto seguro
    e sao 'pogaveis' com ataque pra baixo."""

    def __init__(self, x, y, largura, altura=200):
        self.x, self.y = x, y
        self.largura, self.altura = largura, altura
        self.dano = DANO_ESPINHO
        # >>> SPRITE AQUI: assets/objetos/espinho.png (1 modulo; repete pela largura, ponta em cima)
        self.anim = Animacao("objetos/espinho")

    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.largura, self.altura)

    def desenhar(self, tela, camera_x, camera_y=0):
        r = self.rect.move(-camera_x, -camera_y)
        img = self.anim.frame()
        if img:
            tela.set_clip(r.clip(tela.get_rect()))
            pygame.draw.rect(tela, (22, 22, 32), r)
            for x0 in range(r.left, r.right, img.get_width()):
                tela.blit(img, (x0, r.top))
            tela.set_clip(None)
            return
        n = max(1, r.width // 20)
        w = r.width / n
        pygame.draw.rect(tela, (22, 22, 32), (r.left, r.top + 24, r.width, max(0, r.height - 24)))
        for i in range(n):
            x0 = r.left + i * w
            pygame.draw.polygon(tela, (170, 175, 195), [(x0, r.top + 24), (x0 + w / 2, r.top), (x0 + w, r.top + 24)])


class AlvoPogo:
    """Lamparina pendurada. Ataque pra baixo nela = quique (pogo)."""

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.largura, self.altura = 30, 30
        # >>> SPRITE AQUI: assets/objetos/lamparina.png (30x30, centralizada na hitbox)
        self.anim = Animacao("objetos/lamparina")

    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.largura, self.altura)

    def desenhar(self, tela, camera_x, camera_y=0):
        r = self.rect.move(-camera_x, -camera_y)
        if DESENHAR_CORDA_LAMPARINA:
            pygame.draw.line(tela, (90, 80, 60), (r.centerx, 0), (r.centerx, r.top), 2)
        if not desenhar_centro(tela, self.anim, r):
            pygame.draw.rect(tela, (200, 170, 90), r, border_radius=4)


class Coracao:
    """Cura 2 de vida. Cai de inimigos nas salas top-down."""

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.largura, self.altura = 22, 20
        self.coletado = False
        # >>> SPRITE AQUI: assets/itens/coracao.png
        self.anim = Animacao("itens/coracao")

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.largura, self.altura)

    def desenhar(self, tela, cam_x=0, cam_y=0):
        if self.coletado:
            return
        if desenhar_centro(tela, self.anim, self.rect.move(-cam_x, -cam_y)):
            return
        x, y = int(self.x - cam_x), int(self.y - cam_y)
        pygame.draw.circle(tela, (230, 70, 90), (x + 6, y + 7), 6)
        pygame.draw.circle(tela, (230, 70, 90), (x + 16, y + 7), 6)
        pygame.draw.polygon(tela, (230, 70, 90), [(x, y + 9), (x + 22, y + 9), (x + 11, y + 21)])


class ChavePickup:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.largura, self.altura = 24, 24
        self.coletada = False
        # >>> SPRITE AQUI: assets/itens/chave.png
        self.anim = Animacao("itens/chave")

    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.largura, self.altura)

    def desenhar(self, tela):
        if self.coletada:
            return
        if desenhar_centro(tela, self.anim, self.rect):
            return
        pygame.draw.circle(tela, (230, 200, 90), (self.x + 12, self.y + 8), 8)
        pygame.draw.rect(tela, (230, 200, 90), (self.x + 9, self.y + 12, 6, 14))


class Bau:
    def __init__(self, x, y, cura=5):
        self.x, self.y = x, y
        self.largura, self.altura = 40, 30
        self.cura = cura
        self.aberto = False
        # >>> SPRITE AQUI: assets/itens/bau_fechado.png e bau_aberto.png (esticados na hitbox 40x30)
        self.animador = Animador("itens", {"bau_fechado": {}, "bau_aberto": {}}, modo="esticar",
                                 fallback={"bau_aberto": "bau_fechado", "bau_fechado": "bau_aberto"})

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.largura, self.altura)

    def abrir(self, jogador):
        if not self.aberto:
            self.aberto = True
            jogador.curar(self.cura)

    def desenhar(self, tela, camera_x, camera_y):
        r = self.rect.move(-camera_x, -camera_y)
        if self.animador.desenhar(tela, "bau_aberto" if self.aberto else "bau_fechado", r):
            return
        cor = (90, 70, 40) if not self.aberto else (60, 50, 35)
        pygame.draw.rect(tela, cor, r, border_radius=4)
        if not self.aberto:
            pygame.draw.rect(tela, (200, 180, 80), (r.x + r.width // 2 - 4, r.y + 6, 8, 8))


class Porta:
    def __init__(self, x, y, largura, altura, destino, trancada=False, precisa_chave=None, cor_brilho=None,
                 sprite="porta"):
        self.x, self.y = x, y
        self.largura, self.altura = largura, altura
        self.destino = destino
        self.trancada = trancada
        self.precisa_chave = precisa_chave
        self.cor_brilho_custom = cor_brilho
        # >>> SPRITE AQUI (PORTAS): assets/portas/<sprite>_normal.png e <sprite>_trancada.png
        #     sprite="porta" (90x150) | "escada" (90x30, no topo da sala) | "escada_baixo" (90x30, embaixo)
        #     | "grande" (30x150). O PNG e esticado no tamanho da porta.
        self.sprite = sprite
        self.animador = Animador("portas", {f"{sprite}_normal": {}, f"{sprite}_trancada": {}}, modo="esticar",
                                 fallback={f"{sprite}_trancada": f"{sprite}_normal"})

    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.largura, self.altura)

    def desenhar(self, tela, camera_x, camera_y, perto, tempo):
        r = self.rect.move(-camera_x, -camera_y)
        estado = f"{self.sprite}_{'trancada' if self.trancada else 'normal'}"
        if self.animador.desenhar(tela, estado, r):
            if perto:      # brilho de "pode interagir" continua por cima do sprite
                pulso = 0.55 + 0.45 * math.sin(tempo * 4)
                cor_b = (255, 120, 120) if self.trancada else (self.cor_brilho_custom or (150, 190, 255))
                pygame.draw.rect(tela, tuple(int(c * pulso) for c in cor_b), r, width=3, border_radius=8)
            return
        cor_base = (55, 35, 35) if self.trancada else (30, 32, 46)
        pygame.draw.rect(tela, cor_base, r, border_radius=8)
        pulso = 0.55 + 0.45 * math.sin(tempo * 4) if perto else 0.3
        cor_brilho = (255, 120, 120) if self.trancada else (self.cor_brilho_custom or (150, 190, 255))
        cor_final = tuple(int(c * pulso) for c in cor_brilho)
        pygame.draw.rect(tela, cor_final, r, width=4, border_radius=10)

# ============================================================
# SalaPlataforma - base de TODAS as salas de plataforma
# (entrada de controles, combate, pogo, espinhos, queda, camera)
# ============================================================
class SalaPlataforma:
    perspectiva = "plataforma"
    permite_ataque = True

    def __init__(self, largura_sala, chao_y, colisores, spawn, porta_saida=None):
        self.largura_sala = largura_sala
        self.chao_y = chao_y
        self.colisores = colisores
        self.spawn = spawn
        self.porta_saida = porta_saida
        self.porta_volta = None   # as salas preenchem depois do super().__init__
        self.spawns = {}          # {"sala_de_origem": (x, y)}
        self.inimigos = []
        self.alvos_pogo = []
        self.espinhos = []
        self.vinheta = None
        self.fonte = pygame.font.Font(None, 26)

    def entrar(self, jogador, origem=None):
        pos = self.spawns.get(origem, self.spawn)
        jogador.x, jogador.y = pos
        jogador.vel_x = jogador.vel_y = 0
        jogador.knock_timer = 0
        jogador.ultimo_seguro = pos

    def camera_x(self, jogador):
        return int(max(0, min(jogador.x - LARGURA_TELA // 2, self.largura_sala - LARGURA_TELA)))

    def perto_da_porta(self, jogador):
        return bool(self.porta_saida) and jogador.rect.colliderect(self.porta_saida.rect.inflate(30, 30))

    def _porta_interagida(self, jogador):
        for p in (self.porta_saida, self.porta_volta):
            if p and not p.trancada and jogador.rect.colliderect(p.rect.inflate(30, 30)):
                return p.destino
        return None

    def atualizar_extra(self, jogador, dt, estado_jogo):
        pass

    def _voltar_ao_seguro(self, jogador):
        jogador.x, jogador.y = jogador.ultimo_seguro
        jogador.vel_x = jogador.vel_y = 0
        jogador.knock_timer = 0

    def _combate(self, jogador, dt):
        for e in self.inimigos:          # PARRY tem prioridade sobre o golpe normal
            jogador.aparar(e)
        hb = jogador.hitbox_ataque
        baixo = jogador.dir_ataque == "baixo"

        if hb:
            if baixo and not jogador.pogo_usado:
                if any(hb.colliderect(a.rect) for a in self.alvos_pogo) or \
                   any(hb.colliderect(e.rect) for e in self.espinhos):
                    jogador.pogo()
            for e in self.inimigos:
                if e.vivo and id(e) not in jogador.acertados and hb.colliderect(e.rect):
                    jogador.acertados.add(id(e))
                    if e.receber_dano(jogador.dano_ataque):
                        hitstop(0.05)
                        tremer(0.12, 3)
                        if not isinstance(e, TorreMiniBoss):
                            e.empurrar(e.rect.centerx - jogador.rect.centerx, 0, 7)
                    if baixo and not jogador.pogo_usado:
                        jogador.pogo()   # pogo tambem quica em inimigos

        for e in self.inimigos:
            e.atualizar(jogador, dt)
            jogador.aparar(e)        # PARRY: tem que vir antes do dano de contato
            if e.perigoso and jogador.rect.colliderect(e.rect):
                jogador.receber_dano(e.dano_contato, e.rect.center)

        for esp in self.espinhos:
            if jogador.rect.colliderect(esp.rect):
                jogador.receber_dano(esp.dano)
                self._voltar_ao_seguro(jogador)

        if jogador.y > ALTURA_TELA + 250:      # caiu do mapa
            jogador.receber_dano(1)
            self._voltar_ao_seguro(jogador)

    def atualizar(self, jogador, teclas, eventos, dt, estado_jogo):
        jogador.atualizar_plataforma(teclas, self.colisores, dt)
        jogador.x = max(0, min(jogador.x, self.largura_sala - jogador.largura))   # paredes invisiveis
        jogador.atualizar_timers(dt)

        destino = None
        for ev in eventos:
            if ev.type == pygame.KEYDOWN:
                if ev.key == TECLA_PULO:
                    jogador.pedir_pulo()
                elif ev.key == TECLA_ATAQUE and self.permite_ataque:
                    jogador.tentar_atacar(teclas)
                elif ev.key == TECLA_INTERAGIR:
                    destino = self._porta_interagida(jogador) or destino
            elif ev.type == pygame.KEYUP and ev.key == TECLA_PULO:
                jogador.soltar_pulo()

        self._combate(jogador, dt)
        self.atualizar_extra(jogador, dt, estado_jogo)
        return destino

    def desenhar_entidades(self, tela, jogador, tempo, camera_x):
        for a in self.alvos_pogo:
            a.desenhar(tela, camera_x)
        for esp in self.espinhos:
            esp.desenhar(tela, camera_x)
        for e in self.inimigos:
            e.desenhar(tela, camera_x, 0)
        perto = self.perto_da_porta(jogador)
        if self.porta_saida:
            self.porta_saida.desenhar(tela, camera_x, 0, perto, tempo)
        if self.porta_volta:
            perto_volta = jogador.rect.colliderect(self.porta_volta.rect.inflate(30, 30))
            self.porta_volta.desenhar(tela, camera_x, 0, perto_volta, tempo)
            if perto_volta:
                self.escrever(tela, "Pressione E para voltar", (20, 50))
        if self.vinheta:
            tela.blit(self.vinheta, (0, 0))
        jogador.desenhar(tela, camera_x, 0)
        return perto

    def escrever(self, tela, texto, pos=(20, 20)):
        tela.blit(self.fonte.render(texto, True, (255, 255, 255)), pos)
class ChuvaRaios:
    """Chuva em coordenadas de TELA (nao rola com a camera) + raios aleatorios."""

    def __init__(self, qtd=170, intervalo=(4.0, 9.0)):
        self.gotas = [self._nova_gota(True) for _ in range(qtd)]
        self.intervalo = intervalo
        self.ultimo = _agora()
        self.prox_raio = self.ultimo + random.uniform(*intervalo)
        self.raio_t0 = -99
        self.raio_pontos = []
        self.clarao = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)

    def _nova_gota(self, inicial=False):
        return {"x": random.uniform(-100, LARGURA_TELA + 50),
                "y": random.uniform(0, ALTURA_TELA) if inicial else random.uniform(-60, 0),
                "vel": random.uniform(14, 22),
                "comp": random.randint(10, 20)}

    def _gerar_raio(self, chao_y):
        x, y = random.randint(80, LARGURA_TELA - 80), 0
        pontos = [(x, y)]
        while y < chao_y:
            y += random.randint(25, 55)
            x += random.randint(-35, 35)
            pontos.append((x, min(y, chao_y)))
        return pontos

    def desenhar(self, tela, chao_y):
        agora = _agora()
        dt = min(agora - self.ultimo, 0.05)
        self.ultimo = agora

        # ---- raio novo?
        if agora >= self.prox_raio:
            self.raio_t0 = agora
            self.raio_pontos = self._gerar_raio(chao_y)
            self.prox_raio = agora + random.uniform(*self.intervalo)
            tremer(0.25, 3)                      # trovao

        k = agora - self.raio_t0
        # ---- clarao (pisca duas vezes e some)
        if k < 0.6:
            if k < 0.08:
                a = 190
            elif k < 0.16:
                a = 40
            else:
                a = 150 * max(0, 1 - (k - 0.16) / 0.44)
            self.clarao.fill((215, 220, 255, int(a)))
            tela.blit(self.clarao, (0, 0))
        # ---- o raio em si
        if k < 0.22 and len(self.raio_pontos) > 1:
            pygame.draw.lines(tela, (150, 160, 255), False, self.raio_pontos, 7)   # brilho
            pygame.draw.lines(tela, (255, 255, 255), False, self.raio_pontos, 3)   # nucleo

        # ---- gotas
        for g in self.gotas:
            g["y"] += g["vel"] * dt * 60
            g["x"] -= g["vel"] * 0.25 * dt * 60
            if g["y"] > ALTURA_TELA or g["x"] < -40:
                g.update(self._nova_gota())
            pygame.draw.line(tela, (170, 185, 230),
                             (g["x"], g["y"]), (g["x"] - g["comp"] * 0.25, g["y"] + g["comp"]), 1)

# ============================================================
# sala 1 - portao (plataforma, sem combate)
# ============================================================
class Sala1Portao(SalaPlataforma):
    permite_ataque = False

    def __init__(self):
        largura, chao_y = 2200, 480
        super().__init__(largura, chao_y, [pygame.Rect(0, chao_y, largura, 200)], (80, chao_y - 54),
                         Porta(largura - 140, chao_y - 150, 90, 150, destino="sala2"))
        rng = random.Random(7)
        self.arvores = [{
            "x": x + rng.randint(-20, 20),
            "altura_tronco": rng.randint(90, 160),
            "raio_folhas": rng.randint(40, 65),
        } for x in range(50, largura - 50, 140)]
        self.vinheta = criar_vinheta(LARGURA_TELA, ALTURA_TELA, forca=120)
        self.neblina = criar_particulas_neblina(30, largura, chao_y, cor=(220, 180, 210))
        self.chuva = ChuvaRaios()
        self.fonte = pygame.font.Font(None, 28)
        # >>> SPRITE AQUI: assets/cenario/fundo_sala1.png (ceu) e assets/cenario/arvore.png
        self.fundo = Animacao("cenario/fundo_sala1")
        self.sprite_arvore = Animacao("cenario/arvore")
        self.spawns = {"sala2": (largura - 260, chao_y - 54)}

    def desenhar(self, tela, jogador, tempo):
        camera_x = self.camera_x(jogador)

        img_fundo = self.fundo.frame()
        if img_fundo:
            desenhar_fundo(tela, img_fundo, (46, 34, 58), camera_x, self.largura_sala)
        else:
            tela.fill((46, 34, 58))          # limpa o quadro anterior (some o menu)
            for y in range(0, self.chao_y, 4):
                t = y / self.chao_y
                cor = (int(46 + t * 20), int(34 + t * 10), int(58 + t * 30))
                pygame.draw.rect(tela, cor, (0, y, LARGURA_TELA, 4))   # faixa cheia, sem buracos

        for arv in self.arvores:
            ax = arv["x"] - camera_x * 0.9
            if -100 < ax < LARGURA_TELA + 100:
                base_y = self.chao_y
                img_arv = self.sprite_arvore.frame()
                if img_arv:
                    tela.blit(img_arv, img_arv.get_rect(midbottom=(int(ax), base_y)))
                    continue
                pygame.draw.rect(tela, (60, 40, 35), (ax - 6, base_y - arv["altura_tronco"], 12, arv["altura_tronco"]))
                for dx, dy, r in [(0, 0, 1), (-18, 10, 0.8), (18, 10, 0.8), (0, -20, 0.7)]:
                    pygame.draw.circle(tela, (225, 150, 185),
                                        (int(ax + dx), int(base_y - arv["altura_tronco"] - 10 + dy)),
                                        int(arv["raio_folhas"] * r))

        pygame.draw.rect(tela, (40, 32, 30), (0, self.chao_y, LARGURA_TELA, ALTURA_TELA - self.chao_y))
        pygame.draw.rect(tela, (55, 44, 40), (0, self.chao_y, LARGURA_TELA, 6))
        desenhar_neblina(tela, self.neblina, self.largura_sala, LARGURA_TELA, ALTURA_TELA, camera_x)

        perto = self.desenhar_entidades(tela, jogador, tempo, camera_x)
        self.chuva.desenhar(tela, self.chao_y)
        if perto:
            dica = self.fonte.render("Pressione E para entrar no castelo", True, (255, 255, 255))
            tela.blit(dica, dica.get_rect(center=(LARGURA_TELA // 2, 40)))
        elif jogador.x < 500:
            self.escrever(tela, "A/D mover · SHIFT correr · ESPAÇO pular (segure = mais alto)", (20, 60))
# ============================================================
# sala 2 - tutorial (plataforma): pulo, ataque, pogo, espinhos, inimigo
# ============================================================
class Sala2Tutorial(SalaPlataforma):
    def __init__(self):
        largura, chao_y = 2000, 480
        colisores = [
            pygame.Rect(0, chao_y, 780, 200),          # chao antes do fosso
            pygame.Rect(1120, chao_y, 880, 200),       # chao depois do fosso
            pygame.Rect(400, chao_y - 90, 140, 20),    # plataforma pra treinar pulo
        ]
        super().__init__(largura, chao_y, colisores, (140, chao_y - 54),
                         Porta(largura - 140, chao_y - 150, 90, 150, destino="sala3"))
        self.espinhos = [Espinhos(780, chao_y + 60, 340)]
        self.alvos_pogo = [AlvoPogo(935, chao_y - 85)]
        self.vinheta = criar_vinheta(LARGURA_TELA, ALTURA_TELA, forca=150)
        self.neblina = criar_particulas_neblina(25, largura, chao_y)
        # >>> SPRITE AQUI: assets/cenario/fundo_sala2.png
        self.fundo = Animacao("cenario/fundo_sala2")
        self.porta_volta = Porta(20, chao_y - 150, 90, 150, destino="sala1")
        self.spawns = {"sala3": (largura - 230, chao_y - 54)}

    def desenhar(self, tela, jogador, tempo):
        camera_x = self.camera_x(jogador)
        desenhar_fundo(tela, self.fundo.frame(), (16, 16, 26), camera_x, self.largura_sala)
        desenhar_bloco_pedra(tela, self.colisores[0], camera_x)
        desenhar_bloco_pedra(tela, self.colisores[1], camera_x)
        desenhar_plataforma_fina(tela, self.colisores[2], camera_x)
        desenhar_neblina(tela, self.neblina, self.largura_sala, LARGURA_TELA, ALTURA_TELA, camera_x)
        perto = self.desenhar_entidades(tela, jogador, tempo, camera_x)

        dica = "A/D mover · SHIFT correr · ESPAÇO pular · Q atacar (W+Q pra cima)"
        if 560 < jogador.x < 1130:
            dica = "No ar: S + Q acertando a lamparina (ou espinhos/inimigos) = POGO!"
        elif jogador.x >= 1130:
            dica = "Ataque o bicho com Q. Cair nos espinhos tira vida."
        if perto:
            dica = "Pressione E para seguir em frente"
        self.escrever(tela, dica)

# ============================================================
# sala 3 - salao dos guardas (top-down)
# ============================================================
class Sala3:
    """Sala unica sem rolagem. Peoes perseguem, bispo atira. Pedras bloqueiam
    movimento e tiros. Inimigos podem dropar coracao. Ao limpar a sala a chave
    aparece e a escada destranca. A porta grande so abre com a chave grande.
    Ao VOLTAR com a chave grande, os peoes estao dormindo (enfeite)."""
 
    perspectiva = "topdown"
    dropa_chave = True      # a Sala8 (que herda daqui) desliga
    peoes_dormem = True     # ao voltar com a chave grande, peoes dormem na sala
 
    def __init__(self):
        self.largura_sala = LARGURA_TELA
        self.altura_sala = ALTURA_TELA
        self.spawn = (LARGURA_TELA // 2 - 17, ALTURA_TELA - 120)
 
        self.obstaculos = [pygame.Rect(150, 250, 70, 70), pygame.Rect(580, 250, 70, 70)]
        self.inimigos = [Peao(180, 140), Peao(560, 140), Peao(260, 390), Peao(620, 390), Bispo(380, 100)]
        self.pos_peoes = [(e.x, e.y) for e in self.inimigos if isinstance(e, Peao)]
        self.dorminhocos = []
        self.projeteis = []
        self.coracoes = []
        self.chave = None
        self.limpa = False
        self.timer_ataque = 2.0   # tempo ate o proximo peao atacar
        # >>> SPRITE AQUI: assets/cenario/fundo_sala3.png (800x600) e assets/objetos/pedra.png
        self.fundo = Animacao("cenario/fundo_sala3")
        self.sprite_pedra = Animacao("objetos/pedra")
 
        self.porta_escada = Porta(LARGURA_TELA // 2 - 45, 0, 90, 30, destino="sala4", trancada=True, sprite="escada")
        self.porta_grande = Porta(0, ALTURA_TELA // 2 - 75, 30, 150, destino="sala6",
                                   trancada=True, precisa_chave="grande", sprite="grande")
        self.porta_baixo = Porta(LARGURA_TELA // 2 - 45, ALTURA_TELA - 30, 90, 30,
                                 destino="sala2", sprite="escada_baixo")
        self.spawns = {"sala4": (LARGURA_TELA // 2 - 17, 70),
                       "sala6": (70, ALTURA_TELA // 2 - 27)}
        self.fonte = pygame.font.Font(None, 26)
 
    def entrar(self, jogador, origem=None):
        jogador.x, jogador.y = self.spawns.get(origem, self.spawn)
        jogador.knock_timer = 0
        if self.peoes_dormem and not self.dorminhocos and estado_jogo.chave_grande > 0:
            for x, y in self.pos_peoes:                # peoes dormindo (so enfeite)
                p = Peao(x, y)
                p.estado = "dormindo"
                self.dorminhocos.append(p)
 
    def atualizar(self, jogador, teclas, eventos, dt, estado_jogo):
        jogador.atualizar_topdown(teclas, self.obstaculos)
        jogador.x = max(20, min(jogador.x, self.largura_sala - jogador.largura - 20))
        jogador.y = max(20, min(jogador.y, self.altura_sala - jogador.altura - 20))
        jogador.atualizar_timers(dt)
 
        for evento in eventos:
            if evento.type == pygame.KEYDOWN:
                if evento.key == TECLA_ATAQUE:
                    jogador.tentar_atacar(topdown=True)
                if evento.key == TECLA_INTERAGIR:
                    for porta in (self.porta_escada, self.porta_grande, self.porta_baixo):
                        if not porta.trancada and jogador.rect.colliderect(porta.rect.inflate(30, 30)):
                            return porta.destino
 
        # PARRY primeiro: tem prioridade sobre o golpe normal (senao o empurrao do golpe
        # cancelaria a investida antes de ela poder ser aparada)
        for alvo in self.inimigos + self.projeteis:
            jogador.aparar(alvo)
 
        hb = jogador.hitbox_ataque
        if hb:
            for e in self.inimigos:
                if e.vivo and id(e) not in jogador.acertados and hb.colliderect(e.rect):
                    jogador.acertados.add(id(e))
                    if e.receber_dano(jogador.dano_ataque):
                        hitstop(0.05)
                        tremer(0.1, 3)
                        e.empurrar(e.rect.centerx - jogador.rect.centerx,
                                   e.rect.centery - jogador.rect.centery, 10)
 
        # coordenador: so UM peao ataca por vez, os outros ficam girando
        peoes = [e for e in self.inimigos if isinstance(e, Peao) and e.vivo]
        if peoes and not any(p.atacando for p in peoes):
            self.timer_ataque -= dt
            if self.timer_ataque <= 0:
                orbitando = [p for p in peoes if p.estado == "orbitar"]
                if orbitando:
                    random.choice(orbitando).pedir_ataque()
                    self.timer_ataque = random.uniform(1.4, 2.2)
 
        for e in self.inimigos:
            e.atualizar(jogador, dt, self.obstaculos, self.projeteis)
            e.x = max(20, min(e.x, self.largura_sala - e.largura - 20))
            e.y = max(20, min(e.y, self.altura_sala - e.altura - 20))
            jogador.aparar(e)        # PARRY: tem que vir antes do dano de contato
            if e.perigoso and jogador.rect.colliderect(e.rect):
                jogador.receber_dano(e.dano_contato, e.rect.center)
            if not e.vivo and not e.drop_feito:
                e.drop_feito = True
                if random.random() < 0.4:
                    self.coracoes.append(Coracao(e.rect.centerx - 11, e.rect.centery - 10))
 
        for p in self.projeteis:
            p.atualizar(self.obstaculos, self.largura_sala, self.altura_sala)
            jogador.aparar(p)        # PARRY: Q na hora do tiro reflete o projetil
            if p.refletido:
                if p.vivo:
                    for e in self.inimigos:
                        if e.vivo and p.rect.colliderect(e.rect):
                            p.vivo = False
                            if e.receber_dano(p.dano):
                                hitstop(0.05)
                                tremer(0.12, 3)
                            break
            elif p.vivo and jogador.rect.colliderect(p.rect):
                p.vivo = False
                jogador.receber_dano(p.dano, (p.x, p.y))
        self.projeteis = [p for p in self.projeteis if p.vivo]
 
        for c in self.coracoes:
            if not c.coletado and jogador.rect.colliderect(c.rect):
                c.coletado = True
                jogador.curar(2)
 
        if not self.limpa and all(not i.vivo for i in self.inimigos):
            self.limpa = True
            self.projeteis = []
            if self.dropa_chave:
                self.chave = ChavePickup(self.largura_sala // 2 - 12, self.altura_sala // 2 - 12)
            self.porta_escada.trancada = False
            estado_jogo.flags["sala3_limpa"] = True
 
        if self.chave and not self.chave.coletada and jogador.rect.colliderect(self.chave.rect):
            self.chave.coletada = True
            estado_jogo.chave_pequena += 1
 
        if estado_jogo.chave_grande > 0:
            self.porta_grande.trancada = False
 
        return None
 
    def desenhar(self, tela, jogador, tempo):
        img_fundo = self.fundo.frame()
        if img_fundo:
            desenhar_fundo(tela, img_fundo, (15, 13, 18))
        else:
            for tx in range(0, self.largura_sala // TAMANHO_TILE + 1):
                for ty in range(0, self.altura_sala // TAMANHO_TILE + 1):
                    tela.blit(gerar_tile_pedra(tx, ty, cor1=(38, 32, 40), cor2=(30, 26, 32)),
                              (tx * TAMANHO_TILE, ty * TAMANHO_TILE))
            pygame.draw.rect(tela, (15, 13, 18), (0, 0, self.largura_sala, self.altura_sala), width=20)
 
        for o in self.obstaculos:
            if desenhar_esticado(tela, self.sprite_pedra, o):
                continue
            pygame.draw.rect(tela, (70, 66, 80), o, border_radius=10)
            pygame.draw.rect(tela, (20, 18, 26), o, width=3, border_radius=10)
 
        perto_escada = jogador.rect.colliderect(self.porta_escada.rect.inflate(30, 30))
        perto_grande = jogador.rect.colliderect(self.porta_grande.rect.inflate(30, 30))
        perto_baixo = jogador.rect.colliderect(self.porta_baixo.rect.inflate(30, 30))
        self.porta_escada.desenhar(tela, 0, 0, perto_escada, tempo)
        self.porta_grande.desenhar(tela, 0, 0, perto_grande, tempo)
        self.porta_baixo.desenhar(tela, 0, 0, perto_baixo, tempo)
 
        for c in self.coracoes:
            c.desenhar(tela)
        for p in self.dorminhocos:                 # peoes dormindo (enfeite)
            p.desenhar(tela, 0, 0)
        for e in self.inimigos:
            e.desenhar(tela, 0, 0)
        for p in self.projeteis:
            p.desenhar(tela)
        if self.chave:
            self.chave.desenhar(tela)
        jogador.desenhar(tela, 0, 0)
 
        if perto_baixo:
            dica = "Pressione E para voltar"
        elif not self.limpa:
            vivos = sum(1 for i in self.inimigos if i.vivo)
            dica = f"Derrote os guardas ({vivos} restantes) - Q ataca | Q na hora da investida/tiro = PARRY"
        elif perto_escada:
            dica = "Pressione E para subir a escada"
        elif perto_grande and self.porta_grande.trancada:
            dica = "Porta trancada - precisa da chave grande"
        elif perto_grande:
            dica = "Pressione E para abrir a porta grande"
        elif self.peoes_dormem and not self.porta_grande.trancada:
            dica = "A chave grande destrancou a porta da esquerda!"
        else:
            dica = ""
        if dica:
            tela.blit(self.fonte.render(dica, True, (255, 255, 255)), (20, ALTURA_TELA - 30))
 
 

# ============================================================
# sala 4 - puzzle (top-down)
# ============================================================
COR_FUNDO = (16, 6, 20)
COR_CHAO = (46, 14, 46)
COR_BORDA = (215, 70, 205)
COR_BLOCO_CENTRAL = (36, 30, 44)
COR_TORRE = (232, 232, 238)
COR_TORRE_CONTORNO = (20, 18, 24)
COR_PORTA_BRILHO = (225, 110, 215)
COR_PAREDE = (62, 30, 70)
COR_PAREDE_SEC = (66, 33, 74)     # a parede secreta e quase igual as outras
COR_CHAO2 = (52, 18, 52)


class Sala4:
    """LABIRINTO GRANDE (a camera acompanha o jogador). Gerado por codigo, sempre igual.
    - Entrada embaixo a esquerda; a porta de cima so abre com a CHAVE do bau (bem visivel,
      num beco sem saida bem longe da entrada).
    - 3 SALOES ABERTOS com um bloco no meio e torres girando em volta (dano 3).
    - Um beco sem saida na BORDA do mapa tem uma parede secreta (parece parede normal):
      bata nela com Q pra abrir a passagem pra sala escura com o bau +vida +dano.
    - Coracoes (cura 2) escondidos em becos."""

    perspectiva = "topdown"
    NC, NR = 20, 14          # colunas x linhas de celulas
    P, T, C = 110, 20, 90    # passo da grade, espessura das paredes, largura dos corredores
    # saloes abertos 3x3: (coluna, linha, n_torres, raio da orbita, velocidade angular)
    SALOES = [(8, 5, 4, 105, 0.9), (2, 1, 4, 105, -1.0), (14, 9, 5, 110, 1.1)]

    def __init__(self):
        P, T, C = self.P, self.T, self.C
        self.largura_sala = self.NC * P + T
        self.altura_sala = self.NR * P + T
        self.fonte = pygame.font.Font(None, 26)
        self.textos = TextosFlutuantes()
        self.secreta_aberta = False
        self.tem_chave = False
        self._gerar_labirinto()
        # >>> SPRITE AQUI: assets/cenario/fundo_sala4.png (opcional), bloco_central, parede_labirinto,
        #     parede_secreta
        self.fundo = Animacao("cenario/fundo_sala4")
        self.sprite_bloco = Animacao("cenario/bloco_central")
        self.sprite_parede = Animacao("cenario/parede_labirinto")
        self.sprite_parede_secreta = Animacao("cenario/parede_secreta")
        rng = random.Random(4)
        self.sparkles = [(rng.randint(40, self.largura_sala - 40), rng.randint(40, self.altura_sala - 40),
                          rng.uniform(0, 6.28)) for _ in range(70)]

    # ---------------- geracao ----------------
    def _centro(self, cel):
        return cel[0] * self.P + self.T + self.C // 2, cel[1] * self.P + self.T + self.C // 2

    def _spawn_em(self, cel):
        cx, cy = self._centro(cel)
        return (cx - 17, cy - 27)

    def _gerar_labirinto(self):
        NC, NR, P, T, C = self.NC, self.NR, self.P, self.T, self.C
        rng = random.Random(11)
        liga = set()                              # pares de celulas ligadas (sem parede)
        vis, pilha = {(0, 0)}, [(0, 0)]
        dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
        while pilha:                              # "recursive backtracker": corredores longos e sinuosos
            c, r = pilha[-1]
            viz = [(c + dc, r + dr) for dc, dr in dirs
                   if 0 <= c + dc < NC and 0 <= r + dr < NR and (c + dc, r + dr) not in vis]
            if viz:
                n = rng.choice(viz)
                liga.add(frozenset(((c, r), n)))
                vis.add(n)
                pilha.append(n)
            else:
                pilha.pop()
        em_salao = set()
        for pc, pr, _, _, _ in self.SALOES:      # saloes abertos: derruba as paredes de dentro
            for c in range(pc, pc + 3):
                for r in range(pr, pr + 3):
                    em_salao.add((c, r))
                    if c < pc + 2:
                        liga.add(frozenset(((c, r), (c + 1, r))))
                    if r < pr + 2:
                        liga.add(frozenset(((c, r), (c, r + 1))))
        self.liga = liga

        def vizinhos(cel):
            return [(cel[0] + dc, cel[1] + dr) for dc, dr in dirs if frozenset((cel, (cel[0] + dc, cel[1] + dr))) in liga]

        inicio = (0, NR - 1)
        dist, fila = {inicio: 0}, [inicio]
        for cel in fila:                          # distancia (em celulas) desde a entrada
            for n in vizinhos(cel):
                if n not in dist:
                    dist[n] = dist[cel] + 1
                    fila.append(n)
        self.dist, self.inicio = dist, inicio
        becos = [c for c in dist if len(vizinhos(c)) == 1 and c not in em_salao and c != inicio]
        saida = max((c for c in dist if c[1] == 0 and c not in em_salao), key=dist.get)
        cel_bau = max((c for c in becos if c != saida), key=dist.get)
        borda = lambda c: c[0] in (0, NC - 1) or c[1] in (0, NR - 1)
        cands = [c for c in becos if borda(c) and c not in (saida, cel_bau)]
        if not cands:
            cands = [c for c in dist if borda(c) and c not in em_salao and c not in (inicio, saida, cel_bau)]
        cel_sec = max(cands, key=dist.get)
        usados = {inicio, saida, cel_bau, cel_sec}
        outros = sorted((c for c in becos if c not in usados), key=dist.get)
        cel_coracoes = [outros[len(outros) * k // 4] for k in (1, 2, 3)] if len(outros) >= 4 else outros[:3]
        self.cel_saida, self.cel_bau, self.cel_sec = saida, cel_bau, cel_sec

        # ---- paredes: pecas de corredor (C x T) + postes nos cantos (T x T)
        verticais, horizontais = set(), set()
        for r in range(NR):
            for c in range(NC + 1):
                if c in (0, NC) or frozenset(((c - 1, r), (c, r))) not in liga:
                    verticais.add((c, r))
        for r in range(NR + 1):
            for c in range(NC):
                if r in (0, NR) or frozenset(((c, r - 1), (c, r))) not in liga:
                    horizontais.add((c, r))
        postes = []
        for pc in range(NC + 1):
            for pr in range(NR + 1):
                if ((pc, pr - 1) in verticais or (pc, pr) in verticais
                        or (pc - 1, pr) in horizontais or (pc, pr) in horizontais):
                    postes.append(pygame.Rect(pc * P, pr * P, T, T))
        c, r = cel_sec                            # parede secreta: peca da borda do mapa
        if c == 0:
            chave, self.parede_secreta = ("v", (0, r)), pygame.Rect(0, r * P + T, T, C)
            porta_r = pygame.Rect(0, r * P + T + 10, 40, C - 20)
        elif c == NC - 1:
            chave, self.parede_secreta = ("v", (NC, r)), pygame.Rect(NC * P, r * P + T, T, C)
            porta_r = pygame.Rect(NC * P - 20, r * P + T + 10, 40, C - 20)
        elif r == NR - 1:
            chave, self.parede_secreta = ("h", (c, NR)), pygame.Rect(c * P + T, NR * P, C, T)
            porta_r = pygame.Rect(c * P + T + 10, NR * P - 20, C - 20, 40)
        else:
            chave, self.parede_secreta = ("h", (c, 0)), pygame.Rect(c * P + T, 0, C, T)
            porta_r = pygame.Rect(c * P + T + 10, 0, C - 20, 40)
        (verticais if chave[0] == "v" else horizontais).discard(chave[1])
        pecas = [pygame.Rect(c * P, r * P + T, T, C) for c, r in verticais]
        pecas += [pygame.Rect(c * P + T, r * P, C, T) for c, r in horizontais]
        self.paredes = pecas + postes
        self.porta_secreta = Porta(porta_r.x, porta_r.y, porta_r.w, porta_r.h, destino="sala4s",
                                   cor_brilho=(255, 215, 120), sprite="secreta")

        # ---- saloes: bloco no meio + torres girando
        self.blocos, self.torres = [], []
        for pc, pr, n, raio, vel in self.SALOES:
            cx, cy = pc * P + T + (3 * P - T) // 2, pr * P + T + (3 * P - T) // 2
            self.blocos.append(pygame.Rect(cx - 40, cy - 40, 80, 80))
            self.torres += [TorreObstaculo(cx, cy, raio, angulo_inicial=i * 2 * math.pi / n, vel_angular=vel,
                                           cor=COR_TORRE, cor_contorno=COR_TORRE_CONTORNO) for i in range(n)]
        self.solidos = self.paredes + self.blocos + [self.parede_secreta]
        self._i_secreta = len(self.solidos) - 1

        # ---- itens e portas
        bx, by = self._centro(cel_bau)
        self.bau = Bau(bx - 20, by - 15, cura=5)                 # bau da chave: SEMPRE visivel
        self.coracoes = [Coracao(self._centro(c)[0] - 11, self._centro(c)[1] - 10) for c in cel_coracoes]
        self.porta_baixo = Porta(T, self.NR * P - 10, C, 30, destino="sala3",
                                 cor_brilho=COR_PORTA_BRILHO, sprite="escada_baixo")
        self.porta_saida = Porta(saida[0] * P + T, 0, C, 30, destino="sala5", cor_brilho=COR_PORTA_BRILHO,
                                 trancada=True, precisa_chave="labirinto", sprite="escada")
        self.spawn = self._spawn_em(inicio)
        self.spawns = {"sala5": self._spawn_em(saida), "sala4s": self._spawn_em(cel_sec)}

    # ---------------- jogo ----------------
    def entrar(self, jogador, origem=None):
        jogador.x, jogador.y = self.spawns.get(origem, self.spawn)
        jogador.knock_timer = 0

    def _camera(self, jogador):
        cx = jogador.x + jogador.largura / 2 - LARGURA_TELA / 2
        cy = jogador.y + jogador.altura / 2 - ALTURA_TELA / 2
        return (int(max(0, min(cx, self.largura_sala - LARGURA_TELA))),
                int(max(0, min(cy, self.altura_sala - ALTURA_TELA))))

    def _perto(self, jogador, alvo, folga=20):
        """alvo = Rect ou qualquer objeto com .rect (bau, porta)."""
        rect = getattr(alvo, "rect", alvo)
        return jogador.rect.colliderect(rect.inflate(folga, folga))

    def atualizar(self, jogador, teclas, eventos, dt, estado_jogo):
        zona = jogador.rect.inflate(300, 300)      # so testa colisao com as paredes aqui perto
        obst = [self.solidos[i] for i in zona.collidelistall(self.solidos)]
        jogador.atualizar_topdown(teclas, obst)
        jogador.x = max(0, min(jogador.x, self.largura_sala - jogador.largura))
        jogador.y = max(0, min(jogador.y, self.altura_sala - jogador.altura))
        jogador.atualizar_timers(dt)

        for torre in self.torres:
            torre.atualizar(dt)
            if jogador.rect.colliderect(torre.rect):
                jogador.receber_dano(torre.dano_contato, torre.rect.center)
        for c in self.coracoes:
            if not c.coletado and jogador.rect.colliderect(c.rect):
                c.coletado = True
                jogador.curar(2)
                self.textos.adicionar("+2", c.rect.centerx, c.y - 6, (235, 90, 100))

        self.tem_chave = estado_jogo.chave_labirinto > 0
        if self.tem_chave:
            self.porta_saida.trancada = False

        destino = None
        for evento in eventos:
            if evento.type == pygame.KEYDOWN:
                if evento.key == TECLA_ATAQUE:
                    jogador.tentar_atacar(topdown=True)
                if evento.key == TECLA_INTERAGIR:
                    if not self.bau.aberto and self._perto(jogador, self.bau):
                        self.bau.abrir(jogador)
                        estado_jogo.chave_labirinto += 1
                        estado_jogo.flags["sala4_bau_pego"] = True
                        self.tem_chave = True
                        self.porta_saida.trancada = False
                        self.textos.adicionar("CHAVE!", self.bau.rect.centerx, self.bau.y - 10, (230, 200, 90))
                    elif self.secreta_aberta and self._perto(jogador, self.porta_secreta, 30):
                        destino = self.porta_secreta.destino
                    elif self._perto(jogador, self.porta_saida, 30) and not self.porta_saida.trancada:
                        destino = self.porta_saida.destino
                    elif self._perto(jogador, self.porta_baixo, 30):
                        destino = self.porta_baixo.destino

        # parede secreta: um golpe de espada abre (nao tem nenhuma dica na tela)
        hb = jogador.hitbox_ataque
        if hb and not self.secreta_aberta and hb.colliderect(self.parede_secreta):
            self.secreta_aberta = True
            self.solidos[self._i_secreta] = pygame.Rect(-9999, -9999, 1, 1)
            hitstop(0.06)
            tremer(0.3, 5)
        return destino

    def desenhar(self, tela, jogador, tempo):
        P, T, C = self.P, self.T, self.C
        cam_x, cam_y = self._camera(jogador)
        vista = pygame.Rect(cam_x, cam_y, LARGURA_TELA, ALTURA_TELA)

        img_fundo = self.fundo.frame()
        if img_fundo:
            desenhar_fundo(tela, img_fundo, COR_FUNDO, cam_x, self.largura_sala)
        else:
            tela.fill(COR_FUNDO)
            pygame.draw.rect(tela, COR_CHAO, pygame.Rect(0, 0, self.largura_sala, self.altura_sala).move(-cam_x, -cam_y))
            for c in range(max(0, cam_x // P), min(self.NC, (cam_x + LARGURA_TELA) // P + 1)):
                for r in range(max(0, cam_y // P), min(self.NR, (cam_y + ALTURA_TELA) // P + 1)):
                    if (c + r) % 2:
                        pygame.draw.rect(tela, COR_CHAO2, (c * P + T - cam_x, r * P + T - cam_y, C, C))

        for x, y, fase in self.sparkles:
            if vista.collidepoint(x, y):
                desenhar_sparkle(tela, x - cam_x, y - cam_y, 5, 90 + 90 * math.sin(tempo * 2 + fase))

        # paredes (so as que aparecem na tela)
        visiveis = [self.paredes[i] for i in vista.inflate(40, 40).collidelistall(self.paredes)]
        if self.sprite_parede.existe:
            for r in visiveis:
                desenhar_esticado(tela, self.sprite_parede, r.move(-cam_x, -cam_y))
        else:
            for r in visiveis:                       # contorno unico: 1o passo contorno, 2o passo miolo
                pygame.draw.rect(tela, COR_BORDA, r.move(-cam_x, -cam_y).inflate(4, 4))
            for r in visiveis:
                pygame.draw.rect(tela, COR_PAREDE, r.move(-cam_x, -cam_y))

        # parede secreta: quase igual as outras (so um tiquinho diferente de perto)
        ps = self.parede_secreta.move(-cam_x, -cam_y)
        if not self.secreta_aberta:
            if vista.colliderect(self.parede_secreta):
                if not desenhar_esticado(tela, self.sprite_parede_secreta, ps):
                    pygame.draw.rect(tela, COR_BORDA, ps.inflate(4, 4))
                    pygame.draw.rect(tela, COR_PAREDE_SEC, ps)
                    d = math.hypot(jogador.rect.centerx - self.parede_secreta.centerx,
                                   jogador.rect.centery - self.parede_secreta.centery)
                    cor = (18, 6, 24) if d < 90 else (50, 22, 58)       # rachadura so aparece de pertinho
                    pygame.draw.lines(tela, cor, False, [(ps.x + 3, ps.y + 4), (ps.centerx, ps.centery - 3),
                                                         (ps.centerx - 5, ps.centery + 4), (ps.right - 3, ps.bottom - 4)], 1)
        else:
            pygame.draw.rect(tela, (10, 4, 14), ps)
            self.porta_secreta.desenhar(tela, cam_x, cam_y, self._perto(jogador, self.porta_secreta, 30), tempo)

        for b in self.blocos:
            br = b.move(-cam_x, -cam_y)
            if not vista.colliderect(b):
                continue
            if not desenhar_esticado(tela, self.sprite_bloco, br):
                pygame.draw.rect(tela, COR_BLOCO_CENTRAL, br)
                desenhar_moldura_rabiscada(tela, br, COR_BORDA, seed=22, amplitude=2, passo=10, largura=2)

        for c in self.coracoes:
            c.desenhar(tela, cam_x, cam_y)
        self.bau.desenhar(tela, cam_x, cam_y)
        for torre in self.torres:
            if vista.inflate(60, 60).colliderect(torre.rect):
                torre.desenhar(tela, cam_x, cam_y)

        perto_porta = self._perto(jogador, self.porta_saida, 30)
        perto_baixo = self._perto(jogador, self.porta_baixo, 30)
        self.porta_saida.desenhar(tela, cam_x, cam_y, perto_porta, tempo)
        self.porta_baixo.desenhar(tela, cam_x, cam_y, perto_baixo, tempo)
        jogador.desenhar(tela, cam_x, cam_y)
        self.textos.desenhar(tela, cam_x, cam_y)

        # setinha-bussola pra porta de cima (so depois de pegar a chave)
        if self.tem_chave and not perto_porta:
            dx = self.porta_saida.rect.centerx - jogador.rect.centerx
            dy = self.porta_saida.rect.centery - jogador.rect.centery
            d = math.hypot(dx, dy)
            if d > 160:
                ux, uy = dx / d, dy / d
                bx = jogador.rect.centerx - cam_x + ux * 80
                by = jogador.rect.centery - cam_y + uy * 80
                pygame.draw.polygon(tela, (255, 215, 120), [(bx + ux * 14, by + uy * 14),
                                                            (bx - uy * 8, by + ux * 8), (bx + uy * 8, by - ux * 8)])

        perto_secreto = (not self.secreta_aberta) and self._perto(jogador, self.parede_secreta, 20) \
            and jogador.atacando_timer > 0
        dica = ""
        if not self.bau.aberto and self._perto(jogador, self.bau):
            dica = "Um baú! Pressione E para abrir"
        elif self.secreta_aberta and self._perto(jogador, self.porta_secreta, 30):
            dica = "Uma passagem secreta! Pressione E para entrar"
        elif perto_baixo:
            dica = "Pressione E para voltar"
        elif perto_porta:
            dica = "Porta trancada - ache o baú com a chave" if self.porta_saida.trancada else "Pressione E para seguir"
        elif self.tem_chave:
            dica = "Você tem a chave! Siga a seta até a porta de cima"
        elif not self.bau.aberto:
            dica = "Ache o baú com a chave no labirinto (cuidado com as torres)"
        if dica:
            tela.blit(self.fonte.render(dica, True, (255, 255, 255)), (20, ALTURA_TELA - 30))

# ============================================================
# sala 4-secreta - sala escura com um CAMINHO DE LUZES ate o bau (top-down)
# ============================================================
LUZ_DO_JOGADOR = 42     # raio da luzinha que acompanha o jogador (0 = escuridao total)


def _pontos_ao_longo(poli, passo):
    """Pontos igualmente espacados ao longo de uma poligonal."""
    pts, falta = [poli[0]], passo
    for (x1, y1), (x2, y2) in zip(poli, poli[1:]):
        seg, pos = math.hypot(x2 - x1, y2 - y1), 0.0
        while seg - pos >= falta:
            pos += falta
            pts.append((x1 + (x2 - x1) * pos / seg, y1 + (y2 - y1) * pos / seg))
            falta = passo
        falta -= seg - pos
    if math.hypot(pts[-1][0] - poli[-1][0], pts[-1][1] - poli[-1][1]) > passo * 0.4:
        pts.append(poli[-1])
    return pts


def _dist_ponto_poli(p, poli):
    melhor = 1e9
    for (x1, y1), (x2, y2) in zip(poli, poli[1:]):
        dx, dy = x2 - x1, y2 - y1
        t = max(0, min(1, ((p[0] - x1) * dx + (p[1] - y1) * dy) / ((dx * dx + dy * dy) or 1)))
        melhor = min(melhor, math.hypot(p[0] - (x1 + dx * t), p[1] - (y1 + dy * t)))
    return melhor


class Sala4Secreta:
    """Sala grande e TOTALMENTE escura (a camera acompanha o jogador). Nao tem luz em cima do bau:
    existe uma TRILHA DE LUZES que o jogador precisa ACHAR. Cada luz so se acende quando voce chega
    perto dela (e so depois da anterior), e a trilha leva ate o bau: +5 de vida maxima e +1 de dano."""

    perspectiva = "topdown"
    LARGURA, ALTURA = 1400, 1000
    # caminho que as luzes seguem (a primeira fica longe da entrada; a ultima fica em cima do bau)
    TRILHA = [(420, 820), (700, 640), (640, 360), (520, 170), (900, 150), (1100, 400), (1230, 720), (1250, 830)]

    def __init__(self):
        self.largura_sala, self.altura_sala = self.LARGURA, self.ALTURA
        self.spawn = (110, self.ALTURA - 120)
        self.spawns = {}
        self.porta_baixo = Porta(60, self.ALTURA - 30, 90, 30, destino="sala4",
                                 cor_brilho=(255, 215, 120), sprite="escada_baixo")
        self.bau = Bau(1230, 860, cura=0)
        self.pedestal = pygame.Rect(self.bau.x - 20, self.bau.y + 18, 80, 26)   # so enfeite
        self.textos = TextosFlutuantes()
        self.fonte = pygame.font.Font(None, 26)
        self.tempo_procurando = 0.0
        # >>> SPRITE AQUI: assets/cenario/fundo_sala4s.png, assets/cenario/pedestal.png,
        #     assets/objetos/luz_guia.png (30x30, a luzinha da trilha)
        self.fundo = Animacao("cenario/fundo_sala4s")
        self.sprite_pedestal = Animacao("cenario/pedestal")
        self.sprite_luz = Animacao("objetos/luz_guia")

        pts = _pontos_ao_longo(self.TRILHA, 120)
        self.luzes = [{"x": x, "y": y, "raio_rev": 300 if i == 0 else 190, "rev": False, "t0": 0.0,
                       "fase": random.Random(i).uniform(0, 6.28)} for i, (x, y) in enumerate(pts)]

        rng = random.Random(5)                    # pilares escondidos no escuro (longe da trilha)
        poli = [(127, 907)] + self.TRILHA
        self.pilares = []
        for _ in range(900):
            if len(self.pilares) >= 16:
                break
            r = pygame.Rect(rng.randint(40, self.LARGURA - 120), rng.randint(40, self.ALTURA - 120),
                            rng.randint(40, 80), rng.randint(40, 80))
            if _dist_ponto_poli(r.center, poli) < 110 + max(r.w, r.h) / 2:
                continue
            if any(r.colliderect(p.inflate(80, 80)) for p in self.pilares) or r.colliderect(self.pedestal.inflate(160, 160)):
                continue
            self.pilares.append(r)

    def entrar(self, jogador, origem=None):
        jogador.x, jogador.y = self.spawns.get(origem, self.spawn)
        jogador.knock_timer = 0

    def _camera(self, jogador):
        cx = jogador.x + jogador.largura / 2 - LARGURA_TELA / 2
        cy = jogador.y + jogador.altura / 2 - ALTURA_TELA / 2
        return (int(max(0, min(cx, self.largura_sala - LARGURA_TELA))),
                int(max(0, min(cy, self.altura_sala - ALTURA_TELA))))

    def atualizar(self, jogador, teclas, eventos, dt, estado_jogo):
        jogador.atualizar_topdown(teclas, self.pilares)
        jogador.x = max(20, min(jogador.x, self.largura_sala - jogador.largura - 20))
        jogador.y = max(20, min(jogador.y, self.altura_sala - jogador.altura - 20))
        jogador.atualizar_timers(dt)

        agora = _agora()
        pc = jogador.rect.center
        for i, l in enumerate(self.luzes):         # acende as luzes em ordem, so de pertinho
            if not l["rev"] and (i == 0 or self.luzes[i - 1]["rev"]) \
                    and math.hypot(pc[0] - l["x"], pc[1] - l["y"]) < l["raio_rev"]:
                l["rev"], l["t0"] = True, agora
        if not self.luzes[0]["rev"]:
            self.tempo_procurando += dt

        destino = None
        for evento in eventos:
            if evento.type == pygame.KEYDOWN:
                if evento.key == TECLA_ATAQUE:
                    jogador.tentar_atacar(topdown=True)
                if evento.key == TECLA_INTERAGIR:
                    if not self.bau.aberto and jogador.rect.colliderect(self.bau.rect.inflate(40, 40)):
                        self.bau.abrir(jogador)
                        jogador.vida_max += 5          # +5 de vida maxima (e ja cura os 5)
                        jogador.curar(5)
                        jogador.dano_bonus += 1        # +1 de dano
                        estado_jogo.flags["sala4_bau_secreto"] = True
                        bx, by = self.bau.rect.centerx, self.bau.y - 10
                        self.textos.adicionar("+5 VIDA", bx, by, (235, 90, 100))
                        self.textos.adicionar("+1 DANO", bx, by - 30, (255, 190, 90), atraso=0.25)
                        tremer(0.25, 4)
                    elif jogador.rect.colliderect(self.porta_baixo.rect.inflate(30, 30)):
                        destino = self.porta_baixo.destino
        return destino

    def desenhar(self, tela, jogador, tempo):
        cam_x, cam_y = self._camera(jogador)
        agora = _agora()
        img_fundo = self.fundo.frame()
        if img_fundo:
            desenhar_fundo(tela, img_fundo, (12, 10, 16), cam_x, self.largura_sala)
        else:
            for tx in range(cam_x // TAMANHO_TILE, (cam_x + LARGURA_TELA) // TAMANHO_TILE + 1):
                for ty in range(cam_y // TAMANHO_TILE, (cam_y + ALTURA_TELA) // TAMANHO_TILE + 1):
                    tela.blit(gerar_tile_pedra(tx, ty, cor1=(44, 38, 50), cor2=(36, 31, 42)),
                              (tx * TAMANHO_TILE - cam_x, ty * TAMANHO_TILE - cam_y))

        for p in self.pilares:
            pr = p.move(-cam_x, -cam_y)
            pygame.draw.rect(tela, (70, 64, 82), pr, border_radius=8)
            pygame.draw.rect(tela, (22, 18, 28), pr, width=3, border_radius=8)
        ped = self.pedestal.move(-cam_x, -cam_y)
        if not desenhar_esticado(tela, self.sprite_pedestal, ped):
            pygame.draw.rect(tela, (80, 74, 92), ped, border_radius=6)
            pygame.draw.rect(tela, (25, 20, 32), ped, width=3, border_radius=6)
        self.bau.desenhar(tela, cam_x, cam_y)

        luzes_tela = []
        for l in self.luzes:
            if not l["rev"]:
                continue
            k = min(1.0, (agora - l["t0"]) / 0.7)                       # acende devagarzinho
            lx, ly = l["x"] - cam_x, l["y"] - cam_y
            raio = 70 * k + math.sin(tempo * 4 + l["fase"]) * 3
            if -100 < lx < LARGURA_TELA + 100 and -100 < ly < ALTURA_TELA + 100:
                tela.blit(criar_luz(int(raio) + 1, int(60 * k), (255, 200, 110)), (lx - max(2, int(raio) + 1), ly - max(2, int(raio) + 1)))
                if not desenhar_centro(tela, self.sprite_luz, pygame.Rect(lx - 15, ly - 15, 30, 30)):
                    pygame.draw.circle(tela, (255, 235, 170), (int(lx), int(ly)), 5)
                    pygame.draw.circle(tela, (255, 190, 90), (int(lx), int(ly)), 9, 2)
                desenhar_sparkle(tela, lx + math.sin(tempo + l["fase"]) * 14, ly - 10 + math.cos(tempo * 0.8 + l["fase"]) * 10,
                                 3, 120 + 80 * math.sin(tempo * 2 + l["fase"]), (255, 225, 160))
            luzes_tela.append((lx, ly, raio, 235 * k))

        self.porta_baixo.desenhar(tela, cam_x, cam_y,
                                  jogador.rect.colliderect(self.porta_baixo.rect.inflate(30, 30)), tempo)
        jogador.desenhar(tela, cam_x, cam_y)

        luzes_tela.append((self.porta_baixo.rect.centerx - cam_x, self.porta_baixo.rect.centery - cam_y, 55, 110))
        if LUZ_DO_JOGADOR > 0:
            luzes_tela.append((jogador.rect.centerx - cam_x, jogador.rect.centery - cam_y, LUZ_DO_JOGADOR, 170))
        aplicar_escuridao(tela, luzes_tela, alpha=252)

        self.textos.desenhar(tela, cam_x, cam_y)
        if not self.bau.aberto and jogador.rect.colliderect(self.bau.rect.inflate(40, 40)):
            dica = "Um baú! Pressione E para abrir"
        elif jogador.rect.colliderect(self.porta_baixo.rect.inflate(30, 30)):
            dica = "Pressione E para voltar"
        elif not self.luzes[0]["rev"]:
            dica = "Está tudo escuro... procure uma luz"
            if self.tempo_procurando > 45:
                dica = "Dica: a primeira luz fica a nordeste da entrada"
        elif not self.bau.aberto:
            dica = "Siga as luzes"
        else:
            dica = ""
        if dica:
            tela.blit(self.fonte.render(dica, True, (255, 255, 255)), (20, ALTURA_TELA - 30))

# ============================================================
# sala 5 - mini-boss (plataforma)
# ============================================================
class Sala5MiniBoss(SalaPlataforma):
    def __init__(self):
        largura, chao_y = 1400, 480
        super().__init__(largura, chao_y, [pygame.Rect(0, chao_y, largura, 200)], (150, chao_y - 54), None)
        self.miniboss = TorreMiniBoss(largura - 300, chao_y, 20, largura - 20)
        self.inimigos = [self.miniboss]
        self.derrotado = False
        self.vinheta = criar_vinheta(LARGURA_TELA, ALTURA_TELA, forca=160)
        # >>> SPRITE AQUI: assets/cenario/fundo_sala5.png
        self.fundo = Animacao("cenario/fundo_sala5")
        self.porta_volta = Porta(20, chao_y - 150, 90, 150, destino="sala4")
 
    def entrar(self, jogador, origem=None):
        super().entrar(jogador, origem)
        b = self.miniboss
        if b.vivo:      # saiu no meio da luta: a torre "dorme" de novo
            b.estado, b.timer, b.vel_y = "dormindo", 0, 0
            b.x, b.y = self.largura_sala - 300, self.chao_y - b.altura
            b.atordoado_timer, b.parry_no_pouso = 0, False
 
    def atualizar_extra(self, jogador, dt, estado_jogo):
        if not self.miniboss.vivo and not self.derrotado:
            self.derrotado = True
            estado_jogo.chave_grande += 1
            estado_jogo.flags["sala5_miniboss_derrotado"] = True
            tremer(0.5, 8)
 
    def desenhar(self, tela, jogador, tempo):
        camera_x = self.camera_x(jogador)
        desenhar_fundo(tela, self.fundo.frame(), (14, 12, 20), camera_x, self.largura_sala)
        desenhar_bloco_pedra(tela, self.colisores[0], camera_x)
        self.desenhar_entidades(tela, jogador, tempo, camera_x)
 
        b = self.miniboss
        if b.vivo and b.ativo:
            pct = max(0, b.vida / b.vida_max)
            pygame.draw.rect(tela, (40, 10, 10), (200, ALTURA_TELA - 40, 400, 10))
            pygame.draw.rect(tela, (200, 60, 60), (200, ALTURA_TELA - 40, 400 * pct, 10))
            self.escrever(tela, "Torre: Q na hora da investida/salto = PARRY (ela fica atordoada)")
        elif b.vivo:
            self.escrever(tela, "Uma torre guarda a chave grande...")
        else:
            self.escrever(tela, "Torre derrotada! Chave grande conquistada - volte à sala dos guardas.")
# ============================================================
# sala 6 - parkour vertical (plataforma)
# ============================================================
class Sala6Parkour(SalaPlataforma):
    def __init__(self):
        largura, chao_y = 1000, 560
        colisores = [
            pygame.Rect(0, chao_y, 300, 60),
            pygame.Rect(600, 260, 260, 20),   # plataforma final, perto da porta
        ]
        super().__init__(largura, chao_y, colisores, (150, chao_y - 54),
                         Porta(760, 260 - 150, 90, 150, destino="sala7"))
        self.alvos_pogo = [AlvoPogo(340, 460), AlvoPogo(420, 400), AlvoPogo(500, 340), AlvoPogo(580, 300)]
        self.espinhos = [Espinhos(300, chao_y + 15, 700, 100)]   # fosso de espinhos
        self.vinheta = criar_vinheta(LARGURA_TELA, ALTURA_TELA, forca=170)
        # >>> SPRITE AQUI: assets/cenario/fundo_sala6.png
        self.fundo = Animacao("cenario/fundo_sala6")
        self.porta_volta = Porta(20, chao_y - 150, 90, 150, destino="voltar")  # "voltar" = sala de onde veio
        self.spawns = {"sala7": (680, 260 - 54)}

    def desenhar(self, tela, jogador, tempo):
        camera_x = self.camera_x(jogador)
        desenhar_fundo(tela, self.fundo.frame(), (10, 10, 16), camera_x, self.largura_sala)
        desenhar_bloco_pedra(tela, self.colisores[0], camera_x)
        desenhar_plataforma_fina(tela, self.colisores[1], camera_x)
        perto = self.desenhar_entidades(tela, jogador, tempo, camera_x)

        dica = "Pogo (S + Q no ar) nas lamparinas pra subir. Espinhos embaixo!"
        if perto:
            dica = "Pressione E para enfrentar o chefe final"
        self.escrever(tela, dica)


# ============================================================
# inimigos novos de plataforma
# ============================================================
class Rastejante(Inimigo):
    """Bichinho do chao: anda de um lado pro outro."""

    def __init__(self, x, chao_y, x_min, x_max):
        super().__init__(x, chao_y - 30, 46, 30, vida=6, dano_contato=2, cor=(150, 110, 90))
        self.x_min, self.x_max = x_min, x_max
        self.dir = random.choice((-1, 1))
        # >>> SPRITE AQUI: assets/rastejante/idle, andar
        self.animador = Animador("rastejante", {"idle": {}, "andar": {}}, **SPRITE_AJUSTE["rastejante"])

    def atualizar(self, jogador, dt):
        if not self.vivo:
            return
        self.atualizar_timers(dt)
        if abs(self.kx) > 0.3:
            self.x += self.kx
            self.kx *= 0.82
        else:
            self.kx = 0
            self.x += 1.4 * self.dir
        if self.x <= self.x_min:
            self.dir = 1
        elif self.x + self.largura >= self.x_max:
            self.dir = -1
        self.x = max(self.x_min, min(self.x, self.x_max - self.largura))
        self.olhando_direita = self.dir > 0

    def desenhar(self, tela, camera_x, camera_y):
        if not self.vivo:
            return
        if self.desenhar_sprite(tela, camera_x, camera_y, "andar", flip=not self.olhando_direita):
            self.desenhar_barra_vida(tela, camera_x, camera_y)
            return
        r = self.rect.move(-camera_x, -camera_y)
        cor = (255, 255, 255) if self.invencivel_timer > 0 else self.cor
        pygame.draw.rect(tela, cor, r, border_radius=10)
        ox = 28 if self.olhando_direita else 8
        pygame.draw.rect(tela, (20, 10, 10), (r.x + ox, r.y + 8, 8, 8))
        self.desenhar_barra_vida(tela, camera_x, camera_y)


class Voador(Inimigo):
    """Inseto que voa em 8 em volta de um ponto. Da pra fazer pogo nele."""

    def __init__(self, cx, cy, amp_x=100, amp_y=40):
        super().__init__(cx - 19, cy - 15, 38, 30, vida=6, dano_contato=2, cor=(120, 200, 140))
        self.cx, self.cy, self.amp_x, self.amp_y = cx, cy, amp_x, amp_y
        self.t = random.uniform(0, 6.28)
        # >>> SPRITE AQUI: assets/voador/idle, voar
        self.animador = Animador("voador", {"idle": {}, "voar": {}}, **SPRITE_AJUSTE["voador"])

    def atualizar(self, jogador, dt):
        if not self.vivo:
            return
        self.atualizar_timers(dt)
        if abs(self.kx) + abs(self.ky) > 0.3:
            self.x += self.kx
            self.y += self.ky
            self.kx *= 0.82
            self.ky *= 0.82
            return
        self.t += dt * 1.6
        alvo_x = self.cx + math.sin(self.t) * self.amp_x - self.largura / 2
        alvo_y = self.cy + math.sin(self.t * 2) * self.amp_y - self.altura / 2
        self.x += (alvo_x - self.x) * 0.1
        self.y += (alvo_y - self.y) * 0.1
        self.olhando_direita = math.cos(self.t) > 0

    def desenhar(self, tela, camera_x, camera_y):
        if not self.vivo:
            return
        if self.desenhar_sprite(tela, camera_x, camera_y, "voar", flip=not self.olhando_direita):
            self.desenhar_barra_vida(tela, camera_x, camera_y)
            return
        r = self.rect.move(-camera_x, -camera_y)
        cor = (255, 255, 255) if self.invencivel_timer > 0 else self.cor
        asa = 8 + int(6 * math.sin(_agora() * 25))
        pygame.draw.ellipse(tela, cor, r)
        pygame.draw.ellipse(tela, (200, 240, 210), (r.centerx - 20, r.top - asa // 2, 16, asa))
        pygame.draw.ellipse(tela, (200, 240, 210), (r.centerx + 4, r.top - asa // 2, 16, asa))
        self.desenhar_barra_vida(tela, camera_x, camera_y)



# ============================================================
# sala 7 - galeria dos rastejantes (plataforma)
# ============================================================
class Sala7Galeria(SalaPlataforma):
    def __init__(self):
        largura, chao_y = 2000, 480
        colisores = [
            pygame.Rect(0, chao_y, 700, 200),
            pygame.Rect(900, chao_y, 1100, 200),
            pygame.Rect(1150, chao_y - 90, 140, 20),
        ]
        super().__init__(largura, chao_y, colisores, (140, chao_y - 54),
                         Porta(largura - 140, chao_y - 150, 90, 150, destino="sala8"))
        self.espinhos = [Espinhos(700, chao_y + 60, 200)]
        self.alvos_pogo = [AlvoPogo(785, chao_y - 85)]
        self.inimigos = [Rastejante(400, chao_y, 300, 650),
                         Rastejante(1000, chao_y, 950, 1350),
                         Rastejante(1500, chao_y, 1450, 1900)]
        self.vinheta = criar_vinheta(LARGURA_TELA, ALTURA_TELA, forca=160)
        self.neblina = criar_particulas_neblina(20, largura, chao_y)
        # >>> SPRITE AQUI: assets/cenario/fundo_sala7.png
        self.fundo = Animacao("cenario/fundo_sala7")
        self.porta_volta = Porta(20, chao_y - 150, 90, 150, destino="sala6")
        self.spawns = {"sala8": (largura - 260, chao_y - 54)}

    def desenhar(self, tela, jogador, tempo):
        camera_x = self.camera_x(jogador)
        desenhar_fundo(tela, self.fundo.frame(), (14, 14, 22), camera_x, self.largura_sala)
        desenhar_bloco_pedra(tela, self.colisores[0], camera_x)
        desenhar_bloco_pedra(tela, self.colisores[1], camera_x)
        desenhar_plataforma_fina(tela, self.colisores[2], camera_x)
        desenhar_neblina(tela, self.neblina, self.largura_sala, LARGURA_TELA, ALTURA_TELA, camera_x)
        perto = self.desenhar_entidades(tela, jogador, tempo, camera_x)
        self.escrever(tela, "Pressione E para seguir" if perto else "Cuidado com os rastejantes. Use o pogo no fosso!")


# ============================================================
# sala 8 - travessia de pogo (plataforma): so cordas + pilar e obstaculos
# Apague a class Sala8Salao e cole este bloco no lugar.
# ============================================================
class Lamina:
    """Serra pendurada numa corrente que sobe e desce. So causa dano ao encostar."""

    def __init__(self, x, y_alto, y_baixo, vel=1.6, fase=0.0):
        self.x = x
        self.largura = self.altura = 44
        self.y_alto, self.y_baixo = y_alto, y_baixo     # y do TOPO da serra (em cima / embaixo)
        self.vel, self.t = vel, fase
        self.dano_contato = 2
        self.y = y_alto
        self._mover(0)
        # >>> SPRITE AQUI: assets/objetos/lamina.png (44x44, centralizada na hitbox)
        self.anim = Animacao("objetos/lamina")

    def _mover(self, dt):
        self.t += dt * self.vel
        k = (math.sin(self.t) + 1) / 2
        self.y = self.y_alto + (self.y_baixo - self.y_alto) * k

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.largura, self.altura)

    def atualizar(self, dt):
        self._mover(dt)

    def desenhar(self, tela, camera_x, camera_y=0):
        r = self.rect.move(-camera_x, -camera_y)
        pygame.draw.line(tela, (90, 80, 60), (r.centerx, 0), (r.centerx, r.top), 2)   # corrente
        if desenhar_centro(tela, self.anim, r):
            if DEBUG["hitbox"]:
                pygame.draw.rect(tela, (0, 255, 0), r, 1)
            return
        cx, cy = r.center
        ang0 = _agora() * 8
        for i in range(8):                               # dentes girando
            a = ang0 + i * math.pi / 4
            p1 = (cx + math.cos(a) * 18, cy + math.sin(a) * 18)
            p2 = (cx + math.cos(a + 0.2) * 26, cy + math.sin(a + 0.2) * 26)
            p3 = (cx + math.cos(a + 0.4) * 18, cy + math.sin(a + 0.4) * 18)
            pygame.draw.polygon(tela, (190, 195, 215), [p1, p2, p3])
        pygame.draw.circle(tela, (150, 155, 175), (cx, cy), 19)
        pygame.draw.circle(tela, (50, 52, 70), (cx, cy), 19, 3)
        pygame.draw.circle(tela, (50, 52, 70), (cx, cy), 5)


class Sala8Pogo(SalaPlataforma):
    """Percurso: [inicio] -> cordas (1 serra) -> PILAR (pausa/ponto seguro) -> cordas (2 serras)
    -> [outro lado] espinhos no chao + 1 lamina -> porta."""
 
    def __init__(self):
        largura, chao_y = 2500, 480
        self.pilar = pygame.Rect(1040, chao_y - 40, 140, 240)       # topo a 40px acima do chao
        colisores = [
            pygame.Rect(0, chao_y, 400, 200),         # inicio
            self.pilar,                               # pausa no meio do fosso
            pygame.Rect(1880, chao_y, 620, 200),      # outro lado
        ]
        super().__init__(largura, chao_y, colisores, (140, chao_y - 54),
                         Porta(largura - 140, chao_y - 150, 90, 150, destino="sala9"))
        self.espinhos = [
            Espinhos(400, chao_y + 60, 640),          # fosso antes do pilar
            Espinhos(1180, chao_y + 60, 700),         # fosso depois do pilar
            Espinhos(1960, chao_y - 24, 100, 24),     # espinhos no chao (pular por cima)
        ]
        # lamparinas (x, y do topo): trecho 1 e trecho 2
        cordas = [(500, 420), (600, 380), (700, 420), (840, 380), (940, 420),
                  (1280, 420), (1380, 380), (1520, 420), (1660, 380), (1760, 420)]
        self.alvos_pogo = [AlvoPogo(x, y) for x, y in cordas]
        # serras ENTRE as cordas (sobem e descem cruzando o caminho do pogo)
        topo, base = chao_y - 230, chao_y - 100
        self.laminas = [
            Lamina(763, topo, base, vel=1.3, fase=0.0),            # trecho 1
            Lamina(1443, topo, base, vel=1.3, fase=0.0),           # trecho 2 (a)
            Lamina(1583, topo, base, vel=1.3, fase=math.pi),       # trecho 2 (b) - oposta a (a)
            Lamina(2150, chao_y - 200, chao_y - 44, vel=1.6),      # no chao do outro lado
        ]
        self.vinheta = criar_vinheta(LARGURA_TELA, ALTURA_TELA, forca=170)
        self.neblina = criar_particulas_neblina(20, largura, chao_y)
        # >>> SPRITE AQUI: assets/cenario/fundo_sala8.png
        self.fundo = Animacao("cenario/fundo_sala8")
        self.porta_volta = Porta(20, chao_y - 150, 90, 150, destino="sala7")
        self.spawns = {"sala9": (largura - 260, chao_y - 54)}
 
    def atualizar_extra(self, jogador, dt, estado_jogo):
        for lam in self.laminas:
            lam.atualizar(dt)
            if jogador.rect.colliderect(lam.rect):
                jogador.receber_dano(lam.dano_contato, lam.rect.center)
 
    def desenhar(self, tela, jogador, tempo):
        camera_x = self.camera_x(jogador)
        desenhar_fundo(tela, self.fundo.frame(), (12, 10, 18), camera_x, self.largura_sala)
        for c in self.colisores:                      # inicio, pilar e outro lado (tudo de pedra)
            desenhar_bloco_pedra(tela, c, camera_x)
        desenhar_neblina(tela, self.neblina, self.largura_sala, LARGURA_TELA, ALTURA_TELA, camera_x)
        for lam in self.laminas:
            lam.desenhar(tela, camera_x)
        perto = self.desenhar_entidades(tela, jogador, tempo, camera_x)
 
        if perto:
            dica = "Pressione E para seguir"
        elif jogador.x < 450:
            dica = "Sem chão à frente: pogo (S + Q no ar) nas lamparinas pra atravessar!"
        elif jogador.x < self.pilar.left - 20:
            dica = "Uma serra no caminho! Fique quicando na lamparina e espere a hora de passar."
        elif jogador.x <= self.pilar.right:
            dica = "Um pilar de pedra: respire! Se cair, você volta pra cá. Mais serras à frente."
        elif jogador.x < 1880:
            dica = "Duas serras em sequência. Cada uma sobe quando a outra desce!"
        else:
            dica = "Pule os espinhos e desvie da lâmina."
        self.escrever(tela, dica)
 
# ============================================================
# sala 9 - abismo (plataforma, pogo + insetos)
# ============================================================
class Sala9Abismo(SalaPlataforma):
    def __init__(self):
        largura, chao_y = 1900, 480
        colisores = [
            pygame.Rect(0, chao_y, 400, 200),
            pygame.Rect(700, chao_y - 90, 140, 20),
            pygame.Rect(1100, 300, 140, 20),
            pygame.Rect(1500, chao_y, 400, 200),
        ]
        super().__init__(largura, chao_y, colisores, (140, chao_y - 54),
                         Porta(largura - 140, chao_y - 150, 90, 150, destino="sala10"))
        self.espinhos = [Espinhos(400, chao_y + 60, 1100)]
        self.alvos_pogo = [AlvoPogo(500, 420), AlvoPogo(580, 380), AlvoPogo(960, 340),
                           AlvoPogo(1320, 340), AlvoPogo(1410, 400)]
        self.inimigos = [Voador(900, 290), Voador(1350, 240)]
        self.vinheta = criar_vinheta(LARGURA_TELA, ALTURA_TELA, forca=170)
        # >>> SPRITE AQUI: assets/cenario/fundo_sala9.png
        self.fundo = Animacao("cenario/fundo_sala9")
        self.porta_volta = Porta(20, chao_y - 150, 90, 150, destino="sala8")
        self.spawns = {"sala10": (largura - 260, chao_y - 54)}

    def desenhar(self, tela, jogador, tempo):
        camera_x = self.camera_x(jogador)
        desenhar_fundo(tela, self.fundo.frame(), (12, 10, 18), camera_x, self.largura_sala)
        desenhar_bloco_pedra(tela, self.colisores[0], camera_x)
        desenhar_plataforma_fina(tela, self.colisores[1], camera_x)
        desenhar_plataforma_fina(tela, self.colisores[2], camera_x)
        desenhar_bloco_pedra(tela, self.colisores[3], camera_x)
        perto = self.desenhar_entidades(tela, jogador, tempo, camera_x)
        self.escrever(tela, "Pressione E para enfrentar o Rei" if perto
                      else "Pogo nas lamparinas (e nos insetos!). Espinhos embaixo.")




# ============================================================
# sala 10 - BOSS FINAL: os Bispos Gemeos (top-down, tabuleiro)
# Cole este bloco no lugar do antigo (de "CELULA = 100" ate o fim da Sala10Boss)
# ============================================================
CELULA = 100
COLS, LINS = 8, 6


def centro_celula(c, r):
    return c * CELULA + CELULA // 2, r * CELULA + CELULA // 2


class BispoXadrez(Inimigo):
    """Bispo do tabuleiro: so anda nas DIAGONAIS. Ciclo: espera -> aviso (mostra a diagonal)
    -> investida (desliza ate a borda) -> descanso. Parry na investida atordoa.
    Em furia (vida < 50% ou o parceiro caiu) atira 4 projeteis em X ao parar.
    Aos 50% de vida dispara o RICOCHETE (os dois saem quicando nas paredes)."""

    VEL_INVESTIDA = 900        # px/s
    VEL_RICOCHETE = 480        # px/s
    TEMPO_RICOCHETE = 4.0      # s quicando
    VEL_RICOCHETE_BRAVO = 620  # px/s quando o parceiro morre (mais rapido)
    DIAGONAIS = ((1, 1), (1, -1), (-1, 1), (-1, -1))

    def __init__(self, col, lin, pasta, cor):
        cx, cy = centro_celula(col, lin)
        super().__init__(cx - 17, cy - 24, 34, 48, vida=24, dano_contato=3, cor=cor)
        # espera | aviso | investida | descanso | atordoado | aviso_rico | ricochete
        self.estado = "espera"
        self.timer = 0
        self.alvo = (cx, cy)
        self.caminho = []           # casas (col, lin) da diagonal anunciada
        self.furia = False
        self.novos_tiros = []       # projeteis novos (a sala recolhe)
        self.rico_gatilho = False   # ja usou o ricochete dos 50%?
        self.bravo = False          # parceiro morreu: mais rapido e mira no jogador
        self.vx = self.vy = 0
        # >>> SPRITE AQUI: assets/<pasta>/idle, aviso, investida, atordoado, atirar
        self.animador = Animador(pasta, {"idle": {}, "aviso": {}, "investida": {}, "atordoado": {}, "atirar": {}},
                                 fallback={"aviso": "idle", "investida": "aviso", "atordoado": "idle",
                                           "atirar": "aviso"}, **SPRITE_AJUSTE["bispo"])

    @property
    def celula(self):
        cx, cy = self.rect.center
        return (max(0, min(COLS - 1, int(cx // CELULA))), max(0, min(LINS - 1, int(cy // CELULA))))

    @property
    def parryavel(self):
        return self.vivo and self.estado in ("investida", "ricochete")

    def ser_aparado(self, jogador):
        self.atordoado_timer = TEMPO_ATORDOADO_PARRY
        self.estado, self.timer = "atordoado", TEMPO_ATORDOADO_PARRY
        self.caminho = []

    def iniciar_ricochete(self, bravo=False):
        self.estado, self.timer = "aviso_rico", (0.7 if bravo else 1.0)
        self.atordoado_timer = 0
        self.caminho = []

    def _planejar(self, jogador):
        c, r = self.celula
        ini = centro_celula(c, r)
        opcoes = []
        for dc, dr in self.DIAGONAIS:
            n = 0
            while 0 <= c + dc * (n + 1) < COLS and 0 <= r + dr * (n + 1) < LINS:
                n += 1
            if n >= 1:
                fim = centro_celula(c + dc * n, r + dr * n)
                opcoes.append((_dist_ponto_poli(jogador.rect.center, [ini, fim]), dc, dr, n))
        if not opcoes:
            return False
        opcoes.sort()
        _, dc, dr, n = opcoes[0] if random.random() < (0.95 if self.bravo else 0.7) else random.choice(opcoes)
        self.caminho = [(c + dc * i, r + dr * i) for i in range(1, n + 1)]
        self.alvo = centro_celula(*self.caminho[-1])
        return True

    def pedir_ataque(self, jogador):
        if self.vivo and self.estado == "espera" and self._planejar(jogador):
            self.estado, self.timer = "aviso", (0.45 if self.bravo else 0.6 if self.furia else 0.85)
            return True
        return False

    def _terminar_investida(self):
        self.estado, self.timer = "descanso", (0.5 if self.bravo else 0.7)
        self.caminho = []
        if self.furia:                                   # tiros em X
            cx, cy = self.rect.center
            for dx, dy in self.DIAGONAIS:
                self.novos_tiros.append(Projetil(cx, cy, dx * 3.2, dy * 3.2, dano=2, dono=self))

    def atualizar(self, jogador, dt):
        if not self.vivo:
            return
        self.atualizar_timers(dt)
        self.olhando_direita = jogador.rect.centerx > self.rect.centerx
        if self.estado == "aviso":
            self.timer -= dt
            if self.timer <= 0:
                self.estado = "investida"
        elif self.estado == "investida":
            cx, cy = self.rect.center
            dx, dy = self.alvo[0] - cx, self.alvo[1] - cy
            d = math.hypot(dx, dy)
            passo = self.VEL_INVESTIDA * dt
            if d <= passo:
                self.x, self.y = self.alvo[0] - self.largura / 2, self.alvo[1] - self.altura / 2
                self._terminar_investida()
            else:
                self.x += dx / d * passo
                self.y += dy / d * passo
        elif self.estado == "aviso_rico":
            self.timer -= dt
            if self.timer <= 0:
                if self.bravo:                             # sai MIRANDO no jogador (com um pouco de erro)
                    cx, cy = self.rect.center
                    ang = math.atan2(jogador.rect.centery - cy, jogador.rect.centerx - cx) + random.uniform(-0.3, 0.3)
                    vel = self.VEL_RICOCHETE_BRAVO
                else:
                    ang = random.uniform(0, 2 * math.pi)
                    while abs(math.cos(ang)) < 0.35 or abs(math.sin(ang)) < 0.35:   # evita direcao quase reta
                        ang = random.uniform(0, 2 * math.pi)
                    vel = self.VEL_RICOCHETE
                self.vx = math.cos(ang) * vel
                self.vy = math.sin(ang) * vel
                self.estado, self.timer = "ricochete", self.TEMPO_RICOCHETE
        elif self.estado == "ricochete":
            self.timer -= dt
            if self.bravo:                                 # curva de leve em direcao ao jogador
                cx, cy = self.rect.center
                dx, dy = jogador.rect.centerx - cx, jogador.rect.centery - cy
                d = math.hypot(dx, dy) or 1
                vel = self.VEL_RICOCHETE_BRAVO
                self.vx += dx / d * vel * 0.8 * dt
                self.vy += dy / d * vel * 0.8 * dt
                m = math.hypot(self.vx, self.vy) or 1
                self.vx, self.vy = self.vx / m * vel, self.vy / m * vel
            self.x += self.vx * dt
            self.y += self.vy * dt
            quicou = False
            if self.x < 0:
                self.x, self.vx, quicou = 0, abs(self.vx), True
            elif self.x + self.largura > LARGURA_TELA:
                self.x, self.vx, quicou = LARGURA_TELA - self.largura, -abs(self.vx), True
            if self.y < 0:
                self.y, self.vy, quicou = 0, abs(self.vy), True
            elif self.y + self.altura > ALTURA_TELA:
                self.y, self.vy, quicou = ALTURA_TELA - self.altura, -abs(self.vy), True
            if quicou:
                tremer(0.08, 2)
            if self.timer <= 0:
                self.estado, self.timer = "descanso", 1.0
        elif self.estado in ("descanso", "atordoado"):
            self.timer -= dt
            if self.timer <= 0:
                self.estado = "espera"

    def desenhar(self, tela, camera_x, camera_y):
        if not self.vivo:
            return
        est = {"espera": "idle", "descanso": "idle", "aviso_rico": "aviso",
               "ricochete": "investida"}.get(self.estado, self.estado)
        if self.furia and self.estado == "descanso":
            est = "atirar"
        if self.desenhar_sprite(tela, camera_x, camera_y, est, flip=not self.olhando_direita):
            self.desenhar_barra_vida(tela, camera_x, camera_y)
            return
        r = self.rect.move(-camera_x, -camera_y)
        cor = self.cor
        if self.bravo:
            cor = (min(255, cor[0] + 90), cor[1] // 2, cor[2] // 2)      # fica avermelhado
        if self.invencivel_timer > 0:
            cor = (255, 255, 255)
        elif self.estado in ("aviso", "aviso_rico") and int(self.timer * 16) % 2 == 0:
            cor = (255, 120, 120)
        elif self.estado == "atordoado":
            cor = (130, 130, 165)
        pygame.draw.rect(tela, cor, r, border_radius=6)
        pygame.draw.polygon(tela, cor, [(r.centerx, r.top - 16), (r.left + 4, r.top + 4), (r.right - 4, r.top + 4)])
        pygame.draw.rect(tela, (20, 16, 28), r, width=2, border_radius=6)
        self.desenhar_barra_vida(tela, camera_x, camera_y)


class Sala10Boss:
    perspectiva = "topdown"
    EXTRA_ALTURA = 1200        # px que a sala cresce pra CIMA depois da vitoria
    ESPERA_CREDITOS = 10.0     # s perto da porta do fundo (depois da vitoria) ate subirem os creditos

    def __init__(self):
        self.largura_sala, self.altura_sala = LARGURA_TELA, ALTURA_TELA
        self.spawn = (LARGURA_TELA // 2 - 17, ALTURA_TELA - 120)
        self.spawns = {}
        # um bispo em casa clara e outro em casa escura (paridade diferente, como no xadrez)
        self.bispos = [BispoXadrez(1, 1, "bispo_branco", (235, 235, 245)),
                       BispoXadrez(6, 1, "bispo_preto", (75, 60, 100))]
        self.projeteis = []
        self.timer_ataque = 2.5
        self.intro = 2.0
        self.comecou = False
        self.vitoria_timer = None
        self.espera_porta = 0.0
        self.y_min = 0              # topo do mundo (vira -EXTRA_ALTURA apos a vitoria)
        self.cam_y = 0.0
        self.vinheta = criar_vinheta(LARGURA_TELA, ALTURA_TELA, forca=150)
        self.fonte = pygame.font.Font(None, 26)
        self._tile = pygame.Surface((CELULA, CELULA), pygame.SRCALPHA)
        # >>> SPRITE AQUI: assets/cenario/fundo_sala10.png (800x600; se existir, substitui o tabuleiro)
        self.fundo = Animacao("cenario/fundo_sala10")
        self.porta_baixo = Porta(LARGURA_TELA // 2 - 45, ALTURA_TELA - 30, 90, 30,
                                 destino="sala9", sprite="escada_baixo")
        # porta do fundo: so enfeite (nao leva a lugar nenhum), serve pro sprite do fim da demo
        # >>> SPRITE AQUI: assets/portas/fim_normal.png e fim_trancada.png (90x60)
        self.porta_fundo = Porta(LARGURA_TELA // 2 - 45, 0, 90, 60, destino="sala10", sprite="fim")

    def entrar(self, jogador, origem=None):
        jogador.x, jogador.y = self.spawns.get(origem, self.spawn)
        jogador.knock_timer = 0
        self.cam_y = 0.0

    def atualizar(self, jogador, teclas, eventos, dt, estado_jogo):
        jogador.atualizar_topdown(teclas, [])
        jogador.x = max(20, min(jogador.x, self.largura_sala - jogador.largura - 20))
        jogador.y = max(self.y_min + 20, min(jogador.y, self.altura_sala - jogador.altura - 20))
        jogador.atualizar_timers(dt)

        destino = None
        for ev in eventos:
            if ev.type == pygame.KEYDOWN:
                if ev.key == TECLA_ATAQUE:
                    jogador.tentar_atacar(topdown=True)
                if ev.key == TECLA_INTERAGIR and not self.porta_baixo.trancada \
                        and jogador.rect.colliderect(self.porta_baixo.rect.inflate(30, 30)):
                    destino = self.porta_baixo.destino

        vivos = [b for b in self.bispos if b.vivo]

        # PARRY primeiro (bispos na investida/ricochete + projeteis)
        for alvo in vivos + self.projeteis:
            jogador.aparar(alvo)

        hb = jogador.hitbox_ataque
        if hb:
            for b in vivos:
                if id(b) not in jogador.acertados and hb.colliderect(b.rect):
                    jogador.acertados.add(id(b))
                    if b.receber_dano(jogador.dano_ataque):
                        hitstop(0.05)
                        tremer(0.12, 3)

        if not self.comecou:
            self.intro -= dt
            if self.intro <= 0:
                self.comecou = True
        else:
            self.porta_baixo.trancada = bool(vivos)        # sem fugir da luta
            for b in vivos:
                b.furia = b.vida <= b.vida_max / 2 or len(vivos) < 2
            for b in vivos:                                # gatilho do RICOCHETE (50% de vida)
                if not b.rico_gatilho and b.vida <= b.vida_max / 2:
                    b.rico_gatilho = True
                    for o in vivos:
                        o.iniciar_ricochete()
                    tremer(0.5, 6)
                    break
            if len(vivos) == 1 and not vivos[0].bravo:     # um caiu: o outro fica BRAVO
                b = vivos[0]
                b.bravo = b.furia = True
                b.rico_gatilho = True
                b.iniciar_ricochete(bravo=True)
                self.timer_ataque = 1.0
                tremer(0.8, 8)
            livres = [b for b in vivos if b.estado == "espera"]
            ocupados = [b for b in vivos if b.estado in ("aviso", "investida", "descanso",
                                                         "aviso_rico", "ricochete")]
            if livres and not ocupados:                    # ataque SINCRONIZADO
                self.timer_ataque -= dt
                if self.timer_ataque <= 0:
                    for b in livres:
                        b.pedir_ataque(jogador)
                    furia = any(b.furia for b in vivos)
                    self.timer_ataque = (random.uniform(0.4, 0.8) if any(b.bravo for b in vivos)
                                         else random.uniform(0.6, 1.1) if furia else random.uniform(1.1, 1.8))
            for b in vivos:
                b.atualizar(jogador, dt)
                jogador.aparar(b)
                if b.perigoso and jogador.rect.colliderect(b.rect):
                    jogador.receber_dano(b.dano_contato, b.rect.center)
                self.projeteis += b.novos_tiros
                b.novos_tiros = []

        # projeteis (tiros em X)
        for p in self.projeteis:
            p.atualizar([], self.largura_sala, self.altura_sala)
            jogador.aparar(p)
            if p.refletido:
                if p.vivo:
                    for b in vivos:
                        if b.vivo and p.rect.colliderect(b.rect):
                            p.vivo = False
                            if b.receber_dano(p.dano):
                                hitstop(0.08)
                                tremer(0.2, 5)
                            break
            elif p.vivo and jogador.rect.colliderect(p.rect):
                p.vivo = False
                jogador.receber_dano(p.dano, (p.x, p.y))
        self.projeteis = [p for p in self.projeteis if p.vivo]

        # vitoria
        if self.comecou and not [b for b in self.bispos if b.vivo]:
            self.projeteis = []
            self.porta_baixo.trancada = False
            if self.vitoria_timer is None:
                self.vitoria_timer = 0.0          # marca que a luta acabou
                self.y_min = -self.EXTRA_ALTURA   # o teto se abre: a sala cresce pra cima
                self.porta_fundo.y = self.y_min   # a porta vai pro fim do corredor
                tremer(1.0, 8)
            # o jogador anda ate a porta do fundo e espera 10s pra subirem os creditos
            if jogador.rect.colliderect(self.porta_fundo.rect.inflate(60, 60)):
                self.espera_porta += dt
                if self.espera_porta >= self.ESPERA_CREDITOS:
                    estado_jogo.flags["venceu"] = True
            else:
                self.espera_porta = 0.0

        # camera: fica fixa na arena e so sobe quando o jogador sobe (depois da vitoria)
        alvo = jogador.y + jogador.altura / 2 - ALTURA_TELA / 2
        alvo = max(self.y_min, min(alvo, 0))
        self.cam_y += (alvo - self.cam_y) * min(1.0, 6 * dt)
        return destino

    def desenhar(self, tela, jogador, tempo):
        cam_y = int(self.cam_y)
        vivos = [b for b in self.bispos if b.vivo]
        img_fundo = self.fundo.frame()
        tela.fill((20, 8, 14))
        # tabuleiro (e a extensao pra cima depois da vitoria)
        for r in range(int(self.y_min // CELULA), LINS):
            y = r * CELULA - cam_y
            if y > ALTURA_TELA or y + CELULA < 0 or (img_fundo and r >= 0):
                continue
            for c in range(COLS):
                if r < 0:
                    cor = (58, 46, 70) if (c + r) % 2 == 0 else (38, 30, 52)
                else:
                    cor = (46, 38, 60) if (c + r) % 2 == 0 else (30, 24, 42)
                pygame.draw.rect(tela, cor, (c * CELULA, y, CELULA, CELULA))
        if img_fundo:
            tela.blit(img_fundo, (0, -cam_y))

        # aviso das diagonais (casas vermelhas)
        for b in self.bispos:
            if b.vivo and b.estado in ("aviso", "investida"):
                alpha = int(70 + 60 * math.sin(tempo * 14)) if b.estado == "aviso" else 150
                self._tile.fill((255, 60, 60, alpha))
                for c, r in b.caminho:
                    tela.blit(self._tile, (c * CELULA, r * CELULA - cam_y))

        # porta do fundo (enfeite durante a luta; destino final depois dela)
        self.porta_fundo.trancada = bool(vivos)
        perto_fundo = jogador.rect.colliderect(self.porta_fundo.rect.inflate(60, 60))
        if not vivos:                                   # brilho quente em volta da porta
            luz = criar_luz(200, 110, (255, 225, 150))
            d = self.porta_fundo.rect
            tela.blit(luz, (d.centerx - 200, d.centery - cam_y - 200))
        self.porta_fundo.desenhar(tela, 0, cam_y, perto_fundo, tempo)

        perto = jogador.rect.colliderect(self.porta_baixo.rect.inflate(30, 30))
        self.porta_baixo.desenhar(tela, 0, cam_y, perto, tempo)
        for b in self.bispos:
            b.desenhar(tela, 0, cam_y)
        for p in self.projeteis:
            p.desenhar(tela)
        tela.blit(self.vinheta, (0, 0))
        jogador.desenhar(tela, 0, cam_y)

        # barras de vida dos dois bispos (somem quando a luta acaba)
        if vivos:
            for i, b in enumerate(self.bispos):
                x = 60 + i * 400
                pct = max(0, b.vida / b.vida_max)
                pygame.draw.rect(tela, (40, 10, 10), (x, ALTURA_TELA - 58, 280, 10))
                pygame.draw.rect(tela, b.cor if b.vivo else (60, 60, 60), (x, ALTURA_TELA - 58, 280 * pct, 10))
                pygame.draw.rect(tela, (235, 235, 240), (x, ALTURA_TELA - 58, 280, 10), 1)

        if not vivos:
            if self.espera_porta > 0:
                dica = f"Aguarde diante da porta... {max(0, int(self.ESPERA_CREDITOS - self.espera_porta) + 1)}"
            else:
                dica = "O teto se abriu! Suba pelo corredor até a porta lá no alto..."
        elif not self.comecou:
            dica = "Dois bispos guardam o tabuleiro..."
        elif any(b.bravo for b in vivos):
            dica = "O bispo restante está FURIOSO! Ele mira em você - dê parry!"
        elif any(b.estado in ("aviso_rico", "ricochete") for b in vivos):
            dica = "RICOCHETE! Desvie deles quicando nas paredes (ou dê parry!)"
        elif any(b.furia for b in vivos):
            dica = "Fúria! Cuidado com os tiros em X - dê parry neles pra devolver o dano!"
        else:
            dica = "Eles atacam juntos pelas diagonais. Q na hora da investida = PARRY!"
        if perto and not self.porta_baixo.trancada and vivos:
            dica = "Pressione E para voltar"
        tela.blit(self.fonte.render(dica, True, (255, 255, 255)), (20, ALTURA_TELA - 30))
# ============================================================
# main
# ============================================================
try:
    if not pygame.mixer.get_init():
        pygame.mixer.init()
except pygame.error:
    pass                                   # sem placa de som: o jogo roda mudo, sem quebrar
 
VOLUME_PADRAO = {"musica": 0.7, "efeitos": 0.8}
VOLUME = dict(VOLUME_PADRAO)
 
# acoes que o jogador pode remapear (o movimento continua WASD + setas)
CONTROLES_PADRAO = {"ataque": pygame.K_q, "pulo": pygame.K_SPACE,
                    "interagir": pygame.K_e, "correr": pygame.K_LSHIFT}
CONTROLES = dict(CONTROLES_PADRAO)
TECLAS_RESERVADAS = {pygame.K_ESCAPE, pygame.K_F1,
                     pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d,
                     pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT}
 
ARQUIVO_CONFIG = os.path.join(os.path.dirname(PASTA_ASSETS), "config.json")
PASTA_AUDIO = os.path.join(PASTA_ASSETS, "audio")
# >>> AUDIO AQUI (opcional): coloque em assets/audio/
#     musicas : menu.ogg, jogo.ogg            (tambem aceita .mp3 / .wav)
#     efeitos : clique.ogg, golpe.ogg, parry.ogg, dano.ogg, pogo.ogg   (.ogg ou .wav)
#     Sem arquivo = silencio (nunca quebra). Use tocar_som("nome") / tocar_musica("nome").
 
_sons = {}
_musica_atual = None
_musicas_ausentes = set()
 
 
def _mixer_ok():
    return pygame.mixer.get_init() is not None
 
 
def aplicar_volumes():
    if _mixer_ok():
        pygame.mixer.music.set_volume(VOLUME["musica"])
 
 
def carregar_som(nome):
    """assets/audio/<nome>.ogg|.wav. Devolve None se nao existir."""
    if nome in _sons:
        return _sons[nome]
    som = None
    if _mixer_ok():
        for ext in (".ogg", ".wav"):
            caminho = os.path.join(PASTA_AUDIO, nome + ext)
            if os.path.isfile(caminho):
                try:
                    som = pygame.mixer.Sound(caminho)
                    break
                except pygame.error:
                    som = None
    _sons[nome] = som
    return som
 
 
def tocar_som(nome):
    som = carregar_som(nome)
    if som:
        som.set_volume(VOLUME["efeitos"])
        som.play()
 
 
def tocar_musica(nome, loop=True):
    """Pode chamar todo frame: so troca quando o nome muda."""
    global _musica_atual
    if not _mixer_ok() or nome == _musica_atual or nome in _musicas_ausentes:
        return
    for ext in (".ogg", ".mp3", ".wav"):
        caminho = os.path.join(PASTA_AUDIO, nome + ext)
        if os.path.isfile(caminho):
            try:
                pygame.mixer.music.load(caminho)
                pygame.mixer.music.set_volume(VOLUME["musica"])
                pygame.mixer.music.play(-1 if loop else 0)
                _musica_atual = nome
                return
            except pygame.error:
                break
    _musicas_ausentes.add(nome)
 
 
# ---------- controles ----------
def aplicar_controles():
    """Copia CONTROLES pras constantes que o resto do jogo ja usa."""
    global TECLA_ATAQUE, TECLA_PULO, TECLA_INTERAGIR, TECLA_CORRER
    TECLA_ATAQUE = CONTROLES["ataque"]
    TECLA_PULO = CONTROLES["pulo"]
    TECLA_INTERAGIR = CONTROLES["interagir"]
    k = CONTROLES["correr"]
    TECLA_CORRER = (pygame.K_LSHIFT, pygame.K_RSHIFT) if k in (pygame.K_LSHIFT, pygame.K_RSHIFT) else (k,)
 
 
def _teclas_da(acao):
    """Conjunto de teclas que a acao usa (correr com SHIFT ocupa os dois SHIFTs)."""
    k = CONTROLES[acao]
    if acao == "correr" and k in (pygame.K_LSHIFT, pygame.K_RSHIFT):
        return {pygame.K_LSHIFT, pygame.K_RSHIFT}
    return {k}
 
 
def nome_tecla(acao):
    """Texto bonito da tecla de uma acao (use nas dicas da tela)."""
    k = CONTROLES[acao]
    if acao == "correr" and k in (pygame.K_LSHIFT, pygame.K_RSHIFT):
        return "SHIFT"
    n = pygame.key.name(k)
    bonitos = {"space": "ESPAÇO", "left shift": "SHIFT ESQ.", "right shift": "SHIFT DIR.",
               "left ctrl": "CTRL ESQ.", "right ctrl": "CTRL DIR.", "left alt": "ALT ESQ.",
               "right alt": "ALT DIR.", "return": "ENTER", "backspace": "BACKSPACE"}
    return bonitos.get(n, n.upper()) if n else f"TECLA {k}"
 
 
# ---------- salvar / carregar ----------
def salvar_config():
    try:
        with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
            json.dump({"volume": VOLUME, "controles": CONTROLES}, f, indent=2)
    except OSError:
        pass
 
 
def carregar_config():
    try:
        with open(ARQUIVO_CONFIG, encoding="utf-8") as f:
            dados = json.load(f)
        for k in VOLUME:
            v = dados.get("volume", {}).get(k)
            if isinstance(v, (int, float)):
                VOLUME[k] = max(0.0, min(1.0, float(v)))
        for k in CONTROLES:
            v = dados.get("controles", {}).get(k)
            if isinstance(v, int):
                CONTROLES[k] = v
    except (OSError, ValueError, AttributeError):
        pass
    aplicar_controles()
    aplicar_volumes()
 
 
class MenuOpcoes:
    """Tela de opcoes: 2 sliders de volume + 4 botoes de tecla (clique, aperte a tecla nova).
    Se a tecla ja e usada por outra acao, as duas TROCAM de tecla. ESC cancela / volta."""
 
    ACOES = [("ataque", "Atacar"), ("pulo", "Pular"), ("interagir", "Interagir"), ("correr", "Correr")]
 
    def __init__(self):
        self.aguardando = None          # acao esperando uma tecla
        self.arrastando = None          # slider sendo arrastado
        self.aviso, self.aviso_ate = "", 0.0
        self.fundo = None               # foto do jogo (quando abre durante a partida)
        self.sliders = {"musica": pygame.Rect(330, 130, 300, 12), "efeitos": pygame.Rect(330, 190, 300, 12)}
        self.rotulos_slider = {"musica": "Música", "efeitos": "Efeitos"}
        self.botoes_tecla = {a: pygame.Rect(330, 280 + i * 50, 220, 38) for i, (a, _) in enumerate(self.ACOES)}
        self.rotulos_acao = dict(self.ACOES)
        self.btn_padrao = pygame.Rect(170, 520, 220, 50)
        self.btn_voltar = pygame.Rect(410, 520, 220, 50)
        self._painel = pygame.Surface((620, 560), pygame.SRCALPHA)
        pygame.draw.rect(self._painel, (8, 6, 14, 215), self._painel.get_rect(), border_radius=14)
 
    def abrir(self, tela, origem):
        self.aguardando = self.arrastando = None
        self.aviso = ""
        self.fundo = None
        if origem == "jogando":                      # congela o jogo de fundo, escurecido
            self.fundo = tela.copy()
            escuro = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
            escuro.fill((0, 0, 0, 150))
            self.fundo.blit(escuro, (0, 0))
 
    # ---------------- logica ----------------
    def _avisar(self, texto):
        self.aviso, self.aviso_ate = texto, _agora() + 2.5
 
    def _ajustar(self, nome, x):
        r = self.sliders[nome]
        v = max(0.0, min(1.0, (x - r.x) / r.w))
        VOLUME[nome] = round(v * 20) / 20           # passos de 5%
        aplicar_volumes()
 
    def _atribuir(self, acao, tecla):
        antiga = CONTROLES[acao]
        if tecla in _teclas_da(acao):
            return                                   # mesma tecla: nada a fazer
        for outra in CONTROLES:
            if outra != acao and tecla in _teclas_da(outra):
                CONTROLES[outra] = antiga            # troca as duas de lugar
                self._avisar(f"{self.rotulos_acao[outra]} agora usa {pygame.key.name(antiga).upper() or 'outra tecla'}")
                break
        CONTROLES[acao] = tecla
        aplicar_controles()
        salvar_config()
 
    def _restaurar(self):
        VOLUME.update(VOLUME_PADRAO)
        CONTROLES.update(CONTROLES_PADRAO)
        aplicar_controles()
        aplicar_volumes()
        salvar_config()
        self._avisar("Opções restauradas.")
 
    def processar(self, eventos):
        """Devolve "voltar" quando o jogador sai da tela."""
        for ev in eventos:
            if self.aguardando and ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    self.aguardando = None
                elif ev.key in TECLAS_RESERVADAS:
                    self._avisar("Essa tecla é do movimento/sistema. Escolha outra.")
                else:
                    self._atribuir(self.aguardando, ev.key)
                    self.aguardando = None
                continue
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                salvar_config()
                return "voltar"
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self.aguardando = None
                for nome, r in self.sliders.items():
                    if r.inflate(0, 30).collidepoint(ev.pos):
                        self.arrastando = nome
                        self._ajustar(nome, ev.pos[0])
                for acao, r in self.botoes_tecla.items():
                    if r.collidepoint(ev.pos):
                        self.aguardando = acao
                if self.btn_padrao.collidepoint(ev.pos):
                    self._restaurar()
                if self.btn_voltar.collidepoint(ev.pos):
                    salvar_config()
                    return "voltar"
            elif ev.type == pygame.MOUSEMOTION and self.arrastando:
                self._ajustar(self.arrastando, ev.pos[0])
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and self.arrastando:
                if self.arrastando == "efeitos":
                    tocar_som("clique")              # ouve o volume novo
                self.arrastando = None
                salvar_config()
        return None
 
    # ---------------- desenho ----------------
    def desenhar(self, tela, mouse_pos):
        if self.fundo:
            tela.blit(self.fundo, (0, 0))
        else:
            desenhar_fundo(tela, anim_menu_fundo.frame(), (20, 20, 30))
        tela.blit(self._painel, (90, 20))
 
        titulo = fonte_game_over.render("OPÇÕES", True, BRANCO)
        tela.blit(titulo, titulo.get_rect(center=(LARGURA_TELA // 2, 65)))
 
        for nome, r in self.sliders.items():         # sliders de volume
            v = VOLUME[nome]
            rot = fonte_botao.render(self.rotulos_slider[nome], True, BRANCO)
            tela.blit(rot, rot.get_rect(midleft=(130, r.centery)))
            pygame.draw.rect(tela, (50, 50, 65), r, border_radius=6)
            pygame.draw.rect(tela, (250, 7, 121), (r.x, r.y, int(r.w * v), r.h), border_radius=6)
            pygame.draw.circle(tela, BRANCO, (r.x + int(r.w * v), r.centery), 12)
            pct = fonte_hud.render(f"{int(round(v * 100))}%", True, BRANCO)
            tela.blit(pct, pct.get_rect(midleft=(r.right + 25, r.centery)))
 
        sub = fonte_botao.render("Controles", True, (250, 7, 121))
        tela.blit(sub, sub.get_rect(center=(LARGURA_TELA // 2, 252)))
        for acao, r in self.botoes_tecla.items():    # botoes de tecla
            rot = fonte_botao.render(self.rotulos_acao[acao], True, BRANCO)
            tela.blit(rot, rot.get_rect(midleft=(130, r.centery)))
            if self.aguardando == acao:
                cor, texto = (250, 7, 121), "Pressione uma tecla..."
            else:
                cor, texto = (CINZA_CLARO if r.collidepoint(mouse_pos) else CINZA_ESCURO), nome_tecla(acao)
            pygame.draw.rect(tela, cor, r, border_radius=8)
            txt = fonte_hud.render(texto, True, BRANCO)
            tela.blit(txt, txt.get_rect(center=r.center))
 
        dica = fonte_hud.render("Mover: WASD ou setas   |   ESC: voltar", True, (170, 170, 185))
        tela.blit(dica, dica.get_rect(center=(LARGURA_TELA // 2, 478)))
        if self.aviso and _agora() < self.aviso_ate:
            av = fonte_hud.render(self.aviso, True, (255, 210, 120))
            tela.blit(av, av.get_rect(center=(LARGURA_TELA // 2, 500)))
 
        desenhar_botao(self.btn_padrao, "PADRÃO", CINZA_ESCURO, CINZA_CLARO, mouse_pos)
        desenhar_botao(self.btn_voltar, "VOLTAR", VERMELHO_ESCURO, VERMELHO_CLARO, mouse_pos)
 
 
carregar_config()          # le config.json (se existir) e aplica volume + teclas
 
# ============================================================
# main
# ============================================================
tela = pygame.display.set_mode((LARGURA_TELA, ALTURA_TELA))
pygame.display.set_caption("O Cavaleiro e o Castelo — Demo")
clock = pygame.time.Clock()
 
fonte_hud = pygame.font.Font(None, 24)
fonte_titulo = pygame.font.Font(None, 72)
fonte_botao = pygame.font.Font(None, 40)
fonte_game_over = pygame.font.Font(None, 60)
 
BRANCO = (255, 255, 255)
CINZA_ESCURO = (60, 60, 70)
CINZA_CLARO = (90, 90, 105)
VERMELHO_ESCURO = (120, 40, 40)
VERMELHO_CLARO = (160, 60, 60)
 
botao_iniciar = pygame.Rect(300, 260, 200, 60)
botao_opcoes = pygame.Rect(300, 340, 200, 60)      # NOVO
botao_sair = pygame.Rect(300, 420, 200, 60)        # desceu de 340 pra 420
 
# >>> SPRITE AQUI: assets/ui/menu_fundo.png e assets/ui/game_over_fundo.png (800x600)
anim_menu_fundo = Animacao("ui/menu_fundo")
anim_game_over_fundo = Animacao("ui/game_over_fundo")
 
 
def desenhar_botao(rect, texto, cor_normal, cor_hover, mouse_pos):
    cor = cor_hover if rect.collidepoint(mouse_pos) else cor_normal
    pygame.draw.rect(tela, cor, rect, border_radius=8)
    texto_render = fonte_botao.render(texto, True, BRANCO)
    tela.blit(texto_render, texto_render.get_rect(center=rect.center))
 
 
# ---------- opcoes (NOVO) ----------
menu_opcoes = MenuOpcoes()
opcoes_origem = "menu"             # de onde a tela de opcoes foi aberta: "menu" ou "jogando"
opcoes_ignora_eventos = False
 
 
def abrir_opcoes(origem):
    """Troca pra tela de opcoes e lembra de onde veio (pra VOLTAR levar de volta)."""
    global tela_jogo, opcoes_origem, opcoes_ignora_eventos
    opcoes_origem = origem
    opcoes_ignora_eventos = True       # ignora os eventos deste frame (o mesmo clique que abriu)
    menu_opcoes.abrir(tela, origem)
    tela_jogo = "opcoes"
 
 
def criar_salas():
    return {
        "sala1": Sala1Portao(),
        "sala2": Sala2Tutorial(),
        "sala3": Sala3(),
        "sala4": Sala4(),
        "sala4s": Sala4Secreta(),
        "sala5": Sala5MiniBoss(),
        "sala6": Sala6Parkour(),
        "sala7": Sala7Galeria(),
        "sala8": Sala8Pogo(),
        "sala9": Sala9Abismo(),
        "sala10": Sala10Boss(),
    }
 
 
estado_jogo = EstadoJogo()
jogador = Jogador(0, 0)
salas = criar_salas()
sala_atual = None
 
 
# ordem das salas (pra saber se o jogador esta AVANCANDO ou voltando)
ORDEM_SALAS = {"sala1": 1, "sala2": 2, "sala3": 3, "sala4": 4, "sala4s": 4.5, "sala5": 5,
               "sala6": 6, "sala7": 7, "sala8": 8, "sala9": 9, "sala10": 10}
 
 
def trocar_sala(nome, origem=None):
    """origem = sala de onde o jogador esta saindo (define onde ele nasce na nova sala).
    nome == "voltar" = volta pra sala de onde ele veio (usado na sala 6, que tem 2 entradas)."""
    global sala_atual
    if nome == "voltar":
        nome = estado_jogo.veio_de.get(origem, "sala3")
    if origem and ORDEM_SALAS[nome] > ORDEM_SALAS[origem]:      # so guarda ao AVANCAR (voltar nao sobrescreve)
        estado_jogo.veio_de[nome] = origem
    estado_jogo.sala_atual = nome
    sala_atual = salas[nome]
    sala_atual.entrar(jogador, origem)
 
 
def novo_jogo():
    """Reinicia TUDO (vida, chaves, inimigos, mini-boss...)."""
    global estado_jogo, jogador, salas
    estado_jogo = EstadoJogo()
    jogador = Jogador(0, 0)
    salas = criar_salas()
    trocar_sala("sala1")
 
 
preparar_assets()   # cria assets/ e assets/SPRITES_FALTANDO.txt
 
# ---------- creditos (ficam FORA do loop) ----------
CREDITOS = [
    ("SOUL HEART", (250, 7, 121)), "",
    ("Programação", (250, 7, 121)), "Pedro Ocanha", "",
    ("Arte", (250, 7, 121)), "Pedro Ocanha", "Bruno Gabriel", "Gilvan Henrique", "",
    ("Música", (250, 7, 121)), "Pedro Ocanha", "",
    ("Beta Testers", (250, 7, 121)), "Lucazsrk", "MLZBRASILBYMIGUELARRAES", "Thallys(Buddha)", "",
    ("Obrigado por Jogar a Demo", (250, 7, 121)), "", "", "", "",
    ("2027", (250, 7, 121)),
]
ESPACO_CREDITO = 44
CREDITOS_Y_FINAL = 180 - (len(CREDITOS) - 1) * ESPACO_CREDITO   # onde o ultimo item para
creditos_y = ALTURA_TELA
 
tela_jogo = "menu"  # "menu" | "jogando" | "game_over" | "vitoria" | "opcoes"
tempo_total = 0.0
rodando = True


async def main():
    global tela_jogo, creditos_y, tempo_total, rodando, opcoes_ignora_eventos
    while rodando:
        dt = clock.tick(FPS) / 1000
        tempo_total += dt
        mouse_pos = pygame.mouse.get_pos()
        teclas = pygame.key.get_pressed()
        eventos = pygame.event.get()

        for evento in eventos:
            if evento.type == pygame.QUIT:
                rodando = False
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_F1:
                DEBUG["hitbox"] = not DEBUG["hitbox"]      # F1: mostra/esconde hitboxes
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if tela_jogo == "menu":
                    if botao_iniciar.collidepoint(mouse_pos):
                        novo_jogo()
                        tela_jogo = "jogando"
                    elif botao_opcoes.collidepoint(mouse_pos):
                        abrir_opcoes("menu")
                    elif botao_sair.collidepoint(mouse_pos):
                        rodando = False
                elif tela_jogo == "game_over" or (tela_jogo == "vitoria" and creditos_y <= CREDITOS_Y_FINAL):
                    if botao_iniciar.collidepoint(mouse_pos):
                        novo_jogo()
                        tela_jogo = "jogando"

        if tela_jogo == "menu":
            desenhar_fundo(tela, anim_menu_fundo.frame(), (20, 20, 30))
            titulo = fonte_titulo.render("Soul Heart", True, BRANCO)
            tela.blit(titulo, titulo.get_rect(center=(LARGURA_TELA // 2, 160)))
            desenhar_botao(botao_iniciar, "INICIAR", CINZA_ESCURO, CINZA_CLARO, mouse_pos)
            desenhar_botao(botao_opcoes, "OPÇÕES", CINZA_ESCURO, CINZA_CLARO, mouse_pos)
            desenhar_botao(botao_sair, "SAIR", VERMELHO_ESCURO, VERMELHO_CLARO, mouse_pos)

        elif tela_jogo == "jogando":
            if FX["hitstop"] > 0:          # congela o jogo por um instante ao bater/apanhar
                FX["hitstop"] -= dt
                proxima_sala = None
            else:
                proxima_sala = sala_atual.atualizar(jogador, teclas, eventos, dt, estado_jogo)
            sala_atual.desenhar(tela, jogador, tempo_total)
            desenhar_hud(tela, jogador, estado_jogo, fonte_hud)

            if FX["tremor"] > 0:           # screen shake
                FX["tremor"] -= dt
                mag = FX["mag"]
                copia = tela.copy()
                tela.fill((0, 0, 0))
                tela.blit(copia, (random.randint(-mag, mag), random.randint(-mag, mag)))
            else:
                FX["mag"] = 0

            if proxima_sala:
                trocar_sala(proxima_sala, estado_jogo.sala_atual)

            if jogador.vida <= 0:
                tela_jogo = "game_over"
            elif estado_jogo.flags.get("venceu"):
                tela_jogo = "vitoria"
                creditos_y = ALTURA_TELA

            if tela_jogo == "jogando":                              # ESC abre as opcoes
                for evento in eventos:
                    if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                        abrir_opcoes("jogando")

        elif tela_jogo == "opcoes":
            if opcoes_ignora_eventos:
                opcoes_ignora_eventos = False
                resultado = None
            else:
                resultado = menu_opcoes.processar(eventos)
            menu_opcoes.desenhar(tela, mouse_pos)
            if resultado == "voltar":
                tela_jogo = opcoes_origem

        elif tela_jogo == "game_over":
            desenhar_fundo(tela, anim_game_over_fundo.frame(), (15, 8, 8))
            texto = fonte_game_over.render("VOCÊ MORREU", True, (200, 50, 50))
            tela.blit(texto, texto.get_rect(center=(LARGURA_TELA // 2, 220)))
            desenhar_botao(botao_iniciar, "TENTAR DE NOVO", CINZA_ESCURO, CINZA_CLARO, mouse_pos)

        elif tela_jogo == "vitoria":
            tela.fill((6, 5, 12))
            creditos_y = max(CREDITOS_Y_FINAL, creditos_y - 55 * dt)      # sobe e para no ultimo item
            for i, item in enumerate(CREDITOS):
                titulo_com_cor = isinstance(item, tuple)
                texto, cor = item if titulo_com_cor else (item, (225, 225, 235))
                y = creditos_y + i * ESPACO_CREDITO
                if -40 < y < ALTURA_TELA + 40 and texto:
                    fonte = fonte_titulo if texto == "SOUL HEART" else fonte_botao if titulo_com_cor else fonte_hud
                    img = fonte.render(texto, True, cor)
                    tela.blit(img, img.get_rect(center=(LARGURA_TELA // 2, y)))
            if creditos_y <= CREDITOS_Y_FINAL:
                desenhar_botao(botao_iniciar, "JOGAR DE NOVO", CINZA_ESCURO, CINZA_CLARO, mouse_pos)

        # ---- estas 2 linhas ficam AQUI, no fim do while (fora de qualquer if) ----
        pygame.display.flip()
        await asyncio.sleep(0)   # devolve o controle ao navegador

    pygame.quit()
    sys.exit()


asyncio.run(main())