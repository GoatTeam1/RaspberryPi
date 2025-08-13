#!/usr/bin/env bash
# Bloquea todo egreso excepto DNS(53), NTP(123) y email/webhook (587/443). Ejecuta en el host.
set -e
sudo iptables -P OUTPUT DROP
sudo iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
sudo iptables -A OUTPUT -p udp --dport 123 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --dport 587 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -A OUTPUT -o lo -j ACCEPT
echo "Egreso endurecido. Verifica que tus alertas aún salen."
