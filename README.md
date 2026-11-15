# Guia de Instalação do Gentoo Linux

Tutorial de instalação do Gentoo Linux baseado no Amd64 Handbook oficial, utilizando **Systemd**, **Distribution Kernel** (`sys-kernel/gentoo-kernel`) e inicialização segura via **UEFI Secure Boot** com **Shim + GRUB + MOK**.

---

## Organização Modular do `/etc/portage/`

No Gentoo, as definições de compilação por pacote (`USE flags`), palavras-chave (`accept_keywords`) e licenças (`license`) podem ser definidas em arquivos únicos ou, preferencialmente, dentro de diretórios modulares sob `/etc/portage/`.

O uso de **diretórios modulares** é a prática recomendada:
- **Ordem lexicográfica de leitura**: O Portage lê todos os arquivos contidos no diretório em ordem alfabética/numérica (`00-` é lido antes de `01-`). Se houver regras conflitantes para um mesmo pacote, a regra do arquivo lido por último prevalece.
- **Manutenção simplificada**: Cada arquivo agrupa pacotes de uma camada lógica do sistema.

### Estrutura adotada neste repositório:

#### Diretório `/etc/portage/package.use/`:
- `00-core`: Flags baseline globais (`*/* X dbus udev alsa opengl pulseaudio pipewire`), flags de arquitetura de CPU (`CPU_FLAGS_X86`) geradas pelo `cpuid2cpuflags`, placas de vídeo (`VIDEO_CARDS`) e dispositivos de entrada (`INPUT_DEVICES`).
- `01-kernel`: Flags dos pacotes do kernel (`sys-kernel/gentoo-kernel`, `sys-kernel/installkernel`), assinaturas (`modules-sign`, `secureboot`) e a flag `*/* dist-kernel` (mantida comentada até o passo do kernel).
- `02-network`: Conectividade e gerenciamento de rede (`net-misc/networkmanager`, `net-wireless/wpa_supplicant`, `gnome-extra/nm-applet`).
- `03-bootloader`: Carregador de inicialização e assinatura EFI (`sys-boot/grub`, `sys-boot/shim`).
- `04-xorg`: Servidor gráfico X11, utilitários e drivers (`x11-base/xorg-server`, `xf86-input-libinput`, `xinit`, `xrandr`, `xhost`, `setxkbmap`, `xdg-user-dirs`).
- `05-audio`: Subsistema de áudio moderno com PipeWire, WirePlumber, controle de volume (`pavucontrol`, `libpulse`) e player multimídia (`mpv`).
- `06-wm-bspwm`: Gerenciador de janelas BSPWM, atalhos SXHKD, barra Polybar, compositor Picom, launcher Rofi, notificações Dunst, SDDM, bloqueio de tela (`xsecurelock`) e temas (`qt6ct`, `lxappearance`, `numlockx`).
- `07-services`: Serviços de sistema como Bluetooth (`bluez`, `blueman`), firewall (`ufw`), integração de arquivos (`gvfs`), Flatpak, Polkit, clipboard (`xclip`), notificações (`libnotify`), `xdg-utils` e ZRAM.
- `08-apps`: Aplicações de usuário, incluindo Firefox binário (`firefox-bin`), terminal Kitty, gerenciador de arquivos Yazi, visualizador Feh, captura com Maim, `yt-dlp`, busca (`ripgrep`, `fd`), descompactadores (`zip`, `unzip`, `p7zip`) e Neovim.
- `09-fonts`: Subsistema Fontconfig, renderização FreeType (`harfbuzz`) e fontes (Fira Code, Noto, Noto CJK, Noto Emoji, Nerd Fonts).

#### Diretório `/etc/portage/package.accept_keywords/`:
- `06-wm-bspwm`: Desmascara pacotes em testes (`~amd64`) para utilitários do GURU como `xsecurelock`.
- `07-services`: Libera o utilitário de controle de brilho `app-misc/brightnessctl` (`~amd64`).
- `08-apps`: Libera versões upstream recentes de utilitários como `yazi` e `fastfetch`.
- `09-fonts`: Libera fontes Nerd Fonts provenientes do repositório GURU.

#### Diretório `/etc/portage/package.license/`:
- `08-apps`: Aceitação explícita de licença redistribuível para pacotes binários oficiais (ex: `www-client/firefox-bin Mozilla2.0`).

---

# 1. Preparing the disks

> [!NOTE]
> Identifique o nome do seu disco com `lsblk`.
> - Discos SATA/SCSI costumam ser `/dev/sda` (partições `sda1`, `sda2`, etc.).
> - Discos NVMe costumam ser `/dev/nvme0n1` (partições `nvme0n1p1`, `nvme0n1p2`, etc.).
> Substitua `/dev/disco` e as numerações a seguir de acordo com o seu hardware.

| Partição | Ponto de Montagem | Tamanho | Início (MiB) | Fim (MiB) | Tipo / Sistema de Arquivos |
| :------: | :---------------: | :-----: | :----------: | :-------: | :------------------------: |
| 1 | `/boot/efi` | 512 MB | 1 | 513 | FAT32 (ESP) |
| 2 | `/boot` | 1024 MB | 513 | 1537 | Ext4 |
| 3 | `[SWAP]` | 4096 MB | 1537 | 5633 | Linux Swap |
| 4 | `/` | 30720 MB (30 GB) | 5633 | 36353 | Ext4 |
| 5 | `/var` | 51200 MB (50 GB) | 36353 | 87553 | Ext4 |
| 6 | `/home` | Restante | 87553 | -1 | Ext4 |

> [!IMPORTANT]
> **Por que 50 GB para a partição `/var`?**
> É em `/var/tmp/portage` que o Gentoo realiza a compilação de todos os pacotes. Pacotes de grande porte (como GCC, Rust, Clang, Chromium e WebKit) demandam dezenas de gigabytes de espaço temporário de compilação. Um `/var` de 50 GB evita falhas de compilação e a mensagem de *"parallelism reduced"* causada por falta de espaço em disco.

### Comandos para particionamento:
```bash
# Limpeza de assinaturas e partições anteriores:
wipefs -a /dev/disco
sgdisk --zap-all /dev/disco
partprobe /dev/disco

# Criação das partições via parted:
parted -a optimal /dev/disco
```
Dentro do shell do `parted`:
```parted
mklabel gpt
unit mib
mkpart efi fat32 1 513
set 1 esp on
set 1 boot on
mkpart boot ext4 513 1537
mkpart swap linux-swap 1537 5633
mkpart rootfs ext4 5633 36353
mkpart var ext4 36353 87553
mkpart home ext4 87553 -1
print
quit
```

### Comandos para formatação:
```bash
lsblk
mkfs.fat -F32 -n EFI /dev/disco1
mkfs.ext4 -L BOOT /dev/disco2
mkswap -L SWAP /dev/disco3
swapon /dev/disco3
mkfs.ext4 -L ROOTFS /dev/disco4
mkfs.ext4 -L VAR /dev/disco5
mkfs.ext4 -L HOME /dev/disco6
```

---

# 2. Installing the Gentoo installation files

### Montando as partições:
```bash
mkdir --parents /mnt/gentoo
mount /dev/disco4 /mnt/gentoo
cd /mnt/gentoo
mkdir -p boot/efi var home
mount /dev/disco2 /mnt/gentoo/boot
mount /dev/disco1 /mnt/gentoo/boot/efi
mount /dev/disco5 /mnt/gentoo/var
mount /dev/disco6 /mnt/gentoo/home
```

### Verificando e sincronizando a data e hora:
> [!IMPORTANT]
> Sincronize a data/hora **antes** de tentar conexões HTTPS. Relógios defasados geram erros de validação SSL/TLS ao baixar arquivos.

```bash
date
chronyd -q
```
Se estiver sem acesso à rede NTP no momento, configure manualmente no formato `MMDDhhmmYYYY`:
```bash
date 111309402026
```

### Baixando e extraindo o Stage3:
```bash
cd /mnt/gentoo
links https://www.gentoo.org/downloads/
# Navegue até a seção amd64 e baixe a variante: "Stage 3 | Systemd"
```
Extraia preservando atributos estendidos e proprietários numéricos:
```bash
tar xpvf stage3-*.tar.xz --xattrs-include='*.*' --numeric-owner
```

### Verificando a integridade da imagem (Recomendado):
```bash
gpg --import /usr/share/openpgp-keys/gentoo-release.asc
sha256sum --check stage3-*.tar.xz.sha256
```

---

# 3. Installing the Gentoo base system

### Clonando as configurações deste repositório:
```bash
git clone https://github.com/Julio-C-Oliveira/pessoal_gentoo.git /mnt/gentoo/home/pessoal_gentoo
cp /mnt/gentoo/home/pessoal_gentoo/make.conf /mnt/gentoo/etc/portage/make.conf
cp -r /mnt/gentoo/home/pessoal_gentoo/package.use /mnt/gentoo/etc/portage/
cp -r /mnt/gentoo/home/pessoal_gentoo/package.accept_keywords /mnt/gentoo/etc/portage/
cp -r /mnt/gentoo/home/pessoal_gentoo/package.license /mnt/gentoo/etc/portage/
```

> [!WARNING]
> **ATENÇÃO: Flag `*/* dist-kernel` em `01-kernel`**:
> O arquivo `package.use/01-kernel` deste repositório vem intencionalmente com a linha `*/* dist-kernel` **comentada**.
> **Mantenha-a comentada neste momento!**
> Habilitar `dist-kernel` antes de chegar na etapa de configuração do kernel pode gerar erros de dependências prematuras durante a atualização inicial do conjunto `@world`. Você só deverá descomentá-la na Seção 4 ("Configuring the Linux kernel").

> [!IMPORTANT]
> **Ajuste o número de jobs no `make.conf`!**
> Abra `/mnt/gentoo/etc/portage/make.conf` e confira as variáveis `MAKEOPTS` e `EMERGE_DEFAULT_OPTS`. A regra padrão é **2 GB de RAM por job**. Se sua máquina tiver 8 GB de RAM, utilize no máximo `-j4 -l4`.

> [!NOTE]
> O arquivo `make.conf` deste repositório já vem com os mirrors brasileiros (`GENTOO_MIRRORS`) devidamente pré-configurados. Não é necessário rodar `mirrorselect >> make.conf`.

### Preparando e entrando no Chroot:
```bash
cp --dereference /etc/resolv.conf /mnt/gentoo/etc/
mount --types proc /proc /mnt/gentoo/proc
mount --rbind /sys /mnt/gentoo/sys
mount --make-rslave /mnt/gentoo/sys
mount --rbind /dev /mnt/gentoo/dev
mount --make-rslave /mnt/gentoo/dev
mount --bind /run /mnt/gentoo/run
mount --make-slave /mnt/gentoo/run

# Ajuste de segurança para o /dev/shm:
test -L /dev/shm && rm /dev/shm && mkdir /dev/shm
mount --types tmpfs --options nosuid,nodev,noexec shm /dev/shm
chmod 1777 /dev/shm /run/shm

# Entrada no ambiente chroot:
chroot /mnt/gentoo /bin/bash
source /etc/profile
export PS1="(chroot) ${PS1}"
```

### Configurando o Portage e selecionando o Profile:
```bash
emerge-webrsync
eselect profile list
```
Identifique o número correspondente ao perfil **systemd** de 64 bits (ex: `default/linux/amd64/23.0/systemd`):
```bash
eselect profile set <NUMERO_DO_SEU_PROFILE_SYSTEMD>
```

### Configurando as CPU Flags:
```bash
emerge --ask --oneshot app-portage/cpuid2cpuflags
cpuid2cpuflags > /etc/portage/package.use/00-core
```

### Configurando a Placa de Vídeo (`VIDEO_CARDS`):
Identifique seu hardware gráfico:
```bash
emerge --ask app-editors/vim
emerge --ask --oneshot sys-apps/pciutils
lspci -k | grep -A 3 -i "VGA"
```

Tabela de referência para a variável `VIDEO_CARDS`:
| GPU / Ambiente | Valor para `VIDEO_CARDS` |
| :------------: | :----------------------: |
| Intel (Nehalem e mais recentes) | `intel` |
| AMD (GCN 3+, RDNA) | `amdgpu radeonsi` |
| Nvidia (Driver proprietário oficial) | `nvidia` |
| Nvidia (Driver livre) | `nouveau` |
| VMware | `vmware` |
| QEMU / KVM | `virgl` |
| VirtualBox | `virtualbox` |

Adicione em `/etc/portage/package.use/00-core`:
```text
*/* VIDEO_CARDS: -* intel
```

### Atualizando o conjunto @world:
```bash
emerge --ask app-portage/gentoolkit
emerge --ask --verbose --update --deep --changed-use @world
emerge --ask --depclean
```

### Timezone e Locales:
```bash
ln -sf ../usr/share/zoneinfo/America/Belem /etc/localtime

# Descomente pt_BR.UTF-8 UTF-8 e en_US.UTF-8 UTF-8:
vim /etc/locale.gen
locale-gen

eselect locale list
eselect locale set <numero_do_pt_BR>

env-update && source /etc/profile && export PS1="(chroot) ${PS1}"
```

---

# 4. Configuring the Linux kernel

Neste guia utilizamos o **Distribution Kernel** (`sys-kernel/gentoo-kernel`) com módulos e binários assinados digitalmente para suporte a **Secure Boot**.

### Instalando Firmwares e Microcode:
```bash
emerge --ask sys-kernel/linux-firmware
emerge --ask sys-firmware/sof-firmware        # Firmware de áudio para chipsets recentes
emerge --ask sys-firmware/intel-microcode     # Obrigatório se CPU Intel; CPUs AMD já vêm no linux-firmware
```

### Instalando e configurando o `installkernel`:
O `installkernel` orquestra a geração do initramfs (via Dracut) e a instalação no GRUB. As flags necessárias já estão definidas no arquivo `package.use/01-kernel` (`sys-kernel/installkernel grub dracut`).

Identifique o UUID da partição raiz:
```bash
blkid | grep ROOTFS
```
Crie a instrução para o Dracut apontando para a partição raiz:
```bash
mkdir -p /etc/dracut.conf.d
vim /etc/dracut.conf.d/00-installkernel.conf
```
Conteúdo do arquivo (atenção aos espaços antes e depois das aspas):
```ini
kernel_cmdline=" root=UUID=<SEU_UUID_ROOTFS_AQUI> "
```
Instale o utilitário:
```bash
emerge --ask sys-kernel/installkernel
```

### Gerando as chaves de assinatura (Secure Boot e Módulos do Kernel):
Criaremos um par de chaves próprio para assinar o kernel e os módulos.

```bash
mkdir -p /etc/portage/certs
cd /etc/portage/certs

# Gerando o certificado e a chave privada em formato PEM:
openssl req -new -noenc -utf8 -sha256 -x509 \
  -subj "/C=BR/ST=Para/L=Belem/O=Gentoo/CN=Kernel Signing/" \
  -outform PEM -out kernel_key.pem -keyout kernel_key.pem

chmod 400 kernel_key.pem
chown root:root kernel_key.pem

# Gerando a versão DER pública necessária para o mokutil / MOKManager:
openssl x509 -in kernel_key.pem -inform PEM -out kernel_key.der -outform DER
```

> [!IMPORTANT]
> **Ponto exato de ativação da flag `*/* dist-kernel`!**
> Abra o arquivo `/etc/portage/package.use/01-kernel` e **descomente** a linha `*/* dist-kernel`.
> Ela deve ser ativada **exatamente neste ponto**, antes de compilar o kernel, para que todos os drivers e pacotes que fornecem módulos usem o kernel distribuído (`dist-kernel`). Habilitar antes desta etapa pode causar falhas de compilação ou inconsistências.

Confira se o arquivo `/etc/portage/package.use/01-kernel` contém as flags de assinatura e o suporte a módulos do kernel distribuído ativados:
```text
sys-kernel/installkernel grub dracut
sys-kernel/gentoo-kernel modules-sign secureboot
*/* dist-kernel
```

### Compilando e instalando o Kernel:
```bash
emerge --ask sys-kernel/gentoo-kernel
emerge --ask @module-rebuild
```

---

# 5. Configuring the system

### Configurando o `/etc/fstab`:
Obtenha os UUIDs das partições com `blkid`.
Edite o arquivo `/etc/fstab`:
```bash
vim /etc/fstab
```
Exemplo de estrutura:
```text
# <device>               <mount>      <type>  <options>                     <dump> <pass>
UUID=XXXX-XXXX           /boot/efi    vfat    defaults,noatime,umask=0077   0 2
UUID=XXXX-XXXX           /boot        ext4    defaults,noatime              0 2
UUID=XXXX-XXXX           /            ext4    defaults,noatime              0 1
UUID=XXXX-XXXX           /var         ext4    defaults,noatime              0 2
UUID=XXXX-XXXX           /home        ext4    defaults,noatime              0 2
UUID=XXXX-XXXX           none         swap    sw                            0 0
```

### Hostname e Hosts:
```bash
echo tux > /etc/hostname

vim /etc/hosts
```
Adicione:
```text
127.0.0.1     tux.localdomain tux localhost
::1           tux.localdomain tux localhost
```

### Configurando a Rede:
Assegure a presença de `net-wireless/wpa_supplicant dbus` no arquivo `package.use/02-network`.
```bash
emerge --ask net-misc/networkmanager net-wireless/iw net-wireless/wpa_supplicant
systemctl enable NetworkManager
```

### Senha de Root e Serviços do Sistema:
```bash
# Defina a senha do usuário root:
passwd

systemd-machine-id-setup
systemctl preset-all --preset-mode=enable-only

emerge --ask sys-apps/mlocate app-shells/bash-completion net-misc/chrony sys-block/io-scheduler-udev-rules
systemctl enable chronyd.service
```

---

# 6. Configuring the bootloader (GRUB + Shim + Secure Boot)

Configuraremos uma cadeia de boot compatível com UEFI Secure Boot utilizando o **Shim** da Microsoft e o **GRUB** assinado pela sua própria chave MOK.

### Configurando flags e instalando pacotes:
1. Verifique no `/etc/portage/make.conf` se a plataforma do GRUB está no plural:
   ```text
   GRUB_PLATFORMS="efi-64"
   ```
2. Verifique se o arquivo `/etc/portage/package.use/03-bootloader` contém:
   ```text
   sys-boot/grub secureboot
   ```
3. Instale o GRUB e os utilitários de Secure Boot:
   ```bash
   emerge --ask sys-boot/grub sys-boot/shim sys-boot/mokutil sys-boot/efibootmgr
   ```

### Copiando os binários para a partição EFI (ESP):
```bash
mkdir -p /boot/efi/EFI/Gentoo

# Copia o Shim assinado pela Microsoft e o gerenciador de MOK:
cp /usr/share/shim/BOOTX64.EFI /boot/efi/EFI/Gentoo/shimx64.efi
cp /usr/share/shim/mmx64.efi /boot/efi/EFI/Gentoo/mmx64.efi

# Copia o binário do GRUB que foi assinado automaticamente com a sua chave MOK durante o emerge:
cp /usr/lib/grub/grub-x86_64.efi.signed /boot/efi/EFI/Gentoo/grubx64.efi
```

### Cadastrando o certificado no MOK (Machine Owner Key):
```bash
mokutil --import /etc/portage/certs/kernel_key.der
```
> [!IMPORTANT]
> O `mokutil` solicitará que você defina uma senha temporária. Guarde essa senha; ela será solicitada na tela azul de validação no próximo reboot.

### Criando a entrada na NVRAM UEFI:
```bash
efibootmgr --create --disk /dev/disco --part 1 --loader '\EFI\Gentoo\shimx64.efi' --label 'Gentoo (GRUB via Shim)' --unicode
```

### Gerando o arquivo de configuração do GRUB:
```bash
grub-mkconfig -o /boot/efi/EFI/Gentoo/grub.cfg

echo "GRUB_CFG=/boot/efi/EFI/Gentoo/grub.cfg" > /etc/env.d/99grub
env-update
```

> [!NOTE]
> Não é necessário executar `systemd-firstboot`, pois você já configurou hostname, fuso horário, locales, machine-id e senha de root manualmente nos passos anteriores. Além disso, ele falha dentro do chroot quando a mídia LiveCD de instalação roda OpenRC.

---

# 7. Users, Passwords and Sudo (OBRIGATÓRIO ANTES DO REBOOT)

> [!CAUTION]
> **ATENÇÃO MÁXIMA: DEFINA AS SENHAS ANTES DE REINICIAR!**
> O Gentoo **não possui nenhuma senha padrão** para o `root` (a conta vem bloqueada no Stage 3). Se você reiniciar o computador antes de executar o `passwd` ou criar seu usuário, **você ficará trancado fora do sistema** sem conseguir fazer login no console!

### 1. Definindo a senha do Root:
```bash
passwd
```

### 2. Criando o usuário comum e definindo a senha:
Crie o usuário `tux` com os grupos necessários para administração, áudio, vídeo e dispositivos:
```bash
useradd -m -G users,wheel,audio,video,input -s /bin/bash tux
passwd tux
```

### 3. Instalando o Sudo e concedendo privilégios:
```bash
emerge --ask app-admin/sudo
echo "tux ALL=(ALL:ALL) ALL" > /etc/sudoers.d/10-tux
chmod 0440 /etc/sudoers.d/10-tux
```

### 4. Desabilitando o login direto do root (Hardening de Segurança):
Com o usuário `tux` devidamente criado e o `sudo` configurado para administração, é uma boa prática de segurança (*hardening*) travar a senha da conta `root`:
```bash
passwd -dl root
```

> [!NOTE]
> **Por que é altamente recomendado desativar o login por senha direta do root?**
> 1. **Proteção contra ataques de força bruta**: Como o usuário `root` existe obrigatoriamente em todos os sistemas Unix/Linux, ele é o alvo primordial de ataques automatizados de adivinhação de senhas (especialmente se o SSH for ativado posteriormente). O parâmetro `-l` bloqueia a senha no `/etc/shadow`, rejeitando sumariamente qualquer tentativa de autenticação direta.
> 2. **Auditoria e Rastreabilidade**: Quando você executa ações administrativas com `sudo`, o systemd registra nos logs (`journalctl`) exatamente **qual usuário** disparou o comando, quando e com quais parâmetros. O login direto como root elimina essa autoria individual.
> 3. **Prevenção de acidentes catastróficos**: Usar a conta de superusuário continuamente reduz a atenção e facilita erros irreversíveis de deleção de arquivos de sistema (`rm -rf`) ou permissões corrompidas. O `sudo` força uma pausa consciente para operações de privilégio elevado.
> 4. **Sem perda de poder administrativo**: Você continua com acesso root completo sempre que precisar, bastando executar `sudo -i` ou `sudo <comando>` digitando a sua própria senha de usuário (`tux`).
> 
> *(Caso prefira manter uma senha direta de emergência exclusiva para o root no console local, você pode optar por pular este comando).*

### 5. Limpeza de arquivos temporários:
```bash
rm -f /stage3-*.tar.*
```

### 6. Saindo do Chroot e Reiniciando:
Após confirmar que as senhas foram definidas com sucesso:
```bash
exit
cd
umount -l /mnt/gentoo/dev{/shm,/pts,}
umount -R /mnt/gentoo
reboot
```
*(Remova o pendrive de instalação da porta USB)*

---

# 8. Primeiro Boot e Homologação no MOKManager

### 1. Homologando a Chave no MOKManager (Tela Azul):
Ao reiniciar com o Secure Boot ativado no setup da sua placa-mãe, o **Shim** detectará que há uma nova chave aguardando aprovação e abrirá a interface azul do **MOKManager** (*Shim UEFI key management*):

1. Pressione qualquer tecla antes do encerramento da contagem regressiva para entrar no menu.
2. Selecione a opção **Enroll MOK** e pressione Enter.
3. (Opcional) Selecione **View key 0** para inspecionar os dados do certificado gerado anteriormente (*Gentoo Kernel Signing*).
4. Selecione **Continue**.
5. Na tela que pergunta *"Enroll the key(s)?"*, selecione **Yes**.
6. Digite a **senha temporária** que você definiu no comando `mokutil --import` e pressione Enter.
7. Selecione **Reboot**.

Pronto! Agora o firmware UEFI aceita o Shim, o Shim valida o GRUB, e o GRUB carrega seu kernel e módulos com total conformidade do Secure Boot.

### 2. Fazendo Login no Terminal (TTY):
Após a inicialização, o Gentoo exibirá o prompt de texto no console:
```text
tux login: tux
Password: <digite a senha que você configurou no passwd tux>
```
*(Lembre-se: os caracteres da senha não aparecem na tela por segurança).*

> [!TIP]
> **Recuperação de Emergência (Se reiniciou sem definir senha):**
> Caso tenha esquecido de rodar `passwd` antes do reboot:
> 1. No menu do GRUB, selecione a entrada do Gentoo e pressione a tecla **`e`**.
> 2. Vá até o fim da linha que começa com `linux` e adicione `init=/bin/bash`.
> 3. Pressione `Ctrl + X` para inicializar direto no prompt do root.
> 4. Execute `mount -o remount,rw /`, defina a senha com `passwd` e reinicie com `reboot -f`.

---

---

# 9. Installing the Graphical Stack (BSPWM, Áudio e Aplicações)

Após o reboot e a entrada no sistema final instalado, instale a interface gráfica, áudio e ferramentas de usuário utilizando a organização modular de flags configuradas nos arquivos `package.use/`, `package.accept_keywords/` e `package.license/`.

### Habilitando o Repositório Comunitário GURU:
O GURU funciona de forma análoga ao AUR do Arch Linux e provê pacotes como `xsecurelock` e as fontes `nerd-fonts`.

```bash
emerge --ask app-eselect/eselect-repository dev-vcs/git
eselect repository enable guru
emaint sync -r guru
```

### 1. Servidor Gráfico (Xorg):
As flags estão definidas em `package.use/04-xorg`.

```bash
emerge --ask x11-base/xorg-server x11-drivers/xf86-input-libinput x11-apps/xinit x11-apps/xrandr x11-apps/xhost x11-apps/setxkbmap x11-misc/xdg-user-dirs
```

### 2. Subsistema de Áudio (PipeWire + WirePlumber + MPV):
As flags estão definidas em `package.use/05-audio`.

```bash
emerge --ask media-video/pipewire media-video/wireplumber media-sound/pavucontrol media-libs/libpulse media-video/mpv
```

### 3. Gerenciador de Janelas, Interface e Temas (BSPWM + SDDM):
As flags e keywords estão definidas em `package.use/06-wm-bspwm` e `package.accept_keywords/06-wm-bspwm`.

```bash
emerge --ask x11-wm/bspwm x11-misc/sxhkd x11-misc/polybar x11-misc/picom x11-misc/rofi x11-misc/dunst gui-apps/sddm x11-misc/xsecurelock lxde-base/lxappearance x11-themes/gnome-themes-standard gui-apps/qt6ct x11-misc/numlockx
```

### 4. Serviços de Sistema e Conectividade:
As flags estão definidas em `package.use/07-services`.

```bash
emerge --ask net-misc/networkmanager gnome-extra/nm-applet net-wireless/bluez net-wireless/blueman net-firewall/ufw gnome-base/gvfs sys-apps/flatpak gnome-extra/polkit-gnome app-misc/brightnessctl x11-misc/xclip x11-misc/xdg-utils x11-libs/libnotify gnome-base/dconf
```

### 5. Aplicações de Usuário:
As flags, licenças e keywords estão definidas em `package.use/08-apps`, `package.accept_keywords/08-apps` e `package.license/08-apps`.

```bash
emerge --ask www-client/firefox-bin x11-terms/kitty app-misc/yazi media-gfx/feh media-gfx/maim net-misc/yt-dlp app-misc/fastfetch app-editors/neovim app-editors/vim sys-apps/ripgrep sys-apps/fd app-arch/p7zip app-arch/zip app-arch/unzip dev-vcs/git app-admin/stow net-misc/curl net-misc/wget dev-util/github-cli
```

### 6. Tipografia e Fontes:
As flags e keywords estão definidas em `package.use/09-fonts` e `package.accept_keywords/09-fonts`.

```bash
emerge --ask media-fonts/fira-code media-fonts/noto media-fonts/noto-cjk media-fonts/noto-emoji media-fonts/nerd-fonts
```

### 7. Ativação dos Serviços:

**Serviços de Sistema (root):**
```bash
systemctl enable sddm.service
systemctl enable bluetooth.service
systemctl enable ufw.service
```

Configuração básica do firewall UFW:
```bash
ufw default deny incoming
ufw default allow outgoing
ufw --force enable
```

**Serviços de Áudio do Usuário (executar como seu usuário comum):**
```bash
systemctl --user enable --now pipewire.service pipewire-pulse.service wireplumber.service
```

### 8. Aplicando seus Dotfiles com GNU Stow:
Como o seu usuário comum (`tux`):
```bash
cd ~/dotfiles
mkdir -p ~/.config ~/.local/bin
stow bash git bspwm sxhkd picom polybar rofi kitty yazi theme dirs xsecurelock
```

---

# 10. Otimizações de Desempenho: Swap em RAM com ZRAM

Como o kernel de distribuição (`sys-kernel/gentoo-kernel`) já traz o módulo de kernel `zram` ativado por padrão e o sistema utiliza o **systemd**, a maneira mais limpa, estável e nativa de gerenciar o ZRAM é utilizando o gerador oficial **`sys-apps/zram-generator`**.

O ZRAM cria um bloco comprimido em tempo real na própria memória RAM que atua como área de swap extremamente rápida. Com isso, os dados inativos são compactados (geralmente com taxa de 2:1 a 3:1 via algoritmo `zstd`), multiplicando a capacidade utilizável da sua memória física sem a lentidão de leituras/escritas em disco.

### 1. Instalando o Gerador de ZRAM:
> [!NOTE]
> No Gentoo, o pacote oficial do Portage se chama **`sys-apps/zram-generator`** (projeto upstream `systemd/zram-generator`).

```bash
sudo emerge --ask sys-apps/zram-generator
```

### 2. Criando o arquivo de configuração:
Crie o arquivo `/etc/systemd/zram-generator.conf`:
```bash
sudo vim /etc/systemd/zram-generator.conf
```

Adicione a configuração abaixo (cria um dispositivo de tamanho equivalente a 100% da RAM física usando o algoritmo ultrarrápido `zstd` e prioridade máxima `100`):
```ini
[zram0]
zram-size = ram
compression-algorithm = zstd
swap-priority = 100
```

> [!TIP]
> **Swap Híbrido Inteligente**: Ao definir `swap-priority = 100`, o kernel sempre usará a compactação em RAM primeiro. Sua partição de 4GB em disco (`/dev/disco3`) permanece como salvaguarda secundária caso o uso de memória ultrapasse a RAM ou para hibernação.

### 3. Recarregando o systemd e iniciando o ZRAM:
```bash
sudo systemctl daemon-reload
sudo systemctl start systemd-zram-setup@zram0.service
```

### 4. Confirmando o funcionamento:
Inspecione o dispositivo criado:
```bash
zramctl
swapon --show
```
Deverá aparecer o dispositivo `/dev/zram0` ativo com o algoritmo `zstd` e prioridade `100`.

*(Nota: O `systemd-zram-generator` gera o serviço dinamicamente e ativa o `/dev/zram0` de forma 100% automática a cada boot — não é necessário rodar `systemctl enable`).*

### 5. Ajuste fino de desempenho (`vm.swappiness`):
Como o ZRAM é executado na RAM e sua compressão é ordens de grandeza mais rápida que a escrita em disco, é recomendado instruir o kernel a ser mais agressivo na compactação de páginas anônimas antes de tentar descartar caches úteis de arquivos:

```bash
echo "vm.swappiness = 180" | sudo tee /etc/sysctl.d/99-zram.conf
sudo sysctl --system
```

Verifique se o parâmetro foi aplicado com sucesso:
```bash
cat /proc/sys/vm/swappiness
```
*(O retorno deve ser `180`).*

---

# 11. Final System Update and Cleanup (@world)

Após a conclusão da instalação da interface gráfica, serviços, aplicativos e configuração do ZRAM, execute uma atualização e recompilação final preventiva do conjunto `@world`.

Este procedimento garante que:
- Quaisquer pacotes cujas flags foram modificadas ou adicionadas no `package.use/` durante a instalação sejam devidamente recompilados para aplicar as novas opções.
- Todas as dependências do sistema fiquem 100% alinhadas com as flags globais (`00-core`).
- Bibliotecas antigas ou dependências temporárias de compilação sejam removidas de forma limpa.

### 1. Recompilação profunda com as novas flags:
```bash
sudo emerge --ask --verbose --update --deep --changed-use @world
```

### 2. Remoção de dependências órfãs e limpeza:
```bash
sudo emerge --ask --depclean
```

### 3. Recompilação preventiva de bibliotecas preservadas (se houver):
```bash
sudo emerge @preserved-rebuild
```

---

# 12. Guia Rápido de Comandos e Manutenção do Gentoo (Portage Cheat Sheet)

Um guia prático com os comandos e fluxos essenciais para o dia a dia e manutenção contínua do seu Gentoo Linux.

---

### 1. Tabela de Parâmetros Mais Usados do `emerge`

| Opção Longa | Opção Curta | Descrição |
| :--- | :---: | :--- |
| `--ask` | `-a` | Exibe o plano de instalação detalhado e solicita confirmação antes de compilar. |
| `--verbose` | `-v` | Mostra detalhes completos das USE flags (habilitadas, desabilitadas e novas). |
| `--pretend` | `-p` | Simula a execução sem baixar ou instalar nada (dry-run). |
| `--update` | `-u` | Atualiza os pacotes especificados para a versão mais recente. |
| `--deep` | `-D` | Considera toda a árvore de dependências (não apenas dependências diretas). |
| `--newuse` | `-N` | Recompila pacotes cujas USE flags foram alteradas desde a última compilação. |
| `--oneshot` | `-1` | Instala o pacote sem gravá-lo no arquivo `@world` (ideal para dependências temporárias). |
| `--depclean` | `-c` | Remove pacotes e dependências órfãs não mais referenciadas no `@world`. |

---

### 2. Sincronização dos Repositórios
Mantenha a árvore do Portage e seus repositórios sincronizados:

```bash
# Sincroniza todos os repositórios configurados (gentoo oficial, guru, etc.):
emaint sync -a

# Alternativa clássica:
emerge --sync
```

---

### 3. Busca e Inspeção de Pacotes
Antes de instalar, investigue quais pacotes existem e quais flags estão disponíveis:

```bash
# Buscar por nome de pacote:
emerge --search firefox

# Buscar por palavra-chave na descrição:
emerge --searchdesc "terminal emulator"

# Simular instalação inspecionando detalhadamente as USE flags:
emerge -pv kitty

# Ver explicação detalhada de cada USE flag do pacote (via gentoolkit):
equery uses media-video/pipewire

# Descobrir a qual pacote pertence determinado arquivo no sistema:
equery belongs /usr/bin/bspwm

# Listar todos os arquivos instalados por um pacote:
equery files x11-wm/bspwm
```

---

### 4. Instalação e Remoção

```bash
# Instalar um pacote (adicionando ao conjunto @world):
sudo emerge --ask x11-terms/kitty

# Instalar sem registrar no @world (ideal para ferramentas de compilação pontuais):
sudo emerge --ask --oneshot app-portage/cpuid2cpuflags

# Desinstalar um pacote específico e limpar dependências desnecessárias:
sudo emerge --ask --depclean x11-terms/kitty
```

---

### 5. Atualização Completa do Sistema (`@world`)
A rotina clássica e recomendada de atualização periódica do Gentoo:

```bash
# 1. Sincronizar os repositórios:
emaint sync -a

# 2. Ler notícias de segurança ou intervenções manuais anunciadas pelos desenvolvedores:
eselect news read

# 3. Atualizar todos os pacotes do sistema com dependências profundas e novas flags:
sudo emerge --ask --verbose --update --deep --newuse @world

# 4. Remover bibliotecas e pacotes órfãos deixados por atualizações:
sudo emerge --ask --depclean

# 5. Recompilar pacotes que dependem de bibliotecas atualizadas (se houver):
sudo emerge @preserved-rebuild
```

---

### 6. Gerenciamento de Arquivos de Configuração (`/etc/`)
Quando uma atualização traz mudanças em arquivos de `/etc/`, o Portage não sobrescreve suas edições pessoais. Em vez disso, ele cria arquivos protegidos `._cfg0000_<nome>`.

```bash
# Ferramenta interativa recomendada para revisar diffs e mesclar arquivos:
sudo dispatch-conf
# Teclas no dispatch-conf:
#   'u' = usar o novo arquivo fornecido pelo pacote
#   'z' = manter o seu arquivo atual (descartar o novo)
#   'm' = mesclar manualmente as diferenças (merge)

# Alternativa nativa clássica:
sudo etc-update
```

---

### 7. Comandos Essenciais do `eselect`
O `eselect` gerencia módulos, links simbólicos e componentes do sistema:

```bash
# Listar e selecionar perfis do sistema:
eselect profile list
sudo eselect profile set <numero>

# Gerenciar repositórios adicionais (overlays):
eselect repository list
sudo eselect repository enable guru
emaint sync -r guru

# Ler avisos e comunicados importantes do Gentoo:
eselect news list
eselect news read
```



