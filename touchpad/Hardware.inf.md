# Touchpad 093A:3016 — ASUS Vivobook S 14 S5406SA

## Identificação

| Item | Valor |
|---|---|
| Fabricante do chip | PixArt (`093A`) |
| Produto | `093A:3016`, versão `0100` |
| ID ACPI | `ASCP1200` (compatível `PNP0C50`, HID sobre I2C) |
| Tipo | Precision Touchpad (PTP) do Windows, clickpad (sem botões físicos separados) |
| Tamanho da área de toque | 126,9 × 82,0 mm |

## Interface

| Item | Valor |
|---|---|
| Barramento | I2C HID v1.00 |
| Controlador I2C | Intel Core Ultra 200V I2C #1 (`8086:a879`) |
| Interrupção | Linha GPIO própria |
| Pode acordar o sistema | Sim |

## Capacidades

| Item | Valor |
|---|---|
| Toques simultâneos | 5 |
| Por toque | Posição X/Y, ID do contato, toque ativo, confiança (palma) |
| Botões | 1 (clique da superfície inteira) |
| Pressão / tamanho do contato / háptico | Não tem |
| Scan time | 16 bits, unidade 100 µs |

| Eixo | Lógico | Físico | Resolução |
|---|---|---|---|
| X | 0–3996 | 0–126,9 mm | ≈ 31,5 unidades/mm |
| Y | 0–2582 | 0–82,0 mm | ≈ 31,5 unidades/mm |

## Relatórios HID

| Report ID | Tipo | Conteúdo | Valor lido |
|---|---|---|---|
| `0x01` | Input | Modo mouse de compatibilidade: 2 botões, X/Y/roda relativos de 8 bits | — |
| `0x54` | Input | Touchpad: 5 contatos, contagem de contatos, scan time, botão e campos do fabricante (página `0xFF01`) | — |
| `0x02` | Feature | Máximo de contatos | `05` = 5 |
| `0x03` | Feature | Modo de entrada | `03` = Precision Touchpad (0 seria mouse) |
| `0x05` | Feature | Liga/desliga superfície e botão | `03` = superfície e botão ligados |
| `0x06` | Feature | Tipo do touchpad | `00` = superfície que afunda no clique (clickpad, não pressure pad) |
| `0x07` | Feature | Modo de latência | sem resposta (0 bytes) |
| `0x0B` | Feature | Fabricante `0xFF00`, 256 bytes: certificação PTP do Windows | blob de 256 bytes de aparência aleatória (assinatura) |
| `0x0D` | Feature | Fabricante `0xFF00`, 32 bits | `02 01 06 33` (significado desconhecido; talvez versão de firmware) |
| `0x41` | Feature | Fabricante `0xFF00`, 256 bytes | tudo zero |
| `0x42` | Feature | Fabricante `0xFF00`, 3 bytes | `79 00 02` (desconhecido) |
| `0x43` | Feature | Fabricante `0xFF00`, 3 bytes | `7e 00 00` (desconhecido) |

Valores lidos em 2026-11-24 com GET_FEATURE (só leitura).
