# emerge-progress

Utilitário em Python puro (sem dependências externas) para acompanhar em tempo real o progresso geral da fila e das compilações individuais do Gentoo Portage (`emerge`).

Ao contrário de scripts simples que monitoram apenas o Ninja, o `emerge-progress` detecta múltiplos sistemas de build, acompanha múltiplos pacotes paralelos (`--jobs=2` ou superior) e consolida o progresso geral da fila em um painel atualizado *in-place*.

---

## Recursos

- **Painel de Progresso Geral da Fila**:
  - Barra de progresso geral ponderada (pacotes concluídos + fração de avanço dos pacotes ativos).
  - Contagem `[concluídos/total]` e quantidade de pacotes ativos simultaneamente.
  - Tempo total decorrido da fila e ETA global estimado.
  - Exibição do último pacote concluído (com duração) e métricas leves do sistema via `/proc` (Load Average e uso de RAM).
- **Suporte Nativo a Compilações Paralelas (`--jobs`)**:
  - Monitora todos os `build.log` ativos simultaneamente em `/var/tmp/portage/*/*/temp/build.log`, sem alternar ou zerar contadores quando dois ou mais pacotes compilam ao mesmo tempo.
- **Múltiplos Sistemas de Build**:
  - **Ninja / Meson**: Captura etapas `[X/Y]` nativas e calcula porcentagem exata.
  - **CMake**: Captura porcentagem `[X%]` nativa gerada pelo Makefile do CMake.
  - **Cargo (Rust)**: Monitora contagem de crates e etapas `(X/Y)`.
  - **`./configure` (Autoconf)**: Detecta testes de configuração (`checking ...`) antes do início da compilação.
  - **GNU Make / Autotools**:
    - Na primeira compilação (sem histórico no `emerge.log`), conta os arquivos-fonte em `/var/tmp/portage/<cat>/<pkg>/work/` para estimar a porcentagem (`~XX.X%`) e deduplica compilações PIC/non-PIC do `libtool`.
    - Extrai histórico de compilações anteriores em `/var/log/emerge.log` como fallback para estimativa e cálculo de tempo restante (ETA).
- **Interface Terminal Otimizada**:
  - Atualização contínua *in-place* com truncamento seguro de linhas ANSI para evitar quebras de linha (*line-wrap*) e scroll infinito no terminal.
  - Cores ANSI com suporte automático a terminais sem cor / `NO_COLOR`.
- **Modo Snapshot (`--once` / `-o`)**:
  - Saída compacta em linha única combinando o progresso geral da fila e os pacotes ativos, ideal para scripts, Tmux status bar, Waybar ou Polybar.
- **Zero Dependências**:
  - Funciona diretamente com o Python 3 padrão do Gentoo.

---

## Permissões para Leitura do `/var/log/emerge.log`

Por padrão no Gentoo, o arquivo `/var/log/emerge.log` pertence ao grupo `portage` (permissão `660` ou `640`). Para que o `emerge-progress` consiga exibir o Progresso Geral da fila sem precisar de `sudo`, adicione seu usuário ao grupo `portage`:

```bash
sudo gpasswd -a $USER portage
```
*(Faça logout e login novamente, ou execute `newgrp portage`, para a permissão entrar em vigor).*

---

## Como Usar

### Execução Direta
```bash
./scripts/emerge-progress
```

### Criar Atalho Global (Recomendado)
Para poder chamar `emerge-progress` de qualquer diretório:

1. **Via link simbólico em `~/.local/bin`:**
```bash
mkdir -p ~/.local/bin
ln -sf "$(pwd)/scripts/emerge-progress" ~/.local/bin/emerge-progress
```
*(Certifique-se de que `~/.local/bin` está no seu `$PATH`)*

2. **Ou via alias no seu `~/.bashrc`:**
```bash
alias emerge-progress="/home/julio/Documentos/pessoal_gentoo/scripts/emerge-progress"
```

---

## Opções de Linha de Comando

```text
usage: emerge-progress [-h] [-o] [-i INTERVAL] [--emerge-log EMERGE_LOG]
                       [--portage-tmp PORTAGE_TMP] [--no-color]

options:
  -h, --help            Exibe a mensagem de ajuda e sai.
  -o, --once            Imprime o status atual em linha única e sai imediatamente.
  -i, --interval N      Intervalo de atualização em segundos no modo contínuo (padrão: 0.5s).
  --emerge-log PATH     Caminho alternativo para o emerge.log (padrão: /var/log/emerge.log).
  --portage-tmp PATH    Caminho alternativo para o diretório de build (padrão: /var/tmp/portage).
  --no-color            Desativa cores e códigos ANSI.
```

---

## Exemplos de Saída

### Modo Contínuo (Live)
```text
╭─ Progresso Geral da Fila ────────────────────────────────────────────────────╮
│ [████████████░░░░░░░░░░░░░░░░░░]  41.2% | 18/45 concluídos (2 ativos)        │
│ Tempo: 14m 20s (ETA: ~20m 15s) | Load: 2.15 1.98 | RAM: 3.4/7.8GB (43%)      │
│ Último concluído: dev-libs/boehm-gc-8.2.12 (14s)                             │
╰──────────────────────────────────────────────────────────────────────────────╯
▶ [19/45] dev-libs/libconfig-1.8.2 [Compiling/Packaging]
  [██████████████████░░░░░░░░░░░░] ~62.5% | Make/Autotools (25/40 objs) | 9s (ETA: ~5s) >> libconfigcpp.o
▶ [20/45] x11-libs/libxcb-1.17.0 [Configuring]
  [      <===>                   ]   ---% | ./configure (84 checks) | 4s (ETA: --) >> checking for xcb-proto...
```

### Modo Snapshot (`--once`)
```text
Fila: 18/45 (41.2%, ETA: ~20m 15s) | [19/45] dev-libs/libconfig-1.8.2: ~62.5% (Make/Autotools (25/40 objs)) | [20/45] x11-libs/libxcb-1.17.0: ---% (./configure (84 checks))
```

---

## Testes Automatizados

Para executar os testes unitários:
```bash
python3 scripts/test_emerge_progress.py -v
```
