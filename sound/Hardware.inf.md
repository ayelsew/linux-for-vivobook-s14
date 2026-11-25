# Som — ASUS Vivobook S 14 S5406SA

## Identificação

| Item | Valor |
|---|---|
| Processador | Intel Core Ultra 7 256V (Lunar Lake) |
| Controlador de áudio | Intel Smart Sound Technology (SST), PCI `8086:A828`, subsys `1043:10C4` |
| Codec | Realtek ALC294 (`10EC:0294`), subsys `1043:10C4`, revisão `1000` |
| Microfones internos | Microfones digitais (DMIC) ligados direto no DSP da Intel, não no codec |
| Amplificador externo (smart amp) | Não tem: nenhum Cirrus (`CSC3551`) nem TI (`TIAS2781`) no ACPI. O ALC294 alimenta os alto-falantes |

## Ligações do DSP Intel SST

| Ligação | ID | Uso |
|---|---|---|
| HD-Audio | `INTELAUDIO\FUNC_01&VEN_10EC&DEV_0294` | Codec Realtek: alto-falantes e conector P2 |
| DMIC | `DEV_AE20` | Microfones internos ("Microphone Array") |
| Bluetooth | `DEV_AE30` | Áudio Bluetooth clássico com offload |
| Bluetooth LE | `DEV_AE33` | LE Audio com offload |
| USB | `DEV_AE50` | Áudio USB com offload |

## Saídas e entradas (endpoints do Windows)

| Endpoint | Formato padrão | Observação |
|---|---|---|
| Speakers (Realtek) | 2 canais, 48 kHz, 24 bits (em 32) | 2 alto-falantes frontais (esquerdo e direito) |
| Headphones (Realtek) | 2 canais, 48 kHz, 24 bits (em 32) | Conector P2; aparece desconectado sem fone |
| Microphone (Realtek) | — | Microfone do conector combo (fone com microfone); desconectado sem fone |
| Microphone Array (Intel SST DMIC) | 2 canais, 48 kHz, 24 bits (em 32) | Microfones internos |

## Arquivo de ajuste Dolby

O driver Dolby traz um ajuste feito para este modelo:
[DEV_0294_SUBSYS_104310C4_PCI_SUBSYS_10C41043.xml](DEV_0294_SUBSYS_104310C4_PCI_SUBSYS_10C41043.xml)
(versão do ajuste 11, data 15/01/2025). O que ele faz está em [Good on Windows.md](Good%20on%20Windows.md).

No Windows ele fica em:
`C:\Windows\System32\DriverStore\FileRepository\dax3_ext_rtk.inf_amd64_*\`

Valores lidos em 2026-11-25 no Windows 11 (Gerenciador de Dispositivos, `pnputil` e registro MMDevices).
