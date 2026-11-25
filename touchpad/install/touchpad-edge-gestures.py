#!/usr/bin/env python3
"""touchpad-edge-gestures.py — gestos de borda do touchpad ASUS (o "Smart Gesture" do MyASUS) no Linux.

Gestos (iguais aos do Windows):
  borda ESQUERDA, deslizar para cima/baixo ......... volume + / −
  borda DIREITA, deslizar para cima/baixo .......... brilho + / −
  borda de CIMA, deslizar para a direita/esquerda .. próxima / anterior (mídia)
  canto SUPERIOR DIREITO → centro .................. abre CORNER_PROGRAM (no Windows: MyASUS)

Como funciona: o touchpad (ASCP1200, PixArt 093A:3016) manda os toques da borda como toques normais; quem
impede o cursor de mexer é o libinput (palm detection: toque que COMEÇA na faixa da borda é ignorado). No
Windows, o driver/serviço da ASUS (asusptpfilter + AsusPTPService) transforma esses toques em ações. Aqui este
script lê o mesmo dispositivo evdev (sem "grab": o KWin/libinput continua recebendo tudo) e faz as ações.
Zonas medidas com edge-capture.py num S5406SA.

Roda como o SEU usuário (wpctl, playerctl e o brilho via logind precisam da sessão). Precisa de permissão de
leitura em /dev/input/eventN do touchpad: ver 70-touchpad-edge-gestures.rules (instalado pelo gtouchpad).

Uso:
    python3 -I touchpad-edge-gestures.py              # normal
    python3 -I touchpad-edge-gestures.py --dry-run    # só mostra os gestos detectados, não executa nada
    python3 -I touchpad-edge-gestures.py -v           # mostra também a posição de início de cada toque
"""

# ============================== CONFIGURAÇÃO ==============================

# Programa aberto pelo gesto do canto superior direito → centro (no Windows abre o MyASUS).
# Escreva o caminho do programa; pode ter argumentos, separados por espaço como num terminal.
# Exemplos: "/usr/bin/systemsettings"   "/usr/bin/systemsettings kcm_powerdevilprofilesconfig"
# Vazio = o gesto do canto não faz nada. Normalmente vem de ~/.config/gtouchpad.conf (gtouchpad corner),
# que o serviço passa como variável de ambiente CORNER_PROGRAM; este valor é só o padrão.
CORNER_PROGRAM = ""

VOLUME_STEP = "5%"          # quanto cada passo muda o volume
VOLUME_MAX = "1.0"          # teto do volume (1.0 = 100 %; não passar disso protege os alto-falantes)
BRIGHTNESS_STEP_PCT = 5     # quanto cada passo muda o brilho, em % do máximo
BRIGHTNESS_MIN_PCT = 1      # brilho mínimo (não deixa apagar a tela de vez)

# Zonas de borda, em fração do tamanho do touchpad (medido: borda esq. X ≤ 3,4 %, dir. ≥ 96,8 %, topo Y ≤ 4 %).
# Maiores que a faixa do libinput = toque que começa ali MEXE O CURSOR e também dispara o gesto.
EDGE_X = 0.04               # largura das faixas esquerda/direita
EDGE_Y = 0.05               # altura da faixa de cima

# Trecho AO LONGO de cada borda onde o gesto pode começar (medido com edge-capture.py em 2026-11-24).
# Y: 0 = em cima, 1 = embaixo. X: 0 = esquerda, 1 = direita.
LEFT_Y_RANGE = (0.22, 0.88)     # volume
RIGHT_Y_RANGE = (0.26, 0.88)    # brilho
TOP_X_RANGE = (0.23, 0.79)      # mídia
# Canto superior direito: X ≥ 1 − EDGE_X e Y ≤ EDGE_Y. Não encosta nos trechos acima, então é uma zona própria.

STEP_DISTANCE = 0.08        # bordas laterais: deslocamento vertical (fração da altura) por passo
SWIPE_DISTANCE = 0.15       # borda de cima: deslocamento horizontal (fração da largura) para disparar
CORNER_DISTANCE = 0.20      # canto: quanto o dedo precisa andar para dentro (fração da altura)
DECIDE_DISTANCE = 0.03      # anda isso antes de decidir a direção (para separar canto/topo/borda direita)

TOUCHPAD_NAME = "ASCP1200:00 093A:3016 Touchpad"

# ==========================================================================

import argparse
import fcntl
import functools
import glob
import importlib.util
import math
import os
import queue
import shlex
import struct
import subprocess
import threading
import time
import types

# Valor escolhido com "gtouchpad corner" (~/.config/gtouchpad.conf, passado pelo serviço).
CORNER_PROGRAM = os.environ.get("CORNER_PROGRAM", CORNER_PROGRAM)

EV_SYN, EV_KEY, EV_ABS = 0, 1, 3
SYN_REPORT, SYN_DROPPED = 0, 3
ABS_MT_SLOT, ABS_MT_POSITION_X, ABS_MT_POSITION_Y, ABS_MT_TRACKING_ID = 0x2F, 0x35, 0x36, 0x39
EVENT = struct.Struct("llHHi")  # struct input_event (x86_64)

ARGS = None


def log(msg):
    print(time.strftime("%H:%M:%S ") + msg, flush=True)


def find_device():
    for p in sorted(glob.glob("/sys/class/input/event*")):
        try:
            with open(p + "/device/name") as f:
                if f.read().strip() == TOUCHPAD_NAME:
                    return "/dev/input/" + os.path.basename(p)
        except OSError:
            pass
    return None


def abs_range(fd, code):
    # EVIOCGABS(code) = _IOR('E', 0x40 + code, struct input_absinfo) — 6 × int32
    req = (2 << 30) | (24 << 16) | (ord("E") << 8) | (0x40 + code)
    buf = fcntl.ioctl(fd, req, bytes(24))
    _, lo, hi, *_ = struct.unpack("6i", buf)
    return lo, hi


# ------------------------------------------------------------------ ações

# As ações rodam numa thread separada, em ordem: um comando lento (wpctl, busctl...) não trava a leitura
# do touchpad. Fila cheia = o usuário está mais rápido que os comandos; o passo extra é descartado.
ACTIONS = queue.Queue(maxsize=16)


def action_worker():
    while True:
        fn, arg = ACTIONS.get()
        try:
            fn(arg)
        except Exception as e:  # uma ação com erro não pode matar a thread
            log(f"   erro na ação {fn.__name__}: {e}")


def do(fn, arg):
    try:
        ACTIONS.put_nowait((fn, arg))
    except queue.Full:
        log("   ação descartada (fila cheia)")


def run(cmd, detach=False):
    if ARGS.dry_run:
        log(f"   (dry-run) {' '.join(cmd)}")
        return
    try:
        if detach:
            subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        else:
            subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=3)
    except (OSError, subprocess.SubprocessError) as e:
        log(f"   erro ao executar {cmd[0]}: {e}")


# ------------------------------------------------------------------ ambiente gráfico (DE)
# O que cada gesto FAZ fica em desktops/<nome>_ctl.py, um arquivo por DE (contrato em desktops/README.md).
# Aqui só se escolhe o arquivo certo pelo XDG_CURRENT_DESKTOP.

REPO_URL = "https://github.com/ayelsew/linux-for-vivobook-s14"
DESKTOPS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "desktops")
BACKEND = None      # módulo *_ctl.py escolhido
CTX = None          # o que o módulo recebe: run, log e os limites de volume/brilho


def load_desktops():
    mods = []
    for path in sorted(glob.glob(os.path.join(DESKTOPS_DIR, "*_ctl.py"))):
        name = os.path.basename(path)[:-3]
        try:  # carrega pelo caminho: python3 -I não procura módulos na pasta do script
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except Exception as e:
            log(f"erro carregando {name}.py: {e}")
            continue
        missing = [a for a in ("DESKTOP", "volume", "brightness", "media") if not hasattr(mod, a)]
        if missing:
            log(f"{name}.py ignorado: falta {', '.join(missing)}")
            continue
        mods.append(mod)
    return mods


def detect_desktop():
    mods = load_desktops()
    current = os.environ.get("XDG_CURRENT_DESKTOP", "")
    names = [n.upper() for n in current.split(":")]
    for mod in mods:
        if mod.DESKTOP.upper() in names:
            return mod.DESKTOP, mod
    fallback = next((m for m in mods if getattr(m, "FALLBACK", False)), None)
    if fallback is None:
        raise SystemExit(f"nenhuma integração de ambiente gráfico em {DESKTOPS_DIR}")
    log(f"ambiente gráfico '{current or 'desconhecido'}' sem suporte: usando {fallback.DESKTOP} como padrão "
        f"(pode não mostrar aviso na tela). Contribua com um PR: {REPO_URL}")
    return None, fallback


def action(name):
    """Ação do módulo do DE pronta para a fila: recebe só o argumento do gesto."""
    fn = functools.partial(getattr(BACKEND, name), CTX)
    fn.__name__ = name
    return fn


def corner(_=None):
    cmd = shlex.split(CORNER_PROGRAM)
    if not cmd:
        return
    run(cmd, detach=True)


# ------------------------------------------------------------------ gestos

class Gestures:
    def __init__(self, xr, yr):
        self.x0, self.x1 = xr
        self.y0, self.y1 = yr
        self.w = self.x1 - self.x0
        self.h = self.y1 - self.y0
        self.g = None

    def start(self, tid, x, y):
        fx = (x - self.x0) / self.w
        fy = (y - self.y0) / self.h
        # As zonas não se sobrepõem: no máximo uma é verdadeira.
        corner = fx >= 1 - EDGE_X and fy <= EDGE_Y
        left = fx <= EDGE_X and LEFT_Y_RANGE[0] <= fy <= LEFT_Y_RANGE[1]
        right = fx >= 1 - EDGE_X and RIGHT_Y_RANGE[0] <= fy <= RIGHT_Y_RANGE[1]
        top = fy <= EDGE_Y and TOP_X_RANGE[0] <= fx <= TOP_X_RANGE[1]
        if not (corner or left or right or top):
            if ARGS.verbose and (fx <= EDGE_X or fx >= 1 - EDGE_X or fy <= EDGE_Y):
                log(f"toque na borda fora das zonas em {fx:.1%},{fy:.1%}")
            self.g = None
            return
        self.g = {"tid": tid, "sx": x, "sy": y, "ay": y, "corner": corner, "left": left, "right": right,
                  "top": top, "kind": None, "done": False}
        if ARGS.verbose:
            zone = next(z for z in ("corner", "left", "right", "top") if self.g[z])
            log(f"toque na zona {zone} em {fx:.1%},{fy:.1%}")

    def move(self, tid, x, y):
        g = self.g
        if not g or g["tid"] != tid or g["done"]:
            return
        dx, dy = x - g["sx"], y - g["sy"]
        if g["kind"] is None:
            if math.hypot(dx / self.w, dy / self.h) < DECIDE_DISTANCE:
                return
            if g["corner"]:
                if dx < 0 and dy > 0 and min(-dx / self.w, dy / self.h) > DECIDE_DISTANCE * 0.4:
                    g["kind"] = "corner"
                else:
                    g["done"] = True  # saiu do canto sem ir para o centro: ignora o toque
                    return
            elif abs(dy) / self.h > abs(dx) / self.w and (g["left"] or g["right"]):
                g["kind"] = "left" if g["left"] else "right"
            elif g["top"]:
                g["kind"] = "top"
            else:
                g["done"] = True  # direção não combina com a borda: ignora o toque
                return
            if ARGS.verbose:
                log(f"gesto: {g['kind']}")

        if g["kind"] in ("left", "right"):
            step = STEP_DISTANCE * self.h
            while abs(y - g["ay"]) >= step:
                up = y < g["ay"]  # Y cresce para baixo
                g["ay"] += -step if up else step
                log(f"{'volume' if g['kind'] == 'left' else 'brilho'} {'+' if up else '−'}")
                do(action("volume" if g["kind"] == "left" else "brightness"), up)
        elif g["kind"] == "top":
            if abs(dx) >= SWIPE_DISTANCE * self.w:
                log("mídia: " + ("próxima" if dx > 0 else "anterior"))
                do(action("media"), dx > 0)
                g["done"] = True
        elif g["kind"] == "corner":
            if math.hypot(dx / self.h, dy / self.h) >= CORNER_DISTANCE:
                log(f"canto → {CORNER_PROGRAM}")
                do(corner, None)
                g["done"] = True

    def cancel(self, reason="mais de um dedo"):
        if self.g and not self.g["done"] and ARGS.verbose:
            log(f"gesto cancelado ({reason})")
        self.g = None


def loop(dev):
    fd = os.open(dev, os.O_RDONLY)
    try:
        xr, yr = abs_range(fd, ABS_MT_POSITION_X), abs_range(fd, ABS_MT_POSITION_Y)
        log(f"touchpad {dev}: X {xr[0]}–{xr[1]}, Y {yr[0]}–{yr[1]}; canto abre: {CORNER_PROGRAM}"
            + ("  [dry-run]" if ARGS.dry_run else ""))
        gest = Gestures(xr, yr)
        slots = {}          # slot -> [tracking_id, x, y, novo]
        slot = 0
        dropped = False     # o kernel perdeu eventos (buffer cheio): ignora até o próximo SYN_REPORT
        while True:
            data = os.read(fd, EVENT.size * 64)
            for off in range(0, len(data) - EVENT.size + 1, EVENT.size):
                _, _, typ, code, val = EVENT.unpack_from(data, off)
                if typ == EV_SYN and code == SYN_DROPPED:
                    dropped = True
                    continue
                if dropped:
                    if typ == EV_SYN and code == SYN_REPORT:
                        # Estado dos dedos desconhecido: esquece tudo. Dedos que já estavam no touchpad
                        # ficam ignorados até levantar; o próximo toque começa limpo.
                        dropped = False
                        slots.clear()
                        gest.cancel("eventos perdidos")
                        log("eventos perdidos (SYN_DROPPED); estado dos dedos reiniciado")
                    continue
                if typ == EV_ABS:
                    if code == ABS_MT_SLOT:
                        slot = val
                    else:
                        s = slots.setdefault(slot, [-1, 0, 0, False])
                        if code == ABS_MT_TRACKING_ID:
                            s[0] = val
                            s[3] = val != -1
                        elif code == ABS_MT_POSITION_X:
                            s[1] = val
                        elif code == ABS_MT_POSITION_Y:
                            s[2] = val
                elif typ == EV_SYN and code == SYN_REPORT:
                    active = [s for s in slots.values() if s[0] != -1]
                    if len(active) == 1:
                        tid, x, y, new = active[0]
                        if new:
                            gest.start(tid, x, y)
                        else:
                            gest.move(tid, x, y)
                    elif len(active) > 1:
                        gest.cancel()
                    else:
                        gest.g = None
                    for s in slots.values():
                        s[3] = False
    finally:
        os.close(fd)


def main():
    global ARGS, BACKEND, CTX
    ap = argparse.ArgumentParser(description="Gestos de borda do touchpad ASUS")
    ap.add_argument("--dry-run", action="store_true", help="só mostra os gestos, não executa nada")
    ap.add_argument("-v", "--verbose", action="store_true")
    ARGS = ap.parse_args()
    desktop, BACKEND = detect_desktop()
    if desktop:
        log(f"ambiente gráfico: {desktop}")
    CTX = types.SimpleNamespace(run=run, log=log, volume_step=VOLUME_STEP, volume_max=float(VOLUME_MAX),
                                brightness_step_pct=BRIGHTNESS_STEP_PCT, brightness_min_pct=BRIGHTNESS_MIN_PCT)
    threading.Thread(target=action_worker, daemon=True).start()

    waited = False
    no_perm = False
    while True:  # aguenta o touchpad sumir/voltar (ex.: suspensão)
        dev = find_device()
        if not dev:
            if not waited:
                log(f"touchpad '{TOUCHPAD_NAME}' não encontrado; esperando...")
                waited = True
            time.sleep(2)
            continue
        waited = False
        try:
            loop(dev)
        except PermissionError:
            # Sem sair: o serviço reiniciaria a cada 3 s para sempre. A permissão pode chegar depois
            # (regra udev instalada, ou o logind libera o acesso ao entrar na sessão): tenta de novo devagar.
            if not no_perm:
                log(f"sem permissão para ler {dev}: instale 70-touchpad-edge-gestures.rules "
                    "(gtouchpad install). Tentando de novo a cada 10 s...")
                no_perm = True
            time.sleep(10)
            continue
        except OSError as e:
            log(f"touchpad perdido ({e}); tentando de novo...")
            time.sleep(1)
        no_perm = False


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
