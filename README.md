Baseado no Amd64Handbook do Gentoo. Utilizando Systemd ao invés de OpenRC.

# Preparing the disks

| Partição | Tamanho | Ponto Inicial | Ponto Final |
| :------: | :-----: | :-----------: | :---------: |
| /boot/efi | 512MB | 1 | 513 |
| /boot | 1024MB | 513 | 1537 |
| swap | 4096MB | 1537 | 5633 |
| / | 30720MB | 5633 | 36353 |
| /var | 40960MB | 36353 | 77313 |
| /home | -1 | 77313 | -1 |

**Comandos para partição:**
- ` wipefs -a /dev/disco ` - Remove assinaturas antigas.
- ` sgdisk --zap-all /dev/disco ` - Zera a tabela de partições.
- ` partprobe /dev/disco ` - Informa o Kernel da remoção das partições.
- ` parted -a optimal /dev/disco ` - Abre a sessão de edição do parted.
    - ` mklabel gpt ` - Cria tabela de partições GPT.
    - ` unit mib ` - Define o formato que vai ser utilizado.
    - ` mkpart efi fat32 1 513 ` - /boot/efi com 512MB.
    - ` set 1 esp on ` - Flag obrigatória para UEFI. Serve para identificar a partição correta onde oestão os bootloaders.
    - ` set 1 boot on ` - Flag opcional para compatibilidade com alguns firmwares.
    - ` mkpart boot ext4 513 1537 ` - /boot com 1GB.
    - ` mkpart swap linux-swap 1537 5633 ` - swap com 4GB.
    - ` mkpart rootfs ext4 5633 36353 ` - / com 30GB.
    - ` mkpart var ext4 36353 77313 ` - /var com 20GB.
    - ` mkpart home ext4 77313 -1` - /home com tudo que restou.
    - ` print ` - Exibe as partições definidas.
    - ` quit ` - Sai do parted.

**Comandos para formatação:**
- ` lsblk ` - Serve para verificar as partições dos disco.
- ` mkfs.fat -F32 -n EFI /dev/disco1 ` - Formata a partição efi com fat32.
- ` mkfs.ext4 -L BOOT /dev/disco2 ` - Formata a partição boot com ext4.
- ` mkswap -L SWAP /dev/disco3 ` - Formata a partição swap como swap.
- ` swapon /dev/disco3 ` - Ativa o swap utilizando a partição swap.
- ` mkfs.ext4 -L ROOTFS /dev/disco4 ` - Formata a partição rootfs com ext4.
- ` mkfs.ext4 -L VAR /dev/disco5 ` - Formata a partição var com ext4.
- ` mkfs.ext4 -L HOME /dev/disco6 ` - Formata a partição home com ext4.

Ainda não sei como montar na mão partições com btrfs, e swap em zram.

# Installing the Gentoo installation files

**Montando as partições:**
- ` mkdir --parents /mnt/gentoo ` - ...
- ` cd /mnt/gentoo ` - ...
- ` mount /dev/disco4 /mnt/gentoo` - ...
- ` mkdir boot var home ` - ...
- ` mount /dev/disco2 /mnt/gentoo/boot` - ...
- ` mkdir boot/efi ` - ...
- ` mount /dev/disco1 /mnt/gentoo/boot/efi` - ...
- ` mount /dev/disco5 /mnt/gentoo/var` - ...
- ` mount /dev/disco6 /mnt/gentoo/home` - ...

**Baixando e extraindo:**
- ` links https://www.gentoo.org/downloads/ ` - ...
- ` tar xpvf stage3.tar.xz --xattrs-include='*.*' --numeric-owner ` - ...

**Verificando a hora:**
- ` date ` - Vê o horário.
- ` chronyd -q ` - Sincroniza o horário. net-misc/chrony

Se não tiver acesso a internet dá pra usar o:

- ` date 100313162021 ` - Pra setar a data nesse formato: MMDDhhmmYYYY.

**Verificando a integridade da imagem:**
- ` gpg --import /usr/share/openpgp-keys/gentoo-release.asc ` - ...
- ` openssl dgst -r -sha512 stage3-amd64-<release>-<init>.tar.xz ` - ...
- ` sha256sum --check stage3-amd64-<release>-<init>.tar.xz.sha256.verified ` - ...

# Installing the Gentoo base system

**Make.conf:**
- ` git clone https://github.com/Julio-C-Oliveira/pessoal_gentoo.git /mnt/gentoo/home/pessoal_gentoo ` - Nesse repositório tem um make.conf que define os parâmetros gerais do portage.
- ` cp /mnt/gentoo/home/pessoal_gentoo/make.conf /mnt/gentoo/etc/portage/make.conf ` 
- ` ` - Quero adicionar nos meus dotfiles USE FLAGS para cada pacote, ao invés de utilizar as globais. Aqui vai ficar o comando para copiar ass flags, ou usar o stow pra isso.

Desative a flag dist-kernel no USE FLAGS global.

Pegou logo o make.conf porque depois vai ter o chroot.

**Chroot:**
- ` cp --dereference /etc/resolv.conf /mnt/gentoo/etc/ ` - ...
- ` mount --types proc /proc /mnt/gentoo/proc ` - ...
- ` mount --rbind /sys /mnt/gentoo/sys ` - ...
- ` mount --make-rslave /mnt/gentoo/sys ` - ...
- ` mount --rbind /dev /mnt/gentoo/dev ` - ...
- ` mount --make-rslave /mnt/gentoo/dev ` - ...
- ` mount --bind /run /mnt/gentoo/run ` - ...
- ` mount --make-slave /mnt/gentoo/run ` - ...
- ` ls -ld /dev/shm ` - ...

Se o shm for um link simbólico:
- ` test -L /dev/shm && rm /dev/shm && mkdir /dev/shm ` - ... 
- ` mount --types tmpfs --options nosuid,nodev,noexec shm /dev/shm ` - ... 
- ` chmod 1777 /dev/shm /run/shm ` - ... 

Caso não seja:
- ` chroot /mnt/gentoo /bin/bash ` - ...
- ` source /etc/profile ` - ...
- ` export PS1="(chroot) ${PS1}" ` - ...

**Configurando o Portage:**
- ` emerge-webrsync ` - ...
- ` emerge --ask --verbose --oneshot app-portage/mirrorselect ` - Um utilitário pra selecionar os mirrors.
- ` mirrorselect -i -o >> /etc/portage/make.conf ` - Salva os resultados no make.conf.
- ` emerge --sync ` - Atualiza o repositório de ebuild.

**Selecionando o profile:**
- ` eselect profile list ` - Seleciona o que tiver igual o teu stage3 file.
- ` eselect profile set 5 ` - Selecione o seu.
- ` eselect profile list ` - Verifique se foi alterado com sucesso.

**Configurando USE flags:**
- ` emerge --info | grep ^USE ` - Serve para ver quais estão ativas no momento.
- ` less /var/db/repos/gentoo/profiles/use.desc ` - Uma forma de ver as USE flags.

**Configurando CPU Flags:**
- ` emerge --ask --oneshot app-portage/cpuid2cpuflags ` - Serve para ver as flags aceitas pela cpu.
- ` cpuid2cpuflags ` - ...
- ` echo "*/* $(cpuid2cpuflags)" > /etc/portage/package.use/00-core ` - ...

**Configurando o video cards:**
- ` emerge --ask app-editors/vim ` - Um editor de texto.
- ` emerge --ask --oneshot sys-apps/pciutils ` - Um utilitário.
- ` lspci -k | grep -A 3 -i "VGA" ` - ...
- `  vim /etc/portage/package.use/00-core ` - Adicione ou altere a área de GPU para a correta. Nesse formato:
```
*/* VIDEO_CARDS: -* intel
```

| GPU |	VIDEO_CARDS |
:-: | :---------:
(Official) Nvidia Maxwell and newer	| nvidia 
Nouveau Nvidia Supported list |	nouveau
AMD since Sea Islands |	amdgpu radeonsi
ATI and older AMD |	See radeon#Feature support
Intel Nehalem and newer	| intel
Intel Gen 2 and 3 Supported list | intel i915 |
QEMU/KVM | virgl |
WSL | d3d12 

Se tá em dúvida vai no site do Gentoo.

**Configure as licenças no Make.conf:**
- ` vim /etc/portage/make.conf ` - Lá tem a váriavel ACCEPT_LICENSE.

Para definir a licença individualmente por pacote use:

- ` mkdir /etc/portage/package.license ` - Nessa pasta ficam os arquivos que liberam licenças para apps especificos.

Ex:
- ` /etc/portage/package.license/kernel ` - Criar um arquivo lá, definir os pacotes e ao lado as licenças aceitas para ele.
```
app-arch/unrar unRAR
sys-kernel/linux-firmware linux-fw-redistributable
sys-firmware/intel-microcode intel-ucode
```

**Instalando um utilitário:**
- ` emerge --ask app-portage/gentoolkit ` - Um utilitário de USE flags.
- ` equery uses <nome-do-pacote> ` - Verifica quais flags um pacote tem.
- ` eclean-dist --deep ` - Limpa binários antigos.

**Atualizando o @World:**
- ` emerge --ask --verbose --update --deep --changed-use @world ` - Atualiza o worl.
- ` emerge --ask --pretend --depclean ` - Mostra pacotes orfãos, tipo o cpuid2cpuflags que foi instalado com a flag oneshot. 
- ` emerge --noreplace categoria/nome-do-pacote ` - Caso queira manter algum dos citados.
- ` emerge --ask --depclean ` - Remove os pacotes orfãos.

**Timezone:**
- ` ls -l /usr/share/zoneinfo ` - ...
- ` ls -l /usr/share/zoneinfo/America/ ` - ...
- ` ln -sf ../usr/share/zoneinfo/America/Belem /etc/localtime ` - ...

**Locale generation:**
- ` vim /etc/locale.gen ` - Busque pt-br e descomente.
- ` locale-gen ` - Gere.
- ` eselect locale list ` - Veja qual o número do seu locale.
- ` eselect locale set 2 ` - Selecione ele.
- ` env-update && source /etc/profile && export PS1="(chroot) ${PS1}" ` - Atualiza o ambiente.

# Configuring the Linux kernel
**Instalando firmwares e microcode:**
- ` vim  /etc/portage/package.use/01-kernel  ` - Definir as USE Flags para o linux-firmware.
```
sys-kernel/installkernel-65 dracut grub
```
- ` emerge --ask sys-kernel/linux-firmware ` - Linux firmwares.
- ` emerge --ask sys-firmware/sof-firmware ` - Firmwares de áudio para hardwares mais novos.
- ` emerge --ask sys-firmware/intel-microcode ` - Os microcodes da AMD já vem com o linux-firmwares, porém os da intel vem separadamente.

**Instalando o installkernel:**
- ` vim  /etc/portage/package.use/01-kernel  ` - Definir as USE Flags para o installkernel.
```
sys-kernel/installkernel grub dracut
```
- ` mkdir /etc/dracut.conf.d ` - ...
- ` lsblk ` - Ver as partições.
- ` blkid ` - Ver o UUID das partições.
- ` vim /etc/dracut.conf.d/00-installkernel.conf` - Instruir o dracut sobre em qual partição está a raiz.
```
kernel_cmdline=" root=UUID=2122cd72-94d7-4dcc-821e-3705926deecc " # Note leading and trailing spaces
```
- ` emerge --ask sys-kernel/installkernel ` - Instala uma interface que facilita algumas operações com o kernel.

**Signed kernel modules:**

- ` vim /etc/portage/package.use/kernel  ` - ...
```
sys-kernel/gentoo-kernel modules-sign secureboot
```

Verifique  se os caminhos das chaves já estão definidos no seu make.conf

- ` mkdir -p /etc/portage/certs ` - ...
- ` cd /etc/portage/certs ` - ...
- ` openssl req -new -noenc -utf8 -sha256 -x509 -outform PEM -out kernel_key.pem -keyout kernel_key.pem ` - ...
- ` chown root:root kernel_key.pem ` - ...
- ` chmod 400 kernel_key.pem ` - ...

**Instalando o Kernel:**
- ` emerge --ask sys-kernel/gentoo-kernel ` - ...
- ` emerge --depclean ` - ...

Se quiser pode rodar o:
- ` emerge --prune sys-kernel/gentoo-kernel ` - Serve para limpar versões antigas do kernel.

Ative a flag dist-kernel no USE FLAGS global.

- ` emerge --ask @module-rebuild ` - Recompila os módulos para se adaptarem ao novo kernel.

Se você instalou algum módulo que precise ser carregado no initframs:

- ` emerge --config sys-kernel/gentoo-kernel ` - ...

# Configuring the system

**Configurando o fstab:**
- ` lsblk ` - Ver as partições.
- ` blkid ` - Ver o UUID das partições.

The first field shows the block special device or remote filesystem to be mounted. Several kinds of device identifiers are available for block special device nodes, including paths to device files, filesystem labels and UUIDs, and partition labels and UUIDs.

The second field shows the mount point at which the partition should be mounted.

The third field shows the type of filesystem used by the partition.

The fourth field shows the mount options used by mount when it wants to mount the partition. As every filesystem has its own mount options, so system admins are encouraged to read the mount man page (man mount) for a full listing. Multiple mount options are comma-separated.

The fifth field is used by dump to determine if the partition needs to be dumped or not. This can generally be left as 0 (zero).

The sixth field is used by fsck to determine the order in which filesystems should be checked if the system wasn't shut down properly. The root filesystem should have 1 while the rest should have 2 (or 0 if a filesystem check is not necessary).

- ` vim /etc/fstab` - ...

Ex:
```
# <device>               <mount>      <type>  <options>             <dump> <pass>
UUID=XXXX-XXXX           /boot/efi    vfat    defaults,noatime,umask=0077  0 2
UUID=XXXX-XXXX           /boot        ext4    defaults,noatime             0 2
UUID=XXXX-XXXX           /            ext4    defaults,noatime             0 1
UUID=XXXX-XXXX           /var         ext4    defaults,noatime             0 2
UUID=XXXX-XXXX           /home        ext4    defaults,noatime             0 2
UUID=XXXX-XXXX           none         swap    sw                           0 0
```

Recomendo o defaults,noatime inicialmente. Depois lê a documentação do mount.

**Definir o hostname:**
- ` echo tux > /etc/hostname ` - ...

**Configurando a rede:**
- ` vim /etc/portage/package.use/network ` - ...
```
net-wireless/wpa_supplicant dbus
```
- ` emerge --ask net-misc/networkmanager ` - ...
- ` systemctl enable NetworkManager ` - ...
- ` emerge --ask net-wireless/iw net-wireless/wpa_supplicant ` - ...

**Editando o hostfile:**
- ` vim /etc/hosts  ` - ...
```
FILE /etc/hostsFilling in the networking information
# This defines the current system and must be set
127.0.0.1     tux.homenetwork tux localhost
::1           tux.homenetwork tux localhost

# Optional definition of extra systems on the network
192.168.0.5   jenny.homenetwork jenny
192.168.0.6   benny.homenetwork benny
```

**Informações do sistema:**
- ` passwd ` - Define a senha do root.

**Configuração de boot e de init:**
- ` systemd-machine-id-setup ` - ...
- ` systemd-firstboot --prompt ` - ...
- `  systemctl preset-all --preset-mode=enable-only` - ...

**Indexação de arquivos:**
- ` emerge --ask sys-apps/mlocate ` - ...

**Auto complete no bash:**
- ` emerge --ask app-shells/bash-completion ` - ...

**Sincronização de horário:**
- ` emerge --ask net-misc/chrony ` - ...
- ` systemctl enable chronyd.service ` - ...

**filesystem tools:**
- ` emerge --ask sys-block/io-scheduler-udev-rules ` - ...

# Configuring the bootloader

**Emerge:**
- ` emerge --ask --verbose sys-boot/grub sys-boot/shim sys-boot/mokutil sys-boot/efibootmgr ` - ...
- ` vim /etc/portage/make.conf ` - Edite a plataforma  do grub de acordo com o seu sistema.
```
GRUB_PLATFORMS="efi-64"
```
- ` emerge sys-boot/grub sys-boot/shim sys-boot/mokutil sys-boot/efibootmgr ` - ...

**Instalação:**
- ` mkdir -p /boot/efi/EFI/Gentoo ` - ...
```
cp /usr/share/shim/BOOTX64.EFI /boot/efi/EFI/Gentoo/shimx64.efi
cp /usr/share/shim/mmx64.efi /boot/efi/EFI/Gentoo/mmx64.efi
cp /usr/lib/grub/grub-x86_64.efi.signed /boot/efi/EFI/Gentoo/grubx64.efi
```
- ` cd /boot/efi/EFI/Gentoo ` - ...
- ` openssl x509 -in /etc/portage/certs/kernel_key.pem -inform PEM -out /etc/portage/certs/kernel_key.der -outform DER ` - ...
- ` mokutil --import /etc/portage/certs/kernel_key.der ` - ...
- ` efibootmgr --create --disk /dev/boot-disk --part boot-partition-id --loader '\EFI\Gentoo\shimx64.efi' --label 'GRUB via Shim' --unicode ` - ...

**Configurando o Grub:**
- ` grub-mkconfig -o /boot/efi/EFI/Gentoo/grub.cfg  ` - ...
- ` vim /etc/env.d/99grub ` - ...
```
GRUB_CFG=/boot/efi/EFI/Gentoo/grub.cfg
```
- ` env-update ` - ...

**Reboot:**
- ` exit ` - ...
- ` cd ` - ...
- ` umount -l /mnt/gentoo/dev{/shm,/pts,} ` - ...
- ` umount -R /mnt/gentoo ` - ...
- ` reboot ` - Remova o pendrive  de instalação antes.

# Finalizing
- ` useradd -m -G users,wheel,audio,video,input -s /bin/bash tux  ` - ...
- ` passwd tux ` - ...

**Sudo:**
- ` emerge --ask app-admin/sudo ` - ...
- ` echo "tux ALL=(ALL:ALL) ALL" > /etc/sudoers.d/10-tux ` - Configurando o sudoers.
- ` chmod 0440 /etc/sudoers.d/10-tux ` - ...

**Instalando um utilitário para ver as flags e dando o rebuild final:**
- ` app-portage/gentoolkit ` - ...
- ` emerge --ask --verbose --update --deep --newuse --with-bdeps=y @world ` - ...

**Desabilitando o login root:**
- ` passwd -dl root ` - ...

**Limpando remanecentes:**
- ` rm /stage3-*.tar.* ` - ...

End

Aumentar a /var para 30GB+ pra evitar o parallelism reduced.

Testando o vmware para video card

Pode ser uma boa adicionar o grub as flags do linux-firmware