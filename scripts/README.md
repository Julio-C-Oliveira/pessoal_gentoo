# emerge-progress

Utilitário em Python puro (sem dependências externas) para acompanhar o progresso em tempo real das instalações e compilações do Gentoo Portage (`emerge`).

Ao contrário de scripts simples que monitoram apenas o Ninja, o `emerge-progress` detecta múltiplos sistemas de build e fornece uma visão completa do processo.

---

## Recursos

- **Múltiplos Sistemas de Build**:
  - **Ninja / Meson**: Captura etapas `[X/Y]` nativas e calcula porcentagem exata.
  - **CMake**: Captura porcentagem `[X%]` nativa gerada pelo Makefile do CMake.
  - **Cargo (Rust)**: Monitora contagem de crates e etapas `(X/Y)`.
  - **GNU Make / Autotools**:
    - Extrai histórico de compilações anteriores em `/var/log/emerge.log` para calcular porcentagem e tempo restante estimado (ETA), similar ao `qlop`.
    - Contabiliza objetos compilados (`.o`) e exibe o arquivo que o compilador (`gcc`/`clang`) está processando no momento.
- **Progresso Global da Fila**:
  - Exibe posição na fila (ex: `[2/5] sys-devel/gcc-13.2.0`).
  - Monitora fases do Portage: `Cleaning`, `Compiling/Packaging`, `Installing`, `Merging`, `Completed installation`.
- **Interface Terminal Otimizada**:
  - Atualização contínua no mesmo local (sem poluir o scroll do terminal).
  - Cores ANSI com suporte automático a terminais sem cor / `NO_COLOR`.
- **Modo Snapshot (`--once` / `-1`)**:
  - Saída compacta em linha única, ideal para scripts, Tmux status bar, Waybar ou Polybar.
- **Zero Dependências**:
  - Funciona diretamente com o Python 3 padrão do Gentoo.

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
Substitua a função antiga pelo alias:
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
Portage [1/3] media-video/ffmpeg-6.1 [Compiling/Packaging]
  [█████████░░░░░░░░░░░░░░░░░░░░░]  30.4% | Make/Autotools (42 objs) | 30s (ETA: 1m 09s) (hist: 1m 40s) >> f_metadata.o
```

### Modo Snapshot (`--once`)
```text
[1/3] media-video/ffmpeg-6.1 (Compiling/Packaging) | [█████████░░░░░░░░░░░░░░░░░░░░░]  30.4% | Make/Autotools (42 objs) | 30s (ETA: 1m 09s)
```

---

## Testes Automatizados

Para executar os testes unitários:
```bash
python3 scripts/test_emerge_progress.py
```
