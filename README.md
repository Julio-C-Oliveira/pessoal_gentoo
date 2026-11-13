# Guia de Instalação do Gentoo Linux

Tutorial de instalação do Gentoo Linux baseado no Amd64 Handbook oficial, utilizando **Systemd**, **Distribution Kernel** (`sys-kernel/gentoo-kernel`) e inicialização segura via **UEFI Secure Boot** com **Shim + GRUB + MOK**.

---

## Organização Modular do `/etc/portage/package.use/`

No Gentoo, as flags de compilação por pacote (`USE flags`) podem ser definidas em um único arquivo `/etc/portage/package.use` ou, preferencialmente, dentro de um diretório modular `/etc/portage/package.use/`.

O uso de um **diretório** é a prática recomendada:
- **Ordem lexicográfica de leitura**: O Portage lê todos os arquivos contidos no diretório em ordem alfabética/numérica (`00-` é lido antes de `01-`). Se houver regras conflitantes para um mesmo pacote, a regra do arquivo lido por último prevalece.
- **Manutenção simplificada**: Cada arquivo agrupa pacotes de uma camada lógica do sistema.

### Estrutura adotada neste repositório:
- `00-core`: Flags de arquitetura de CPU (`CPU_FLAGS_X86`) geradas pelo `cpuid2cpuflags`, placas de vídeo e pacotes essenciais do sistema base.
- `01-kernel`: Flags dos pacotes do kernel (`sys-kernel/gentoo-kernel`, `sys-kernel/installkernel`, `sys-kernel/linux-firmware`), assinaturas (`modules-sign`, `secureboot`) e a flag `*/* dist-kernel`.
- `02-network`: Conectividade e gerenciamento de rede (`net-misc/networkmanager`, `net-wireless/wpa_supplicant`).
- `03-bootloader`: Carregador de inicialização e assinatura EFI (`sys-boot/grub`, `sys-boot/shim`).

> [!TIP]
> **Sugestões para expansão futura**:
> - `04-desktop`: Servidor gráfico (Wayland/X11), áudio (`pipewire`), fontes e bibliotecas gráficas.
> - `05-apps`: Navegadores, editores de código e aplicações de usuário final.

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
```

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

Confira se o arquivo `/etc/portage/package.use/01-kernel` contém as flags de assinatura e o suporte a módulos do kernel distribuído:
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
systemd-firstboot --prompt
```

### Reiniciando o sistema:
```bash
exit
cd
umount -l /mnt/gentoo/dev{/shm,/pts,}
umount -R /mnt/gentoo
reboot
```
*(Remova o pendrive de instalação da porta USB)*

---

# 7. Primeiro Boot: Homologando a Chave no MOKManager

Ao reiniciar com o Secure Boot ativado no setup da sua placa-mãe, o **Shim** detectará que há uma nova chave aguardando aprovação e abrirá a interface azul do **MOKManager** (*Shim UEFI key management*):

1. Pressione qualquer tecla antes do encerramento da contagem regressiva para entrar no menu.
2. Selecione a opção **Enroll MOK** e pressione Enter.
3. (Opcional) Selecione **View key 0** para inspecionar os dados do certificado gerado anteriormente (*Gentoo Kernel Signing*).
4. Selecione **Continue**.
5. Na tela que pergunta *"Enroll the key(s)?"*, selecione **Yes**.
6. Digite a senha temporária que você definiu no comando `mokutil --import` e pressione Enter.
7. Selecione **Reboot**.

Pronto! Agora o firmware UEFI aceita o Shim, o Shim valida o GRUB, e o GRUB carrega seu kernel e módulos com total conformidade do Secure Boot.

---

# 8. Finalizing

### Criando o usuário padrão e configurando o sudo:
```bash
useradd -m -G users,wheel,audio,video,input -s /bin/bash tux
passwd tux

emerge --ask app-admin/sudo
echo "tux ALL=(ALL:ALL) ALL" > /etc/sudoers.d/10-tux
chmod 0440 /etc/sudoers.d/10-tux
```

### Desabilitando o login direto do root:
```bash
passwd -dl root
```

### Limpeza final e recompilação preventiva:
```bash
rm -f /stage3-*.tar.*
emerge --ask --verbose --update --deep --newuse --with-bdeps=y @world
```
