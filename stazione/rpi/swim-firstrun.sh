#!/bin/bash
# SwimTimer: configurazione di riserva (Wi-Fi, SSH, utente) senza cloud-init.
B=/boot/firmware
LOG=$B/diag-firstrun.txt
exec >"$LOG" 2>&1
UD=$B/user-data
SSID=$(sed -n "/con-name, wifi-1/s/.*, ssid, \([^,]*\),.*/\1/p" "$UD")
P1=$(sed -n "/con-name, wifi-1/s/.*wifi-sec.psk, '\(.*\)' \]\s*$/\1/p" "$UD")
P2=$(sed -n "/con-name, wifi-2/s/.*wifi-sec.psk, '\(.*\)' \]\s*$/\1/p" "$UD")
PP=$(sed -n "s/^\s*plain_text_passwd:\s*//p" "$UD" | tr -d '\r')
set +x
echo "lunghezze: wifi1=${#P1} wifi2=${#P2} pi=${#PP}"
set -x
id swim || useradd -m -s /bin/bash -G users,adm,dialout,audio,netdev,video,plugdev,input,gpio,spi,i2c,render,sudo swim
set +x
[ -n "$PP" ] && echo "swim:$PP" | chpasswd
set -x
echo 'swim ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/010_swim && chmod 440 /etc/sudoers.d/010_swim
install -d -m 700 -o swim -g swim /home/swim/.ssh
grep -o 'ssh-ed25519 [^ ]* [^ ]*' "$UD" | head -1 > /home/swim/.ssh/authorized_keys
chown swim:swim /home/swim/.ssh/authorized_keys; chmod 600 /home/swim/.ssh/authorized_keys
systemctl enable ssh
echo swimtimer-pi > /etc/hostname
sed -i 's/127.0.1.1.*/127.0.1.1\tswimtimer-pi/' /etc/hosts
raspi-config nonint do_wifi_country IT || true
for f in /var/lib/systemd/rfkill/*:wlan; do echo 0 > "$f"; done
D=/etc/NetworkManager/system-connections
mkdir -p $D; rm -f $D/wifi-1.nmconnection $D/wifi-2.nmconnection
mk() { # nome priorita password (chiamare con set +x); SSID letto da user-data
cat > $D/$1.nmconnection <<EOF
[connection]
id=$1
uuid=$(cat /proc/sys/kernel/random/uuid)
type=wifi
autoconnect=true
autoconnect-priority=$2
[wifi]
mode=infrastructure
ssid=$SSID
[wifi-security]
key-mgmt=wpa-psk
psk=$3
[ipv4]
method=auto
[ipv6]
method=auto
EOF
chmod 600 $D/$1.nmconnection
}
set +x
mk wifi-1 10 "$P1"
mk wifi-2 5 "$P2"
set -x
ls -l $D
# diagnosi a ogni avvio, salvata sulla SD
cat > /usr/local/bin/swim-diag.sh <<'EOF'
#!/bin/bash
sleep 45
{ date; hostname; nmcli -t dev; nmcli -t -f NAME,DEVICE con show --active; ip -4 -br a; systemctl is-active ssh; journalctl -b -u NetworkManager --no-pager | grep -v -i psk | tail -40; } > /boot/firmware/diag.txt 2>&1
EOF
chmod 755 /usr/local/bin/swim-diag.sh
cat > /etc/systemd/system/swim-diag.service <<'EOF'
[Unit]
Description=SwimTimer diagnosi rete su /boot/firmware/diag.txt
After=NetworkManager.service
[Service]
Type=oneshot
ExecStart=/usr/local/bin/swim-diag.sh
[Install]
WantedBy=multi-user.target
EOF
systemctl enable swim-diag.service
ls -l /etc/cloud/cloud-init.disabled 2>/dev/null; cloud-init status --long 2>/dev/null | head -5
sed -i 's| systemd.run=[^ ]*||; s| systemd.run_success_action=[^ ]*||; s| systemd.unit=kernel-command-line.target||' $B/cmdline.txt
rm -f $B/swim-firstrun.sh
sync
exit 0
